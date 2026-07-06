"""Valutazione combo reliquiario staff-defined."""
from __future__ import annotations

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIE_NATURALI,
    CARTA_ENERGIE_SOPRANNATURALI,
    COMBO_TRIGGER_CARTE,
    COMBO_TRIGGER_ENERGIE_NAT,
    COMBO_TRIGGER_ENERGIE_SOP,
    COMBO_TRIGGER_LEGAME,
    COMBO_TRIGGER_SET,
    ComboReliquiario,
)


def _equipped_entries(personaggio):
    from personaggi.carte_collezionabili_models import ReliquiarioSlot

    rows = (
        ReliquiarioSlot.objects.filter(
            personaggio=personaggio,
            carta_posseduta__isnull=False,
        )
        .select_related("carta_posseduta__carta")
        .order_by("slot_index")
    )
    out = []
    for row in rows:
        carta = row.carta_posseduta.carta
        out.append({
            "slot_index": row.slot_index,
            "carta": carta,
            "codice": carta.codice,
            "legame_id": (carta.legame_id or "").strip(),
            "set_collezione": (carta.set_collezione or "").strip(),
            "energia": carta.energia,
        })
    return out


def _match_indices(entries, predicate):
    indices = [e["slot_index"] for e in entries if predicate(e)]
    codici = [e["codice"] for e in entries if predicate(e)]
    return indices, codici


def valuta_combo_reliquiario(combo: ComboReliquiario, entries: list[dict]) -> dict | None:
    if not entries:
        return None

    trigger = combo.tipo_trigger
    min_count = max(1, int(combo.param_min_count or 1))

    if trigger == COMBO_TRIGGER_LEGAME:
        legame = (combo.param_legame_id or "").strip()
        if not legame:
            return None
        matched = [e for e in entries if e["legame_id"] == legame]
        if len(matched) < min_count:
            return None
        return {
            "slot_indices": [e["slot_index"] for e in matched],
            "carta_codici": [e["codice"] for e in matched],
        }

    if trigger == COMBO_TRIGGER_SET:
        set_slug = (combo.param_set_collezione or "").strip()
        if not set_slug:
            return None
        matched = [e for e in entries if e["set_collezione"] == set_slug]
        if len(matched) < min_count:
            return None
        return {
            "slot_indices": [e["slot_index"] for e in matched],
            "carta_codici": [e["codice"] for e in matched],
        }

    if trigger == COMBO_TRIGGER_CARTE:
        required = [str(c).strip() for c in (combo.param_carte_codici or []) if str(c).strip()]
        if not required:
            return None
        present = {e["codice"] for e in entries}
        if not all(code in present for code in required):
            return None
        matched = [e for e in entries if e["codice"] in required]
        return {
            "slot_indices": [e["slot_index"] for e in matched],
            "carta_codici": required,
        }

    if trigger == COMBO_TRIGGER_ENERGIE_NAT:
        naturals = {e["energia"] for e in entries if e["energia"] in CARTA_ENERGIE_NATURALI}
        if len(naturals) < min_count:
            return None
        matched = [e for e in entries if e["energia"] in CARTA_ENERGIE_NATURALI]
        return {
            "slot_indices": [e["slot_index"] for e in matched],
            "carta_codici": [e["codice"] for e in matched],
        }

    if trigger == COMBO_TRIGGER_ENERGIE_SOP:
        sopra = {e["energia"] for e in entries if e["energia"] in CARTA_ENERGIE_SOPRANNATURALI}
        if len(sopra) < min_count:
            return None
        matched = [e for e in entries if e["energia"] in CARTA_ENERGIE_SOPRANNATURALI]
        return {
            "slot_indices": [e["slot_index"] for e in matched],
            "carta_codici": [e["codice"] for e in matched],
        }

    return None


def calcola_combo_reliquiario_attive(personaggio) -> list[dict]:
    entries = _equipped_entries(personaggio)
    if not entries:
        return []

    combos = (
        ComboReliquiario.objects.filter(
            campagna_id=personaggio.campagna_id,
            attiva=True,
        )
        .order_by("ordine", "nome")
    )
    legami = []
    for combo in combos:
        match = valuta_combo_reliquiario(combo, entries)
        if not match:
            continue
        legami.append({
            "id": str(combo.id),
            "codice": combo.codice,
            "nome": combo.nome,
            "testo": combo.testo or "",
            "descrizione": combo.testo or combo.nome,
            "colore": combo.colore or "#10b981",
            "slot_indices": match["slot_indices"],
            "carta_codici": match["carta_codici"],
        })
    return legami
