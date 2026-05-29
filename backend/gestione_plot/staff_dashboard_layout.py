"""
Layout globale del menu Dashboard Staff (singleton ConfigurazioneSito).
"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from django.core.exceptions import ValidationError

STAFF_DASHBOARD_LAYOUT_VERSION = 1

KNOWN_STAFF_TOOL_IDS = frozenset({
    "plot",
    "qr-debug",
    "mostri",
    "abilita",
    "cerimoniali",
    "tessiture",
    "infusioni",
    "proposte",
    "oggetti",
    "oggetti-base",
    "tabelle",
    "immagini",
    "inventari",
    "manifesti",
    "nodi",
    "innesco-timer",
    "pilotaggio",
    "effetti-casuali",
    "social-report",
    "risorse-pool",
    "ere-prefetture",
    "carriere-korps",
    "creazione-guidata",
    "dichiarazioni-glossario",
    "arcana-profiles",
    "campagne",
    "maintenance",
    "messaggi",
    "scommesse",
    "manuali-pdf",
    "negozi-mercante",
})

DEFAULT_STAFF_DASHBOARD_LAYOUT: dict[str, Any] = {
    "version": STAFF_DASHBOARD_LAYOUT_VERSION,
    "groups": [
        {
            "id": "evento",
            "label": "Evento in campo",
            "icon": "Map",
            "palette": "indigo",
            "order": 0,
            "collapsed_default": False,
            "tool_ids": [
                "plot",
                "pilotaggio",
                "manifesti",
                "nodi",
                "innesco-timer",
                "qr-debug",
                "scommesse",
                "negozi-mercante",
            ],
        },
        {
            "id": "database",
            "label": "Database regole",
            "icon": "BookOpen",
            "palette": "blue",
            "order": 1,
            "collapsed_default": True,
            "tool_ids": [
                "mostri",
                "abilita",
                "cerimoniali",
                "tessiture",
                "infusioni",
                "oggetti",
                "oggetti-base",
                "tabelle",
                "effetti-casuali",
                "ere-prefetture",
                "carriere-korps",
                "dichiarazioni-glossario",
            ],
        },
        {
            "id": "giocatori",
            "label": "Giocatori e contenuti",
            "icon": "Users",
            "palette": "teal",
            "order": 2,
            "collapsed_default": True,
            "tool_ids": [
                "creazione-guidata",
                "inventari",
                "proposte",
                "immagini",
                "manuali-pdf",
                "risorse-pool",
            ],
        },
        {
            "id": "comunicazione",
            "label": "Comunicazione",
            "icon": "MessageSquare",
            "palette": "emerald",
            "order": 3,
            "collapsed_default": False,
            "tool_ids": ["messaggi", "social-report"],
        },
        {
            "id": "sistema",
            "label": "Sistema",
            "icon": "Settings",
            "palette": "slate",
            "order": 4,
            "collapsed_default": True,
            "tool_ids": ["campagne", "arcana-profiles", "maintenance"],
        },
    ],
    "pinned_tool_ids": ["plot", "messaggi"],
    "tool_labels": {},
}

ALLOWED_GROUP_PALETTES = frozenset({
    "indigo",
    "sky",
    "blue",
    "cyan",
    "teal",
    "emerald",
    "violet",
    "purple",
    "fuchsia",
    "rose",
    "red",
    "orange",
    "amber",
    "stone",
    "slate",
})

ALLOWED_GROUP_ICONS = frozenset({
    "Map",
    "BookOpen",
    "Users",
    "MessageSquare",
    "Settings",
    "Layers",
    "Globe2",
    "Package",
    "QrCode",
    "Sparkles",
})


def default_staff_dashboard_layout() -> dict[str, Any]:
    return deepcopy(DEFAULT_STAFF_DASHBOARD_LAYOUT)


def _coerce_tool_ids(raw: Any) -> list[str]:
    if not isinstance(raw, list):
        return []
    out: list[str] = []
    seen: set[str] = set()
    for item in raw:
        tid = str(item).strip()
        if not tid or tid in seen:
            continue
        if tid not in KNOWN_STAFF_TOOL_IDS:
            raise ValidationError(f"Tool sconosciuto: {tid}")
        seen.add(tid)
        out.append(tid)
    return out


def validate_staff_dashboard_layout(data: Any) -> dict[str, Any]:
    if data is None:
        return default_staff_dashboard_layout()
    if not isinstance(data, dict):
        raise ValidationError("Layout deve essere un oggetto JSON.")

    version = data.get("version", STAFF_DASHBOARD_LAYOUT_VERSION)
    if version != STAFF_DASHBOARD_LAYOUT_VERSION:
        raise ValidationError(f"Versione layout non supportata: {version}")

    groups_in = data.get("groups")
    if groups_in is None:
        groups_in = default_staff_dashboard_layout()["groups"]
    if not isinstance(groups_in, list):
        raise ValidationError("groups deve essere una lista.")

    seen_group_ids: set[str] = set()
    seen_tool_ids: set[str] = set()
    normalized_groups: list[dict[str, Any]] = []

    for idx, group in enumerate(groups_in):
        if not isinstance(group, dict):
            raise ValidationError(f"Gruppo #{idx + 1} non valido.")
        gid = str(group.get("id") or "").strip()
        if not gid:
            raise ValidationError(f"Gruppo #{idx + 1}: id mancante.")
        if gid in seen_group_ids:
            raise ValidationError(f"Gruppo duplicato: {gid}")
        seen_group_ids.add(gid)

        label = str(group.get("label") or "").strip()
        if not label:
            raise ValidationError(f"Gruppo {gid}: label mancante.")

        icon = str(group.get("icon") or "Layers").strip()
        if icon not in ALLOWED_GROUP_ICONS:
            raise ValidationError(f"Gruppo {gid}: icona non consentita ({icon}).")

        palette = str(group.get("palette") or "slate").strip()
        if palette not in ALLOWED_GROUP_PALETTES:
            raise ValidationError(f"Gruppo {gid}: palette non consentita ({palette}).")

        try:
            order = int(group.get("order", idx))
        except (TypeError, ValueError) as exc:
            raise ValidationError(f"Gruppo {gid}: order non valido.") from exc

        collapsed_default = bool(group.get("collapsed_default", False))
        tool_ids = _coerce_tool_ids(group.get("tool_ids"))
        for tid in tool_ids:
            if tid in seen_tool_ids:
                raise ValidationError(f"Tool {tid} presente in più gruppi.")
            seen_tool_ids.add(tid)

        normalized_groups.append({
            "id": gid,
            "label": label,
            "icon": icon,
            "palette": palette,
            "order": order,
            "collapsed_default": collapsed_default,
            "tool_ids": tool_ids,
        })

    normalized_groups.sort(key=lambda g: (g["order"], g["id"]))

    pinned_tool_ids = _coerce_tool_ids(data.get("pinned_tool_ids", []))

    tool_labels_in = data.get("tool_labels") or {}
    if not isinstance(tool_labels_in, dict):
        raise ValidationError("tool_labels deve essere un oggetto.")
    tool_labels: dict[str, str] = {}
    for key, raw_val in tool_labels_in.items():
        tid = str(key).strip()
        if tid not in KNOWN_STAFF_TOOL_IDS:
            raise ValidationError(f"Etichetta per tool sconosciuto: {tid}")
        label_val = str(raw_val or "").strip()
        if not label_val:
            continue
        if len(label_val) > 120:
            raise ValidationError(f"Etichetta troppo lunga per {tid} (max 120).")
        tool_labels[tid] = label_val

    return {
        "version": STAFF_DASHBOARD_LAYOUT_VERSION,
        "groups": normalized_groups,
        "pinned_tool_ids": pinned_tool_ids,
        "tool_labels": tool_labels,
    }


def effective_staff_dashboard_layout(raw: Any) -> dict[str, Any]:
    """Merge layout salvato con default (tool/gruppi mancanti → default + sezione implicita Altro lato client)."""
    if not raw:
        return default_staff_dashboard_layout()
    try:
        return validate_staff_dashboard_layout(raw)
    except ValidationError:
        return default_staff_dashboard_layout()
