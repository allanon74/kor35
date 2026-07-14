"""
Spec `mse_game_spec` per il gioco KOR35 (Card Studio game-first).

Fonte di verità: `carte_collezionabili_models` e `docs/wiki/carte/regolamento-gioco.md`
(Cronache delle Sette Elegie — 7 aure, 4 tipi carta).
"""
from __future__ import annotations

from typing import Any

from personaggi.mse_kor35_symbol_font import KOR35_SYMBOL_FONT_NAME
from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_ARCANA,
    CARTA_ENERGIA_CHOICES,
    CARTA_ENERGIA_INNATA,
    CARTA_ENERGIA_MAGICA,
    CARTA_ENERGIA_MARZIALE,
    CARTA_ENERGIA_PSIONICA,
    CARTA_ENERGIA_SACRA,
    CARTA_ENERGIA_TECNOLOGICA,
    CARTA_RARITA_CHOICES,
    CARTA_RARITA_COMUNE,
    CARTA_RARITA_EPICA,
    CARTA_RARITA_LEGGENDARIA,
    CARTA_RARITA_NON_COMUNE,
    CARTA_RARITA_RARA,
    CARTA_RARITA_UNICA,
    CARTA_TIPO_CHOICES,
    CARTA_TIPO_EVENTO,
    CARTA_TIPO_LUOGO,
    CARTA_TIPO_OGGETTO,
    CARTA_TIPO_PERSONAGGIO,
)

# Bump quando cambiano campi/choice del gioco KOR35 (refresh automatico su merge).
KOR35_MSE_GAME_SPEC_VERSION = "kor35-sette-elegie-2"

KOR35_TYPE_CHOICES = [code for code, _label in CARTA_TIPO_CHOICES]
KOR35_ENERGY_CHOICES = [code for code, _label in CARTA_ENERGIA_CHOICES]
KOR35_RARITY_CHOICES = [code for code, _label in CARTA_RARITA_CHOICES]

# Colori allineati alle Aure Punteggio (sigle AMZ, ATE, …) — vedi tests_carte_collezionabili.
KOR35_TYPE_COLORS = {
    CARTA_TIPO_PERSONAGGIO: "rgb(96,165,250)",
    CARTA_TIPO_OGGETTO: "rgb(250,204,21)",
    CARTA_TIPO_LUOGO: "rgb(74,222,128)",
    CARTA_TIPO_EVENTO: "rgb(244,114,182)",
}

KOR35_ENERGY_COLORS = {
    CARTA_ENERGIA_MARZIALE: "rgb(76,54,245)",      # Blu — naturale
    CARTA_ENERGIA_TECNOLOGICA: "rgb(250,246,16)",  # Giallo — naturale
    CARTA_ENERGIA_INNATA: "rgb(199,158,11)",       # Arancione — naturale
    CARTA_ENERGIA_MAGICA: "rgb(0,0,0)",            # Nero — soprannaturale
    CARTA_ENERGIA_SACRA: "rgb(255,255,255)",       # Bianco — soprannaturale
    CARTA_ENERGIA_PSIONICA: "rgb(239,170,255)",    # Viola — soprannaturale
    CARTA_ENERGIA_ARCANA: "rgb(146,250,136)",      # Verde — soprannaturale
}

KOR35_RARITY_COLORS = {
    CARTA_RARITA_COMUNE: "rgb(156,163,175)",
    CARTA_RARITA_NON_COMUNE: "rgb(34,197,94)",
    CARTA_RARITA_RARA: "rgb(59,130,246)",
    CARTA_RARITA_EPICA: "rgb(168,85,247)",
    CARTA_RARITA_LEGGENDARIA: "rgb(250,204,21)",
    CARTA_RARITA_UNICA: "rgb(239,68,68)",
}

KOR35_ENERGY_LABELS = dict(CARTA_ENERGIA_CHOICES)
KOR35_TYPE_LABELS = dict(CARTA_TIPO_CHOICES)
KOR35_RARITY_LABELS = dict(CARTA_RARITA_CHOICES)


def _package_choice_field(
    name: str,
    *,
    match: str,
    initial: str = "",
    required: bool = False,
    description: str = "",
) -> dict[str, Any]:
    return {
        "name": name,
        "type": "package choice",
        "editable": True,
        "multi_line": False,
        "identifying": False,
        "choices": [],
        "choice_colors": {},
        "choice_colors_cardlist": {},
        "default": "",
        "initial": initial,
        "description": description,
        "match": match,
        "required": required,
        "empty_name": "(none)",
        "card_list_name": name,
        "card_list_visible": False,
        "card_list_allow": False,
        "show_statistics": False,
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
    energy_desc = (
        "Aura della carta (KOR35: energia). "
        "Naturali: Marziale MAR, Tecnologica TEC, Innata INN. "
        "Soprannaturali: Magica MAG, Sacra SAC, Psionica PSI, Arcana ARC. "
        "Le terre (LUO) non hanno aura."
    )
    type_desc = (
        "Tipo carta Sette Elegie (KOR35: tipo): "
        "PG Personaggio, OGG Equipaggiamento, LUO Terra, EVT Effetto monouso."
    )
    return {
        "version": KOR35_MSE_GAME_SPEC_VERSION,
        "has_keywords": True,
        "keyword_modes": ["kor35", "reminder"],
        "card_list_color_script": "",
        "card_fields": [
            _text_field(
                "code",
                card_list_visible=True,
                card_list_column=0,
                description=(
                    "Codice carta: codice set + trattino + numero a 3 cifre "
                    "(es. sette-elegie-001). Assegnato automaticamente alla creazione."
                ),
            ),
            _text_field(
                "name",
                identifying=True,
                card_list_visible=True,
                card_list_column=1,
                description="Nome carta (KOR35: nome).",
            ),
            _choice_field(
                "type",
                choices=KOR35_TYPE_CHOICES,
                choice_colors_cardlist=KOR35_TYPE_COLORS,
                card_list_visible=True,
                card_list_column=2,
                initial=CARTA_TIPO_PERSONAGGIO,
                description=type_desc,
            ),
            _choice_field(
                "energy",
                choices=KOR35_ENERGY_CHOICES,
                choice_colors_cardlist=KOR35_ENERGY_COLORS,
                card_list_visible=True,
                card_list_column=3,
                initial=CARTA_ENERGIA_MARZIALE,
                description=energy_desc,
            ),
            _choice_field(
                "rarity",
                choices=KOR35_RARITY_CHOICES,
                choice_colors_cardlist=KOR35_RARITY_COLORS,
                card_list_visible=True,
                card_list_column=4,
                initial=CARTA_RARITA_COMUNE,
                description="Rarità catalogo KOR35 (COM, NC, RAR, EPI, LEG, UNI).",
            ),
            _number_field(
                "cost",
                card_list_visible=True,
                card_list_column=5,
                show_statistics=True,
                description="Costo mana 0–3 (KOR35: costo_gioco).",
            ),
            _number_field(
                "attack",
                card_list_column=6,
                description="Forza in combattimento (KOR35: attacco).",
            ),
            _number_field(
                "health",
                card_list_column=7,
                description="Robustezza (KOR35: salute).",
            ),
            _number_field(
                "initiative",
                card_list_column=8,
                description="Iniziativa in combattimento (KOR35: iniziativa).",
            ),
            _text_field(
                "rules",
                multi_line=True,
                show_statistics=False,
                description="Testo regole con keyword KOR35 (KOR35: testo_gioco).",
            ),
            _text_field(
                "lore",
                multi_line=True,
                show_statistics=False,
                description="Testo flavor (KOR35: testo_lore).",
            ),
            _package_choice_field(
                "symbol_font",
                match="KOR35 Aure",
                initial=KOR35_SYMBOL_FONT_NAME,
                required=False,
                description="Font simboli per le 7 Aure in anteprima ed export PNG.",
            ),
        ],
        "set_fields": [
            _text_field("title", identifying=True),
            _text_field("description", multi_line=True),
            _text_field("code"),
        ],
        "pack_items": [
            {
                "name": "rare+",
                "select": "no replace",
                "filter": {
                    "kind": "script",
                    "expr": (
                        'card.rarity == "RAR" or card.rarity == "EPI" '
                        'or card.rarity == "LEG" or card.rarity == "UNI"'
                    ),
                },
            },
            {
                "name": "non common",
                "select": "no replace",
                "filter": {"kind": "script", "expr": 'card.rarity == "NC"'},
            },
            {
                "name": "common",
                "select": "no replace",
                "filter": {"kind": "script", "expr": 'card.rarity == "COM"'},
            },
        ],
        "pack_types": [
            {
                "name": "Sette Elegie booster",
                "select": "all",
                "selectable": True,
                "summary": True,
                "enabled": True,
                "items": [
                    {"name": "rare+", "amount": {"kind": "literal", "value": "1"}},
                    {"name": "non common", "amount": {"kind": "literal", "value": "3"}},
                    {"name": "common", "amount": {"kind": "literal", "value": "11"}},
                ],
            },
        ],
        "kor35_energy_labels": KOR35_ENERGY_LABELS,
        "kor35_type_labels": KOR35_TYPE_LABELS,
        "kor35_rarity_labels": KOR35_RARITY_LABELS,
    }


def _kor35_spec_is_stale(spec: dict | None) -> bool:
    """True se la spec è il vecchio placeholder (6 elementi MTG-like) o pre-Sette Elegie."""
    if not spec:
        return True
    if spec.get("version") == KOR35_MSE_GAME_SPEC_VERSION:
        return False
    if spec.get("version") in (None, "", "1"):
        return True
    for field in spec.get("card_fields") or []:
        if field.get("name") != "energy":
            continue
        names = [c.get("name") for c in field.get("choices") or []]
        if len(names) != 7:
            return True
        if any(code in names for code in ("FUO", "OMB", "LUC", "NAT")):
            return True
        expected = set(KOR35_ENERGY_CHOICES)
        if set(names) != expected:
            return True
    return False


def merge_kor35_game_meta(meta: dict | None, *, force_refresh: bool = False) -> dict:
    """Aggiunge o aggiorna mse_game_spec KOR35 (7 aure Sette Elegie)."""
    merged = dict(meta or {})
    existing = merged.get("mse_game_spec")
    canonical = kor35_mse_game_spec()

    if force_refresh or _kor35_spec_is_stale(existing):
        merged["mse_game_spec"] = canonical
        return merged

    spec = dict(existing)
    if not spec.get("pack_types"):
        spec["pack_types"] = canonical.get("pack_types", [])
        spec["pack_items"] = canonical.get("pack_items", [])
        merged["mse_game_spec"] = spec
    return merged
