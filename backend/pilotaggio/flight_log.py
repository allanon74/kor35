"""
Diario di volo: log leggibile per analisi post-partita (precipizi, eventi, DEFCON).

Le voci sono append-only per sessione; non devono mai bloccare il motore di gioco.
"""
from __future__ import annotations

import logging
from typing import Any, Optional

from django.utils import timezone

logger = logging.getLogger(__name__)

# Motivi tecnici sessione.crash_reason → spiegazione per il pilota
SPIEGAZIONE_CRASH: dict[str, str] = {
    "catastrophic_event": (
        "Condizione catastrofica (CA) di un evento attivo: la nave non ha rispettato "
        "i parametri minimi di sicurezza entro il tempo previsto."
    ),
    "defcon_overflow": (
        "Il livello DEFCON ha superato la soglia massima (troppi errori o eventi non risolti)."
    ),
    "end_of_energy": (
        "Energia esaurita: carburante e batterie a zero, senza produzione attiva."
    ),
    "fault_effect_shipwreck": (
        "Guasto critico su un sottosistema con effetto «naufragio»."
    ),
    "manual_abort": "Volo interrotto manualmente dall'equipaggio o dallo staff.",
    "ca_guasto_target_missing": (
        "Errore di configurazione evento (obsoleto): bersaglio CA non trovato."
    ),
}

SPIEGAZIONE_ESITO_TICK: dict[str, str] = {
    "st": "Soluzione totale (ST): evento risolto, DEFCON −1.",
    "sp": "Soluzione parziale (SP): evento prosegue, DEFCON invariato.",
    "ko": "Nessuna soluzione: DEFCON +1.",
    "ca": "Condizione catastrofica (CA) attiva: precipizio nave.",
    "ca_grace": (
        "Condizione catastrofica rilevata al primo controllo: tempo di reazione, "
        "DEFCON +1 (niente precipizio immediato)."
    ),
    "ca_guasto": "Condizione catastrofica: guasto forzato su sottosistema/i.",
    "ca_config": "Condizione catastrofica senza bersaglio valido: timeout evento, DEFCON +1.",
    "timeout": "Tempo evento scaduto: DEFCON +1.",
    "wait": "Attesa intervallo DEFCON (nessuna valutazione).",
}


def spiega_crash(reason: str) -> str:
    key = str(reason or "").strip() or "catastrophic_event"
    return SPIEGAZIONE_CRASH.get(key, f"Precipizio (motivo tecnico: {key}).")


def spiega_esito_tick(esito: str) -> str:
    return SPIEGAZIONE_ESITO_TICK.get(
        str(esito or "").strip().lower(),
        f"Valutazione evento: esito «{esito}».",
    )


def registra_voce_diario(
    sessione,
    categoria: str,
    messaggio: str,
    *,
    dati: Optional[dict[str, Any]] = None,
    evento_attivo=None,
    defcon_pre: Optional[int] = None,
    defcon_post: Optional[int] = None,
) -> None:
    """Scrive una riga diario; errori non propagati al motore."""
    if sessione is None or not getattr(sessione, "pk", None):
        return
    try:
        from .models import VoceDiarioVolo

        VoceDiarioVolo.objects.create(
            sessione=sessione,
            categoria=str(categoria or "info")[:32],
            messaggio=str(messaggio or "").strip()[:4000],
            dati_json=dati or {},
            evento_attivo=evento_attivo,
            defcon_pre=defcon_pre,
            defcon_post=defcon_post,
        )
    except Exception:
        logger.exception("Impossibile registrare voce diario volo sessione=%s", sessione.pk)


def log_volo_iniziato(sessione, *, partenza: str, arrivo: str) -> None:
    registra_voce_diario(
        sessione,
        "volo_iniziato",
        f"Nuovo volo pianificato: {partenza} → {arrivo}. DEFCON iniziale 0.",
        dati={"partenza": partenza, "arrivo": arrivo},
        defcon_pre=0,
        defcon_post=0,
    )


def log_decollo(sessione) -> None:
    registra_voce_diario(
        sessione,
        "decollo",
        "Decollo effettuato: motori in spinta, eventi di volo abilitati.",
        defcon_pre=int(sessione.defcon or 0),
        defcon_post=int(sessione.defcon or 0),
    )


def log_evento_comparso(sessione, istanza) -> None:
    nome = getattr(getattr(istanza, "evento", None), "nome", "Evento")
    sec = None
    if istanza.prossima_valutazione_at and istanza.created_at:
        sec = int(
            max(1, (istanza.prossima_valutazione_at - istanza.created_at).total_seconds())
        )
    intervallo = sec or getattr(istanza, "intervallo_reazione_secondi", None)
    msg = f"Compare evento «{nome}»."
    if intervallo:
        msg += f" Prossima valutazione tra circa {intervallo}s (DEFCON {sessione.defcon})."
    registra_voce_diario(
        sessione,
        "evento_comparso",
        msg,
        evento_attivo=istanza,
        dati={
            "evento_nome": nome,
            "ticks_rimanenti": istanza.ticks_rimanenti,
            "intervallo_secondi": intervallo,
        },
        defcon_pre=int(sessione.defcon or 0),
        defcon_post=int(sessione.defcon or 0),
    )


def log_valutazione_evento(
    sessione,
    istanza,
    esito_tick: str,
    defcon_pre: int,
    defcon_post: int,
) -> None:
    if esito_tick == "wait":
        return
    nome = getattr(getattr(istanza, "evento", None), "nome", "Evento")
    spiegazione = spiega_esito_tick(esito_tick)
    delta = defcon_post - defcon_pre
    delta_txt = ""
    if delta > 0:
        delta_txt = f" DEFCON {defcon_pre} → {defcon_post} (+{delta})."
    elif delta < 0:
        delta_txt = f" DEFCON {defcon_pre} → {defcon_post} ({delta})."
    registra_voce_diario(
        sessione,
        "evento_valutato",
        f"Evento «{nome}»: {spiegazione}{delta_txt}",
        evento_attivo=istanza,
        dati={
            "evento_nome": nome,
            "esito_tick": esito_tick,
            "valutazioni": int(istanza.valutazioni_eseguite or 0),
            "ticks_rimanenti": istanza.ticks_rimanenti,
            "esito_evento": istanza.esito,
        },
        defcon_pre=defcon_pre,
        defcon_post=defcon_post,
    )


def log_precipizio(sessione, reason: str, *, evento_attivo=None) -> None:
    from .models import DEFCON_MAX

    spiegazione = spiega_crash(reason)
    nome_ev = ""
    if evento_attivo is not None:
        nome_ev = getattr(getattr(evento_attivo, "evento", None), "nome", "") or ""
    msg = f"PRECIPIZIO: {spiegazione}"
    if nome_ev:
        msg += f" Evento correlato: «{nome_ev}»."
    registra_voce_diario(
        sessione,
        "precipizio",
        msg,
        evento_attivo=evento_attivo,
        dati={"crash_reason": reason, "evento_nome": nome_ev},
        defcon_post=DEFCON_MAX + 1,
    )


def log_arrivo(sessione, *, emergenza: bool = False) -> None:
    tipo = "arrivo_emergenza" if emergenza else "arrivo"
    msg = (
        "Atterraggio di emergenza eseguito."
        if emergenza
        else "Destinazione raggiunta con successo."
    )
    registra_voce_diario(
        sessione,
        tipo,
        msg,
        defcon_pre=int(sessione.defcon or 0),
        defcon_post=int(sessione.defcon or 0),
    )


def log_guasto_sottosistema(sessione, stato, *, causa: str = "random") -> None:
    codice = getattr(getattr(stato, "sottosistema", None), "codice", "?")
    nome = getattr(getattr(stato, "sottosistema", None), "nome", codice)
    causa_txt = {
        "random": "guasto casuale da stress del sistema",
        "qr": "scansione QR guasto",
        "staff": "intervento staff",
        "ca": "condizione catastrofica evento",
        "pilota": "comando plancia (espulsione/offline)",
    }.get(causa, causa)
    registra_voce_diario(
        sessione,
        "guasto",
        f"Sottosistema {codice} ({nome}) offline: {causa_txt}.",
        dati={"codice": codice, "causa": causa},
        defcon_pre=int(sessione.defcon or 0),
        defcon_post=int(sessione.defcon or 0),
    )


def riepilogo_sessione_per_pilota(sessione) -> dict:
    """Sintesi leggibile per elenco voli passati."""
    from .models import EVENTO_ESITO_PENDING, EventoAttivoSessione, VoceDiarioVolo

    stato = sessione.stato
    etichetta_stato = {
        "crashed": "Precipitata",
        "arrivata": "Arrivata",
        "volo": "In volo",
        "idle": "Idle",
    }.get(stato, stato)
    ultimo_evento = (
        EventoAttivoSessione.objects.filter(sessione=sessione)
        .exclude(esito=EVENTO_ESITO_PENDING)
        .order_by("-risolto_at", "-created_at")
        .select_related("evento")
        .first()
    )
    voci = VoceDiarioVolo.objects.filter(sessione=sessione).count()
    durata = None
    if sessione.started_at and sessione.ended_at:
        durata = int((sessione.ended_at - sessione.started_at).total_seconds())
    elif sessione.started_at:
        durata = int((timezone.now() - sessione.started_at).total_seconds())
    return {
        "id": str(sessione.pk),
        "stato": stato,
        "stato_etichetta": etichetta_stato,
        "defcon_finale": sessione.defcon,
        "crash_reason": sessione.crash_reason or "",
        "crash_spiegazione": spiega_crash(sessione.crash_reason)
        if stato == "crashed"
        else "",
        "partenza_nome": getattr(sessione.prefettura_partenza, "nome", None),
        "arrivo_nome": getattr(sessione.prefettura_arrivo, "nome", None),
        "started_at": sessione.started_at.isoformat() if sessione.started_at else None,
        "ended_at": sessione.ended_at.isoformat() if sessione.ended_at else None,
        "durata_secondi": durata,
        "ultimo_evento_nome": getattr(ultimo_evento.evento, "nome", None)
        if ultimo_evento
        else None,
        "voci_diario": voci,
    }
