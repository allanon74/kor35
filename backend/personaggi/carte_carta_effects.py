"""
EffectScript v1 legati alla carta (non alle keyword condivise).
"""
from __future__ import annotations

from typing import Any

from django.core.exceptions import ValidationError

from personaggi.carte_effect_script import validate_effect_script

CARTA_EFFECT_EVENT_LABELS = {
    "on_play": "Ingresso in gioco",
    "on_exhaust": "Alla morte / esaurimento",
    "manual": "Attivabile",
    "on_turn_start": "Continuo (inizio turno)",
    "on_turn_end": "Continuo (fine turno)",
    "on_attack": "Dopo attacco",
}

MAX_CARTA_EFFECT_SCRIPTS = 12


def _parse_json_list(value) -> list:
    if value in (None, "", []):
        return []
    if isinstance(value, str):
        import json

        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            raise ValidationError("effect_scripts: JSON non valido.") from exc
    if not isinstance(value, list):
        raise ValidationError("effect_scripts deve essere un array JSON.")
    return value


def normalize_carta_effect_entry(raw: Any, *, index: int = 0) -> dict:
    """Normalizza una voce {codice?, nome?, script}."""
    if not isinstance(raw, dict):
        raise ValidationError(f"effect_scripts[{index}] deve essere un oggetto.")
    script = raw.get("script")
    if not isinstance(script, dict):
        raise ValidationError(f"effect_scripts[{index}].script è obbligatorio.")
    script = validate_effect_script(script)
    event = (script.get("trigger") or {}).get("event")
    if event not in CARTA_EFFECT_EVENT_LABELS:
        raise ValidationError(f"effect_scripts[{index}]: trigger.event non valido.")
    codice = (raw.get("codice") or "").strip().upper()
    nome = (raw.get("nome") or "").strip()
    if event == "manual" and not codice and not nome:
        raise ValidationError(
            f"effect_scripts[{index}]: le abilità manuali richiedono almeno codice o nome."
        )
    return {
        "codice": codice,
        "nome": nome,
        "script": script,
    }


def validate_carta_effect_scripts(value) -> list[dict]:
    entries = _parse_json_list(value)
    if len(entries) > MAX_CARTA_EFFECT_SCRIPTS:
        raise ValidationError(f"Massimo {MAX_CARTA_EFFECT_SCRIPTS} script per carta.")
    out = [normalize_carta_effect_entry(e, index=i) for i, e in enumerate(entries)]
    codici = [e["codice"] for e in out if e["codice"]]
    if len(codici) != len(set(codici)):
        raise ValidationError("effect_scripts: codici duplicati sulla stessa carta.")
    return out


def carta_effect_scripts_raw(carta) -> list[dict]:
    if isinstance(carta, dict):
        return carta.get("effect_scripts") or []
    return getattr(carta, "effect_scripts", None) or []


def iter_carta_scripts_for_event(carta, event: str) -> list[tuple[int, dict, dict]]:
    """(indice, entry, script) per ogni script carta con trigger.event == event."""
    out: list[tuple[int, dict, dict]] = []
    for idx, raw in enumerate(carta_effect_scripts_raw(carta)):
        try:
            entry = normalize_carta_effect_entry(raw, index=idx)
        except ValidationError:
            continue
        script = entry["script"]
        if (script.get("trigger") or {}).get("event") == event:
            out.append((idx, entry, script))
    return out


def lista_abilita_manuali_carta(carta) -> list[dict]:
    """Metadati abilità manuali per UI duello."""
    out: list[dict] = []
    for idx, entry, _script in iter_carta_scripts_for_event(carta, "manual"):
        label = entry.get("nome") or entry.get("codice") or f"Abilità {idx + 1}"
        out.append({
            "index": idx,
            "codice": entry.get("codice") or "",
            "nome": label,
        })
    return out


def trova_script_manuale_carta(carta, *, script_index: int | None, script_codice: str | None) -> tuple[int, dict, dict]:
    matches = iter_carta_scripts_for_event(carta, "manual")
    if not matches:
        raise ValidationError("Questa carta non ha abilità attivabili.")
    if script_codice:
        code = script_codice.strip().upper()
        for idx, entry, script in matches:
            if entry.get("codice") == code:
                return idx, entry, script
        raise ValidationError("Abilità manuale non trovata.")
    if script_index is None:
        raise ValidationError("script_index o script_codice richiesto.")
    try:
        idx = int(script_index)
    except (TypeError, ValueError) as exc:
        raise ValidationError("script_index non valido.") from exc
    for entry_idx, entry, script in matches:
        if entry_idx == idx:
            return entry_idx, entry, script
    raise ValidationError("Abilità manuale non trovata.")
