"""
Stato persistente dei sottosistemi a livello nave (sopravvive tra sessioni/voli).

La sessione runtime (idle o volo) resta la vista operativa per tick e plancia;
ogni save su sessione o su nave mantiene le due tabelle allineate.
"""
from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from django.utils import timezone

if TYPE_CHECKING:
    from .models import SessioneVolo, SottosistemaNave, StatoSottosistemaNave, StatoSottosistemaSessione

CAMPI_STATO_SINCRONI = (
    "online",
    "guasto_at",
    "recovery_at",
    "livello_target",
    "livello_attuale",
    "invertito",
    "espulso",
    "direzione",
)


def _campi_stato_dict(obj) -> Dict[str, Any]:
    return {k: getattr(obj, k) for k in CAMPI_STATO_SINCRONI}


def get_o_crea_stato_nave(sottosistema: "SottosistemaNave") -> "StatoSottosistemaNave":
    from .models import StatoSottosistemaNave

    stato, _ = StatoSottosistemaNave.objects.get_or_create(
        sottosistema=sottosistema,
        defaults={
            "online": True,
            "livello_target": 0,
            "livello_attuale": 0,
            "direzione": "avanti",
        },
    )
    return stato


def defaults_stato_da_nave(sottosistema: "SottosistemaNave") -> Dict[str, Any]:
    return _campi_stato_dict(get_o_crea_stato_nave(sottosistema))


def sync_stato_sessione_a_nave(stato: "StatoSottosistemaSessione") -> None:
    """
    Mirror sessione → nave (UPDATE first per ridurre deadlock con poll concorrenti).
    """
    from .models import StatoSottosistemaNave

    fields = _campi_stato_dict(stato)
    now = timezone.now()
    updated = StatoSottosistemaNave.objects.filter(
        sottosistema_id=stato.sottosistema_id,
    ).update(**fields, updated_at=now)
    if updated == 0:
        StatoSottosistemaNave.objects.create(
            sottosistema_id=stato.sottosistema_id,
            **fields,
        )


def sync_nave_a_sessione(sessione: "SessioneVolo", nave: "StatoSottosistemaNave") -> None:
    """Allinea una riga sessione alla nave (solo chiamata esplicita, es. propaga)."""
    from .models import StatoSottosistemaSessione

    if sessione is None or sessione.is_terminata:
        return
    StatoSottosistemaSessione.objects.filter(
        sessione=sessione,
        sottosistema_id=nave.sottosistema_id,
    ).update(**_campi_stato_dict(nave), updated_at=timezone.now())


def propaga_stati_nave_a_sessione(sessione: "SessioneVolo") -> None:
    """Allinea tutti i sottosistemi attivi della sessione allo stato nave persistente."""
    from .models import SottosistemaNave, StatoSottosistemaSessione

    for sdef in SottosistemaNave.objects.filter(attivo=True).only("pk"):
        nave = get_o_crea_stato_nave(sdef)
        StatoSottosistemaSessione.objects.update_or_create(
            sessione=sessione,
            sottosistema_id=sdef.pk,
            defaults=_campi_stato_dict(nave),
        )


def stato_operativo_sottosistema(
    sottosistema: "SottosistemaNave",
    sessione: Optional["SessioneVolo"] = None,
):
    """
    Stato runtime per UI/QR: sessione se presente (allineata alla nave), altrimenti nave.
    """
    from .engine import get_o_crea_stato_sottosistema

    nave = get_o_crea_stato_nave(sottosistema)
    if sessione is None:
        return nave
    return get_o_crea_stato_sottosistema(sessione, sottosistema)


def fase_operativa_sessione(sessione: Optional["SessioneVolo"]) -> str:
    from .models import SESSIONE_STATO_IDLE, SESSIONE_STATO_VOLO

    if sessione is None:
        return "sosta"
    if sessione.stato == SESSIONE_STATO_IDLE:
        return "riposo"
    if sessione.stato == SESSIONE_STATO_VOLO:
        return "volo"
    return sessione.stato or "sosta"
