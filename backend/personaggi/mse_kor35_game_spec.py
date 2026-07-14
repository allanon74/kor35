"""
Spec `mse_game_spec` per il gioco KOR35 (Card Studio game-first).
Usata da bootstrap gioco quando modello_base=kor35 e meta non ha ancora uno spec.
"""
from __future__ import annotations

from typing import Any

KOR35_TYPE_CHOICES = ["PG", "Creatura", "Evento", "Supporto", "Incantesimo"]
KOR35_ENERGY_CHOICES = ["MAR", "FUO", "NAT", "OMB", "LUC", "ARC"]
KOR35_RARITY_CHOICES = ["COM", "NON", "RAR", "MIT", "UNI"]

KOR35_TYPE_COLORS = {
    "PG": "rgb(96,165,250)",
    "Creatura": "rgb(74,222,128)",
    "Evento": "rgb(250,204,21)",
    "Supporto": "rgb(192,132,252)",
    "Incantesimo": "rgb(244,114,182)",
}

KOR35_ENERGY_COLORS = {
    "MAR": "rgb(59,130,246)",
    "FUO": "rgb(239,68,68)",
    "NAT": "rgb(34,197,94)",
    "OMB": "rgb(107,114,128)",
    "LUC": "rgb(250,204,21)",
    "ARC": "rgb(168,85,247)",
}

KOR35_RARITY_COLORS = {
    "COM": "rgb(156,163,175)",
    "NON": "rgb(34,197,94)",
    "RAR": "rgb(59,130,246)",
    "MIT": "rgb(168,85,247)",
    "UNI": "rgb(250,204,21)",
}


def _choice_field(
    name: str,
    *,
    choices: list[str],
    choice_colors_cardlist: dict[str, str] | None = None,
    identifying: bool = False,
    card_list_visible: bool = False,
    card_list_column: int = 0,
    show_statistics: bool = True,
    initial: str = "",
    description: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "choice",
        "editable": True,
        "multi_line": False,
        "identifying": identifying,
        "choices": [{"name": c} for c in choices],
        "choice_colors": dict(choice_colors_cardlist or {}),
        "choice_colors_cardlist": dict(choice_colors_cardlist or {}),
        "default": "",
        "initial": initial,
        "description": description,
        "card_list_name": name,
        "card_list_visible": card_list_visible,
        "card_list_allow": True,
        "card_list_alignment": "left",
        "card_list_column": card_list_column,
        "card_list_width": 100,
        "show_statistics": show_statistics,
        "match": "",
        "required": True,
        "empty_name": "None",
    }


def _text_field(
    name: str,
    *,
    multi_line: bool = False,
    identifying: bool = False,
    card_list_visible: bool = False,
    card_list_column: int = 0,
    show_statistics: bool = False,
    description: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "text",
        "editable": True,
        "multi_line": multi_line,
        "identifying": identifying,
        "choices": [],
        "choice_colors": {},
        "choice_colors_cardlist": {},
        "default": "",
        "initial": "",
        "description": description,
        "card_list_name": name,
        "card_list_visible": card_list_visible,
        "card_list_allow": True,
        "card_list_alignment": "left",
        "card_list_column": card_list_column,
        "card_list_width": 100,
        "show_statistics": show_statistics,
        "match": "",
        "required": True,
        "empty_name": "None",
    }


def _number_field(
    name: str,
    *,
    card_list_visible: bool = False,
    card_list_column: int = 0,
    show_statistics: bool = False,
    initial: str = "0",
    description: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "number",
        "editable": True,
        "multi_line": False,
        "identifying": False,
        "choices": [],
        "choice_colors": {},
        "choice_colors_cardlist": {},
        "default": "",
        "initial": initial,
        "description": description,
        "card_list_name": name,
        "card_list_visible": card_list_visible,
        "card_list_allow": True,
        "card_list_alignment": "left",
        "card_list_column": card_list_column,
        "card_list_width": 72,
        "show_statistics": show_statistics,
        "match": "",
        "required": True,
        "empty_name": "None",
    }


def kor35_mse_game_spec() -> dict[str, Any]:
    return {
        "version": "1",
        "has_keywords": True,
        "keyword_modes": ["kor35", "reminder"],
        "card_list_color_script": "",
        "card_fields": [
            _text_field(
                "code",
                card_list_visible=True,
                card_list_column=0,
                description="Unique card code in the set (KOR35: codice).",
            ),
            _text_field(
                "name",
                identifying=True,
                card_list_visible=True,
                card_list_column=1,
                description="Card name shown on the template (KOR35: nome).",
            ),
            _choice_field(
                "type",
                choices=KOR35_TYPE_CHOICES,
                choice_colors_cardlist=KOR35_TYPE_COLORS,
                card_list_visible=True,
                card_list_column=2,
                initial="PG",
                description="Card type line (KOR35: tipo).",
            ),
            _choice_field(
                "energy",
                choices=KOR35_ENERGY_CHOICES,
                choice_colors_cardlist=KOR35_ENERGY_COLORS,
                card_list_visible=True,
                card_list_column=3,
                initial="MAR",
                description="Energy / sphere (KOR35: energia).",
            ),
            _choice_field(
                "rarity",
                choices=KOR35_RARITY_CHOICES,
                choice_colors_cardlist=KOR35_RARITY_COLORS,
                card_list_visible=True,
                card_list_column=4,
                initial="COM",
                description="Rarity tier; used by statistics and random packs.",
            ),
            _number_field(
                "cost",
                card_list_visible=True,
                card_list_column=5,
                show_statistics=True,
                description="Play cost 0–3 (KOR35: costo_gioco).",
            ),
            _number_field("attack", card_list_column=6, description="Attack value (KOR35: attacco / forza)."),
            _number_field("health", card_list_column=7, description="Health value (KOR35: salute / robustezza)."),
            _number_field("initiative", card_list_column=8, description="Initiative (KOR35: iniziativa)."),
            _text_field(
                "rules",
                multi_line=True,
                show_statistics=False,
                description="Rules text with KOR35 keyword markup (KOR35: testo_gioco).",
            ),
            _text_field(
                "lore",
                multi_line=True,
                show_statistics=False,
                description="Flavor text for card back (KOR35: testo_lore).",
            ),
        ],
        "set_fields": [
            _text_field("title", identifying=True),
            _text_field("description", multi_line=True),
            _text_field("code"),
        ],
        "pack_items": [
            {
                "name": "rare",
                "select": "no replace",
                "filter": {"kind": "script", "expr": 'card.rarity == "RAR" or card.rarity == "MIT" or card.rarity == "UNI"'},
            },
            {
                "name": "non common",
                "select": "no replace",
                "filter": {"kind": "script", "expr": 'card.rarity == "NON"'},
            },
            {
                "name": "common",
                "select": "no replace",
                "filter": {"kind": "script", "expr": 'card.rarity == "COM"'},
            },
        ],
        "pack_types": [
            {
                "name": "KOR35 booster",
                "select": "all",
                "selectable": True,
                "summary": True,
                "enabled": True,
                "items": [
                    {"name": "rare", "amount": {"kind": "literal", "value": "1"}},
                    {"name": "non common", "amount": {"kind": "literal", "value": "3"}},
                    {"name": "common", "amount": {"kind": "literal", "value": "11"}},
                ],
            },
        ],
    }


def merge_kor35_game_meta(meta: dict | None) -> dict:
    """Aggiunge mse_game_spec KOR35 se assente (inclusi pack types demo)."""
    merged = dict(meta or {})
    if not merged.get("mse_game_spec"):
        merged["mse_game_spec"] = kor35_mse_game_spec()
        return merged
    spec = dict(merged["mse_game_spec"])
    if not spec.get("pack_types"):
        default = kor35_mse_game_spec()
        spec["pack_types"] = default.get("pack_types", [])
        spec["pack_items"] = default.get("pack_items", [])
        merged["mse_game_spec"] = spec
    return merged
