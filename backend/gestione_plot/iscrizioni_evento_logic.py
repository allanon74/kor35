"""
Calcolo importi, posti e validazione scelte per iscrizione eventi con opzioni accessorie.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Iterable
from uuid import UUID

from .models import Evento, EventoIscrizioneOpzione, IscrizioneEventoPagamento, IscrizioneEventoPagamentoOpzione


def opzioni_attive(evento: Evento):
    return evento.iscrizione_opzioni.filter(attiva=True).order_by("ordine", "nome")


def posti_occupati_opzione(opzione: EventoIscrizioneOpzione) -> int:
    """Posti riservati da pagamenti in corso o completati."""
    return IscrizioneEventoPagamentoOpzione.objects.filter(
        opzione=opzione,
        pagamento__stato__in=(
            IscrizioneEventoPagamento.Stato.PENDING,
            IscrizioneEventoPagamento.Stato.CAPTURED,
        ),
    ).count()


def posti_disponibili(opzione: EventoIscrizioneOpzione) -> int | None:
    if opzione.posti_limite is None:
        return None
    return max(0, opzione.posti_limite - posti_occupati_opzione(opzione))


def _user_opzione_sync_ids(evento: Evento, utente) -> set[str]:
    rows = (
        IscrizioneEventoPagamentoOpzione.objects.filter(
            pagamento__evento=evento,
            pagamento__utente=utente,
            pagamento__stato=IscrizioneEventoPagamento.Stato.CAPTURED,
        )
        .values_list("opzione__sync_id", flat=True)
    )
    return {str(s) for s in rows}


def serialize_opzione_for_api(opzione: EventoIscrizioneOpzione, *, gia_acquistata: bool) -> dict:
    occupati = posti_occupati_opzione(opzione)
    limite = opzione.posti_limite
    disponibili = posti_disponibili(opzione)
    esaurita = limite is not None and disponibili == 0 and not gia_acquistata
    return {
        "sync_id": str(opzione.sync_id),
        "nome": opzione.nome,
        "descrizione": opzione.descrizione or "",
        "costo_euro": str(opzione.costo_euro),
        "scelta_giocatore": bool(opzione.scelta_giocatore),
        "obbligatoria": bool(opzione.obbligatoria),
        "posti_limite": limite,
        "posti_occupati": occupati,
        "posti_disponibili": disponibili,
        "esaurita": esaurita,
        "gia_acquistata": gia_acquistata,
    }


def evento_ha_iscrizione_online(evento: Evento) -> bool:
    if not (evento.iscrizione_apertura and evento.iscrizione_chiusura):
        return False
    if evento.iscrizione_costo_euro and evento.iscrizione_costo_euro > 0:
        return True
    return opzioni_attive(evento).exists()


def importo_minimo_iscrizione(evento: Evento) -> Decimal:
    """Costo minimo per una nuova iscrizione (base + automatiche + obbligatorie a scelta)."""
    tot = Decimal(evento.iscrizione_costo_euro or 0)
    for op in opzioni_attive(evento):
        if not op.scelta_giocatore or op.obbligatoria:
            tot += Decimal(op.costo_euro or 0)
    return tot


def _parse_sync_ids(raw_ids: Iterable) -> set[UUID]:
    out: set[UUID] = set()
    for item in raw_ids or []:
        try:
            out.add(UUID(str(item)))
        except (TypeError, ValueError):
            continue
    return out


def _opzione_inclusa_nuova_iscrizione(op: EventoIscrizioneOpzione, selezionate: set[UUID]) -> bool:
    if not op.scelta_giocatore:
        return True
    if op.obbligatoria:
        return op.sync_id in selezionate
    return op.sync_id in selezionate


def risolvi_scelte_iscrizione(
    evento: Evento,
    *,
    modalita: str,
    utente,
    opzione_sync_ids_raw: Iterable,
) -> tuple[list[EventoIscrizioneOpzione], Decimal, list[str]]:
    """
    modalita: 'iscrizione' | 'integra'
    Restituisce (opzioni incluse nel totale, importo, errori).
    """
    errori: list[str] = []
    attive = list(opzioni_attive(evento))
    by_sync = {op.sync_id: op for op in attive}
    selezionate = _parse_sync_ids(opzione_sync_ids_raw)
    gia_acquistate = _user_opzione_sync_ids(evento, utente) if utente else set()

    for uid in selezionate:
        if uid not in by_sync:
            errori.append("Una o più opzioni selezionate non sono valide o non sono attive.")

    if modalita == "integra":
        scelte: list[EventoIscrizioneOpzione] = []
        tot = Decimal("0")
        for uid in selezionate:
            op = by_sync.get(uid)
            if not op:
                continue
            if not op.scelta_giocatore:
                errori.append(f"«{op.nome}» è inclusa automaticamente nell'iscrizione iniziale.")
                continue
            if str(op.sync_id) in gia_acquistate:
                errori.append(f"Hai già acquistato «{op.nome}».")
                continue
            disp = posti_disponibili(op)
            if disp is not None and disp < 1:
                errori.append(f"Posti esauriti per «{op.nome}».")
                continue
            scelte.append(op)
            tot += Decimal(op.costo_euro or 0)
        if not scelte and not errori:
            errori.append("Seleziona almeno un'opzione da aggiungere.")
        return scelte, tot, errori

    scelte = []
    tot = Decimal(evento.iscrizione_costo_euro or 0)
    for op in attive:
        if not _opzione_inclusa_nuova_iscrizione(op, selezionate):
            if op.obbligatoria and op.scelta_giocatore:
                errori.append(f"Devi selezionare l'opzione obbligatoria «{op.nome}».")
            continue
        disp = posti_disponibili(op)
        if disp is not None and disp < 1:
            msg = f"Posti esauriti per «{op.nome}»"
            if not op.scelta_giocatore:
                msg += " (inclusa automaticamente)"
            errori.append(f"{msg}.")
            continue
        scelte.append(op)
        tot += Decimal(op.costo_euro or 0)

    return scelte, tot, errori


def opzioni_integrabili(evento: Evento, utente) -> list[EventoIscrizioneOpzione]:
    gia = _user_opzione_sync_ids(evento, utente)
    out = []
    for op in opzioni_attive(evento):
        if not op.scelta_giocatore:
            continue
        if str(op.sync_id) in gia:
            continue
        if posti_disponibili(op) == 0:
            continue
        out.append(op)
    return out
