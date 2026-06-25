"""
Assegnazione automatica abilità default alle membership carriera/KORP attive.
"""
from __future__ import annotations

from personaggi.models import (
    PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
    CarrieraAbilita,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioCarrieraMembership,
)


def sync_abilita_default_carriere_for_personaggio(personaggio) -> int:
    """
    Riallinea le abilità con origine carriera_default alle membership attive (data_a nulla).
    Ritorna il numero di nuovi link creati.
    """
    if isinstance(personaggio, int):
        personaggio = Personaggio.objects.get(pk=personaggio)

    PersonaggioAbilita.objects.filter(
        personaggio=personaggio,
        origine=PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
    ).delete()

    active_carriere_ids = PersonaggioCarrieraMembership.objects.filter(
        personaggio=personaggio,
        data_a__isnull=True,
    ).values_list("carriera_id", flat=True)

    if not active_carriere_ids:
        return 0

    default_abilita_ids = CarrieraAbilita.objects.filter(
        carriera_id__in=active_carriere_ids,
        is_default=True,
    ).values_list("abilita_id", flat=True).distinct()

    possessed_ids = set(
        PersonaggioAbilita.objects.filter(personaggio=personaggio).values_list("abilita_id", flat=True)
    )

    nuovi_link = []
    for abilita_id in default_abilita_ids:
        if abilita_id in possessed_ids:
            continue
        nuovi_link.append(
            PersonaggioAbilita(
                personaggio=personaggio,
                abilita_id=abilita_id,
                origine=PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
            )
        )
        possessed_ids.add(abilita_id)

    if nuovi_link:
        PersonaggioAbilita.objects.bulk_create(nuovi_link, ignore_conflicts=True)

    if hasattr(personaggio, "_modificatori_calcolati_cache"):
        delattr(personaggio, "_modificatori_calcolati_cache")

    return len(nuovi_link)


def riallinea_abilita_default_carriera(carriera) -> int:
    """Riallinea i membri attivi dopo modifica elenco abilità default sulla carriera."""
    personaggio_ids = (
        PersonaggioCarrieraMembership.objects.filter(
            carriera=carriera,
            data_a__isnull=True,
        )
        .values_list("personaggio_id", flat=True)
        .distinct()
    )
    totale = 0
    for pg_id in personaggio_ids:
        totale += sync_abilita_default_carriere_for_personaggio(pg_id)
    return totale
