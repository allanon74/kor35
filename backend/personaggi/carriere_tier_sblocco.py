"""
Logica tier sbloccati da carriere/KORP per l'acquisto abilità.
"""

from __future__ import annotations

from django.core.cache import cache
from django.db.models import QuerySet

from personaggi.models import (
    TIER_1,
    TIER_2,
    TIER_3,
    TIER_4,
    Carriera,
    CarrieraTierSblocco,
    PersonaggioCarrieraMembership,
    SegnoZodiacale,
    Tier,
)


def tiers_selezionabili_per_sblocco_carriera() -> QuerySet:
    """Tier assegnabili come pool abilità (esclusi carriere/segni zodiacali)."""
    esclusi = set(Carriera.objects.values_list("pk", flat=True))
    esclusi.update(SegnoZodiacale.objects.values_list("pk", flat=True))
    return Tier.objects.filter(tipo__in=(TIER_1, TIER_2, TIER_3, TIER_4)).exclude(pk__in=esclusi).order_by(
        "tipo", "nome"
    )


def get_all_gated_tier_ids() -> set[int]:
    return set(CarrieraTierSblocco.objects.values_list("tier_id", flat=True))


def get_tier_ids_sblocco_for_personaggio(personaggio) -> set[int]:
    carriere_attive = PersonaggioCarrieraMembership.objects.filter(
        personaggio=personaggio,
        data_a__isnull=True,
    ).values_list("carriera_id", flat=True)
    if not carriere_attive:
        return set()
    return set(
        CarrieraTierSblocco.objects.filter(carriera_id__in=carriere_attive).values_list("tier_id", flat=True)
    )


def personaggio_puo_acquistare_abilita_tier(personaggio, abilita) -> bool:
    """
    Se l'abilità è in tier collegati ad almeno una carriera (tiers_sblocco),
    il PG deve avere membership attiva su una carriera che sblocca uno di quei tier.
    """
    gated = get_all_gated_tier_ids()
    if not gated:
        return True

    if hasattr(abilita, "_prefetched_objects_cache") and "abilita_tier_set" in abilita._prefetched_objects_cache:
        skill_tiers = {link.tabella_id for link in abilita.abilita_tier_set.all()}
    else:
        skill_tiers = set(abilita.abilita_tier_set.values_list("tabella_id", flat=True))

    if not skill_tiers:
        return True
    if not (skill_tiers & gated):
        return True

    unlocked = get_tier_ids_sblocco_for_personaggio(personaggio)
    return bool(skill_tiers & unlocked)


def messaggio_blocco_tier_carriera(personaggio) -> str:
    return (
        "Questa abilità appartiene a un tier riservato a carriere o KORP; "
        "serve un'appartenenza attiva che sblocchi quel tier."
    )


def invalidate_acquirable_skills_cache(personaggio_id) -> None:
    cache.delete(f"acquirable_skills_{personaggio_id}")
