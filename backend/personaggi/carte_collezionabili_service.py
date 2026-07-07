"""
Logica carte collezionabili: bustine, reliquiario, collezione.
"""
from __future__ import annotations

import random
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count, Q
from django.utils import timezone

from personaggi.carte_collezionabili_models import (
    AperturaBustinaCarte,
    BustinaCarte,
    CARTE_ACCESSO_OFF,
    CARTE_ACCESSO_OPEN,
    CARTE_ACCESSO_TEST,
    CARTA_ENERGIE_NATURALI,
    CARTA_ENERGIE_SOPRANNATURALI,
    CARTA_ENERGIA_CHOICES,
    CARTA_FONTE_BUSTINA,
    CARTA_RARITA_CHOICES,
    CARTA_RARITA_COMUNE,
    CARTA_RARITA_RARA,
    CARTA_RARITA_UNICA,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_LUOGO,
    CARTA_TIPO_OGGETTO,
    CARTA_TIPO_PERSONAGGIO,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    CARTA_ENERGIA_AURA_SIGLA,
    EspansioneCarte,
    KeywordCarta,
    MAZZI_DUELLO_MAX_PER_PG,
    MAZZO_DUELLO_SIZE,
    MAZZO_MAX_AURE,
    MAZZO_MAX_TERRE,
    MAZZO_MIN_PERSONAGGI,
    MazzoDuello,
    RELIQUIARIO_SLOTS,
    ReliquiarioSlot,
)
from personaggi.models import MODIFICATORE_ADDITIVO, Personaggio, Statistica
from personaggi.carte_legality import (
    carta_disponibile_per_giocatori,
    carta_legale_duello,
    espansione_in_vendita,
    motivo_illegalita_duello,
)
from personaggi.carte_errata_runtime import gameplay_view

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
    out = []
    for carta in qs.select_related("espansione"):
        if carta_disponibile_per_giocatori(carta):
            out.append(carta)
    return out


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
        "in_vendita": espansione_in_vendita(esp),
    }


def _serializza_carta(carta: CartaCollezionabile) -> dict:
    esp = carta.espansione
    gameplay = gameplay_view(carta)
    return {
        "id": str(carta.id),
        "codice": carta.codice,
        "nome": carta.nome,
        "tipo": carta.tipo,
        "energia": carta.energia,
        "rarita": carta.rarita,
        "costo_gioco": gameplay["costo_gioco"],
        "attacco": gameplay["attacco"],
        "salute": gameplay["salute"],
        "iniziativa": gameplay["iniziativa"],
        "testo_gioco": gameplay["testo_gioco"],
        "testo_lore": carta.testo_lore,
        "testo_reliquiario": carta.testo_reliquiario,
        "set_collezione": carta.set_collezione,
        "espansione_id": str(esp.id) if esp else None,
        "espansione_nome": esp.nome if esp else None,
        "espansione_slug": esp.slug if esp else None,
        "campagna_origine": carta.campagna_origine,
        "legame_id": carta.legame_id,
        "tag_tematici": carta.tag_tematici or [],
        "tags": [
            {"codice": t.codice, "nome": t.nome, "colore": t.colore or ""}
            for t in carta.tags.filter(attiva=True).order_by("nome")
        ],
        "bonus_equip": carta.bonus_equip or {},
        "legale_duello": carta.legale_duello,
        "bandita": carta.bandita,
        "ban_reason": carta.ban_reason,
        "layout_versione": carta.layout_versione,
        "errata_attiva": gameplay["errata"],
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


def lista_tags_campagna(campagna) -> list[dict]:
    from personaggi.carte_tag_utils import lista_tags_campagna as _lista

    return _lista(campagna)


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
            "tags": [],
            "regole_mazzo": descrizione_regole_mazzo_duello(),
        }

    possedute = (
        CartaPosseduta.objects.filter(personaggio=personaggio)
        .select_related("carta", "carta__espansione")
        .order_by("-created_at")
    )
    possedute = [cp for cp in possedute if carta_disponibile_per_giocatori(cp.carta)]
    slots = {
        s.slot_index: str(s.carta_posseduta_id) if s.carta_posseduta_id else None
        for s in ReliquiarioSlot.objects.filter(personaggio=personaggio)
    }
    for i in range(RELIQUIARIO_SLOTS):
        slots.setdefault(i, None)

    sets_count = (
        CartaCollezionabile.objects.filter(
            possessioni__personaggio=personaggio,
            attiva=True,
            set_collezione__gt="",
        )
        .filter(Q(espansione__isnull=True) | Q(espansione__attiva=True))
        .values("set_collezione")
        .annotate(owned=Count("possessioni", distinct=True))
    )
    catalogo_sets = (
        CartaCollezionabile.objects.filter(
            campagna_id=personaggio.campagna_id,
            attiva=True,
            set_collezione__gt="",
        )
        .filter(Q(espansione__isnull=True) | Q(espansione__attiva=True))
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
        "tags": lista_tags_campagna(personaggio.campagna),
        "regole_mazzo": descrizione_regole_mazzo_duello(),
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
    """Combo reliquiario attive (definite da staff)."""
    from personaggi.carte_reliquiario_combo import calcola_combo_reliquiario_attive

    return calcola_combo_reliquiario_attive(personaggio)


@transaction.atomic
def apri_bustina(personaggio: Personaggio, bustina_id) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    bustina = BustinaCarte.objects.select_for_update().select_related("espansione").get(pk=bustina_id, attiva=True)
    if bustina.campagna_id != personaggio.campagna_id:
        raise ValidationError("Bustina non disponibile per la campagna del personaggio.")
    if bustina.espansione_id and not espansione_in_vendita(bustina.espansione):
        raise ValidationError("Questa espansione non è attualmente in vendita.")

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

    altri_slot = (
        ReliquiarioSlot.objects.filter(
            personaggio=personaggio,
            carta_posseduta__isnull=False,
        )
        .exclude(pk=slot.pk)
        .select_related("carta_posseduta__carta")
    )
    for altro in altri_slot:
        if altro.carta_posseduta and altro.carta_posseduta.carta_id == cp.carta_id:
            raise ValidationError(
                f"«{cp.carta.nome}» è già equipaggiata nello slot {altro.slot_index + 1}. "
                "Non puoi equipaggiare due copie della stessa carta."
            )

    # Una stessa istanza non può stare in due slot
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
        "in_vendita": espansione_in_vendita(esp) if esp else True,
    }


def lista_bustine(campagna) -> list[dict]:
    if get_carte_accesso_modo(campagna) == CARTE_ACCESSO_OFF:
        return []
    qs = (
        BustinaCarte.objects.filter(campagna=campagna, attiva=True)
        .select_related("espansione")
        .order_by("espansione__ordine", "ordine", "nome")
    )
    out = []
    for b in qs:
        if b.espansione_id and not espansione_in_vendita(b.espansione):
            continue
        out.append(_serializza_bustina(b))
    return out


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


_ENERGIA_ETICHETTA = dict(CARTA_ENERGIA_CHOICES)


def valida_leader_duello(
    leader_id,
    personaggio: Personaggio,
    mazzo_ids: list | None = None,
) -> tuple[bool, list[str]]:
    """Leader = carta Personaggio comandante, separata dalle 15 carte del mazzo."""
    errori: list[str] = []
    if not leader_id:
        errori.append("Seleziona un Leader (Personaggio comandante).")
        return False, errori

    lid = str(leader_id)
    ids_mazzo = [str(x) for x in (mazzo_ids or [])]
    if lid in ids_mazzo:
        errori.append("Il Leader non può essere incluso nelle 15 carte del mazzo.")
        return False, errori

    cp = (
        CartaPosseduta.objects.filter(pk=lid, personaggio=personaggio)
        .select_related("carta")
        .first()
    )
    if not cp:
        errori.append("Il Leader selezionato non appartiene al personaggio.")
        return False, errori
    if cp.carta.tipo != CARTA_TIPO_PERSONAGGIO:
        errori.append("Il Leader deve essere una carta Personaggio.")
        return False, errori
    return True, errori


def valida_setup_duello(
    mazzo_ids: list,
    leader_id,
    personaggio: Personaggio,
) -> tuple[bool, list[str]]:
    """Mazzo 15 carte + Leader (regolamento Sette Elegie)."""
    ok, errs = valida_mazzo_duello(mazzo_ids, personaggio)
    if not ok:
        return False, errs
    ok_l, errs_l = valida_leader_duello(leader_id, personaggio, mazzo_ids)
    if not ok_l:
        return False, errs_l
    return True, []


def descrizione_regole_mazzo_duello() -> list[str]:
    """Regole costruzione mazzo (testo per API / UI)."""
    return [
        f"Esattamente {MAZZO_DUELLO_SIZE} carte (oltre al Leader, scelto a parte).",
        "1 Leader (Personaggio comandante) scelto separatamente — non conta tra le 15 carte; definisce l'aura primaria del mazzo.",
        f"Almeno {MAZZO_MIN_PERSONAGGI} Personaggi.",
        f"Massimo {MAZZO_MAX_TERRE} Terre.",
        f"Massimo {MAZZO_MAX_AURE} aure diverse (Terre senza aura).",
        "Almeno un'aura Naturale (Marziale, Tecnologica, Innata) e una Soprannaturale (Magica, Sacra, Psionica, Arcana).",
        "Per giocare Equipaggiamenti o Effetti di un'aura serve almeno un Personaggio di quell'aura nel mazzo.",
        "Massimo 1 copia per carta (2 se «duplicabile»).",
    ]


def valida_mazzo_duello(carte_possedute_ids: list, personaggio: Personaggio) -> tuple[bool, list[str]]:
    """Validazione regole mazzo 15 carte (regolamento Sette Elegie)."""
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

    for carta in carte:
        if not carta_legale_duello(carta):
            errori.append(f"«{carta.nome}»: {motivo_illegalita_duello(carta)}")

    pg_count = sum(1 for c in carte if c.tipo == CARTA_TIPO_PERSONAGGIO)
    if pg_count < MAZZO_MIN_PERSONAGGI:
        errori.append(
            f"Servono almeno {MAZZO_MIN_PERSONAGGI} Personaggi nel mazzo (attuali: {pg_count})."
        )

    terre = sum(1 for c in carte if c.tipo == CARTA_TIPO_LUOGO)
    if terre > MAZZO_MAX_TERRE:
        errori.append(f"Massimo {MAZZO_MAX_TERRE} Terre nel mazzo (attuali: {terre}).")

    carte_con_aura = [c for c in carte if c.tipo != CARTA_TIPO_LUOGO]
    energie = {c.energia for c in carte_con_aura if c.energia}

    if len(energie) > MAZZO_MAX_AURE:
        errori.append(
            f"Massimo {MAZZO_MAX_AURE} aure diverse nel mazzo (attuali: {len(energie)})."
        )

    if not (energie & CARTA_ENERGIE_NATURALI):
        errori.append(
            "Il mazzo deve includere almeno un'aura Naturale "
            "(Marziale, Tecnologica o Innata)."
        )
    if not (energie & CARTA_ENERGIE_SOPRANNATURALI):
        errori.append(
            "Il mazzo deve includere almeno un'aura Soprannaturale "
            "(Magica, Sacra, Psionica o Arcana)."
        )

    pg_energie = {c.energia for c in carte if c.tipo == CARTA_TIPO_PERSONAGGIO}
    for carta in carte:
        if carta.tipo not in (CARTA_TIPO_OGGETTO, CARTA_TIPO_EVENTO):
            continue
        if carta.energia in pg_energie:
            continue
        aura_nome = _ENERGIA_ETICHETTA.get(carta.energia, carta.energia)
        tipo_nome = "Equipaggiamento" if carta.tipo == CARTA_TIPO_OGGETTO else "Effetto"
        errori.append(
            f"«{carta.nome}» ({tipo_nome} {aura_nome}): "
            f"serve almeno un Personaggio {aura_nome} nel mazzo."
        )

    per_carta: dict[str, int] = {}
    for c in carte:
        key = str(c.id)
        per_carta[key] = per_carta.get(key, 0) + 1

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
            "leader_carta_posseduta_id": m.leader_carta_posseduta_id or None,
            "is_default": m.is_default,
        }
        for m in MazzoDuello.objects.filter(personaggio=personaggio).order_by("-is_default", "nome")
    ]


def get_mazzo_default_ids(personaggio: Personaggio) -> list[str]:
    m = MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).first()
    if m and m.carte_possedute_ids:
        return [str(x) for x in m.carte_possedute_ids]
    return []


def get_mazzo_default_leader_id(personaggio: Personaggio) -> str | None:
    m = MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).first()
    if m and m.leader_carta_posseduta_id:
        return str(m.leader_carta_posseduta_id)
    return None


@transaction.atomic
def salva_mazzo_duello(
    personaggio: Personaggio,
    carte_ids: list,
    *,
    mazzo_id=None,
    nome: str = "Mazzo principale",
    is_default: bool = False,
    leader_carta_posseduta_id=None,
) -> dict:
    assert_personaggio_puo_accedere_carte(personaggio)
    ok, errs = valida_setup_duello(carte_ids, leader_carta_posseduta_id, personaggio)
    if not ok:
        raise ValidationError(" ".join(errs))
    ids = [str(x) for x in carte_ids]
    leader_id = str(leader_carta_posseduta_id)
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
            leader_carta_posseduta_id=leader_id,
            is_default=is_default,
        )

    if is_default:
        MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).exclude(pk=mazzo.pk).update(
            is_default=False
        )

    mazzo.nome = nome
    mazzo.carte_possedute_ids = ids
    mazzo.leader_carta_posseduta_id = leader_id
    mazzo.is_default = is_default or (
        not MazzoDuello.objects.filter(personaggio=personaggio, is_default=True).exclude(pk=mazzo.pk).exists()
    )
    mazzo.save(
        update_fields=[
            "nome",
            "carte_possedute_ids",
            "leader_carta_posseduta_id",
            "is_default",
            "updated_at",
        ]
    )
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
    from personaggi.models import (
        CartaReliquiarioStatistica,
        ComboReliquiarioStatistica,
        stat_link_attivo_in_contesto,
        stat_link_solo_oggetto_ospitante,
    )
    from personaggi.carte_reliquiario_combo import calcola_combo_reliquiario_attive

    if not personaggio_puo_accedere_carte(personaggio):
        return

    def _applica_stat_link(stat_link):
        if stat_link_solo_oggetto_ospitante(stat_link):
            return
        if stat_link.usa_limitazione_elemento or stat_link.usa_limitazione_aura:
            return
        if stat_link.usa_condizione_text:
            if not stat_link_attivo_in_contesto(personaggio, stat_link, {}):
                return
        if stat_link.statistica and stat_link.statistica.parametro:
            add_fn(stat_link.statistica.parametro, stat_link.tipo_modificatore, stat_link.valore)

    slots = (
        ReliquiarioSlot.objects.filter(personaggio=personaggio, carta_posseduta__isnull=False)
        .select_related("carta_posseduta__carta")
    )
    carta_ids = []
    for slot in slots:
        carta_ids.append(slot.carta_posseduta.carta_id)
        bonus = slot.carta_posseduta.carta.bonus_equip or {}
        sigla = (bonus.get("stat_sigla") or "").strip()
        if sigla:
            try:
                valore = float(bonus.get("valore") or 0)
            except (TypeError, ValueError):
                valore = 0
            if valore != 0:
                stat = Statistica.objects.filter(sigla=sigla).first()
                if stat and stat.parametro:
                    add_fn(stat.parametro, MODIFICATORE_ADDITIVO, valore)

    if carta_ids:
        stat_qs = (
            CartaReliquiarioStatistica.objects.filter(carta_id__in=carta_ids)
            .select_related("statistica")
            .prefetch_related("limit_a_aure", "limit_a_elementi")
        )
        for stat_link in stat_qs:
            _applica_stat_link(stat_link)

    combo_attive_ids = [c["id"] for c in calcola_combo_reliquiario_attive(personaggio)]
    if combo_attive_ids:
        combo_stat_qs = (
            ComboReliquiarioStatistica.objects.filter(combo_id__in=combo_attive_ids)
            .select_related("statistica")
            .prefetch_related("limit_a_aure", "limit_a_elementi")
        )
        for stat_link in combo_stat_qs:
            _applica_stat_link(stat_link)


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
