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
        )
    return portale


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
