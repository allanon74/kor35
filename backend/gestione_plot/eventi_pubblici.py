"""Queryset degli eventi visibili sul sito pubblico (homepage wiki e calendario)."""
from datetime import timedelta

from django.utils import timezone


def eventi_pubblici_queryset(now=None):
    """
    Ultimi 30 giorni e futuri, senza le prove di iscrizione PayPal
    (``iscrizione_test_attiva``: visibili solo allo staff della campagna principale).
    """
    from gestione_plot.models import Evento

    oggi = now or timezone.now()
    trenta_giorni_fa = oggi - timedelta(days=30)
    return Evento.objects.filter(
        data_fine__gte=trenta_giorni_fa,
        iscrizione_test_attiva=False,
        archiviato_at__isnull=True,
    ).order_by("data_inizio")


def eventi_calendario_queryset(now=None):
    """Come il sito, ma senza date ancora segnate come provvisorie."""
    return eventi_pubblici_queryset(now).filter(data_da_definire=False)
