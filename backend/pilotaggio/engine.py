"""
Motore della console pilotaggio.

Logica autoritativa lato backend:
- generazione random degli eventi pesata sui pesi configurati;
- valutazione codici in 3 caratteri (esatto/parziale/dannoso);
- aggiornamento DEFCON (gravita') e regola di crash (DEFCON > DEFCON_MAX);
- frequenza eventi e durata countdown variabile in base a DEFCON;
- ripristino automatico sottosistemi dopo `durata_ripristino_secondi`;
- avanzamento sequenze di decollo e atterraggio.

Tutte le mutazioni sui modelli pilotaggio passano da qui in `transaction.atomic`.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import timedelta
from typing import List, Optional, Tuple

from django.db import transaction
from django.utils import timezone

from .models import (
    DEFCON_MAX,
    EVENTO_ESITO_FALLITO,
    EVENTO_ESITO_PARZIALE,
    EVENTO_ESITO_PENDING,
    EVENTO_ESITO_RISOLTO,
    EVENTO_ESITO_TIMEOUT,
    EventoAttivoSessione,
    EventoNave,
    SESSIONE_STATO_ATTERRAGGIO,
    SESSIONE_STATO_ARRIVATA,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_DECOLLO,
    SESSIONE_STATO_VOLO,
    SEQUENZA_ATTERRAGGIO,
    SEQUENZA_DECOLLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
    TentativoCodice,
)


# ---------------------------------------------------------------------------
# Utility codici e validazione
# ---------------------------------------------------------------------------


def normalizza_codice(codice: str) -> str:
    """Normalizza in maiuscolo e rimuove whitespace ai bordi."""
    return (codice or "").strip().upper()


def codice_valido_3char(codice: str) -> bool:
    """Verifica formato esatto: 3 caratteri alfanumerici, ultimo numerico."""
    c = normalizza_codice(codice)
    if len(c) != 3:
        return False
    if not c[:2].isalnum():
        return False
    if not c[2].isdigit():
        return False
    return True


def matcha_pattern(pattern: str, codice: str) -> bool:
    """Match pattern parziale con jolly `_` (singolo carattere)."""
    p = normalizza_codice(pattern)
    c = normalizza_codice(codice)
    if len(p) != len(c):
        return False
    return all(pc == "_" or pc == cc for pc, cc in zip(p, c))


# ---------------------------------------------------------------------------
# Curve di difficolta' in funzione del DEFCON
# ---------------------------------------------------------------------------


def secondi_evento_per_defcon(durata_base: int, defcon: int) -> int:
    """
    Riduce la durata countdown in modo monotono crescente al salire del DEFCON.
    A DEFCON 0 -> durata_base. A DEFCON DEFCON_MAX -> ~30% durata_base.
    """
    base = max(3, int(durata_base or 20))
    fattore = max(0.3, 1.0 - 0.14 * max(0, defcon))
    return max(3, int(round(base * fattore)))


def secondi_prossimo_evento_per_defcon(defcon: int) -> int:
    """
    Intervallo prima del prossimo evento generato.
    A DEFCON 0 -> 60..90s. A DEFCON DEFCON_MAX -> 12..20s.
    """
    minimo_base = 60
    massimo_base = 90
    fattore = max(0.2, 1.0 - 0.16 * max(0, defcon))
    minimo = max(8, int(minimo_base * fattore))
    massimo = max(minimo + 4, int(massimo_base * fattore))
    return random.randint(minimo, massimo)


# ---------------------------------------------------------------------------
# DEFCON e crash
# ---------------------------------------------------------------------------


def applica_delta_defcon(sessione: SessioneVolo, delta: int) -> int:
    """
    Aggiorna DEFCON nei limiti [0, DEFCON_MAX+1].
    Se >DEFCON_MAX la sessione precipita.
    Ritorna il nuovo defcon (puo' essere DEFCON_MAX+1 se crash).
    """
    nuovo = int(sessione.defcon) + int(delta)
    if nuovo < 0:
        nuovo = 0
    if nuovo > DEFCON_MAX:
        sessione.stato = SESSIONE_STATO_CRASHED
        sessione.ended_at = timezone.now()
        sessione.defcon = DEFCON_MAX + 1
        sessione.save(
            update_fields=["stato", "ended_at", "defcon", "updated_at"]
        )
        return sessione.defcon
    sessione.defcon = nuovo
    sessione.save(update_fields=["defcon", "updated_at"])
    return nuovo


# ---------------------------------------------------------------------------
# Sottosistemi: stato runtime, ripristino, validazione
# ---------------------------------------------------------------------------


def get_o_crea_stato_sottosistema(
    sessione: SessioneVolo, sottosistema: SottosistemaNave
) -> StatoSottosistemaSessione:
    stato, _ = StatoSottosistemaSessione.objects.get_or_create(
        sessione=sessione, sottosistema=sottosistema, defaults={"online": True}
    )
    return stato


def applica_recoveries_pendenti(sessione: SessioneVolo) -> None:
    """Riporta online i sottosistemi il cui recovery_at e' scaduto."""
    now = timezone.now()
    qs = StatoSottosistemaSessione.objects.filter(
        sessione=sessione, online=False, recovery_at__isnull=False, recovery_at__lte=now
    )
    for st in qs:
        st.online = True
        st.recovery_at = None
        st.guasto_at = None
        st.save(update_fields=["online", "recovery_at", "guasto_at", "updated_at"])


def sottosistema_offline_per_codice(
    sessione: SessioneVolo, primo_carattere: str
) -> Optional[SottosistemaNave]:
    """
    Ritorna il SottosistemaNave guasto che corrisponde al primo carattere del
    codice inserito, oppure None se non c'e' guasto attivo.
    """
    sottos = SottosistemaNave.objects.filter(codice=primo_carattere.upper()).first()
    if not sottos:
        return None
    stato = StatoSottosistemaSessione.objects.filter(
        sessione=sessione, sottosistema=sottos, online=False
    ).first()
    return sottos if stato else None


# ---------------------------------------------------------------------------
# Generazione eventi random
# ---------------------------------------------------------------------------


def evento_attivo_corrente(sessione: SessioneVolo) -> Optional[EventoAttivoSessione]:
    return (
        EventoAttivoSessione.objects.filter(
            sessione=sessione, esito=EVENTO_ESITO_PENDING
        )
        .order_by("-created_at")
        .first()
    )


def _scegli_evento_random() -> Optional[EventoNave]:
    """Sceglie un evento random pesato sul `peso_random`."""
    eventi: List[EventoNave] = list(EventoNave.objects.filter(attivo=True))
    if not eventi:
        return None
    pesi = [max(1, int(e.peso_random or 1)) for e in eventi]
    return random.choices(eventi, weights=pesi, k=1)[0]


def genera_evento_se_dovuto(sessione: SessioneVolo) -> Optional[EventoAttivoSessione]:
    """
    Crea un nuovo EventoAttivoSessione se:
    - sessione in volo (decollo/volo/atterraggio sono tutti contesti operativi);
    - non c'e' un evento pending;
    - now >= next_event_at (oppure next_event_at e' None).
    """
    if not sessione.is_attiva:
        return None
    if evento_attivo_corrente(sessione) is not None:
        return None

    now = timezone.now()
    if sessione.next_event_at and now < sessione.next_event_at:
        return None

    evento = _scegli_evento_random()
    if not evento:
        sessione.next_event_at = now + timedelta(
            seconds=secondi_prossimo_evento_per_defcon(sessione.defcon)
        )
        sessione.save(update_fields=["next_event_at", "updated_at"])
        return None

    durata = secondi_evento_per_defcon(evento.durata_base_secondi, sessione.defcon)
    istanza = EventoAttivoSessione.objects.create(
        sessione=sessione,
        evento=evento,
        deadline_at=now + timedelta(seconds=durata),
    )
    sessione.next_event_at = istanza.deadline_at + timedelta(
        seconds=secondi_prossimo_evento_per_defcon(sessione.defcon)
    )
    sessione.save(update_fields=["next_event_at", "updated_at"])
    return istanza


def gestisci_timeout_evento(istanza: EventoAttivoSessione) -> Tuple[bool, int]:
    """
    Se l'evento attivo e' scaduto senza risposta:
    - segna esito timeout
    - applica DEFCON +1
    Ritorna (timeout_applicato, nuovo_defcon).
    """
    if istanza.esito != EVENTO_ESITO_PENDING:
        return False, istanza.sessione.defcon
    now = timezone.now()
    if now < istanza.deadline_at:
        return False, istanza.sessione.defcon
    istanza.esito = EVENTO_ESITO_TIMEOUT
    istanza.risolto_at = now
    istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
    nuovo = applica_delta_defcon(istanza.sessione, +1)
    return True, nuovo


# ---------------------------------------------------------------------------
# Tick generale: chiamato dalle viste e/o da un job background
# ---------------------------------------------------------------------------


@dataclass
class TickResult:
    sessione: SessioneVolo
    nuovo_evento: Optional[EventoAttivoSessione]
    timeout_applicato: bool
    transizione_arrivata: bool


@transaction.atomic
def tick_sessione(sessione: SessioneVolo) -> TickResult:
    """
    Avanza lo stato di una sessione nel modo idempotente:
    - applica recoveries sottosistemi;
    - chiude eventi pending scaduti (timeout) e applica DEFCON;
    - genera nuovo evento se necessario;
    - se la durata pianificata e' superata, marca arrivata (in volo->arrivata
      richiede comunque sequenza atterraggio gestita altrove).
    """
    sessione = SessioneVolo.objects.select_for_update().get(pk=sessione.pk)
    if sessione.is_terminata:
        return TickResult(sessione, None, False, False)

    applica_recoveries_pendenti(sessione)

    timeout = False
    pending = evento_attivo_corrente(sessione)
    if pending and timezone.now() >= pending.deadline_at:
        timeout, _ = gestisci_timeout_evento(pending)
        if sessione.is_terminata:
            return TickResult(sessione, None, timeout, False)
        pending = None

    nuovo = None
    if pending is None:
        nuovo = genera_evento_se_dovuto(sessione)

    transizione = False
    if (
        sessione.stato == SESSIONE_STATO_VOLO
        and sessione.started_at
        and sessione.durata_pianificata_secondi
    ):
        scadenza = sessione.started_at + timedelta(
            seconds=int(sessione.durata_pianificata_secondi)
        )
        if timezone.now() >= scadenza:
            sessione.stato = SESSIONE_STATO_ATTERRAGGIO
            sessione.atterraggio_iniziato_at = timezone.now()
            sessione.save(
                update_fields=["stato", "atterraggio_iniziato_at", "updated_at"]
            )
            transizione = True

    return TickResult(sessione, nuovo, timeout, transizione)


# ---------------------------------------------------------------------------
# Calcolo durata viaggio
# ---------------------------------------------------------------------------


def durata_viaggio_secondi(prefettura_partenza, prefettura_arrivo, defcon_iniziale: int) -> int:
    """
    Regole base:
    - stessa prefettura -> 10 min
    - stessa regione    -> 30 min
    - regioni diverse   -> 60 min
    Se DEFCON di partenza > 0 il tempo si allunga del 20% per ogni livello.
    """
    if prefettura_partenza is None or prefettura_arrivo is None:
        return 600
    if prefettura_partenza.pk == prefettura_arrivo.pk:
        base = 10 * 60
    else:
        regione_p = getattr(prefettura_partenza, "regione_id", None)
        regione_a = getattr(prefettura_arrivo, "regione_id", None)
        if regione_p and regione_a and regione_p == regione_a:
            base = 30 * 60
        else:
            base = 60 * 60
    malus = 1.0 + 0.2 * max(0, int(defcon_iniziale or 0))
    return int(round(base * malus))


# ---------------------------------------------------------------------------
# Valutazione codici a 3 caratteri
# ---------------------------------------------------------------------------


@dataclass
class ValutazioneCodice:
    esito: str  # uno tra EVENTO_ESITO_*, oppure 'sequenza_ok'/'sequenza_ko'/'invalido'/'no_evento'
    delta_defcon: int
    nuovo_defcon: int
    descrizione: str
    sequenza_avanzata: bool = False
    sequenza_completa: bool = False


def _processa_sequenza(
    sessione: SessioneVolo, codice: str, tipo: str
) -> Optional[ValutazioneCodice]:
    """
    Gestisce input durante decollo/atterraggio: ogni codice deve corrispondere
    al passo corrente della sequenza attiva. Errore -> sequenza ricomincia da 0
    e DEFCON +1.
    """
    seq = SequenzaVolo.objects.filter(tipo=tipo, attiva=True).order_by("-created_at").first()
    if not seq or not seq.codici:
        return None
    idx_attr = "decollo_idx" if tipo == SEQUENZA_DECOLLO else "atterraggio_idx"
    idx = getattr(sessione, idx_attr) or 0
    atteso = normalizza_codice(seq.codici[idx])
    if codice == atteso:
        idx += 1
        completa = idx >= len(seq.codici)
        setattr(sessione, idx_attr, idx)
        if completa and tipo == SEQUENZA_DECOLLO:
            sessione.stato = SESSIONE_STATO_VOLO
            sessione.decollo_completato_at = timezone.now()
            sessione.save(
                update_fields=[
                    idx_attr,
                    "stato",
                    "decollo_completato_at",
                    "updated_at",
                ]
            )
        elif completa and tipo == SEQUENZA_ATTERRAGGIO:
            sessione.stato = SESSIONE_STATO_ARRIVATA
            sessione.ended_at = timezone.now()
            sessione.save(
                update_fields=[idx_attr, "stato", "ended_at", "updated_at"]
            )
        else:
            sessione.save(update_fields=[idx_attr, "updated_at"])
        return ValutazioneCodice(
            esito="sequenza_ok",
            delta_defcon=0,
            nuovo_defcon=sessione.defcon,
            descrizione=(
                "Sequenza completata."
                if completa
                else f"Passo {idx}/{len(seq.codici)} OK."
            ),
            sequenza_avanzata=True,
            sequenza_completa=completa,
        )

    setattr(sessione, idx_attr, 0)
    sessione.save(update_fields=[idx_attr, "updated_at"])
    nuovo_defcon = applica_delta_defcon(sessione, +1)
    return ValutazioneCodice(
        esito="sequenza_ko",
        delta_defcon=+1,
        nuovo_defcon=nuovo_defcon,
        descrizione=f"Sequenza {tipo} interrotta. Codice atteso era {atteso}.",
    )


@transaction.atomic
def processa_codice(sessione: SessioneVolo, codice_raw: str) -> ValutazioneCodice:
    """
    Punto di ingresso unico per ogni codice digitato dal pilota.

    Regole prioritarie:
    1. crash o terminata -> rifiutato.
    2. fase decollo/atterraggio -> sequenza obbligatoria.
    3. fase volo:
       - formato non valido -> defcon +1
       - sottosistema guasto sul primo char -> defcon +1
       - codice == soluzione esatta evento attivo -> defcon -1
       - codice match parziale evento attivo -> defcon invariato
       - altrimenti -> defcon +1
    """
    sessione = SessioneVolo.objects.select_for_update().get(pk=sessione.pk)
    codice = normalizza_codice(codice_raw)
    defcon_pre = sessione.defcon
    pending = evento_attivo_corrente(sessione)

    if sessione.is_terminata:
        return ValutazioneCodice(
            esito="invalido",
            delta_defcon=0,
            nuovo_defcon=defcon_pre,
            descrizione="Sessione terminata.",
        )

    if not codice_valido_3char(codice):
        nuovo = applica_delta_defcon(sessione, +1)
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito="invalido",
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note="Formato non valido (servono 3 caratteri, ultimo numerico).",
        )
        return ValutazioneCodice(
            esito="invalido",
            delta_defcon=+1,
            nuovo_defcon=nuovo,
            descrizione="Formato codice non valido.",
        )

    if sessione.stato == SESSIONE_STATO_DECOLLO:
        ris = _processa_sequenza(sessione, codice, SEQUENZA_DECOLLO)
        if ris is not None:
            TentativoCodice.objects.create(
                sessione=sessione,
                codice=codice,
                esito=ris.esito,
                defcon_pre=defcon_pre,
                defcon_post=ris.nuovo_defcon,
                note=ris.descrizione,
            )
            return ris

    if sessione.stato == SESSIONE_STATO_ATTERRAGGIO:
        ris = _processa_sequenza(sessione, codice, SEQUENZA_ATTERRAGGIO)
        if ris is not None:
            TentativoCodice.objects.create(
                sessione=sessione,
                codice=codice,
                esito=ris.esito,
                defcon_pre=defcon_pre,
                defcon_post=ris.nuovo_defcon,
                note=ris.descrizione,
            )
            return ris

    sottos_guasto = sottosistema_offline_per_codice(sessione, codice[0])
    if sottos_guasto is not None:
        nuovo = applica_delta_defcon(sessione, +1)
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito="sottosistema_offline",
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note=f"Sottosistema {sottos_guasto.nome} guasto.",
        )
        return ValutazioneCodice(
            esito="sottosistema_offline",
            delta_defcon=+1,
            nuovo_defcon=nuovo,
            descrizione=f"Sottosistema {sottos_guasto.nome} guasto: codice respinto.",
        )

    if pending is None:
        nuovo = applica_delta_defcon(sessione, +1)
        TentativoCodice.objects.create(
            sessione=sessione,
            codice=codice,
            esito="no_evento",
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note="Nessun evento da risolvere.",
        )
        return ValutazioneCodice(
            esito="no_evento",
            delta_defcon=+1,
            nuovo_defcon=nuovo,
            descrizione="Nessun evento attivo: codice penalizzato.",
        )

    evento = pending.evento
    soluzione = normalizza_codice(evento.codice_soluzione_esatta)
    parziali = [normalizza_codice(p) for p in (evento.codici_soluzione_parziale or [])]

    if codice == soluzione:
        pending.esito = EVENTO_ESITO_RISOLTO
        pending.risolto_at = timezone.now()
        pending.codice_inserito = codice
        pending.save(
            update_fields=["esito", "risolto_at", "codice_inserito", "updated_at"]
        )
        nuovo = applica_delta_defcon(sessione, -1)
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito=EVENTO_ESITO_RISOLTO,
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note="Risoluzione esatta.",
        )
        return ValutazioneCodice(
            esito=EVENTO_ESITO_RISOLTO,
            delta_defcon=-1,
            nuovo_defcon=nuovo,
            descrizione="Evento risolto.",
        )

    if any(matcha_pattern(p, codice) for p in parziali):
        pending.esito = EVENTO_ESITO_PARZIALE
        pending.risolto_at = timezone.now()
        pending.codice_inserito = codice
        pending.save(
            update_fields=["esito", "risolto_at", "codice_inserito", "updated_at"]
        )
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito=EVENTO_ESITO_PARZIALE,
            defcon_pre=defcon_pre,
            defcon_post=defcon_pre,
            note="Risoluzione parziale.",
        )
        return ValutazioneCodice(
            esito=EVENTO_ESITO_PARZIALE,
            delta_defcon=0,
            nuovo_defcon=defcon_pre,
            descrizione="Risoluzione parziale: gravita' invariata.",
        )

    pending.esito = EVENTO_ESITO_FALLITO
    pending.risolto_at = timezone.now()
    pending.codice_inserito = codice
    pending.save(
        update_fields=["esito", "risolto_at", "codice_inserito", "updated_at"]
    )
    nuovo = applica_delta_defcon(sessione, +1)
    TentativoCodice.objects.create(
        sessione=sessione,
        evento_attivo=pending,
        codice=codice,
        esito=EVENTO_ESITO_FALLITO,
        defcon_pre=defcon_pre,
        defcon_post=nuovo,
        note="Codice dannoso/errato.",
    )
    return ValutazioneCodice(
        esito=EVENTO_ESITO_FALLITO,
        delta_defcon=+1,
        nuovo_defcon=nuovo,
        descrizione="Codice errato: gravita' aumentata.",
    )
