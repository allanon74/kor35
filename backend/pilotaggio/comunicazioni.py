"""
Console comunicazioni: allarme cromatico, messaggio al dipartimento,
audio sulla plancia e grazia sul primo controllo di catastrofe.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .allarme_equipaggio import (
    ALLARME_EQUIPAGGIO_CHOICES,
    ALLARME_EQUIPAGGIO_CROCIERA,
    imposta_allarme_equipaggio_sessione,
    normalizza_allarme_equipaggio,
)

logger = logging.getLogger(__name__)

ETICHETTE_COLORE = dict(ALLARME_EQUIPAGGIO_CHOICES)


def etichetta_colore(colore: str) -> str:
    key = str(colore or "").strip().lower()
    return ETICHETTE_COLORE.get(key, key or "Allarme")


def _nomi_sottosistemi_guasti(sessione) -> str:
    from .models import StatoSottosistemaSessione

    nomi = [
        (st.sottosistema.nome or st.sottosistema.codice or "").strip()
        for st in StatoSottosistemaSessione.objects.select_related("sottosistema")
        .filter(sessione=sessione, online=False)
        .order_by("sottosistema__ordine", "sottosistema__codice")
    ]
    nomi = [n for n in nomi if n]
    return ", ".join(nomi) if nomi else "nessun sottosistema"


def _evento_pending(sessione):
    from .models import EVENTO_ESITO_PENDING, EventoAttivoSessione

    return (
        EventoAttivoSessione.objects.select_related("evento")
        .filter(sessione=sessione, esito=EVENTO_ESITO_PENDING)
        .order_by("created_at")
        .first()
    )


def render_messaggio(template: str, sessione, evento_nome: str) -> str:
    testo = str(template or "")
    return (
        testo.replace("{sottosistema}", _nomi_sottosistemi_guasti(sessione))
        .replace("{evento}", evento_nome or "nessun evento")
        .strip()
    )


def applica_grazia_colore(sessione, colore: str) -> bool:
    """
    Se il colore coincide con quello richiesto dall'evento e la reazione
    non è ancora scaduta, il primo controllo CA viene saltato.
    """
    from .models import EVENTO_ESITO_PENDING, EventoAttivoSessione

    key = normalizza_allarme_equipaggio(colore)
    if key == ALLARME_EQUIPAGGIO_CROCIERA:
        return False
    now = timezone.now()
    granted = False
    pending = EventoAttivoSessione.objects.select_related("evento").filter(
        sessione=sessione, esito=EVENTO_ESITO_PENDING
    )
    for istanza in pending:
        richiesto = str(getattr(istanza.evento, "allarme_richiesto", "") or "").strip().lower()
        if not richiesto or richiesto != key:
            continue
        if int(istanza.valutazioni_eseguite or 0) > 0:
            continue
        if istanza.reazione_fino_at is not None and now >= istanza.reazione_fino_at:
            continue
        istanza.ca_soppressa_comunicazioni = True
        istanza.save(update_fields=["ca_soppressa_comunicazioni", "updated_at"])
        granted = True
    return granted


def _notifica_dipartimento(dipartimento, *, head: str, body: str) -> int:
    if dipartimento is None or not body:
        return 0
    try:
        from personaggi.notify import notify_users
    except Exception:
        logger.exception("Notify dipartimento non disponibile")
        return 0
    utenti = []
    for persona in dipartimento.membri.select_related("proprietario").all():
        utente = getattr(persona, "proprietario", None)
        if utente is not None:
            utenti.append(utente)
    if not utenti:
        return 0
    try:
        return int(
            notify_users(
                utenti,
                category="in_game",
                head=head,
                body=body,
                url="/",
                extra={"tipo": "allarme_bordo"},
            )
            or 0
        )
    except Exception:
        logger.exception("Invio messaggio dipartimento fallito")
        return 0


def dichiara_allarme_comunicazioni(sessione, allarme: str) -> Dict[str, Any]:
    """
    Imposta il colore, legge l'audio in plancia, avvisa il dipartimento
    e, se il colore è quello dell'evento in reazione, arma la grazia CA.
    """
    from .models import ProtocolloComunicazione

    key = normalizza_allarme_equipaggio(allarme)
    protocollo = (
        ProtocolloComunicazione.objects.select_related("dipartimento")
        .filter(colore=key, attivo=True)
        .first()
    )
    pending = _evento_pending(sessione)
    evento_nome = ""
    if pending is not None and pending.evento_id:
        evento_nome = str(pending.evento.nome or "")
    testo = ""
    dipartimento_nome = ""
    if protocollo is not None:
        testo = render_messaggio(protocollo.testo, sessione, evento_nome)
        if protocollo.dipartimento_id and protocollo.dipartimento is not None:
            dipartimento_nome = protocollo.dipartimento.nome
    annuncio_custom = ""
    if protocollo is not None and str(protocollo.testo_audio or "").strip():
        annuncio_custom = render_messaggio(protocollo.testo_audio, sessione, evento_nome)
    annuncio = imposta_allarme_equipaggio_sessione(
        sessione, key, annuncio=annuncio_custom or None
    )
    inviati = 0
    if protocollo is not None and testo and protocollo.dipartimento_id:
        inviati = _notifica_dipartimento(
            protocollo.dipartimento,
            head=f"{etichetta_colore(key)} — {dipartimento_nome}".strip(" —"),
            body=testo,
        )
    grazia = applica_grazia_colore(sessione, key)
    return {
        "annuncio": annuncio,
        "colore": key,
        "testo": testo,
        "dipartimento": dipartimento_nome,
        "inviati": inviati,
        "grazia": grazia,
    }


def quadro_comunicazioni(sessione) -> Dict[str, Any]:
    """Stato per la console radio: evento senza codici, guasti, protocolli."""
    from .models import ProtocolloComunicazione, PilotRuntimeConfig

    cfg = PilotRuntimeConfig.get_solo()
    pending = _evento_pending(sessione) if sessione is not None else None
    now = timezone.now()
    evento: Optional[Dict[str, Any]] = None
    if pending is not None and pending.evento_id:
        in_reazione = (
            int(pending.valutazioni_eseguite or 0) == 0
            and pending.reazione_fino_at is not None
            and now < pending.reazione_fino_at
        )
        descrizione = str(pending.evento.descrizione or "").strip()
        if len(descrizione) > 320:
            descrizione = descrizione[:317].rstrip() + "…"
        evento = {
            "nome": pending.evento.nome,
            "descrizione": descrizione,
            "in_reazione": in_reazione,
            "reazione_fino_at": (
                pending.reazione_fino_at.isoformat() if pending.reazione_fino_at else None
            ),
        }
    protocolli: List[Dict[str, Any]] = []
    for row in (
        ProtocolloComunicazione.objects.select_related("dipartimento")
        .filter(attivo=True)
        .order_by("ordine", "colore")
    ):
        protocolli.append(
            {
                "colore": row.colore,
                "etichetta": etichetta_colore(row.colore),
                "dipartimento": row.dipartimento.nome if row.dipartimento_id else "",
                "ha_testo": bool(str(row.testo or "").strip()),
            }
        )
    guasti = []
    if sessione is not None:
        from .models import StatoSottosistemaSessione

        guasti = [
            (st.sottosistema.nome or st.sottosistema.codice)
            for st in StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione, online=False)
            .order_by("sottosistema__codice")
        ]
    return {
        "abilitata": bool(cfg.comunicazioni_console_abilitata),
        "allarme": (
            getattr(sessione, "allarme_equipaggio", ALLARME_EQUIPAGGIO_CROCIERA)
            if sessione is not None
            else ALLARME_EQUIPAGGIO_CROCIERA
        ),
        "evento": evento,
        "sottosistemi_guasti": guasti,
        "protocolli": protocolli,
        "sessione_attiva": bool(sessione is not None and getattr(sessione, "is_attiva", False)),
    }
