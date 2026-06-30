"""
Portale A_vista per bustine carte (QR).
"""
from __future__ import annotations

from personaggi.carte_collezionabili_models import BustinaCarte


def ensure_portale_avista(bustina: BustinaCarte):
    from personaggi.models import BustinaCartePortale

    portale = getattr(bustina, "portale_avista", None)
    if portale is None:
        portale = BustinaCartePortale.objects.create(
            bustina=bustina,
            nome=f"Bustina: {bustina.nome}",
            testo=bustina.descrizione or "",
        )
        return portale
    updates = []
    nome = f"Bustina: {bustina.nome}"
    if portale.nome != nome:
        portale.nome = nome
        updates.append("nome")
    testo = bustina.descrizione or ""
    if (portale.testo or "") != testo:
        portale.testo = testo
        updates.append("testo")
    if updates:
        portale.save(update_fields=updates + ["updated_at"])
    return portale


def ensure_bustina_qr(bustina: BustinaCarte):
    """Portale A_vista + QrCode collegato (pattern negozio mercante)."""
    from personaggi.models import QrCode

    portale = ensure_portale_avista(bustina)
    if bustina.qr_code_id:
        qr = bustina.qr_code
        if qr.vista_id != portale.pk:
            qr.vista = portale
            qr.save(update_fields=["vista", "updated_at"])
        return qr, portale

    qr = QrCode.objects.filter(vista_id=portale.pk).first()
    if qr is None:
        qr = QrCode.objects.create(
            vista=portale,
            testo=f"Bustina demo: {bustina.nome}",
        )
    bustina.qr_code = qr
    bustina.save(update_fields=["qr_code", "updated_at"])
    return qr, portale


def bustina_da_vista_pk(vista_pk) -> BustinaCarte | None:
    from personaggi.models import BustinaCartePortale

    portale = (
        BustinaCartePortale.objects.filter(pk=vista_pk)
        .select_related("bustina")
        .first()
    )
    if portale and portale.bustina_id:
        return portale.bustina
    return None
