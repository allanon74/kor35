"""
Riallineamento iscrizioni PayPal CAPTURED → Evento.partecipanti (fonte di verità gameplay).
"""
from __future__ import annotations

import logging

from .models import Evento, IscrizioneEventoPagamento

logger = logging.getLogger(__name__)


def ensure_partecipante_from_pagamento(row: IscrizioneEventoPagamento) -> bool:
    """
    Garantisce che un pagamento ISCRIZIONE CAPTURED sia in Evento.partecipanti.
    Ritorna True se il PG è (o viene messo) tra i partecipanti.
    """
    if row.tipo_ordine != IscrizioneEventoPagamento.TipoOrdine.ISCRIZIONE:
        return False
    if row.stato != IscrizioneEventoPagamento.Stato.CAPTURED:
        return False
    ev = Evento.objects.get(pk=row.evento_id)
    if ev.partecipanti.filter(id=row.personaggio_id).exists():
        return True
    other = ev.partecipanti.filter(
        proprietario_id=row.utente_id, tipologia__giocante=True
    ).exclude(id=row.personaggio_id).exists()
    if other:
        logger.warning(
            "Iscrizione CAPTURED senza M2M: altro PG già iscritto evento=%s user=%s pg=%s",
            row.evento_id,
            row.utente_id,
            row.personaggio_id,
        )
        return False
    ev.partecipanti.add(row.personaggio_id)
    logger.info(
        "Riallineato partecipanti: evento=%s pg=%s da pagamento CAPTURED %s",
        row.evento_id,
        row.personaggio_id,
        row.paypal_order_id,
    )
    return True


def riallinea_iscrizioni_catturate(evento_id=None) -> dict:
    """Ripara M2M partecipanti da pagamenti CAPTURED/ISCRIZIONE orfani."""
    qs = IscrizioneEventoPagamento.objects.filter(
        stato=IscrizioneEventoPagamento.Stato.CAPTURED,
        tipo_ordine=IscrizioneEventoPagamento.TipoOrdine.ISCRIZIONE,
    )
    if evento_id:
        qs = qs.filter(evento_id=evento_id)
    aggiunti = 0
    gia = 0
    conflitti = 0
    for row in qs.select_related("evento"):
        before = row.evento.partecipanti.filter(id=row.personaggio_id).exists()
        ok = ensure_partecipante_from_pagamento(row)
        if before:
            gia += 1
        elif ok:
            aggiunti += 1
        else:
            conflitti += 1
    return {
        "aggiunti": aggiunti,
        "gia_presenti": gia,
        "conflitti": conflitti,
        "esaminati": qs.count(),
    }
