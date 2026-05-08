from dataclasses import dataclass

from .models import DEFAULT_FORMULA_TEMPLATE, formatta_testo_generico


FORMULA_BUILDER_SCHEMA = {
    "default_template": DEFAULT_FORMULA_TEMPLATE,
    "types": [
        {"id": "attack", "label": "Attacco"},
        {"id": "weave", "label": "Tessitura"},
        {"id": "capacity", "label": "Capacita"},
    ],
    "type_templates": {
        "attack": ["rango", "molt", "formula_prefix", "formula_source", "formula_status"],
        "weave": ["formula_type", "rango", "molt", "formula_prefix", "formula_source", "formula_status"],
        "capacity": ["formula_type", "formula_prefix", "formula_source", "formula_status"],
    },
    "sections": [
        {
            "id": "formula_type",
            "label": "Tipo Tessitura",
            "kind": "single",
            "options": [
                {"id": "aura", "label": "Aura", "stats": {"aura": 1}},
                {"id": "proiett", "label": "Proiettile", "stats": {"proiett": 1}},
                {"id": "manovra", "label": "Manovra", "stats": {"manovra": 1}},
            ],
        },
        {
            "id": "formula_prefix",
            "label": "Efficacia",
            "kind": "multi",
            "options": [
                {"id": "prefisso_puro", "label": "Puro", "stats": {"prefisso_puro": 1}},
                {"id": "prefisso_diretto", "label": "Diretto", "stats": {"prefisso_diretto": 1}},
                {"id": "prefisso_ineluttabile", "label": "Ineluttabile", "stats": {"prefisso_ineluttabile": 1}},
            ],
        },
        {
            "id": "formula_target",
            "label": "Bersaglio",
            "kind": "single",
            "options": [
                {"id": "flusso", "label": "Flusso", "stats": {"flusso": 1}},
                {"id": "dardo", "label": "Dardo", "stats": {"dardo": 1, "gittata": 3}},
                {"id": "tocco", "label": "Tocco", "stats": {"tocco": 1}},
                {"id": "cono", "label": "Cono", "stats": {"cono": 1}},
                {"id": "esplos", "label": "Esplosione", "stats": {"esplos": 1}},
                {"id": "tutti", "label": "Tutti", "stats": {"tutti": 1}},
            ],
        },
        {
            "id": "formula_source",
            "label": "Sorgente",
            "kind": "single",
            "options": [
                {"id": "none", "label": "Nessuna", "stats": {}},
                {"id": "chop", "label": "Chop", "stats": {"chop": 1}},
                {"id": "blam", "label": "Blam", "stats": {"blam": 1}},
                {"id": "pierce", "label": "Pierce", "stats": {"pierce": 1}},
                {"id": "mental", "label": "Mental", "stats": {"mental": 1}},
            ],
        },
        {
            "id": "formula_status",
            "label": "Stato",
            "kind": "single",
            "options": [
                {"id": "none", "label": "Nessuno", "stats": {}},
                {"id": "aterra", "label": "A Terra", "stats": {"aterra": 1}},
                {"id": "paralisi", "label": "Paralisi", "stats": {"paralisi": 1}},
                {"id": "repuls", "label": "Repulsione", "stats": {"repuls": 1}},
                {"id": "richiamo", "label": "Richiamo", "stats": {"richiamo": 1}},
                {"id": "esilio", "label": "Esilio", "stats": {"esilio": 1}},
                {"id": "confus", "label": "Confusione", "stats": {"confus": 1}},
                {"id": "silenzio", "label": "Silenzio", "stats": {"silenzio": 1}},
                {"id": "spacca", "label": "Spacca", "stats": {"spacca": 1}},
                {"id": "nega", "label": "Nega", "stats": {"nega": 1}},
                {"id": "disint", "label": "Disintegrazione", "stats": {"disint": 1}},
                {"id": "ripara", "label": "Ripara", "stats": {"ripara": 1}},
            ],
        },
        {
            "id": "formula_damage",
            "label": "Danno",
            "kind": "single",
            "options": [
                {"id": "none", "label": "Nessuno", "stats": {}},
                {"id": "mischia", "label": "Mischia", "stats": {"dannimis": 1}},
                {"id": "distanza", "label": "Distanza", "stats": {"dannidis": 1}},
            ],
        },
    ],
}

FORMULA_CONTROLLED_PARAMS = {
    "aura",
    "proiett",
    "manovra",
    "prefisso_puro",
    "prefisso_diretto",
    "prefisso_ineluttabile",
    "flusso",
    "dardo",
    "tocco",
    "cono",
    "esplos",
    "tutti",
    "chop",
    "blam",
    "pierce",
    "mental",
    "aterra",
    "paralisi",
    "repuls",
    "richiamo",
    "esilio",
    "confus",
    "silenzio",
    "spacca",
    "nega",
    "disint",
    "ripara",
    "dannimis",
    "dannidis",
    "cura",
}


def _iter_selected_options(selections):
    if not isinstance(selections, dict):
        return
    sections = FORMULA_BUILDER_SCHEMA.get("sections") or []
    for section in sections:
        section_id = section.get("id")
        if not section_id:
            continue
        selected = selections.get(section_id)
        if selected is None:
            continue
        selected_ids = selected if isinstance(selected, list) else [selected]
        valid_options = {o.get("id"): o for o in (section.get("options") or [])}
        for option_id in selected_ids:
            option = valid_options.get(option_id)
            if option:
                yield option


def build_stats_by_selection(current_stats, selections):
    stats = dict(current_stats or {})
    for param in FORMULA_CONTROLLED_PARAMS:
        stats[param] = 0
    for option in _iter_selected_options(selections):
        for param, value in (option.get("stats") or {}).items():
            stats[param] = value
    return stats


@dataclass
class _FakeStatistica:
    parametro: str
    valore_base_predefinito: int = 0


@dataclass
class _FakeStatItem:
    statistica: _FakeStatistica
    valore_base: int = 0


def render_formula_preview(formula, stats_by_param, context=None):
    items = [
        _FakeStatItem(statistica=_FakeStatistica(parametro=param), valore_base=value)
        for param, value in (stats_by_param or {}).items()
    ]
    return formatta_testo_generico(
        testo="",
        formula=formula or DEFAULT_FORMULA_TEMPLATE,
        statistiche_base=items,
        personaggio=None,
        context=context or {},
        solo_formula=True,
    )


def build_formula_template(formula_type, selections):
    templates = FORMULA_BUILDER_SCHEMA.get("type_templates") or {}
    blocks = templates.get(formula_type) or templates.get("attack") or []
    if not blocks:
        return DEFAULT_FORMULA_TEMPLATE

    selected_map = selections if isinstance(selections, dict) else {}

    def _section_selected(section_id):
        selected = selected_map.get(section_id)
        if selected is None:
            return False
        if isinstance(selected, list):
            return any(str(x).strip().lower() != "none" for x in selected)
        return str(selected).strip().lower() != "none"

    placeholder_by_block = {
        "formula_type": "{formula_type}",
        "rango": "{rango|:RANGO}",
        "molt": "{molt|:MOLT}",
        "formula_prefix": "{formula_prefix}",
        "formula_target": "{formula_target}",
        "formula_source": "{formula_source}",
        "formula_status": "{formula_status}",
        "formula_cura": "{formula_cura}",
        "formula_damage": "{formula_damage}",
    }

    include_cura = bool(selected_map.get("include_cura"))
    include_danni = bool(selected_map.get("include_danni"))
    damage_mode = str(selected_map.get("damage_mode") or "").strip().lower()

    out = []
    for block in blocks:
        placeholder = placeholder_by_block.get(block)
        if not placeholder:
            continue
        if block in ("rango", "molt"):
            out.append(placeholder)
            continue
        if _section_selected(block):
            out.append(placeholder)

    if include_cura:
        out.append("{formula_cura}")

    if include_danni:
        if damage_mode == "distanza":
            out.append("{dannidis + dannigen|L}")
        else:
            out.append("{dannimis + dannigen|L}")

    return "".join(out) or DEFAULT_FORMULA_TEMPLATE
