"""
Seed idempotente: 20 carte demo «Sette Elegie» + espansione + keyword MVP.

Dati: personaggi/data/carte_esempio_sette_elegie.json
"""
from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from django.db import transaction

DATA_PATH = Path(__file__).with_name("data") / "carte_esempio_sette_elegie.json"

INT_FIELDS = {"costo_gioco", "attacco", "salute", "iniziativa", "ordine_set"}
BOOL_FIELDS = {"duplicabile", "attiva"}
JSON_FIELDS = {"tag_tematici", "bonus_equip"}
STR_FIELDS = {
    "nome",
    "tipo",
    "energia",
    "rarita",
    "testo_gioco",
    "testo_lore",
    "campagna_origine",
    "legame_id",
}


def load_carte_esempio_payload() -> dict:
    with DATA_PATH.open(encoding="utf-8") as fh:
        return json.load(fh)


def _resolve_campagna(campagna_slug: str | None):
    from personaggi.models import Campagna

    if campagna_slug:
        return Campagna.objects.get(slug=campagna_slug)
    campagna = Campagna.objects.filter(attiva=True).order_by("id").first()
    if not campagna:
        raise ValueError("Nessuna campagna attiva; usa --campagna-slug.")
    return campagna


def _seed_keywords(campagna, *, force: bool) -> tuple[int, int]:
    from personaggi.carte_collezionabili_models import KeywordCarta
    from personaggi.carte_effect_script import (
        colpo_influenza_effect_script_template,
        danno_eroe_effect_script_template,
        mutazione_effect_script_template,
        pesca_effect_script_template,
        rigenerazione_energia_effect_script_template,
        validate_effect_script_for_keyword,
    )

    defs = [
        (
            "MUTAZIONE",
            "Mutazione [X]",
            "Quando questo Personaggio si esaurisce, puoi sostituirlo con un Personaggio dalla mano con costo gioco ≤ [X].",
            "Mutazione ≤[X]",
            10,
            mutazione_effect_script_template(),
        ),
        (
            "COLPO",
            "Colpo [X]",
            "Quando giochi questa carta, infliggi [X] danni all'influenza avversaria.",
            "Colpo [X]",
            8,
            colpo_influenza_effect_script_template(),
        ),
        (
            "PESCA",
            "Pesca [X]",
            "All'inizio del tuo turno, mentre questa carta è in gioco: Pesca [X].",
            "Pesca [X]",
            7,
            pesca_effect_script_template(),
        ),
        (
            "RIGENERAZIONE",
            "Rigenerazione [X]",
            "Quando giochi questa carta, guadagni [X] energia.",
            "Rigenerazione [X]",
            6,
            rigenerazione_energia_effect_script_template(),
        ),
        (
            "FERITA",
            "Ferita [X]",
            "Quando giochi questa carta, scegli un eroe avversario e infliggi [X] danni.",
            "Ferita [X]",
            6,
            danno_eroe_effect_script_template(),
        ),
    ]

    created = 0
    updated = 0
    for codice, nome, regola, reminder, priorita, script in defs:
        validate_effect_script_for_keyword(script, nome=nome, codice=codice)
        kw, was_created = KeywordCarta.objects.get_or_create(
            campagna=campagna,
            codice=codice,
            defaults={
                "nome": nome,
                "testo_regola": regola,
                "reminder_breve": reminder,
                "priorita": priorita,
                "attiva": True,
                "effect_script": script,
            },
        )
        if was_created:
            created += 1
            continue
        if force:
            kw.nome = nome
            kw.testo_regola = regola
            kw.reminder_breve = reminder
            kw.priorita = priorita
            kw.attiva = True
            kw.effect_script = script
            kw.save()
            updated += 1
    return created, updated


def _upsert_espansione(campagna, meta: dict, *, force: bool):
    from personaggi.carte_collezionabili_models import EspansioneCarte

    slug = meta["slug"]
    defaults = {
        "nome": meta["nome"],
        "descrizione": meta.get("descrizione", ""),
        "ordine": int(meta.get("ordine") or 0),
        "attiva": True,
    }
    esp, created = EspansioneCarte.objects.get_or_create(
        campagna=campagna,
        slug=slug,
        defaults=defaults,
    )
    if not created and force:
        for key, val in defaults.items():
            setattr(esp, key, val)
        esp.save()
    return esp, created


def _card_defaults(row: dict, espansione) -> dict:
    out = {
        "nome": row["nome"],
        "tipo": row["tipo"],
        "energia": row["energia"],
        "rarita": row["rarita"],
        "costo_gioco": int(row.get("costo_gioco") or 0),
        "testo_gioco": row.get("testo_gioco") or "",
        "testo_lore": row.get("testo_lore") or "",
        "campagna_origine": row.get("campagna_origine") or "",
        "legame_id": row.get("legame_id") or "",
        "tag_tematici": row.get("tag_tematici") or [],
        "bonus_equip": row.get("bonus_equip") or {},
        "duplicabile": bool(row.get("duplicabile", False)),
        "ordine_set": int(row.get("ordine_set") or 0),
        "attiva": True,
        "espansione": espansione,
        "set_collezione": espansione.slug,
    }
    for key in ("attacco", "salute", "iniziativa"):
        if key in row and row[key] is not None:
            out[key] = int(row[key])
        else:
            out[key] = None
    return out


def _upsert_bustina(campagna, espansione, meta: dict, *, force: bool):
    from personaggi.carte_collezionabili_models import BustinaCarte
    from personaggi.bustina_carte_avista import ensure_bustina_qr

    nome = meta["nome"]
    defaults = {
        "descrizione": meta.get("descrizione") or "",
        "costo_crediti": Decimal(str(meta.get("costo_crediti") or "0")),
        "carte_per_bustina": int(meta.get("carte_per_bustina") or 5),
        "garantisce_min_rarita": meta.get("garantisce_min_rarita") or "",
        "set_collezione": espansione.slug,
        "ordine": int(meta.get("ordine") or 0),
        "attiva": True,
        "espansione": espansione,
    }
    bustina, created = BustinaCarte.objects.get_or_create(
        campagna=campagna,
        espansione=espansione,
        nome=nome,
        defaults=defaults,
    )
    if not created and force:
        for key, val in defaults.items():
            setattr(bustina, key, val)
        bustina.save()

    qr_id = None
    if meta.get("con_qr", True):
        qr, _portale = ensure_bustina_qr(bustina)
        qr_id = qr.id

    return bustina, created, qr_id


def _ensure_config_carte_playtest(campagna):
    """Abilita tab carte in OPEN se la config manca o è spenta."""
    from personaggi.carte_collezionabili_models import CARTE_ACCESSO_OPEN, ConfigurazioneCarteCollezionabili

    cfg, created = ConfigurazioneCarteCollezionabili.objects.get_or_create(
        campagna=campagna,
        defaults={"abilitata": True, "accesso_modo": CARTE_ACCESSO_OPEN},
    )
    if not created and (not cfg.abilitata or cfg.accesso_modo == "OFF"):
        cfg.abilitata = True
        cfg.accesso_modo = CARTE_ACCESSO_OPEN
        cfg.save(update_fields=["abilitata", "accesso_modo", "updated_at"])
    return cfg


@transaction.atomic
def seed_carte_esempio(
    *,
    campagna_slug: str | None = None,
    force: bool = False,
    skip_if_complete: bool = False,
    with_keywords: bool | None = None,
) -> dict:
    """
    Carica espansione demo + 20 carte. Ritorna statistiche per CLI/test.
    """
    from personaggi.carte_collezionabili_models import CartaCollezionabile
    from personaggi.carte_collezionabili_service import get_carte_accesso_modo

    payload = load_carte_esempio_payload()
    campagna = _resolve_campagna(campagna_slug)
    _ensure_config_carte_playtest(campagna)
    esp_meta = payload["espansione"]
    codici_attesi = {row["codice"] for row in payload["carte"]}

    if skip_if_complete:
        presenti = set(
            CartaCollezionabile.objects.filter(
                campagna=campagna,
                codice__in=codici_attesi,
            ).values_list("codice", flat=True)
        )
        bustina_meta = payload.get("bustina")
        bustina_ok = True
        if bustina_meta:
            from personaggi.carte_collezionabili_models import BustinaCarte

            bustina_ok = BustinaCarte.objects.filter(
                campagna=campagna,
                espansione__slug=esp_meta["slug"],
                nome=bustina_meta["nome"],
            ).exists()
        if presenti == codici_attesi and bustina_ok:
            return {
                "campagna": campagna.slug,
                "campagna_nome": campagna.nome,
                "skipped": True,
                "carte_create": 0,
                "carte_aggiornate": 0,
                "carte_totali": len(codici_attesi),
                "config_accesso": get_carte_accesso_modo(campagna),
            }

    kw_created = kw_updated = 0
    if with_keywords if with_keywords is not None else payload.get("keywords"):
        kw_created, kw_updated = _seed_keywords(campagna, force=force)

    espansione, esp_created = _upsert_espansione(campagna, esp_meta, force=force)

    carte_create = 0
    carte_aggiornate = 0
    for row in payload["carte"]:
        defaults = _card_defaults(row, espansione)
        carta, created = CartaCollezionabile.objects.get_or_create(
            campagna=campagna,
            codice=row["codice"],
            defaults=defaults,
        )
        if created:
            carte_create += 1
        elif force:
            for key, val in defaults.items():
                setattr(carta, key, val)
            carta.save()
            carte_aggiornate += 1

    bustina_id = None
    bustina_creata = False
    bustina_qr_id = None
    bustina_meta = payload.get("bustina")
    if bustina_meta:
        bustina, bustina_creata, bustina_qr_id = _upsert_bustina(
            campagna, espansione, bustina_meta, force=force
        )
        bustina_id = str(bustina.id)

    from personaggi.carte_combo_reliquiario_seed import seed_combo_reliquiario

    combo_stats = seed_combo_reliquiario(
        campagna=campagna,
        force=force,
        include_catalog_derived=True,
    )

    return {
        "campagna": campagna.slug,
        "campagna_nome": campagna.nome,
        "espansione": espansione.slug,
        "espansione_creata": esp_created,
        "keywords_create": kw_created,
        "keywords_aggiornate": kw_updated,
        "carte_create": carte_create,
        "carte_aggiornate": carte_aggiornate,
        "carte_totali": len(payload["carte"]),
        "bustina_id": bustina_id,
        "bustina_creata": bustina_creata,
        "bustina_qr_id": bustina_qr_id,
        "combo_reliquiario_create": combo_stats["created"],
        "combo_reliquiario_aggiornate": combo_stats["updated"],
        "combo_reliquiario_skipped": combo_stats["skipped"],
        "skipped": False,
    }


@transaction.atomic
def grant_starter_kit(
    campagna,
    *,
    personaggio_nome: str | None = None,
    crediti: Decimal | None = None,
) -> dict:
    """
    Concede 1 copia di ogni carta demo al personaggio (o a tutti i PG della campagna)
    e crediti sufficienti per aprire bustine.
    """
    from personaggi.carte_collezionabili_models import (
        CARTA_FONTE_BUSTINA,
        CartaCollezionabile,
        CartaPosseduta,
    )
    from personaggi.models import Personaggio

    payload = load_carte_esempio_payload()
    esp_slug = payload["espansione"]["slug"]
    carte = CartaCollezionabile.objects.filter(campagna=campagna, espansione__slug=esp_slug)
    if not carte.exists():
        raise ValueError("Esegui prima seed_carte_esempio per creare il catalogo demo.")

    qs = Personaggio.objects.filter(campagna=campagna)
    if personaggio_nome:
        qs = qs.filter(nome__iexact=personaggio_nome.strip())
    if not qs.exists():
        raise ValueError("Nessun personaggio trovato per lo starter kit.")

    if crediti is None:
        bustina_meta = payload.get("bustina") or {}
        crediti = Decimal(str(bustina_meta.get("costo_crediti", 250))) * 2

    personaggi = []
    carte_concedute = 0
    for pg in qs:
        for carta in carte:
            _, created = CartaPosseduta.objects.get_or_create(
                personaggio=pg,
                carta=carta,
                defaults={"fonte": CARTA_FONTE_BUSTINA},
            )
            if created:
                carte_concedute += 1
        attuali = Decimal(str(pg.crediti))
        if crediti > attuali:
            pg.modifica_crediti(crediti - attuali, "Starter kit carte demo")
        personaggi.append(pg.nome)

    return {
        "personaggi": personaggi,
        "carte_concedute": carte_concedute,
        "crediti_target": float(crediti),
    }
