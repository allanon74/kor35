"""
Portale A_vista per lobby scontro carte (QR sessione match).
"""
from __future__ import annotations

from personaggi.carte_collezionabili_models import DuelloCarte


def ensure_portale_avista(duello: DuelloCarte):
    from personaggi.models import ScontroCartePortale

    portale = getattr(duello, "portale_avista", None)
    if portale is None:
        portale = ScontroCartePortale.objects.create(
            duello=duello,
            nome=f"Scontro: {duello.sfidante.nome}",
        )
    return portale


def duello_da_vista_pk(vista_pk) -> DuelloCarte | None:
    from personaggi.models import ScontroCartePortale

    portale = (
        ScontroCartePortale.objects.filter(pk=vista_pk)
        .select_related("duello", "duello__sfidante", "duello__sfidato")
        .first()
    )
    if portale and portale.duello_id:
        return portale.duello
    return None
