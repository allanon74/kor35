"""Bonus passivi da equip (OGG) nel duello live."""
from __future__ import annotations

DUEL_STAT_KEYS = frozenset({"forza", "robustezza", "iniziativa"})

_SIGLA_TO_DUEL = {
    "FOR": "forza",
    "RES": "robustezza",
    "ROB": "robustezza",
    "INI": "iniziativa",
}


def _normalizza_stat(stat: str | None) -> str | None:
    if not stat:
        return None
    raw = str(stat).strip()
    if not raw:
        return None
    upper = raw.upper()
    if upper in _SIGLA_TO_DUEL:
        return _SIGLA_TO_DUEL[upper]
    lower = raw.lower()
    if lower in DUEL_STAT_KEYS:
        return lower
    return None


def applica_bonus_equip_duello(bonus_equip: dict | None, *, is_leader: bool) -> dict:
    """
    Calcola modificatori Forza / Robustezza / Iniziativa da bonus_equip su OGG in campo.

    Formati supportati in bonus_equip:
    - Legacy reliquiario: {"stat_sigla": "FOR", "valore": 1} → +1 forza in duello se equipaggiato
    - Chiavi piatte: forza, robustezza, iniziativa; opz. forza_se_leader, …
    - Lista duello: {"duello": [{"stat": "forza", "valore": 2}, {"stat": "robustezza", "valore": 2, "se_leader": true}]}
    """
    out = {k: 0 for k in DUEL_STAT_KEYS}
    if not bonus_equip or not isinstance(bonus_equip, dict):
        return out

    sigla_key = _normalizza_stat(bonus_equip.get("stat_sigla"))
    if sigla_key:
        out[sigla_key] += _int_val(bonus_equip.get("valore"))

    for stat in DUEL_STAT_KEYS:
        if stat in bonus_equip:
            out[stat] += _int_val(bonus_equip.get(stat))
        if is_leader:
            se_key = f"{stat}_se_leader"
            if se_key in bonus_equip:
                out[stat] += _int_val(bonus_equip.get(se_key))

    duello_entries = bonus_equip.get("duello")
    if duello_entries is None:
        return out
    if isinstance(duello_entries, dict):
        duello_entries = [duello_entries]
    if not isinstance(duello_entries, list):
        return out

    for entry in duello_entries:
        if not isinstance(entry, dict):
            continue
        if entry.get("se_leader") and not is_leader:
            continue
        stat = _normalizza_stat(entry.get("stat") or entry.get("stat_sigla"))
        if stat not in DUEL_STAT_KEYS:
            continue
        out[stat] += _int_val(entry.get("valore"))
    return out


def _int_val(raw, default: int = 0) -> int:
    try:
        return int(raw)
    except (TypeError, ValueError):
        return default


_REL_SIGLE = frozenset({"FOR", "RES", "ROB", "INI"})


def validate_bonus_equip(value) -> dict:
    """Normalizza e valida bonus_equip da API staff."""
    if value in (None, "", {}):
        return {}
    if isinstance(value, str):
        import json

        try:
            value = json.loads(value)
        except json.JSONDecodeError as exc:
            from django.core.exceptions import ValidationError

            raise ValidationError("bonus_equip: JSON non valido.") from exc
    if not isinstance(value, dict):
        from django.core.exceptions import ValidationError

        raise ValidationError("bonus_equip deve essere un oggetto JSON.")

    out: dict = {}
    sigla = (value.get("stat_sigla") or "").strip().upper()
    if sigla:
        if sigla not in _REL_SIGLE:
            from django.core.exceptions import ValidationError

            raise ValidationError(f"stat_sigla non valida: {sigla}. Usa FOR, RES o INI.")
        out["stat_sigla"] = sigla
        out["valore"] = _int_val(value.get("valore"))

    for stat in DUEL_STAT_KEYS:
        if stat in value and value[stat] not in (None, ""):
            out[stat] = _int_val(value.get(stat))
        se_key = f"{stat}_se_leader"
        if se_key in value and value[se_key] not in (None, ""):
            out[se_key] = _int_val(value.get(se_key))

    duello_raw = value.get("duello")
    if duello_raw is not None:
        entries = duello_raw if isinstance(duello_raw, list) else [duello_raw]
        duello_clean = []
        for i, entry in enumerate(entries):
            if not isinstance(entry, dict):
                from django.core.exceptions import ValidationError

                raise ValidationError(f"bonus_equip.duello[{i}] deve essere un oggetto.")
            stat = _normalizza_stat(entry.get("stat") or entry.get("stat_sigla"))
            if not stat:
                from django.core.exceptions import ValidationError

                raise ValidationError(
                    f"bonus_equip.duello[{i}]: statistica non valida "
                    "(forza, robustezza, iniziativa, FOR, RES, INI)."
                )
            val = _int_val(entry.get("valore"))
            row = {"stat": stat, "valore": val}
            if entry.get("se_leader"):
                row["se_leader"] = True
            if val != 0 or row.get("se_leader"):
                duello_clean.append(row)
        if duello_clean:
            out["duello"] = duello_clean

    return out
