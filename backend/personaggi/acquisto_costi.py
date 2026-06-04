"""
Costi effettivi pagati su acquisti revocabili (abilità, tecniche).
Il rimborso in revoca usa sempre i valori memorizzati sul pivot, non il prezzo di listino corrente.
"""
from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from typing import Optional, Tuple

from django.utils import timezone

PARAMETRO_SCONTO_ABILITA = "rid_cos_ab"


def calcola_costi_abilita_acquisto(personaggio, abilita) -> Tuple[int, Decimal]:
    """Ritorna (costo_pc, costo_crediti) come in AcquisisciAbilitaView."""
    mods = personaggio.modificatori_calcolati
    sconto_stat = mods.get(PARAMETRO_SCONTO_ABILITA, {"add": 0, "mol": 1.0})
    sconto_valore = max(0, sconto_stat.get("add", 0))
    sconto_percent = Decimal(sconto_valore) / Decimal(100)
    moltiplicatore_costo = Decimal(1) - sconto_percent
    costo_pc_finale = int(abilita.costo_pc or 0)
    costo_crediti_base = Decimal(abilita.costo_crediti or 0)
    costo_crediti_finale = (costo_crediti_base * moltiplicatore_costo).quantize(Decimal("0.01"))
    return costo_pc_finale, costo_crediti_finale


def calcola_costo_tecnica_acquisto(personaggio, tecnica) -> int:
    return int(personaggio.get_costo_item_scontato(tecnica))


def _importo_pagato_da_movimento(movimento) -> Optional[Decimal]:
    if movimento and movimento.importo < 0:
        return -movimento.importo
    return None


def trova_credito_pagato_acquisto(
    personaggio,
    *,
    descrizione_esatta: str | None = None,
    descrizione_prefix: str | None = None,
    acquired_at=None,
    finestra: timedelta = timedelta(hours=24),
) -> Optional[Decimal]:
    """Cerca il movimento crediti di acquisto più vicino a data_acquisizione."""
    from .models import CreditoMovimento

    qs = CreditoMovimento.objects.filter(personaggio=personaggio, importo__lt=0)
    if descrizione_esatta:
        qs = qs.filter(descrizione=descrizione_esatta)
    elif descrizione_prefix:
        qs = qs.filter(descrizione__startswith=descrizione_prefix)
    if acquired_at:
        start_dt = acquired_at - finestra
        end_dt = acquired_at + finestra
        qs = qs.filter(data__gte=start_dt, data__lte=end_dt)
    mov = qs.order_by("-data").first()
    return _importo_pagato_da_movimento(mov)


def trova_pc_pagato_acquisto_abilita(personaggio, abilita, acquired_at=None) -> Optional[int]:
    from .models import PuntiCaratteristicaMovimento

    desc_prefix = f"Acquisito abilità: {abilita.nome}"
    qs = PuntiCaratteristicaMovimento.objects.filter(
        personaggio=personaggio,
        descrizione__startswith=desc_prefix,
        importo__lt=0,
    )
    if acquired_at:
        start_dt = acquired_at - timedelta(hours=24)
        end_dt = acquired_at + timedelta(hours=24)
        qs = qs.filter(data__gte=start_dt, data__lte=end_dt)
    mov = qs.order_by("-data").first()
    if mov and mov.importo < 0:
        return int(-mov.importo)
    return None


def rimborso_crediti_da_pivot(pivot, *, item, acquired_at) -> Decimal:
    pagato = getattr(pivot, "costo_crediti_pagato", None)
    if pagato is not None and pagato > 0:
        return Decimal(pagato)

    abilita = getattr(pivot, "abilita", None)
    if abilita:
        found = trova_credito_pagato_acquisto(
            pivot.personaggio,
            descrizione_prefix=f"Acquisito abilità: {abilita.nome}",
            acquired_at=acquired_at,
        )
        if found is not None:
            return found
        _, crediti = calcola_costi_abilita_acquisto(pivot.personaggio, abilita)
        return crediti

    for attr, prefix in (
        ("infusione", "Acquisito infusione"),
        ("tessitura", "Acquisito tessitura"),
        ("cerimoniale", "Appreso cerimoniale"),
    ):
        tecnica = getattr(pivot, attr, None)
        if not tecnica:
            continue
        exact = f"{prefix}: {tecnica.nome}"
        found = trova_credito_pagato_acquisto(
            pivot.personaggio, descrizione_esatta=exact, acquired_at=acquired_at
        )
        if found is not None:
            return found
        return Decimal(getattr(item, "costo_crediti", 0) or 0)

    return Decimal(0)


def rimborso_pc_da_pivot(pivot, *, acquired_at) -> int:
    pagato = getattr(pivot, "costo_pc_pagato", None)
    if pagato is not None and pagato > 0:
        return int(pagato)
    abilita = getattr(pivot, "abilita", None)
    if not abilita:
        return 0
    found = trova_pc_pagato_acquisto_abilita(pivot.personaggio, abilita, acquired_at=acquired_at)
    if found is not None:
        return found
    pc, _ = calcola_costi_abilita_acquisto(pivot.personaggio, abilita)
    return pc
