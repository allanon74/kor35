"""
Seed idempotente combo reliquiario legacy (ex calcola_legami_attivi hardcoded).

Crea combo fisse (Triade Naturale, Quadrifoglio Astrale) e, opzionalmente,
una combo per ogni legame_id / set_collezione presente nel catalogo campagna.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count

from personaggi.carte_collezionabili_models import (
    COMBO_TRIGGER_ENERGIE_NAT,
    COMBO_TRIGGER_ENERGIE_SOP,
    COMBO_TRIGGER_LEGAME,
    COMBO_TRIGGER_SET,
    CartaCollezionabile,
    ComboReliquiario,
)

# Combo globali (non dipendono dal catalogo)
FIXED_LEGACY_COMBOS: list[dict] = [
    {
        "codice": "triade-naturale",
        "nome": "Triade Naturale",
        "testo": "Marziale, Tecnologica e Innata equipaggiate nel reliquiario.",
        "colore": "#10b981",
        "tipo_trigger": COMBO_TRIGGER_ENERGIE_NAT,
        "param_min_count": 3,
        "ordine": 10,
    },
    {
        "codice": "quadrifoglio-astrale",
        "nome": "Quadrifoglio Astrale",
        "testo": "Quattro energie soprannaturali diverse nel reliquiario.",
        "colore": "#a78bfa",
        "tipo_trigger": COMBO_TRIGGER_ENERGIE_SOP,
        "param_min_count": 4,
        "ordine": 20,
    },
]


def _resolve_campagna(campagna_slug: str | None):
    from personaggi.models import Campagna

    if campagna_slug:
        return Campagna.objects.get(slug=campagna_slug)
    campagna = Campagna.objects.filter(attiva=True).order_by("id").first()
    if not campagna:
        raise ValueError("Nessuna campagna attiva; usa --campagna-slug.")
    return campagna


def _combo_defaults_from_row(row: dict) -> dict:
    return {
        "nome": row["nome"],
        "testo": row.get("testo", ""),
        "colore": row.get("colore", "#10b981"),
        "tipo_trigger": row["tipo_trigger"],
        "param_legame_id": row.get("param_legame_id", ""),
        "param_set_collezione": row.get("param_set_collezione", ""),
        "param_carte_codici": row.get("param_carte_codici") or [],
        "param_min_count": row.get("param_min_count", 2),
        "ordine": row.get("ordine", 0),
        "attiva": row.get("attiva", True),
    }


def _discover_catalog_combos(campagna) -> list[dict]:
    """Combo derivate da legame_id e set_collezione nel catalogo."""
    rows: list[dict] = []

    legami = (
        CartaCollezionabile.objects.filter(campagna=campagna)
        .exclude(legame_id="")
        .values("legame_id")
        .annotate(n=Count("id"))
        .filter(n__gte=2)
        .order_by("legame_id")
    )
    for entry in legami:
        legame_id = entry["legame_id"]
        rows.append({
            "codice": f"legame-{legame_id}",
            "nome": legame_id.replace("-", " ").title(),
            "testo": f"Almeno 2 carte del legame «{legame_id}» equipaggiate.",
            "colore": "#8b5cf6",
            "tipo_trigger": COMBO_TRIGGER_LEGAME,
            "param_legame_id": legame_id,
            "param_min_count": 2,
            "ordine": 100,
        })

    sets = (
        CartaCollezionabile.objects.filter(campagna=campagna)
        .exclude(set_collezione="")
        .values("set_collezione")
        .annotate(n=Count("id"))
        .filter(n__gte=3)
        .order_by("set_collezione")
    )
    for entry in sets:
        set_slug = entry["set_collezione"]
        rows.append({
            "codice": f"set-{set_slug}",
            "nome": f"Echi di {set_slug.replace('-', ' ').title()}",
            "testo": f"Almeno 3 carte del set «{set_slug}» equipaggiate.",
            "colore": "#38bdf8",
            "tipo_trigger": COMBO_TRIGGER_SET,
            "param_set_collezione": set_slug,
            "param_min_count": 3,
            "ordine": 110,
        })

    return rows


def _upsert_combo(campagna, row: dict, *, force: bool) -> str:
    """Ritorna 'created' | 'updated' | 'skipped'."""
    codice = row["codice"]
    defaults = _combo_defaults_from_row(row)
    combo, created = ComboReliquiario.objects.get_or_create(
        campagna=campagna,
        codice=codice,
        defaults=defaults,
    )
    if created:
        return "created"
    if force:
        for key, val in defaults.items():
            setattr(combo, key, val)
        combo.save()
        return "updated"
    return "skipped"


@transaction.atomic
def seed_combo_reliquiario(
    *,
    campagna_slug: str | None = None,
    campagna=None,
    force: bool = False,
    include_catalog_derived: bool = True,
) -> dict:
    """
    Crea combo legacy per campagna. Idempotente: salta codici già presenti (salvo force).
    """
    if campagna is None:
        campagna = _resolve_campagna(campagna_slug)

    rows = list(FIXED_LEGACY_COMBOS)
    if include_catalog_derived:
        rows.extend(_discover_catalog_combos(campagna))

    stats = {"created": 0, "updated": 0, "skipped": 0, "total": len(rows)}
    for row in rows:
        outcome = _upsert_combo(campagna, row, force=force)
        stats[outcome] += 1

    stats["campagna"] = campagna.slug
    stats["campagna_nome"] = campagna.nome
    return stats
