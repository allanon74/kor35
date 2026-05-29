"""
Ponte A_vista per negozi mercante: QR e plot usano QrCode.vista come gli altri elementi.
Il modello NegozioMercante (UUID, economia) resta la sorgente dati.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Tuple

from django.db import transaction

if TYPE_CHECKING:
    from personaggi.models import QrCode
    from personaggi.negozio_mercante_models import NegozioMercante


def ensure_portale_avista(negozio: NegozioMercante):
    """Crea/aggiorna il record A_vista collegato al negozio."""
    from personaggi.models import NegozioMercantePortale

    portale = getattr(negozio, "portale_avista", None)
    if portale is None:
        portale = NegozioMercantePortale.objects.create(
            nome=negozio.nome or "Negozio",
            testo=negozio.descrizione_immersiva or negozio.descrizione or "",
            negozio=negozio,
        )
        return portale

    updates = []
    if portale.nome != negozio.nome:
        portale.nome = negozio.nome
        updates.append("nome")
    testo = negozio.descrizione_immersiva or negozio.descrizione or ""
    if (portale.testo or "") != testo:
        portale.testo = testo
        updates.append("testo")
    if updates:
        portale.save(update_fields=updates + ["updated_at"])
    return portale


def negozio_da_vista_pk(vista_pk: int) -> NegozioMercante | None:
    from personaggi.models import NegozioMercantePortale

    portale = (
        NegozioMercantePortale.objects.filter(pk=vista_pk)
        .select_related("negozio")
        .first()
    )
    return portale.negozio if portale else None


def associa_qr_a_negozio(negozio: NegozioMercante, qr: QrCode, *, force: bool = False) -> Tuple[bool, dict[str, Any] | None]:
    """
    Collega il QR al portale A_vista del negozio (e a negozio.qr_code per compatibilità).
    Ritorna (ok, payload_errore_409) — payload_errore se conflitto e non force.
    """
    from personaggi.negozio_mercante_models import NegozioMercante
    from personaggi.qr_logic import descrivi_avista_per_associazione_qr

    altro = NegozioMercante.objects.filter(qr_code=qr).exclude(pk=negozio.pk).first()
    if altro and not force:
        return False, {
            "error": "QR già associato",
            "already_associated": True,
            "qr_id": str(qr.id),
            "associazione_attuale": {
                "tipo": "negozio_mercante",
                "nome": altro.nome,
                "elemento_id": str(altro.id),
            },
            "message": (
                f'Questo QR è già collegato al negozio «{altro.nome}». '
                "Confermi di spostarlo su questo negozio?"
            ),
        }

    if qr.vista_id and not force:
        info = descrivi_avista_per_associazione_qr(qr.vista) or {
            "tipo": "sconosciuto",
            "nome": qr.vista.nome,
            "elemento_id": str(qr.vista.pk),
        }
        return False, {
            "error": "QR già associato",
            "already_associated": True,
            "qr_id": str(qr.id),
            "associazione_attuale": info,
            "message": (
                f'Questo QR punta ancora a «{info["nome"]}» ({info["tipo"]}). '
                "Confermi di collegarlo a questo negozio?"
            ),
        }

    with transaction.atomic():
        portale = ensure_portale_avista(negozio)
        NegozioMercante.objects.filter(qr_code=qr).exclude(pk=negozio.pk).update(qr_code=None)
        qr.vista = portale
        qr.save(update_fields=["vista", "updated_at"])
        negozio.qr_code = qr
        negozio.save(update_fields=["qr_code", "updated_at"])

    return True, None


def scollega_qr_da_negozio(negozio: NegozioMercante) -> None:
    with transaction.atomic():
        if negozio.qr_code_id:
            qr = negozio.qr_code
            portale = getattr(negozio, "portale_avista", None)
            if qr and qr.vista_id and portale and qr.vista_id == portale.pk:
                qr.vista = None
                qr.save(update_fields=["vista", "updated_at"])
        negozio.qr_code = None
        negozio.save(update_fields=["qr_code", "updated_at"])
