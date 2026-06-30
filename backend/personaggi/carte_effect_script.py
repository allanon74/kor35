"""
Validazione e helper per EffectScript v1 (duello carte).
Schema: carte_effect_schema.json
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import jsonschema
from django.core.exceptions import ValidationError

from personaggi.carte_keyword_utils import placeholder_nomi

SCHEMA_PATH = Path(__file__).with_name("carte_effect_schema.json")
EFFECT_SCRIPT_VERSION = 1

_SCHEMA: dict | None = None
_VALIDATOR: jsonschema.Draft202012Validator | None = None


def _load_schema() -> dict:
    global _SCHEMA
    if _SCHEMA is None:
        with SCHEMA_PATH.open(encoding="utf-8") as fh:
            _SCHEMA = json.load(fh)
    return _SCHEMA


def get_effect_script_schema() -> dict:
    return _load_schema()


def _validator() -> jsonschema.Draft202012Validator:
    global _VALIDATOR
    if _VALIDATOR is None:
        _VALIDATOR = jsonschema.Draft202012Validator(_load_schema())
    return _VALIDATOR


def _format_schema_errors(errors) -> str:
    msgs = []
    for err in sorted(errors, key=lambda e: list(e.path)):
        path = ".".join(str(p) for p in err.path) or "(root)"
        msgs.append(f"{path}: {err.message}")
    return "; ".join(msgs[:8])


def validate_effect_script(script: Any) -> dict:
    """Valida struttura JSON; ritorna script normalizzato (dict)."""
    if script in (None, "", {}):
        return {}
    if not isinstance(script, dict):
        raise ValidationError("effect_script deve essere un oggetto JSON.")
    errors = list(_validator().iter_errors(script))
    if errors:
        raise ValidationError(f"Script effetti non valido: {_format_schema_errors(errors)}")
    _validate_step_ids_unique(script)
    _validate_choice_refs(script)
    return script


def _validate_step_ids_unique(script: dict):
    seen: set[str] = set()
    for step in script.get("steps") or []:
        if step.get("type") != "player_choice":
            continue
        sid = step.get("id")
        if sid in seen:
            raise ValidationError(f"ID scelta duplicato: {sid}")
        seen.add(sid)


def _validate_choice_refs(script: dict):
    choice_ids = {
        s["id"]
        for s in (script.get("steps") or [])
        if s.get("type") == "player_choice" and s.get("id")
    }
    for step in script.get("steps") or []:
        for field in ("with", "target"):
            ref = _extract_ref(step.get(field))
            if ref and ref.startswith("choice."):
                cid = ref.split(".", 1)[1]
                if cid not in choice_ids:
                    raise ValidationError(f"Riferimento a scelta sconosciuta: {ref}")


def _extract_ref(value) -> str | None:
    if isinstance(value, dict) and "ref" in value:
        return str(value["ref"])
    return None


def validate_effect_script_for_keyword(script: Any, *, nome: str, codice: str = "") -> dict:
    """Allinea params dello script ai placeholder della keyword."""
    script = validate_effect_script(script)
    if not script:
        return {}
    placeholders = placeholder_nomi(nome) or placeholder_nomi(codice)
    declared = script.get("params") or {}
    for ph in placeholders:
        if ph not in declared:
            raise ValidationError(
                f"Lo script deve dichiarare il parametro '{ph}' in params "
                f"(from_placeholder per allineamento con la keyword)."
            )
        pdef = declared[ph]
        if pdef.get("from_placeholder") and pdef["from_placeholder"] != ph:
            raise ValidationError(
                f"params.{ph}.from_placeholder deve essere '{ph}'."
            )
    return script


def resolve_param_values(script: dict, keyword_params: dict[str, str] | None) -> dict[str, int | str]:
    """Risolve param.X da match keyword + default nello script."""
    out: dict[str, int | str] = {}
    keyword_params = keyword_params or {}
    for name, pdef in (script.get("params") or {}).items():
        raw = keyword_params.get(name)
        if raw is None:
            if "default" in pdef:
                raw = pdef["default"]
            else:
                continue
        if pdef.get("type") == "int":
            try:
                out[name] = int(raw)
            except (TypeError, ValueError):
                out[name] = 0
        else:
            out[name] = str(raw)
    return out


def resolve_value_ref(value, *, params: dict, choices: dict, context: dict | None = None):
    """Risolve literal, param.X, choice.id, context.key."""
    context = context or {}
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        return value
    if isinstance(value, dict) and "ref" in value:
        ref = value["ref"]
        if ref.startswith("param."):
            key = ref.split(".", 1)[1]
            return params.get(key)
        if ref.startswith("choice."):
            key = ref.split(".", 1)[1]
            return choices.get(key)
        if ref.startswith("context."):
            key = ref.split(".", 1)[1]
            return context.get(key)
        raise ValidationError(f"Riferimento non supportato: {ref}")
    return value


def mutazione_effect_script_template() -> dict:
    """Script di riferimento per keyword Mutazione [X]."""
    return {
        "version": EFFECT_SCRIPT_VERSION,
        "params": {
            "X": {"type": "int", "from_placeholder": "X", "default": 0},
        },
        "trigger": {"event": "on_exhaust", "source": "this"},
        "steps": [
            {
                "type": "player_choice",
                "id": "replacement",
                "prompt": "Scegli un Personaggio dalla mano con costo gioco ≤ {X}",
                "optional": True,
                "min": 0,
                "max": 1,
                "filter": {
                    "zone": "hand",
                    "owner": "controller",
                    "card_type": "PG",
                    "cost_play_lte": {"ref": "param.X"},
                },
            },
            {
                "type": "replace",
                "slot": "this",
                "with": {"ref": "choice.replacement"},
                "skip_if_no_choice": True,
            },
        ],
    }


def colpo_influenza_effect_script_template() -> dict:
    """Script on_play: infligge X danni all'influenza avversaria."""
    return {
        "version": EFFECT_SCRIPT_VERSION,
        "params": {
            "X": {"type": "int", "from_placeholder": "X", "default": 1},
        },
        "trigger": {"event": "on_play", "source": "this"},
        "steps": [
            {
                "type": "deal_damage",
                "target": "opponent_influence",
                "amount": {"ref": "param.X"},
            },
        ],
    }


def pesca_effect_script_template() -> dict:
    """Script on_turn_start: pesca X carte dal mazzo."""
    return {
        "version": EFFECT_SCRIPT_VERSION,
        "params": {
            "X": {"type": "int", "from_placeholder": "X", "default": 1},
        },
        "trigger": {"event": "on_turn_start", "source": "self"},
        "steps": [
            {
                "type": "draw_cards",
                "count": {"ref": "param.X"},
                "target": "self",
            },
        ],
    }


def rigenerazione_energia_effect_script_template() -> dict:
    """Script on_play: guadagni X energia."""
    return {
        "version": EFFECT_SCRIPT_VERSION,
        "params": {
            "X": {"type": "int", "from_placeholder": "X", "default": 1},
        },
        "trigger": {"event": "on_play", "source": "this"},
        "steps": [
            {
                "type": "modify_energy",
                "target": "self",
                "delta": {"ref": "param.X"},
            },
        ],
    }


def danno_eroe_effect_script_template() -> dict:
    """Script on_play: scegli eroe avversario e infliggi X danni."""
    return {
        "version": EFFECT_SCRIPT_VERSION,
        "params": {
            "X": {"type": "int", "from_placeholder": "X", "default": 1},
        },
        "trigger": {"event": "on_play", "source": "this"},
        "steps": [
            {
                "type": "player_choice",
                "id": "bersaglio",
                "prompt": "Scegli un eroe avversario da colpire per {X} danni",
                "filter": {
                    "target": "hero",
                    "owner": "opponent",
                    "occupied": True,
                },
            },
            {
                "type": "deal_damage",
                "target": {"ref": "choice.bersaglio"},
                "amount": {"ref": "param.X"},
            },
        ],
    }
