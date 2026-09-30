"""
Console comunicazioni: allarme cromatico, messaggio al dipartimento,
audio sulla plancia e grazia sul primo controllo di catastrofe.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from django.utils import timezone

from .allarme_equipaggio import (
    ALLARME_EQUIPAGGIO_AMBRA,
    ALLARME_EQUIPAGGIO_CHOICES,
    ALLARME_EQUIPAGGIO_CROCIERA,
    annuncio_vocale_allarme,
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


def integra_elenco_guasti(testo: str, nomi: str, *, vuoto: str = "") -> str:
    """
    Se l'elenco dei sottosistemi offline non è già nel testo, lo aggiunge.
    Usato dall'allarme ambra, nel messaggio alla KORP e nell'audio di plancia.
    """
    base = str(testo or "").strip()
    elenco = str(nomi or "").strip()
    ha_nomi = bool(elenco) and elenco != "nessun sottosistema"
    if ha_nomi and elenco in base:
        return base
    if not ha_nomi and "nessun sottosistema" in base.lower():
        return base
    coda = (
        f"Sottosistemi guasti: {elenco}."
        if ha_nomi
        else "Nessun sottosistema risulta guasto."
    )
    if coda in base:
        return base
    if not base:
        return (vuoto or coda).strip()
    return f"{base} {coda}"


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


def carriera_e_dipartimento_bordo(carriera) -> bool:
    """KORP oppure tipo segnato come dipartimento nell'elenco Carriere e KORP."""
    if carriera is None:
        return False
    tipo = getattr(carriera, "tipo_carriera", None)
    if tipo is None:
        return False
    codice = str(getattr(tipo, "codice", "") or "").strip().lower()
    nome = str(getattr(tipo, "nome", "") or "").strip().lower()
    return codice in {"korp", "dipartimento"} or nome in {"dipartimento", "dipartimenti"}


def queryset_dipartimenti_bordo():
    from django.db.models import Q
    from personaggi.models import Carriera

    return (
        Carriera.objects.filter(
            Q(tipo_carriera__codice__in=["korp", "dipartimento"])
            | Q(tipo_carriera__nome__iexact="dipartimento")
            | Q(tipo_carriera__nome__iexact="dipartimenti")
        )
        .select_related("tipo_carriera")
        .order_by("nome")
    )


def _personaggi_korp(korp) -> list:
    """Membri attivi del dipartimento (appartenenza ancora aperta)."""
    if korp is None:
        return []
    from personaggi.models import PersonaggioCarrieraMembership

    visti = set()
    persone = []
    righe = (
        PersonaggioCarrieraMembership.objects.filter(
            carriera=korp,
            data_a__isnull=True,
        )
        .select_related("personaggio__proprietario")
        .order_by("personaggio__nome")
    )
    for riga in righe:
        persona = riga.personaggio
        if persona is None or persona.pk in visti:
            continue
        visti.add(persona.pk)
        persone.append(persona)
    return persone


def _notifica_korp(korp, *, head: str, body: str) -> int:
    if korp is None or not body:
        return 0
    try:
        from personaggi.notify import notify_users
    except Exception:
        logger.exception("Notify KORP non disponibile")
        return 0
    utenti = []
    for persona in _personaggi_korp(korp):
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
        logger.exception("Invio messaggio alla KORP fallito")
        return 0


def dichiara_allarme_comunicazioni(sessione, allarme: str) -> Dict[str, Any]:
    """
    Imposta il colore, legge l'audio in plancia, avvisa i membri della KORP
    e, se il colore è quello dell'evento in reazione, arma la grazia CA.
    """
    from .models import ProtocolloComunicazione

    key = normalizza_allarme_equipaggio(allarme)
    protocollo = (
        ProtocolloComunicazione.objects.select_related("korp")
        .filter(colore=key, attivo=True)
        .first()
    )
    pending = _evento_pending(sessione)
    evento_nome = ""
    if pending is not None and pending.evento_id:
        evento_nome = str(pending.evento.nome or "")
    testo = ""
    korp = None
    korp_nome = ""
    if protocollo is not None:
        testo = render_messaggio(protocollo.testo, sessione, evento_nome)
        korp = protocollo.korp if protocollo.korp_id else None
        if korp is not None:
            korp_nome = korp.nome
    annuncio_custom = ""
    if protocollo is not None and str(protocollo.testo_audio or "").strip():
        annuncio_custom = render_messaggio(protocollo.testo_audio, sessione, evento_nome)
    if key == ALLARME_EQUIPAGGIO_AMBRA:
        nomi = _nomi_sottosistemi_guasti(sessione)
        if testo or korp is not None:
            testo = integra_elenco_guasti(
                testo,
                nomi,
                vuoto=(
                    f"Riparare i sottosistemi guasti: {nomi}."
                    if nomi and nomi != "nessun sottosistema"
                    else "Nessun sottosistema risulta guasto."
                ),
            )
        annuncio_custom = integra_elenco_guasti(
            annuncio_custom or annuncio_vocale_allarme(key),
            nomi,
        )
    annuncio = imposta_allarme_equipaggio_sessione(
        sessione, key, annuncio=annuncio_custom or None
    )
    inviati = 0
    if korp is not None and testo:
        inviati = _notifica_korp(
            korp,
            head=f"{etichetta_colore(key)} — {korp_nome}".strip(" —"),
            body=testo,
        )
    grazia = applica_grazia_colore(sessione, key)
    return {
        "annuncio": annuncio,
        "colore": key,
        "testo": testo,
        "dipartimento": korp_nome,
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
        ProtocolloComunicazione.objects.select_related("korp")
        .filter(attivo=True)
        .order_by("ordine", "colore")
    ):
        protocolli.append(
            {
                "colore": row.colore,
                "etichetta": etichetta_colore(row.colore),
                "dipartimento": row.korp.nome if row.korp_id else "",
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
