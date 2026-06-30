"""
Logica carte collezionabili: bustine, reliquiario, collezione.
"""
from __future__ import annotations

import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    AperturaBustinaCarte,
    BustinaCarte,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    CARTA_ENERGIE_NATURALI,
    CARTA_ENERGIE_SOPRANNATURALI,
    CARTA_FONTE_BUSTINA,
    CARTA_RARITA_CHOICES,
    CARTA_RARITA_COMUNE,
    CARTA_RARITA_RARA,
    CARTA_RARITA_UNICA,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTA_ENERGIA_AURA_SIGLA,
    EspansioneCarte,
    KeywordCarta,
    MAZZI_DUELLO_MAX_PER_PG,
    MAZZO_DUELLO_SIZE,
    MazzoDuello,
    RELIQUIARIO_SLOTS,
    ReliquiarioSlot,
)
from personaggi.models import MODIFICATORE_ADDITIVO, Personaggio, Statistica

RARITA_ORDINE = {code: idx for idx, (code, _) in enumerate(CARTA_RARITA_CHOICES)}


def _decimal2(val) -> Decimal:
    return Decimal(str(val)).quantize(Decimal("0.01"))


def get_config_carte(campagna, *, create: bool = False) -> ConfigurazioneCarteCollezionabili | None:
    if create:
        cfg, _ = ConfigurazioneCarteCollezionabili.objects.get_or_create(campagna=campagna)
        return cfg
    return ConfigurazioneCarteCollezionabili.objects.filter(campagna=campagna).first()


def get_carte_accesso_modo(campagna) -> str:
    cfg = get_config_carte(campagna, create=False)
    if not cfg:
        return CARTE_ACCESSO_OFF
    modo = getattr(cfg, "accesso_modo", None) or CARTE_ACCESSO_OFF
    if modo == CARTE_ACCESSO_OFF and getattr(cfg, "abilitata", False):
        return CARTE_ACCESSO_OPEN
    return modo


def is_png_staff_personaggio(personaggio: Personaggio) -> bool:
    return bool(
        personaggio.tipologia_id
        and personaggio.tipologia
        and not personaggio.tipologia.giocante
    )


def personaggio_puo_accedere_carte(personaggio: Personaggio) -> bool:
    modo = get_carte_accesso_modo(personaggio.campagna)
    if modo == CARTE_ACCESSO_OPEN:
        return True
    if modo == CARTE_ACCESSO_TEST:
        return is_png_staff_personaggio(personaggio)
    return False


def is_carte_collezionabili_abilitate(campagna) -> bool:
    """Compat: True se OPEN o TEST (non implica accesso PG)."""
    return get_carte_accesso_modo(campagna) != CARTE_ACCESSO_OFF


def assert_personaggio_puo_accedere_carte(personaggio: Personaggio):
    if not personaggio_puo_accedere_carte(personaggio):
        modo = get_carte_accesso_modo(personaggio.campagna)
        if modo == CARTE_ACCESSO_TEST:
            raise ValidationError("Le carte sono in testing: accesso solo per PnG staff.")
        raise ValidationError("Le carte collezionabili non sono attive in questa campagna.")


# Alias retrocompatibilità
assert_carte_abilitate = assert_personaggio_puo_accedere_carte


def _pool_carte(bustina: BustinaCarte):
    qs = CartaCollezionabile.objects.filter(
        campagna_id=bustina.campagna_id,
        attiva=True,
    )
    if bustina.espansione_id:
        qs = qs.filter(espansione_id=bustina.espansione_id)
    elif bustina.set_collezione:
        qs = qs.filter(set_collezione=bustina.set_collezione)
    return list(qs)


def _carta_unica_gia_posseduta(carta: CartaCollezionabile) -> bool:
    if carta.rarita != CARTA_RARITA_UNICA:
        return False
    return CartaPosseduta.objects.filter(carta_id=carta.id).exists()


def _roll_rarita(probabilita: dict[str, float]) -> str:
    roll = random.random()
    cumulative = 0.0
    for code, _label in CARTA_RARITA_CHOICES:
        cumulative += probabilita.get(code, 0.0)
        if roll <= cumulative:
            return code
    return CARTA_RARITA_COMUNE


def _scegli_carta_da_pool(pool: list[CartaCollezionabile], rarita: str) -> CartaCollezionabile | None:
    candidates = [c for c in pool if c.rarita == rarita and not _carta_unica_gia_posseduta(c)]
    if not candidates:
        # Fallback: qualsiasi carta disponibile non unica già presa
        candidates = [c for c in pool if not _carta_unica_gia_posseduta(c)]
    if not candidates:
        return None
    return random.choice(candidates)


def _conteggio_bustine_oggi(personaggio: Personaggio) -> int:
    oggi = timezone.localdate()
    return AperturaBustinaCarte.objects.filter(
        personaggio=personaggio,
        created_at__date=oggi,
    ).count()


def _conteggio_pity(personaggio: Personaggio, bustina: BustinaCarte) -> int:
    """Bustine consecutive senza Rara+ per questa bustina."""
    aperture = (
        AperturaBustinaCarte.objects.filter(personaggio=personaggio, bustina=bustina)
        .order_by("-created_at")[:50]
    )
    count = 0
    for apr in aperture:
        ids = apr.carte_ottenute_ids or []
        carte = CartaCollezionabile.objects.filter(
            possessioni__id__in=ids,
        ).values_list("rarita", flat=True)
        if any(RARITA_ORDINE.get(r, 0) >= RARITA_ORDINE[CARTA_RARITA_RARA] for r in carte):
            break
        count += 1
    return count


def _serializza_espansione(esp: EspansioneCarte) -> dict:
    return {
        "id": str(esp.id),
        "nome": esp.nome,
        "slug": esp.slug,
        "descrizione": esp.descrizione,
        "immagine_url": esp.immagine.url if esp.immagine else None,
        "ordine": esp.ordine,
    }


def _serializza_carta(carta: CartaCollezionabile) -> dict:
    esp = carta.espansione
    return {
        "id": str(carta.id),
        "codice": carta.codice,
        "nome": carta.nome,
        "tipo": carta.tipo,
        "energia": carta.energia,
        "rarita": carta.rarita,
        "costo_gioco": carta.costo_gioco,
        "attacco": carta.attacco,
        "salute": carta.salute,
        "iniziativa": carta.iniziativa,
        "testo_gioco": carta.testo_gioco,
        "testo_lore": carta.testo_lore,
        "set_collezione": carta.set_collezione,
        "espansione_id": str(esp.id) if esp else None,
        "espansione_nome": esp.nome if esp else None,
        "espansione_slug": esp.slug if esp else None,
        "campagna_origine": carta.campagna_origine,
        "legame_id": carta.legame_id,
        "tag_tematici": carta.tag_tematici or [],
        "bonus_equip": carta.bonus_equip or {},
        "duplicabile": carta.duplicabile,
        "ordine_set": carta.ordine_set,
        "immagine_url": carta.immagine.url if carta.immagine else None,
    }


def _serializza_posseduta(cp: CartaPosseduta) -> dict:
    return {
        "id": str(cp.id),
        "fonte": cp.fonte,
        "serial_globale": cp.serial_globale,
        "ottenuta_at": cp.created_at.isoformat(),
        "carta": _serializza_carta(cp.carta),
        "in_reliquiario": cp.slot_reliquiario.exists(),
    }


def lista_keywords_campagna(campagna) -> list[dict]:
    return [
        {
            "id": str(kw.id),
            "codice": kw.codice,
            "nome": kw.nome,
            "testo_regola": kw.testo_regola,
            "reminder_breve": kw.reminder_breve,
            "priorita": kw.priorita,
        }
        for kw in KeywordCarta.objects.filter(campagna=campagna, attiva=True).order_by("-priorita", "nome")
    ]


def build_collezione_payload(personaggio: Personaggio) -> dict:
    accesso_modo = get_carte_accesso_modo(personaggio.campagna)
    puo_accedere = personaggio_puo_accedere_carte(personaggio)
    if not puo_accedere:
        return {
            "accesso_modo": accesso_modo,
            "puo_accedere": False,
            "is_png_staff": is_png_staff_personaggio(personaggio),
            "abilitata": False,
            "carte": [],
            "reliquiario": {},
            "legami_attivi": [],
            "progress_sets": [],
            "progress_espansioni": [],
            "espansioni": [],
            "mazzi": [],
            "crediti": float(personaggio.crediti),
            "bustine": [],
            "config": {},
            "keywords": [],
        }

    possedute = (
        CartaPosseduta.objects.filter(personaggio=personaggio)
        .select_related("carta", "carta__espansione")
        .order_by("-created_at")
    )
    slots = {
        s.slot_index: str(s.carta_posseduta_id) if s.carta_posseduta_id else None
        for s in ReliquiarioSlot.objects.filter(personaggio=personaggio)
    }
    for i in range(RELIQUIARIO_SLOTS):
        slots.setdefault(i, None)

    sets_count = (
        CartaCollezionabile.objects.filter(
            possessioni__personaggio=personaggio,
            set_collezione__gt="",
        )
        .values("set_collezione")
        .annotate(owned=Count("possessioni", distinct=True))
    )
    catalogo_sets = (
        CartaCollezionabile.objects.filter(
            campagna_id=personaggio.campagna_id,
            attiva=True,
            set_collezione__gt="",
        )
        .values("set_collezione")
        .annotate(total=Count("id"))
    )
    totali_per_set = {row["set_collezione"]: row["total"] for row in catalogo_sets}
    progress_sets = []
    for row in sets_count:
        slug = row["set_collezione"]
        progress_sets.append({
            "set_collezione": slug,
            "owned": row["owned"],
            "total": totali_per_set.get(slug, 0),
        })

    progress_espansioni = _progress_espansioni(personaggio)

    duello_avvio = (
        "lista" if accesso_modo == CARTE_ACCESSO_TEST
        else "lobby" if accesso_modo == CARTE_ACCESSO_OPEN
        else "off"
    )

    return {
        "accesso_modo": accesso_modo,
        "puo_accedere": True,
        "is_png_staff": is_png_staff_personaggio(personaggio),
        "abilitata": True,
        "duello_avvio": duello_avvio,
        "carte": [_serializza_posseduta(cp) for cp in possedute],
        "reliquiario": {str(k): v for k, v in sorted(slots.items())},
        "legami_attivi": calcola_legami_attivi(personaggio),
        "progress_sets": progress_sets,
        "progress_espansioni": progress_espansioni,
        "mazzi": lista_mazzi_duello(personaggio),
        "crediti": float(personaggio.crediti),
        "riserva": float(personaggio.riserva),
        "tema_energie": get_tema_energie_carte(),
        "keywords": lista_keywords_campagna(personaggio.campagna),
    }


def _progress_espansioni(personaggio: Personaggio) -> list[dict]:
    espansioni = EspansioneCarte.objects.filter(
        campagna_id=personaggio.campagna_id,
        attiva=True,
    ).order_by("ordine", "nome")
    result = []
    for esp in espansioni:
        owned = (
            CartaCollezionabile.objects.filter(
                espansione=esp,
                possessioni__personaggio=personaggio,
            )
            .distinct()
            .count()
        )
        total = CartaCollezionabile.objects.filter(espansione=esp, attiva=True).count()
        if total == 0:
            continue
        result.append({
            "espansione_id": str(esp.id),
            "slug": esp.slug,
            "nome": esp.nome,
            "owned": owned,
            "total": total,
        })
    return result


def calcola_legami_attivi(personaggio: Personaggio) -> list[dict]:
    """Combo tematiche dallo slot reliquiario equipaggiato."""
    carte = list(
        CartaCollezionabile.objects.filter(
            possessioni__slot_reliquiario__personaggio=personaggio,
            possessioni__slot_reliquiario__carta_posseduta__isnull=False,
        ).distinct()
    )
    if not carte:
        return []

    legami: list[dict] = []
    energie = {c.energia for c in carte}
    naturali = energie & CARTA_ENERGIE_NATURALI
    soprannaturali = energie & CARTA_ENERGIE_SOPRANNATURALI

    if len(naturali) >= 3:
        legami.append({
            "id": "triade_naturale",
            "nome": "Triade Naturale",
            "descrizione": "Marziale + Tecnologica + Innata equipaggiate.",
        })

    by_legame: dict[str, int] = {}
    by_set: dict[str, int] = {}
    for c in carte:
        if c.legame_id:
            by_legame[c.legame_id] = by_legame.get(c.legame_id, 0) + 1
        if c.set_collezione:
            by_set[c.set_collezione] = by_set.get(c.set_collezione, 0) + 1

    for legame_id, count in by_legame.items():
        if count >= 2:
            legami.append({
                "id": legame_id,
                "nome": legame_id.replace("-", " ").title(),
                "descrizione": f"{count} carte del legame «{legame_id}».",
            })

    for set_slug, count in by_set.items():
        if count >= 3:
            legami.append({
                "id": f"set-{set_slug}",
                "nome": f"Echi di {set_slug.replace('-', ' ').title()}",
                "descrizione": f"{count} carte del set «{set_slug}».",
            })

    if len(soprannaturali) >= 4:
        legami.append({
            "id": "quadrifoglio_astrale",
            "nome": "Quadrifoglio Astrale",
            "descrizione": "Quattro energie soprannaturali diverse.",
        })

    return legami


@transaction.atomic
def apri_bustina(personaggio: Personaggio, bustina_id) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    bustina = BustinaCarte.objects.select_for_update().get(pk=bustina_id, attiva=True)
    if bustina.campagna_id != personaggio.campagna_id:
        raise ValidationError("Bustina non disponibile per la campagna del personaggio.")

    cfg = get_config_carte(personaggio.campagna, create=True)
    if _conteggio_bustine_oggi(personaggio) >= cfg.max_bustine_giorno:
        raise ValidationError(f"Limite giornaliero bustine raggiunto ({cfg.max_bustine_giorno}).")

    costo = _decimal2(bustina.costo_crediti)
    if personaggio.crediti < costo:
        raise ValidationError("Crediti insufficienti.")

    pool = _pool_carte(bustina)
    if not pool:
        raise ValidationError("Nessuna carta disponibile nel pool della bustina.")

    prob = bustina.probabilita_effettive()
    pity = _conteggio_pity(personaggio, bustina)
    force_rara_plus = pity >= cfg.pity_soglia

    ottenute: list[CartaPosseduta] = []
    n = bustina.carte_per_bustina or 5

    for i in range(n):
        rarita = _roll_rarita(prob)
        if force_rara_plus and i == 0:
            rarita = CARTA_RARITA_RARA
        if bustina.garantisce_min_rarita:
            min_ord = RARITA_ORDINE.get(bustina.garantisce_min_rarita, 0)
            if RARITA_ORDINE.get(rarita, 0) < min_ord and i == n - 1:
                rarita = bustina.garantisce_min_rarita

        carta = _scegli_carta_da_pool(pool, rarita)
        if not carta:
            continue

        serial = None
        if carta.rarita == CARTA_RARITA_UNICA:
            gia = CartaPosseduta.objects.filter(carta=carta).exists()
            if gia:
                carta = _scegli_carta_da_pool(pool, CARTA_RARITA_EPICA) or carta
            else:
                max_serial = (
                    CartaPosseduta.objects.filter(serial_globale__isnull=False)
                    .order_by("-serial_globale")
                    .values_list("serial_globale", flat=True)
                    .first()
                )
                serial = (max_serial or 0) + 1

        cp = CartaPosseduta.objects.create(
            personaggio=personaggio,
            carta=carta,
            fonte=CARTA_FONTE_BUSTINA,
            serial_globale=serial,
        )
        ottenute.append(cp)

    if not ottenute:
        raise ValidationError("Impossibile estrarre carte dalla bustina.")

    personaggio.modifica_crediti(-costo, f"Bustina carte: {bustina.nome}")

    AperturaBustinaCarte.objects.create(
        personaggio=personaggio,
        bustina=bustina,
        costo_pagato=costo,
        carte_ottenute_ids=[str(cp.id) for cp in ottenute],
    )

    return {
        "status": "ok",
        "costo": float(costo),
        "carte": [_serializza_posseduta(cp) for cp in ottenute],
        "collezione": build_collezione_payload(personaggio),
    }


@transaction.atomic
def equip_reliquio(personaggio: Personaggio, slot_index: int, carta_posseduta_id=None) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    if slot_index < 0 or slot_index >= RELIQUIARIO_SLOTS:
        raise ValidationError("Slot reliquiario non valido.")

    slot, _ = ReliquiarioSlot.objects.select_for_update().get_or_create(
        personaggio=personaggio,
        slot_index=slot_index,
    )

    if not carta_posseduta_id:
        slot.carta_posseduta = None
        slot.save(update_fields=["carta_posseduta", "updated_at"])
        return build_collezione_payload(personaggio)

    cp = CartaPosseduta.objects.select_related("carta").get(
        pk=carta_posseduta_id,
        personaggio=personaggio,
    )

    # Una carta non può stare in due slot
    ReliquiarioSlot.objects.filter(
        personaggio=personaggio,
        carta_posseduta=cp,
    ).exclude(pk=slot.pk).update(carta_posseduta=None)

    slot.carta_posseduta = cp
    slot.save(update_fields=["carta_posseduta", "updated_at"])
    return build_collezione_payload(personaggio)


def _serializza_bustina(b: BustinaCarte) -> dict:
    esp = b.espansione
    return {
        "id": str(b.id),
        "nome": b.nome,
        "descrizione": b.descrizione,
        "costo_crediti": float(b.costo_crediti),
        "carte_per_bustina": b.carte_per_bustina,
        "set_collezione": b.set_collezione,
        "espansione_id": str(esp.id) if esp else None,
        "espansione_nome": esp.nome if esp else None,
        "espansione_slug": esp.slug if esp else None,
    }


def lista_bustine(campagna) -> list[dict]:
    if get_carte_accesso_modo(campagna) == CARTE_ACCESSO_OFF:
        return []
    qs = (
        BustinaCarte.objects.filter(campagna=campagna, attiva=True)
        .select_related("espansione")
        .order_by("espansione__ordine", "ordine", "nome")
    )
    return [_serializza_bustina(b) for b in qs]


def lista_espansioni_giocatore(campagna) -> list[dict]:
    """Espansioni attive con bustine annidate (per UI giocatore)."""
    if get_carte_accesso_modo(campagna) == CARTE_ACCESSO_OFF:
        return []
    bustine = lista_bustine(campagna)
    bustine_per_esp: dict[str | None, list[dict]] = {}
    for b in bustine:
        key = b.get("espansione_id")
        bustine_per_esp.setdefault(key, []).append(b)

    espansioni = EspansioneCarte.objects.filter(campagna=campagna, attiva=True).order_by("ordine", "nome")
    result = []
    for esp in espansioni:
        payload = _serializza_espansione(esp)
        payload["bustine"] = bustine_per_esp.pop(str(esp.id), [])
        result.append(payload)

    orfane = bustine_per_esp.pop(None, []) + [b for lst in bustine_per_esp.values() for b in lst]
    if orfane:
        result.append({
            "id": None,
            "nome": "Altre bustine",
            "slug": "altre",
            "descrizione": "",
            "immagine_url": None,
            "ordine": 9999,
            "bustine": orfane,
        })
    return result


def valida_mazzo_duello(carte_possedute_ids: list, personaggio: Personaggio) -> tuple[bool, list[str]]:
    """Validazione regole mazzo 15 carte (per fase duello)."""
    errori: list[str] = []
    ids = [str(x) for x in (carte_possedute_ids or [])]
    if len(ids) != MAZZO_DUELLO_SIZE:
        errori.append(f"Il mazzo deve contenere esattamente {MAZZO_DUELLO_SIZE} carte.")
        return False, errori

    possedute = list(
        CartaPosseduta.objects.filter(
            personaggio=personaggio,
            pk__in=ids,
        ).select_related("carta")
    )
    if len(possedute) != len(ids):
        errori.append("Una o più carte non appartengono al personaggio.")
        return False, errori

    carte = [p.carta for p in possedute]
    energie = {c.energia for c in carte}
    if len(energie) < 2:
        errori.append("Il mazzo deve usare almeno 2 energie diverse.")

    naturali = sum(1 for c in carte if c.energia in CARTA_ENERGIE_NATURALI)
    soprannaturali = sum(1 for c in carte if c.energia in CARTA_ENERGIE_SOPRANNATURALI)
    if naturali < 2:
        errori.append("Servono almeno 2 carte Naturali (Marziale/Tecnologica/Innata).")
    if soprannaturali < 2:
        errori.append("Servono almeno 2 carte Soprannaturali.")

    per_energia: dict[str, int] = {}
    per_carta: dict[str, int] = {}
    for c in carte:
        per_energia[c.energia] = per_energia.get(c.energia, 0) + 1
        key = str(c.id)
        per_carta[key] = per_carta.get(key, 0) + 1

    for energia, count in per_energia.items():
        if count > 6:
            errori.append(f"Troppe carte {energia}: massimo 6.")

    for carta_id, count in per_carta.items():
        carta = next(c for c in carte if str(c.id) == carta_id)
        max_copies = 2 if carta.duplicabile else 1
        if count > max_copies:
            errori.append(f"Troppe copie di «{carta.nome}»: massimo {max_copies}.")

    return len(errori) == 0, errori


def lista_mazzi_duello(personaggio: Personaggio) -> list[dict]:
    return [
        {
            "id": str(m.id),
            "nome": m.nome,
            "carte_possedute_ids": m.carte_possedute_ids or [],
            "is_default": m.is_default,
        }
        for m in MazzoDuello.objects.filter(personaggio=personaggio).order_by("-is_default", "nome")
    ]


def get_mazzo_default_ids(personaggio: Personaggio) -> list[str]:
    m = MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).first()
    if m and m.carte_possedute_ids:
        return [str(x) for x in m.carte_possedute_ids]
    return []


@transaction.atomic
def salva_mazzo_duello(
    personaggio: Personaggio,
    carte_ids: list,
    *,
    mazzo_id=None,
    nome: str = "Mazzo principale",
    is_default: bool = False,
) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    ok, errs = valida_mazzo_duello(carte_ids, personaggio)
    if not ok:
        raise ValidationError(" ".join(errs))
    ids = [str(x) for x in carte_ids]
    nome = (nome or "Mazzo").strip()[:80] or "Mazzo"

    if mazzo_id:
        mazzo = MazzoDuello.objects.filter(pk=mazzo_id, personaggio=personaggio).first()
        if not mazzo:
            raise ValidationError("Mazzo non trovato.")
    else:
        if MazzoDuello.objects.filter(personaggio=personaggio).count() >= MAZZI_DUELLO_MAX_PER_PG:
            raise ValidationError(f"Massimo {MAZZI_DUELLO_MAX_PER_PG} mazzi per personaggio.")
        mazzo = MazzoDuello.objects.create(
            personaggio=personaggio,
            nome=nome,
            carte_possedute_ids=ids,
            is_default=is_default,
        )

    if is_default:
        MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).exclude(pk=mazzo.pk).update(
            is_default=False
        )

    mazzo.nome = nome
    mazzo.carte_possedute_ids = ids
    mazzo.is_default = is_default or (
        not MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).exclude(pk=mazzo.pk).exists()
    )
    mazzo.save(update_fields=["nome", "carte_possedute_ids", "is_default", "updated_at"])
    return {"mazzi": lista_mazzi_duello(personaggio), "saved_id": str(mazzo.id)}


@transaction.atomic
def elimina_mazzo_duello(personaggio: Personaggio, mazzo_id) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    mazzo = MazzoDuello.objects.filter(pk=mazzo_id, personaggio=personaggio).first()
    if not mazzo:
        raise ValidationError("Mazzo non trovato.")
    was_default = mazzo.is_default
    mazzo.delete()
    if was_default:
        altro = MazzoDuello.objects.filter(personaggio=personaggio).order_by("nome").first()
        if altro:
            altro.is_default = True
            altro.save(update_fields=["is_default", "updated_at"])
    return {"mazzi": lista_mazzi_duello(personaggio)}


def applica_modificatori_reliquiario(personaggio: Personaggio, add_fn) -> None:
    """Integrazione in Personaggio.modificatori_calcolati."""
    if not personaggio_puo_accedere_carte(personaggio):
        return
    slots = (
        ReliquiarioSlot.objects.filter(personaggio=personaggio, carta_posseduta__isnull=False)
        .select_related("carta_posseduta__carta")
    )
    for slot in slots:
        bonus = slot.carta_posseduta.carta.bonus_equip or {}
        sigla = (bonus.get("stat_sigla") or "").strip()
        if not sigla:
            continue
        try:
            valore = float(bonus.get("valore") or 0)
        except (TypeError, ValueError):
            continue
        if valore == 0:
            continue
        stat = Statistica.objects.filter(sigla=sigla).first()
        if stat and stat.parametro:
            add_fn(stat.parametro, MODIFICATORE_ADDITIVO, valore)


def serializza_bustina_qr(bustina: BustinaCarte, personaggio: Personaggio | None = None) -> dict:
    payload = {
        "bustina_id": str(bustina.id),
        "nome": bustina.nome,
        "descrizione": bustina.descrizione,
        "costo_crediti": float(bustina.costo_crediti),
        "carte_per_bustina": bustina.carte_per_bustina,
        "set_collezione": bustina.set_collezione,
        "espansione_id": str(bustina.espansione_id) if bustina.espansione_id else None,
        "espansione_nome": bustina.espansione.nome if bustina.espansione_id else None,
        "puo_accedere": personaggio_puo_accedere_carte(personaggio) if personaggio else False,
    }
    return payload


def get_tema_energie_carte() -> dict[str, dict]:
    """Colori e metadati aura da Punteggio (tipo AU) per il rendering carte."""
    from personaggi.models import AURA, Punteggio

    aura_sigle = list({s.upper() for s in CARTA_ENERGIA_AURA_SIGLA.values()})
    auras = {
        p.sigla.upper(): p
        for p in Punteggio.objects.filter(tipo=AURA, sigla__in=aura_sigle)
    }
    tema: dict[str, dict] = {}
    for energia, sigla in CARTA_ENERGIA_AURA_SIGLA.items():
        aura = auras.get(sigla.upper())
        if not aura:
            continue
        tema[energia] = {
            "colore": aura.colore,
            "nome": aura.nome,
            "sigla": aura.sigla,
            "icona_url": aura.icona_url,
        }
    return tema


def stato_carte_per_personaggio(personaggio: Personaggio) -> dict:
    accesso_modo = get_carte_accesso_modo(personaggio.campagna)
    puo = personaggio_puo_accedere_carte(personaggio)
    cfg = get_config_carte(personaggio.campagna, create=False)
    payload = {
        "accesso_modo": accesso_modo,
        "puo_accedere": puo,
        "is_png_staff": is_png_staff_personaggio(personaggio),
        "abilitata": puo,
        "modalita_testing": accesso_modo == CARTE_ACCESSO_TEST and puo,
        "duello_avvio": (
            "lista" if accesso_modo == CARTE_ACCESSO_TEST and puo
            else "lobby" if accesso_modo == CARTE_ACCESSO_OPEN and puo
            else "off"
        ),
        "config": {
            "max_bustine_giorno": cfg.max_bustine_giorno if cfg else 10,
            "pity_soglia": cfg.pity_soglia if cfg else 20,
        } if puo else {},
    }
    if puo:
        payload["tema_energie"] = get_tema_energie_carte()
    return payload
