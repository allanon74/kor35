"""
Motore della console pilotaggio.

Logica autoritativa lato backend:
- generazione random degli eventi pesata sui pesi configurati;
- valutazione codici in 3 caratteri (esatto/parziale/dannoso); parziali con `_` o ``XY(N-M)``;
- aggiornamento DEFCON (gravita') e regola di crash (DEFCON > DEFCON_MAX);
- frequenza eventi (prob/tick o intervallo fallback) e durata risoluzione in tick da DEFCON;
- ripristino automatico sottosistemi dopo `durata_ripristino_secondi`;
- avanzamento sequenze di decollo e atterraggio.

Tutte le mutazioni sui modelli pilotaggio passano da qui in `transaction.atomic`.
"""
from __future__ import annotations

import math
import random
import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from .models import (
    DEFCON_MAX,
    EVENTO_ESITO_FALLITO,
    EVENTO_ESITO_GUASTO_CA,
    EVENTO_ESITO_PARZIALE,
    EVENTO_ESITO_PRECIPITAZIO,
    EVENTO_ESITO_PENDING,
    EVENTO_ESITO_RISOLTO,
    EVENTO_ESITO_TIMEOUT,
    EventoAttivoSessione,
    EventoNave,
    SESSIONE_STATO_ARRIVATA,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SEQUENZA_ATTERRAGGIO,
    SEQUENZA_DECOLLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
    TentativoCodice,
)

TIPI_PRODUZIONE = {"generatore"}


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


# Due caratteri (con jolly `_`) + terza cifra in intervallo: es. ML(4-9) -> ML4..ML9
_PATTERN_PARZIALE_RANGE = re.compile(r"^(.{2})\((\d)-(\d)\)$")


def codice_critico_globale_attivo(codice: str) -> bool:
    """True se il codice coincide con un pattern critico globale (staff)."""
    from .models import ComandoCriticoGlobale

    for row in ComandoCriticoGlobale.objects.filter(attivo=True).only("pattern"):
        if matcha_pattern(row.pattern, codice):
            return True
    return False


def matcha_pattern(pattern: str, codice: str) -> bool:
    """
    Match pattern parziale su codice 3 caratteri.

    Formati:
    - Jolly `_` (singolo carattere): es. ``A_3``, ``_B5``.
    - Intervallo sulla terza cifra: ``XY(N-M)`` con X,Y lettere/cifre/jolly,
      N e M cifre singole 0-9 (comprese); es. ``ML(4-9)`` equivale a ML4..ML9.
    """
    raw = (pattern or "").strip()
    c = normalizza_codice(codice)
    if len(c) != 3:
        return False

    m = _PATTERN_PARZIALE_RANGE.match(normalizza_codice(raw))
    if m:
        prefisso, lo_s, hi_s = m.group(1), m.group(2), m.group(3)
        lo, hi = int(lo_s), int(hi_s)
        if lo > hi:
            lo, hi = hi, lo
        if not c[2].isdigit():
            return False
        d = int(c[2])
        if d < lo or d > hi:
            return False
        return all(prefisso[i] == "_" or prefisso[i] == c[i] for i in range(2))

    p = normalizza_codice(raw)
    if len(p) != len(c):
        return False
    return all(pc == "_" or pc == cc for pc, cc in zip(p, c))


# ---------------------------------------------------------------------------
# Curve di difficolta' in funzione del DEFCON
# ---------------------------------------------------------------------------


def _stato_allerta_config(livello: int):
    """Configurazione staff per livello 0..6; None se tabella assente o riga mancante."""
    try:
        from .models import StatoAllertaPilot

        liv = int(livello)
        if liv < 0:
            liv = 0
        if liv > 6:
            liv = 6
        return StatoAllertaPilot.objects.filter(livello=liv).first()
    except Exception:
        return None


def secondi_tick_durante_evento(defcon: int) -> int:
    """
    Durata in secondi di ogni tick motore mentre c'e' un evento attivo (DEFCON).
    In viaggio regolare si usa invece PilotRuntimeConfig.tick_interval_secondi.
    """
    cfg = _stato_allerta_config(defcon)
    if cfg is not None:
        return max(1, int(cfg.tempo_risoluzione_secondi))
    base = 20
    fattore = max(0.3, 1.0 - 0.14 * max(0, defcon))
    return max(1, int(round(base * fattore)))


# Alias retrocompatibile (test / import legacy)
secondi_evento_per_defcon = secondi_tick_durante_evento


def intervallo_tick_sessione(sessione: SessioneVolo) -> float:
    """Intervallo tick in viaggio regolare (Runtime Console, fallback sessione)."""
    try:
        from .models import PilotRuntimeConfig

        cfg = PilotRuntimeConfig.get_solo()
        if cfg and cfg.tick_interval_secondi:
            return max(0.5, float(cfg.tick_interval_secondi))
    except Exception:
        pass
    return max(0.5, float(getattr(sessione, "tick_secondi", None) or 5.0))


def intervallo_tick_effettivo_sessione(sessione: SessioneVolo) -> float:
    """Tick corrente: durata evento DEFCON se c'e' evento attivo, altrimenti runtime."""
    pending = EventoAttivoSessione.objects.filter(
        sessione=sessione, esito=EVENTO_ESITO_PENDING
    ).exists()
    if pending:
        return float(secondi_tick_durante_evento(sessione.defcon))
    return intervallo_tick_sessione(sessione)


def secondi_fino_prossimo_tick(sessione: SessioneVolo) -> float:
    """Secondi mancanti prima del prossimo tick motore (0 = tick consentito)."""
    pending = eventi_attivi_correnti(sessione)
    if pending:
        now = timezone.now()
        interval = float(secondi_tick_durante_evento(sessione.defcon))
        waits = []
        for ev in pending:
            ev.refresh_from_db(
                fields=["prossima_valutazione_at", "created_at", "valutazioni_eseguite"]
            )
            if ev.prossima_valutazione_at is None:
                _programma_prossimo_check_evento(
                    ev, sessione, base=ev.created_at or now
                )
                ev.refresh_from_db(fields=["prossima_valutazione_at"])
            target = ev.prossima_valutazione_at
            if target is None:
                target = now + timedelta(seconds=interval)
            waits.append(max(0.0, (target - now).total_seconds()))
        # Con evento attivo: MAI usare il tick da 5s del volo regolare.
        return min(waits) if waits else interval

    last = getattr(sessione, "ultimo_tick_motore_at", None)
    if last is None:
        return 0.0
    interval = intervallo_tick_sessione(sessione)
    elapsed = (timezone.now() - last).total_seconds()
    return max(0.0, interval - elapsed)


def _programma_prossimo_check_evento(
    istanza: EventoAttivoSessione,
    sessione: SessioneVolo,
    *,
    base: Optional[datetime] = None,
) -> None:
    """
    Programma il prossimo check CA/ST/SP: adesso + tempo_risoluzione del DEFCON corrente.
    Chiamato alla comparsa dell'evento e dopo ogni tick evento.
    """
    sec = secondi_tick_durante_evento(sessione.defcon)
    when = (base or timezone.now()) + timedelta(seconds=sec)
    istanza.prossima_valutazione_at = when
    istanza.intervallo_reazione_secondi = sec
    istanza.reazione_fino_at = when
    istanza.save(
        update_fields=[
            "prossima_valutazione_at",
            "intervallo_reazione_secondi",
            "reazione_fino_at",
            "updated_at",
        ]
    )


def _programma_prossimo_check_evento_se_manca(
    istanza: EventoAttivoSessione, sessione: SessioneVolo
) -> None:
    """Ripara eventi legacy senza timer (solo se prossima_valutazione_at mancante)."""
    if istanza.prossima_valutazione_at is not None:
        return
    _programma_prossimo_check_evento(istanza, sessione, base=istanza.created_at)


def _evento_pronto_per_valutazione(
    istanza: EventoAttivoSessione, sessione: SessioneVolo
) -> bool:
    istanza.refresh_from_db(
        fields=["prossima_valutazione_at", "created_at", "valutazioni_eseguite", "esito"]
    )
    if istanza.esito != EVENTO_ESITO_PENDING:
        return False
    _programma_prossimo_check_evento_se_manca(istanza, sessione)
    if istanza.prossima_valutazione_at is None:
        return False
    return timezone.now() >= istanza.prossima_valutazione_at


def secondi_fino_valutazione_evento(sessione: SessioneVolo) -> Optional[float]:
    """Secondi mancanti al prossimo check evento (None se nessun pending)."""
    pending = eventi_attivi_correnti(sessione)
    if not pending:
        return None
    return secondi_fino_prossimo_tick(sessione)


def _schedula_prossima_valutazione_evento(
    istanza: EventoAttivoSessione, sessione: SessioneVolo
) -> None:
    """Dopo un tick evento: prossimo check tra tempo_risoluzione DEFCON attuale."""
    _programma_prossimo_check_evento(istanza, sessione)


def _incrementa_valutazioni_evento(istanza: EventoAttivoSessione) -> None:
    istanza.valutazioni_eseguite = int(istanza.valutazioni_eseguite or 0) + 1
    istanza.save(update_fields=["valutazioni_eseguite", "updated_at"])


def _ca_scadenza_critica_permessa(istanza: EventoAttivoSessione) -> bool:
    """Primo tick evento = tempo di reazione: niente precipizio da CA/scadenza critica."""
    return int(istanza.valutazioni_eseguite or 0) > 0


def intervallo_loop_motore() -> float:
    """
    Intervallo sleep del worker pilot_tick: sostituito dal tick DEFCON se almeno
    una sessione attiva ha un evento in corso.
    """
    try:
        from .models import PilotRuntimeConfig, SessioneVolo

        cfg = PilotRuntimeConfig.get_solo()
        base = max(0.5, float(cfg.tick_interval_secondi or 5.0))
        attive = SessioneVolo.objects.exclude(stato__in=["arrivata", "crashed"])
        for sessione in attive:
            if EventoAttivoSessione.objects.filter(
                sessione=sessione, esito=EVENTO_ESITO_PENDING
            ).exists():
                return float(secondi_tick_durante_evento(sessione.defcon))
        return base
    except Exception:
        return 5.0


def ticks_durata_evento_catalogo(spec_raw: str) -> int:
    """Durata effettiva dell'evento in numero di tick: `N` o random inclusivo `A-B`."""
    spec = str(spec_raw or "4").strip() or "4"
    if spec.startswith("-") and len(spec) > 1 and spec[1:].isdigit():
        return max(1, int(spec[1:]))
    if "-" in spec:
        a_s, b_s = spec.split("-", 1)
        if a_s.isdigit() and b_s.isdigit():
            a, b = int(a_s), int(b_s)
            if a > b:
                a, b = b, a
            return max(1, random.randint(max(1, a), max(1, b)))
    if spec.isdigit():
        return max(1, int(spec))
    return 4


def scadenza_critica_da_evento(evento: EventoNave) -> bool:
    """Flag catalogo; accetta legacy `durata_tick` con prefisso `-`."""
    if bool(getattr(evento, "scadenza_critica", False)):
        return True
    spec = str(evento.durata_tick or "").strip()
    return spec == "-" or (spec.startswith("-") and len(spec) > 1 and spec[1:].isdigit())


def secondi_durata_totale_evento(ticks: int, defcon: int) -> int:
    """Durata reale evento in secondi = tick evento × durata tick DEFCON."""
    return max(1, int(ticks)) * secondi_tick_durante_evento(defcon)


def secondi_prossimo_evento_per_defcon(defcon: int) -> int:
    """
    Intervallo casuale prima del prossimo evento. Se esiste riga staff per il DEFCON,
    usa [frequenza_evento_min_sec, frequenza_evento_max_sec].
    """
    cfg = _stato_allerta_config(defcon)
    if cfg is not None:
        lo = max(3, min(cfg.frequenza_evento_min_sec, cfg.frequenza_evento_max_sec))
        hi = max(lo, max(cfg.frequenza_evento_min_sec, cfg.frequenza_evento_max_sec))
        return random.randint(lo, hi)
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
        sessione.crash_reason = "defcon_overflow"
        sessione.save(
            update_fields=["stato", "ended_at", "defcon", "crash_reason", "updated_at"]
        )
        from .flight_log import log_precipizio

        log_precipizio(sessione, "defcon_overflow")
        return sessione.defcon
    sessione.defcon = nuovo
    sessione.save(update_fields=["defcon", "updated_at"])
    return nuovo


def forza_precipizio(
    sessione: SessioneVolo,
    reason: str = "catastrophic_event",
    *,
    evento_attivo=None,
) -> int:
    """
    Precipitazione immediata: stato crashed e DEFCON a DEFCON_MAX+1 (es. 6 se MAX=5).
    """
    sessione.stato = SESSIONE_STATO_CRASHED
    sessione.ended_at = timezone.now()
    sessione.defcon = DEFCON_MAX + 1
    sessione.crash_reason = reason or "catastrophic_event"
    sessione.save(
        update_fields=["stato", "ended_at", "defcon", "crash_reason", "updated_at"]
    )
    from .flight_log import log_precipizio

    log_precipizio(sessione, sessione.crash_reason, evento_attivo=evento_attivo)
    return sessione.defcon


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

    auto_qs = StatoSottosistemaSessione.objects.select_related("sottosistema").filter(
        sessione=sessione, online=False, recovery_at__isnull=True
    )
    for st in auto_qs:
        if st.espulso:
            continue
        if random.random() < _prob_ripristino_per_livello(st):
            st.online = True
            st.guasto_at = None
            st.livello_attuale = _clamp_livello(st.livello_target)
            st.save(
                update_fields=[
                    "online",
                    "guasto_at",
                    "livello_attuale",
                    "updated_at",
                ]
            )


def _clamp_livello(val: int) -> int:
    return max(0, min(9, int(val or 0)))


def _prob_guasto_per_livello(stato: StatoSottosistemaSessione) -> float:
    livello = int(stato.livello_attuale or 0)
    curva = stato.sottosistema.guasto_percent_per_livello or {}
    if str(livello) in curva:
        try:
            return max(0.0, min(1.0, float(curva.get(str(livello), 0.0)) / 100.0))
        except Exception:
            pass
    if livello >= 9:
        return float(stato.sottosistema.probabilita_guasto_9 or 0.0)
    if livello == 8:
        return float(stato.sottosistema.probabilita_guasto_8 or 0.0)
    if livello == 7:
        return float(stato.sottosistema.probabilita_guasto_7 or 0.0)
    return 0.0


def _prob_ripristino_per_livello(stato: StatoSottosistemaSessione) -> float:
    livello = int(stato.livello_target or 0)
    curva = stato.sottosistema.ripristino_percent_per_livello or {}
    try:
        return max(0.0, min(1.0, float(curva.get(str(livello), 0.0)) / 100.0))
    except Exception:
        return 0.0


def _avanza_energia_sessione(sessione: SessioneVolo) -> None:
    """
    Simulazione energia/carburante/distanza per tick.
    """
    stati = list(
        StatoSottosistemaSessione.objects.select_related("sottosistema").filter(
            sessione=sessione
        )
    )
    if not stati:
        return

    for st in stati:
        if st.espulso:
            st.online = False
            st.livello_attuale = 0
            st.livello_target = 0
            st.save(update_fields=["online", "livello_attuale", "livello_target", "updated_at"])
            continue
        st.livello_target = _clamp_livello(st.livello_target)
        # Alcuni sistemi hanno inerzia: il livello attuale raggiunge il target per step.
        if st.sottosistema.tipo == "generatore":
            step = max(1, int(st.sottosistema.rampa_livelli_per_tick or 1))
            if st.livello_attuale < st.livello_target:
                st.livello_attuale = min(st.livello_target, st.livello_attuale + step)
            elif st.livello_attuale > st.livello_target:
                st.livello_attuale = max(st.livello_target, st.livello_attuale - step)
        else:
            st.livello_attuale = st.livello_target
        st.save(update_fields=["livello_target", "livello_attuale", "updated_at"])

    produzione = 0.0
    consumo_energia = 0.0
    consumo_carburante = 0.0
    velocita_motore_base = 0.0
    spinta_manovra_avanti = 0.0
    spinta_manovra_indietro = 0.0
    livello_portale = 0
    coeff_portale = 0.15
    capacita_storage = 0.0
    capacita_carburante = 0.0

    for st in stati:
        ss = st.sottosistema
        if not st.online:
            continue
        livello = float(st.livello_attuale or 0)
        if ss.tipo in TIPI_PRODUZIONE:
            produzione += livello * float(ss.coeff_produzione or 0.0)
            consumo_carburante += livello * float(ss.coeff_consumo_carburante or 0.0)
        elif ss.tipo == "batteria":
            capacita_storage += float(ss.capacita_storage or 0.0)
        elif ss.tipo == "serbatoio":
            capacita_carburante += float(ss.capacita_carburante or 0.0)
        else:
            consumo_energia += livello * float(ss.coeff_consumo_energia or 0.0)
        if ss.tipo == "motore":
            velocita_motore_base += livello * float(ss.coeff_produzione or 0.0)
        if ss.tipo == "manovra":
            if st.direzione == "avanti":
                spinta_manovra_avanti += livello * float(ss.coeff_produzione or 0.0)
            elif st.direzione == "indietro":
                spinta_manovra_indietro += livello * float(ss.coeff_produzione or 0.0)
        if ss.tipo == "portale":
            livello_portale = max(livello_portale, int(livello))
            coeff_portale = float(ss.coeff_effetto_speciale or 0.15)

    sessione.storage_energia_massimo = max(0.0, capacita_storage)
    if capacita_carburante > 0:
        sessione.carburante_massimo = max(0.0, capacita_carburante)
        if sessione.carburante_attuale > sessione.carburante_massimo:
            sessione.carburante_attuale = sessione.carburante_massimo
    if sessione.storage_energia_attuale > sessione.storage_energia_massimo:
        sessione.storage_energia_attuale = sessione.storage_energia_massimo

    if sessione.carburante_attuale <= 0:
        produzione = 0.0
        consumo_carburante = 0.0
    else:
        sessione.carburante_attuale = max(
            0.0, sessione.carburante_attuale - min(sessione.carburante_attuale, consumo_carburante)
        )
        # Se il carburante si esaurisce in questo tick, i reattori non producono oltre.
        if sessione.carburante_attuale <= 0:
            produzione = 0.0
            consumo_carburante = 0.0

    saldo = produzione - consumo_energia
    if saldo < 0:
        assorbito = min(sessione.storage_energia_attuale, abs(saldo))
        sessione.storage_energia_attuale -= assorbito
    elif saldo > 0 and sessione.stato == SESSIONE_STATO_IDLE:
        conversione = max(0.0, min(1.0, max((s.sottosistema.coeff_ricarica_storage or 0.5) for s in stati if s.sottosistema.tipo == "batteria") if any(s.sottosistema.tipo == "batteria" for s in stati) else 0.0))
        sessione.storage_energia_attuale = min(
            sessione.storage_energia_massimo,
            sessione.storage_energia_attuale + (saldo * conversione),
        )
        sessione.carburante_attuale = min(
            sessione.carburante_massimo,
            sessione.carburante_attuale + float(sessione.coeff_rigenerazione_carburante_riposo or 0.0),
        )

    # End-of-energy: zero carburante + zero batterie + zero produzione => crash immediato.
    if (
        float(sessione.carburante_attuale or 0.0) <= 0.0
        and float(sessione.storage_energia_attuale or 0.0) <= 0.0
        and float(produzione or 0.0) <= 0.0
    ):
        sessione.produzione_ultimo_tick = 0.0
        sessione.consumo_ultimo_tick = round(consumo_energia, 3)
        sessione.save(
            update_fields=[
                "storage_energia_massimo",
                "storage_energia_attuale",
                "carburante_massimo",
                "carburante_attuale",
                "produzione_ultimo_tick",
                "consumo_ultimo_tick",
                "updated_at",
            ]
        )
        forza_precipizio(sessione, reason="end_of_energy")
        return

    # Formula richiesta: base_motore * potenza_motore * (coeff_portale * livello_portale).
    moltiplicatore_portale = max(0.0, coeff_portale * float(livello_portale))
    velocita_motore = velocita_motore_base * moltiplicatore_portale
    velocita_motore += (spinta_manovra_avanti * 0.35)
    velocita_motore -= (spinta_manovra_indietro * 0.35)
    sessione.distanza_percorsa = min(
        float(sessione.distanza_target or 0.0),
        float(sessione.distanza_percorsa or 0.0) + max(0.0, velocita_motore),
    )
    sessione.produzione_ultimo_tick = round(produzione, 3)
    sessione.consumo_ultimo_tick = round(consumo_energia, 3)
    sessione.save(
        update_fields=[
            "storage_energia_massimo",
            "storage_energia_attuale",
            "carburante_massimo",
            "carburante_attuale",
            "distanza_percorsa",
            "produzione_ultimo_tick",
            "consumo_ultimo_tick",
            "updated_at",
        ]
    )
    _marca_crociera_se_spinta(sessione)

    for st in stati:
        if not st.online:
            continue
        p_guasto = _prob_guasto_per_livello(st)
        if p_guasto <= 0:
            continue
        if random.random() < p_guasto:
            st.online = False
            st.guasto_at = timezone.now()
            st.livello_attuale = 0
            st.livello_target = 0
            st.save(
                update_fields=[
                    "online",
                    "guasto_at",
                    "livello_attuale",
                    "livello_target",
                    "updated_at",
                ]
            )
            from .flight_log import log_guasto_sottosistema

            log_guasto_sottosistema(sessione, st, causa="random")
            applica_effetto_guasto(sessione, st)


def _opposto_direzione(d: str) -> str:
    return {
        "avanti": "indietro",
        "indietro": "avanti",
        "su": "giu",
        "giu": "su",
        "destra": "sinistra",
        "sinistra": "destra",
    }.get((d or "").strip().lower(), "")


def _to_float(v, default=0.0) -> float:
    try:
        return float(v)
    except Exception:
        return float(default)


def applica_effetto_guasto(sessione: SessioneVolo, stato: StatoSottosistemaSessione) -> None:
    cfg = stato.sottosistema.effetti_guasto_json or {}
    _applica_effetto_configurato(sessione, stato, cfg)


def _applica_effetto_configurato(
    sessione: SessioneVolo, stato: StatoSottosistemaSessione, cfg: dict
) -> None:
    tipo = str(cfg.get("tipo") or "none").strip().lower()
    valore = _to_float(cfg.get("valore"), 0.0)
    target_codice = str(cfg.get("target_codice") or "").strip().upper()
    if tipo in {"none", ""}:
        return
    if tipo == "naufragio":
        forza_precipizio(sessione, reason="fault_effect_shipwreck")
        return
    if tipo == "riduci_carburante_percent":
        cut = max(0.0, min(100.0, valore)) / 100.0
        sessione.carburante_attuale = max(0.0, float(sessione.carburante_attuale or 0.0) * (1.0 - cut))
        sessione.save(update_fields=["carburante_attuale", "updated_at"])
        return
    if tipo == "riduci_batterie_percent":
        cut = max(0.0, min(100.0, valore)) / 100.0
        sessione.storage_energia_attuale = max(0.0, float(sessione.storage_energia_attuale or 0.0) * (1.0 - cut))
        sessione.save(update_fields=["storage_energia_attuale", "updated_at"])
        return
    if tipo == "allunga_distanza_percent":
        inc = max(0.0, valore) / 100.0
        sessione.distanza_target = float(sessione.distanza_target or 0.0) * (1.0 + inc)
        sessione.save(update_fields=["distanza_target", "updated_at"])
        return
    if tipo == "guasto_altro_percent":
        if not target_codice:
            return
        p = max(0.0, min(100.0, valore)) / 100.0
        if random.random() > p:
            return
        target = StatoSottosistemaSessione.objects.select_related("sottosistema").filter(
            sessione=sessione, sottosistema__codice=target_codice
        ).first()
        if target and target.online:
            target.online = False
            target.guasto_at = timezone.now()
            target.livello_target = 0
            target.livello_attuale = 0
            target.save(update_fields=["online", "guasto_at", "livello_target", "livello_attuale", "updated_at"])
        return
    if tipo == "guasto_random_percent":
        p = max(0.0, min(100.0, valore)) / 100.0
        if random.random() > p:
            return
        pool = list(
            StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione, online=True)
            .exclude(pk=stato.pk)
        )
        if not pool:
            return
        target = random.choice(pool)
        target.online = False
        target.guasto_at = timezone.now()
        target.livello_target = 0
        target.livello_attuale = 0
        target.save(update_fields=["online", "guasto_at", "livello_target", "livello_attuale", "updated_at"])


def applica_effetto_inversione(sessione: SessioneVolo, stato: StatoSottosistemaSessione) -> None:
    cfg = stato.sottosistema.effetti_inversione_json or {}
    p = max(0.0, min(100.0, _to_float(cfg.get("probabilita_percent"), 0.0))) / 100.0
    if p <= 0 or random.random() > p:
        return
    _applica_effetto_configurato(sessione, stato, cfg)


def applica_effetto_espulsione(sessione: SessioneVolo, stato: StatoSottosistemaSessione) -> None:
    cfg = stato.sottosistema.effetti_espulsione_json or {}
    p = max(0.0, min(100.0, _to_float(cfg.get("probabilita_percent"), 0.0))) / 100.0
    if p <= 0 or random.random() > p:
        return
    _applica_effetto_configurato(sessione, stato, cfg)


def _eval_leaf(cond: dict, stati_by_key: dict, direzione_evento: str) -> bool:
    target = str(cond.get("sottosistema") or "").strip().upper()
    stato = stati_by_key.get(target)
    if stato is None:
        return False
    livello = float(stato.livello_attuale or 0)
    op = str(cond.get("op") or "=").strip().lower()
    tipo = str(stato.sottosistema.tipo or "").strip().lower()
    if tipo in {"batteria", "serbatoio"}:
        if op == "distrutte":
            return not bool(stato.online)
        if op in {"piene", "vuote", "non_piene", "non_vuote"}:
            if tipo == "batteria":
                max_v = float(stato.sessione.storage_energia_massimo or 0.0)
                cur_v = float(stato.sessione.storage_energia_attuale or 0.0)
            else:
                max_v = float(stato.sessione.carburante_massimo or 0.0)
                cur_v = float(stato.sessione.carburante_attuale or 0.0)
            if max_v <= 0:
                return op == "vuote"
            eps = max(0.001, max_v * 0.01)
            if op == "piene":
                return cur_v >= (max_v - eps)
            if op == "vuote":
                return cur_v <= eps
            if op == "non_piene":
                return cur_v < (max_v - eps)
            if op == "non_vuote":
                return cur_v > eps
    if op == "invertito":
        return bool(stato.invertito)
    if op == "non_invertito":
        return not bool(stato.invertito)
    if op == "espulso":
        return bool(stato.espulso)
    if op == "non_espulso":
        return not bool(stato.espulso)
    if op in {"=", "eq"}:
        return livello == _to_float(cond.get("value"))
    if op in {">", "gt"}:
        return livello > _to_float(cond.get("value"))
    if op in {"<", "lt"}:
        return livello < _to_float(cond.get("value"))
    if op in {">=", "gte"}:
        return livello >= _to_float(cond.get("value"))
    if op in {"<=", "lte"}:
        return livello <= _to_float(cond.get("value"))
    if op == "between":
        lo = _to_float(cond.get("min"))
        hi = _to_float(cond.get("max"))
        if lo > hi:
            lo, hi = hi, lo
        return lo <= livello <= hi
    if op == "direction":
        rule = str(cond.get("direction_rule") or "stessa_direzione").strip().lower()
        dir_sub = str(stato.direzione or "").strip().lower()
        dir_evt = str(direzione_evento or "").strip().lower()
        opp = _opposto_direzione(dir_evt)
        if rule == "stessa_direzione":
            return dir_sub == dir_evt
        if rule == "direzione_opposta":
            return dir_sub == opp
        if rule == "non_stessa_direzione":
            return dir_sub != dir_evt
        if rule == "non_direzione_opposta":
            return dir_sub != opp
        return False
    return False


def _eval_group(group: dict, stati_by_key: dict, direzione_evento: str) -> bool:
    logic = str(group.get("logic") or "all").strip().lower()
    conditions = group.get("conditions") or []
    checks = [
        _eval_leaf(c, stati_by_key, direzione_evento)
        for c in conditions
        if isinstance(c, dict)
    ]
    if not checks:
        return False
    return all(checks) if logic == "all" else any(checks)


def _eval_expression(expr: dict, stati_by_key: dict, direzione_evento: str) -> bool:
    if not isinstance(expr, dict):
        return False
    op = str(expr.get("op") or "").strip().lower()
    if op in ("and", "or"):
        items = expr.get("items") or []
        checks = [
            _eval_expression(item, stati_by_key, direzione_evento)
            if isinstance(item, dict) and ("op" in item or "items" in item)
            else _eval_leaf(item, stati_by_key, direzione_evento)
            for item in items
            if isinstance(item, dict)
        ]
        if not checks:
            return False
        return all(checks) if op == "and" else any(checks)
    return _eval_leaf(expr, stati_by_key, direzione_evento)


def _ca_guasto_ids_da_cfg(cfg: dict) -> List[str]:
    """Estrae UUID sottosistema da chiavi singole/plurali nel payload ca_effetto."""
    ids: List[str] = []
    for key in ("sottosistema_ids", "sottosistemi_ids"):
        val = (cfg or {}).get(key)
        if isinstance(val, list):
            ids.extend(str(x).strip() for x in val if str(x).strip())
    sid = (cfg or {}).get("sottosistema_id")
    if sid:
        ids.append(str(sid).strip())
    out: List[str] = []
    seen = set()
    for raw in ids:
        if raw and raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


def _ca_guasto_codici_da_cfg(cfg: dict) -> List[str]:
    """Estrae codici 1-char da chiavi singole/plurali nel payload ca_effetto."""
    codes: List[str] = []
    for key in ("sottosistema_codici", "sottosistemi_codici"):
        val = (cfg or {}).get(key)
        if isinstance(val, list):
            codes.extend(
                str(x).strip().upper()[:1] for x in val if str(x).strip()
            )
    scode = (cfg or {}).get("sottosistema_codice")
    if scode:
        codes.append(str(scode).strip().upper()[:1])
    out: List[str] = []
    seen = set()
    for raw in codes:
        if raw and raw not in seen:
            seen.add(raw)
            out.append(raw)
    return out


def _estrai_codici_sottosistema_da_sezione(regole: dict, key: str) -> List[str]:
    """Estrae codici 1-char citati nelle condizioni di una sezione regole (es. ca)."""
    section = (regole or {}).get(key) or {}
    found: List[str] = []

    def walk(node) -> None:
        if not isinstance(node, dict):
            return
        raw = node.get("sottosistema")
        if raw:
            code = str(raw).strip().upper()[:1]
            if code and code not in found:
                found.append(code)
        for item in node.get("items") or []:
            walk(item)
        for item in node.get("conditions") or []:
            walk(item)

    expr = section.get("expression")
    if isinstance(expr, dict):
        walk(expr)
    for cond in section.get("_conditions") or []:
        walk(cond)
    for group in section.get("groups") or []:
        if isinstance(group, dict):
            for cond in group.get("conditions") or []:
                walk(cond)
    return found


def _stato_sottosistema_ca_per_target(
    sessione: SessioneVolo,
    *,
    sottosistema_id=None,
    sottosistema_codice: str = "",
) -> Optional[StatoSottosistemaSessione]:
    """Risolve lo stato runtime per id o codice sottosistema (crea se assente)."""
    stato = None
    if sottosistema_id:
        stato = (
            StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione, sottosistema_id=sottosistema_id)
            .first()
        )
        sdef = SottosistemaNave.objects.filter(pk=sottosistema_id).first()
        if stato is None and sdef:
            stato = get_o_crea_stato_sottosistema(sessione, sdef)
        if stato is None and sdef is None:
            scode = str(sottosistema_codice or "").strip().upper()[:1]
            if scode:
                sdef = SottosistemaNave.objects.filter(codice=scode).first()
                if sdef:
                    stato = get_o_crea_stato_sottosistema(sessione, sdef)
    else:
        scode = str(sottosistema_codice or "").strip().upper()[:1]
        if scode:
            sdef = SottosistemaNave.objects.filter(codice=scode).first()
            if sdef:
                stato = get_o_crea_stato_sottosistema(sessione, sdef)
    return stato


def _forza_guasto_stato_sottosistema(
    sessione: SessioneVolo,
    stato: StatoSottosistemaSessione,
    *,
    now=None,
    causa: str = "ca",
) -> None:
    """Segna offline un sottosistema e applica gli effetti guasto configurati."""
    ts = now or timezone.now()
    stato.online = False
    stato.guasto_at = ts
    stato.save(
        update_fields=[
            "online",
            "guasto_at",
            "recovery_at",
            "livello_target",
            "livello_attuale",
            "updated_at",
        ]
    )
    applica_effetto_guasto(sessione, stato)
    from .flight_log import log_guasto_sottosistema

    log_guasto_sottosistema(sessione, stato, causa=causa)


def _candidati_stati_ca_guasto(
    sessione: SessioneVolo, cfg: dict
) -> List[StatoSottosistemaSessione]:
    """
    Pool di stati runtime candidati al guasto CA.
    Se non sono indicati id/codici, usa tutti i sottosistemi della sessione.
    """
    stati: List[StatoSottosistemaSessione] = []
    seen_pks = set()
    for sid in _ca_guasto_ids_da_cfg(cfg):
        st = _stato_sottosistema_ca_per_target(sessione, sottosistema_id=sid)
        if st is not None and st.pk not in seen_pks:
            seen_pks.add(st.pk)
            stati.append(st)
    for code in _ca_guasto_codici_da_cfg(cfg):
        st = _stato_sottosistema_ca_per_target(
            sessione, sottosistema_codice=code
        )
        if st is not None and st.pk not in seen_pks:
            seen_pks.add(st.pk)
            stati.append(st)
    if not stati:
        stati = list(
            StatoSottosistemaSessione.objects.select_related("sottosistema")
            .filter(sessione=sessione)
            .order_by("sottosistema__ordine", "sottosistema__codice")
        )
    solo_online = (cfg or {}).get("solo_online", True)
    if solo_online:
        stati = [st for st in stati if st.online and not st.espulso]
    return stati


def _seleziona_stati_ca_guasto(
    sessione: SessioneVolo, cfg: dict
) -> List[StatoSottosistemaSessione]:
    """Risolve gli stati da mettere in guasto in base a ca_effetto."""
    tipo = str((cfg or {}).get("tipo") or "precipizio").strip().lower()
    if tipo == "guasto_sottosistema":
        st = _stato_sottosistema_ca_per_target(
            sessione,
            sottosistema_id=(cfg or {}).get("sottosistema_id"),
            sottosistema_codice=str((cfg or {}).get("sottosistema_codice") or ""),
        )
        return [st] if st is not None else []
    if tipo != "guasto_sottosistemi":
        return []

    candidati = _candidati_stati_ca_guasto(sessione, cfg)
    modalita = str((cfg or {}).get("modalita") or "tutti").strip().lower()
    if modalita == "random":
        quantita = max(1, int((cfg or {}).get("quantita") or 1))
        if not candidati:
            return []
        k = min(quantita, len(candidati))
        return random.sample(candidati, k=k)
    return candidati


def _applica_esito_ca_da_regole(
    sessione: SessioneVolo, istanza: EventoAttivoSessione, regole: dict
) -> Tuple[str, int]:
    """
    Quando le regole valutano CA: default precipizio nave; opzionale guasto forzato
    su uno o più sottosistemi (regole_json['ca_effetto']).
    """
    cfg = (regole or {}).get("ca_effetto") if isinstance(regole, dict) else None
    tipo = str((cfg or {}).get("tipo") or "precipizio").strip().lower()

    # Doppia rete di sicurezza: mai precipizio CA al primo check evento.
    if (
        tipo == "precipizio"
        and int(istanza.valutazioni_eseguite or 0) == 0
    ):
        defcon = applica_delta_defcon(sessione, +1)
        if sessione.is_terminata:
            istanza.esito = EVENTO_ESITO_PRECIPITAZIO
            istanza.risolto_at = timezone.now()
            istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
            return "ca", defcon
        return "ca_grace", defcon

    if tipo in {"guasto_sottosistema", "guasto_sottosistemi"}:
        stati = _seleziona_stati_ca_guasto(sessione, cfg or {})
        if not stati and tipo == "guasto_sottosistema":
            codice_cfg = str((cfg or {}).get("sottosistema_codice") or "").strip().upper()[:1]
            if codice_cfg:
                st = _stato_sottosistema_ca_per_target(
                    sessione, sottosistema_codice=codice_cfg
                )
                if st is not None:
                    stati = [st]
            if not stati:
                for codice in _estrai_codici_sottosistema_da_sezione(regole, "ca"):
                    st = _stato_sottosistema_ca_per_target(
                        sessione, sottosistema_codice=codice
                    )
                    if st is not None:
                        stati = [st]
                        break
        if not stati:
            now = timezone.now()
            istanza.esito = EVENTO_ESITO_TIMEOUT
            istanza.risolto_at = now
            istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
            return "ca_config", applica_delta_defcon(sessione, +1)

        now = timezone.now()
        for stato in stati:
            _forza_guasto_stato_sottosistema(sessione, stato, now=now)
        istanza.esito = EVENTO_ESITO_GUASTO_CA
        istanza.risolto_at = now
        istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
        return "ca_guasto", sessione.defcon

    istanza.esito = EVENTO_ESITO_PRECIPITAZIO
    istanza.risolto_at = timezone.now()
    istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
    return "ca", forza_precipizio(sessione, evento_attivo=istanza)


def _stati_by_key_sessione(sessione: SessioneVolo) -> dict:
    stati = list(
        StatoSottosistemaSessione.objects.select_related("sottosistema").filter(sessione=sessione)
    )
    stati_by_key = {}
    for st in stati:
        stati_by_key[(st.sottosistema.codice or "").strip().upper()] = st
        stati_by_key[(st.sottosistema.nome or "").strip().upper()] = st
    return stati_by_key


def _eval_outcome_regole(regole: dict, key: str, stati_by_key: dict, direzione_evento: str) -> bool:
    section = (regole or {}).get(key) or {}
    expr = section.get("expression")
    if isinstance(expr, dict):
        return _eval_expression(expr, stati_by_key, direzione_evento)
    groups = section.get("groups") or []
    if not groups:
        return False
    return any(
        _eval_group(g, stati_by_key, direzione_evento)
        for g in groups
        if isinstance(g, dict)
    )


def _eval_soluzione_totale(regole: dict, stati_by_key: dict, direzione_evento: str) -> bool:
    return _eval_outcome_regole(regole, "st", stati_by_key, direzione_evento)


def _eval_soluzione_parziale(regole: dict, stati_by_key: dict, direzione_evento: str) -> bool:
    return _eval_outcome_regole(regole, "sp", stati_by_key, direzione_evento)


def _decrementa_ticks_evento(
    sessione: SessioneVolo,
    istanza: EventoAttivoSessione,
    regole: dict,
    *,
    defcon_gia_penalizzato: bool,
) -> Optional[Tuple[str, int]]:
    """Decrementa i tick evento; a zero applica scadenza critica o timeout."""
    ca_permessa = _ca_scadenza_critica_permessa(istanza)
    if istanza.ticks_rimanenti is not None:
        istanza.ticks_rimanenti = max(0, int(istanza.ticks_rimanenti) - 1)
        if istanza.ticks_rimanenti <= 0:
            if istanza.precipita_a_scadenza and ca_permessa:
                return _applica_esito_ca_da_regole(sessione, istanza, regole)
            istanza.esito = EVENTO_ESITO_TIMEOUT
            istanza.risolto_at = timezone.now()
            istanza.save(
                update_fields=["ticks_rimanenti", "esito", "risolto_at", "updated_at"]
            )
            if defcon_gia_penalizzato:
                return "timeout", sessione.defcon
            return "timeout", applica_delta_defcon(sessione, +1)
        istanza.save(update_fields=["ticks_rimanenti", "updated_at"])
        return None

    now = timezone.now()
    if istanza.deadline_at and now >= istanza.deadline_at:
        if istanza.precipita_a_scadenza and ca_permessa:
            return _applica_esito_ca_da_regole(sessione, istanza, regole)
        istanza.esito = EVENTO_ESITO_TIMEOUT
        istanza.risolto_at = now
        istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
        if defcon_gia_penalizzato:
            return "timeout", sessione.defcon
        return "timeout", applica_delta_defcon(sessione, +1)
    return None


def valuta_evento_tick(sessione: SessioneVolo, istanza: EventoAttivoSessione) -> Tuple[str, int]:
    """
    Valutazione fine tick evento (ordine fisso):
    - CA vera → effetto ca_effetto (dal secondo check in poi: tempo di reazione)
    - ST vera → DEFCON -1, evento risolto
    - SP vera → evento prosegue, DEFCON invariato
    - altrimenti → DEFCON +1

    Poi decrementa i tick rimanenti; a zero: scadenza_critica → ca_effetto, altrimenti timeout.
    """
    if not _evento_pronto_per_valutazione(istanza, sessione):
        return "wait", sessione.defcon

    regole = istanza.evento.regole_json or {}
    stati_by_key = _stati_by_key_sessione(sessione)
    direzione = istanza.direzione_evento
    ca_permessa = _ca_scadenza_critica_permessa(istanza)
    esito_diario = None
    defcon_pre = int(sessione.defcon or 0)

    try:
        if ca_permessa and _eval_outcome_regole(regole, "ca", stati_by_key, direzione):
            esito_diario, defcon_out = _applica_esito_ca_da_regole(sessione, istanza, regole)
            return esito_diario, defcon_out

        if _eval_soluzione_totale(regole, stati_by_key, direzione):
            istanza.esito = EVENTO_ESITO_RISOLTO
            istanza.risolto_at = timezone.now()
            istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
            esito_diario = "st"
            return "st", applica_delta_defcon(sessione, -1)

        if _eval_soluzione_parziale(regole, stati_by_key, direzione):
            scadenza = _decrementa_ticks_evento(
                sessione, istanza, regole, defcon_gia_penalizzato=False
            )
            if scadenza is not None:
                esito_diario = scadenza[0]
                return scadenza
            esito_diario = "sp"
            return "sp", sessione.defcon

        defcon = applica_delta_defcon(sessione, +1)
        if sessione.is_terminata:
            istanza.esito = EVENTO_ESITO_PRECIPITAZIO
            istanza.risolto_at = timezone.now()
            istanza.save(update_fields=["esito", "risolto_at", "updated_at"])
            esito_diario = "ca"
            return "ca", defcon

        scadenza = _decrementa_ticks_evento(
            sessione, istanza, regole, defcon_gia_penalizzato=True
        )
        if scadenza is not None:
            esito_diario = scadenza[0]
            return scadenza
        esito_diario = "ko"
        return "ko", defcon
    finally:
        if esito_diario is not None:
            _incrementa_valutazioni_evento(istanza)
            try:
                sessione.refresh_from_db()
                istanza.refresh_from_db()
                from .flight_log import log_valutazione_evento

                log_valutazione_evento(
                    sessione,
                    istanza,
                    esito_diario,
                    defcon_pre,
                    int(sessione.defcon or 0),
                )
            except Exception:
                pass


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


def eventi_attivi_correnti(sessione: SessioneVolo) -> list[EventoAttivoSessione]:
    return list(
        EventoAttivoSessione.objects.filter(
            sessione=sessione, esito=EVENTO_ESITO_PENDING
        ).order_by("-created_at")
    )


def _scegli_evento_random() -> Optional[EventoNave]:
    """Sceglie un evento random pesato sul `peso_random`."""
    eventi: List[EventoNave] = list(EventoNave.objects.filter(attivo=True))
    if not eventi:
        return None
    pesi = [max(1, int(e.peso_random or 1)) for e in eventi]
    return random.choices(eventi, weights=pesi, k=1)[0]


def _motori_in_spinta(sessione: SessioneVolo) -> bool:
    """True se almeno un motore online ha livello attuale > 0."""
    return StatoSottosistemaSessione.objects.filter(
        sessione=sessione,
        sottosistema__tipo="motore",
        online=True,
        livello_attuale__gt=0,
    ).exists()


def _marca_crociera_se_spinta(sessione: SessioneVolo) -> None:
    """Imposta decollo_completato_at al primo tick con motore in spinta."""
    if sessione.decollo_completato_at is not None:
        return
    if not _motori_in_spinta(sessione):
        return
    sessione.decollo_completato_at = timezone.now()
    sessione.save(update_fields=["decollo_completato_at", "updated_at"])
    from .flight_log import log_decollo

    log_decollo(sessione)


def _sessione_ha_decollato(sessione: SessioneVolo) -> bool:
    """
    Crociera iniziata: almeno un motore e' stato acceso almeno una volta in questa sessione.
    Non basta la distanza (manovra/portale) ne' lo stato sessione «volo».
    """
    return sessione.decollo_completato_at is not None


def prepara_sessione_nuovo_volo(sessione: SessioneVolo) -> None:
    """
    Reset runtime per un nuovo decollo sullo stesso record sessione:
    chiude eventi pending residui, azzera distanza e timer eventi.
    """
    now = timezone.now()
    EventoAttivoSessione.objects.filter(
        sessione=sessione, esito=EVENTO_ESITO_PENDING
    ).update(esito=EVENTO_ESITO_TIMEOUT, risolto_at=now, updated_at=now)
    sessione.next_event_at = None
    sessione.distanza_percorsa = 0.0
    sessione.decollo_completato_at = None
    sessione.ultimo_tick_motore_at = None
    sessione.save(
        update_fields=[
            "next_event_at",
            "distanza_percorsa",
            "decollo_completato_at",
            "ultimo_tick_motore_at",
            "updated_at",
        ]
    )


def capacita_carburante_serbatoi() -> float:
    """Somma capacita' dei serbatoi attivi; fallback 1000 se nessun serbatoio configurato."""
    total = float(
        SottosistemaNave.objects.filter(attivo=True, tipo="serbatoio").aggregate(
            total=Sum("capacita_carburante")
        )["total"]
        or 0.0
    )
    return max(0.0, total) or 1000.0


@transaction.atomic
def staff_imposta_carburante_sessione(
    sessione: SessioneVolo, carburante_attuale: float
) -> SessioneVolo:
    """Imposta il carico attuale del serbatoio sulla sessione console (clamp al massimo)."""
    sessione = SessioneVolo.objects.select_for_update().get(pk=sessione.pk)
    massimo = capacita_carburante_serbatoi()
    nuovo = max(0.0, min(float(massimo), float(carburante_attuale)))
    sessione.carburante_massimo = massimo
    sessione.carburante_attuale = nuovo
    sessione.save(update_fields=["carburante_massimo", "carburante_attuale", "updated_at"])
    return sessione


def staff_azione_sottosistema_sessione(
    sessione: SessioneVolo,
    sottosistema: "SottosistemaNave",
    azione: str,
) -> Tuple[str, StatoSottosistemaSessione]:
    """
    Azioni staff live su sottosistema runtime:
    - guasto: offline immediato + effetti guasto
    - ripara: online immediato (come QR repair)
    - ripristino: avvia timer durata_ripristino_secondi
    """
    from .models import SottosistemaNave

    if sessione.is_terminata or not sessione.is_attiva:
        raise ValueError("Sessione non in volo.")
    if not isinstance(sottosistema, SottosistemaNave):
        raise ValueError("Sottosistema non valido.")

    azione = str(azione or "").strip().lower()
    if azione not in {"guasto", "ripara", "ripristino"}:
        raise ValueError("Azione non valida: usare guasto, ripara o ripristino.")

    stato = get_o_crea_stato_sottosistema(sessione, sottosistema)
    now = timezone.now()

    if azione == "guasto":
        if not stato.online and stato.recovery_at and stato.recovery_at > now:
            raise ValueError("Ripristino automatico già in corso.")
        stato.online = False
        stato.guasto_at = now
        stato.recovery_at = None
        stato.save(
            update_fields=["online", "guasto_at", "recovery_at", "updated_at"]
        )
        applica_effetto_guasto(sessione, stato)
        from .flight_log import log_guasto_sottosistema

        log_guasto_sottosistema(sessione, stato, causa="staff")
        return "guasto", stato

    if azione == "ripara":
        if stato.online:
            raise ValueError("Il sottosistema è già online.")
        if stato.recovery_at and stato.recovery_at > now:
            remain = int((stato.recovery_at - now).total_seconds())
            raise ValueError(f"Ripristino in corso ({remain}s rimanenti).")
        stato.online = True
        stato.guasto_at = None
        stato.recovery_at = None
        stato.livello_attuale = _clamp_livello(stato.livello_target)
        stato.save(
            update_fields=[
                "online",
                "guasto_at",
                "recovery_at",
                "livello_attuale",
                "updated_at",
            ]
        )
        return "ripara", stato

    # ripristino programmato
    if stato.online:
        raise ValueError("Il sottosistema è già online.")
    durata = max(1, int(sottosistema.durata_ripristino_secondi or 60))
    stato.recovery_at = now + timedelta(seconds=durata)
    stato.save(update_fields=["recovery_at", "updated_at"])
    return "ripristino", stato


def genera_evento_se_dovuto(sessione: SessioneVolo) -> Optional[EventoAttivoSessione]:
    """
    Crea un nuovo EventoAttivoSessione se:
    - sessione in volo;
    - crociera iniziata (motore acceso almeno una volta, decollo_completato_at);
    - now >= next_event_at (oppure next_event_at e' None).
    """
    if not sessione.is_attiva:
        return None
    if not _sessione_ha_decollato(sessione):
        return None

    now = timezone.now()
    cfg = _stato_allerta_config(sessione.defcon)
    if cfg is not None:
        chance = float(cfg.probabilita_evento_per_tick or 0.0)
        if chance > 0:
            if random.random() > chance:
                return None
        elif sessione.next_event_at and now < sessione.next_event_at:
            # prob=0: niente sorteggio per tick, rispetta l'intervallo programmato
            return None
    elif sessione.next_event_at and now < sessione.next_event_at:
        return None

    evento = _scegli_evento_random()
    if not evento:
        sessione.next_event_at = now + timedelta(
            seconds=secondi_prossimo_evento_per_defcon(sessione.defcon)
        )
        sessione.save(update_fields=["next_event_at", "updated_at"])
        return None

    ticks_rimanenti = ticks_durata_evento_catalogo(evento.durata_tick)
    durata_sec = secondi_durata_totale_evento(ticks_rimanenti, sessione.defcon)
    precipita_a_scadenza = scadenza_critica_da_evento(evento)
    tick_evento_sec = secondi_tick_durante_evento(sessione.defcon)
    prossima = now + timedelta(seconds=tick_evento_sec)
    istanza = EventoAttivoSessione.objects.create(
        sessione=sessione,
        evento=evento,
        deadline_at=now + timedelta(seconds=durata_sec),
        ticks_rimanenti=ticks_rimanenti,
        persiste_fino_st=False,
        precipita_a_scadenza=precipita_a_scadenza,
        prossima_valutazione_at=prossima,
        intervallo_reazione_secondi=tick_evento_sec,
        reazione_fino_at=prossima,
        direzione_evento=(
            random.choice(["avanti", "indietro", "su", "giu", "destra", "sinistra"])
            if (evento.regole_json or {}).get("usa_direzione_evento")
            else ""
        ),
    )
    istanza.refresh_from_db()
    from .flight_log import log_evento_comparso

    log_evento_comparso(sessione, istanza)
    sessione.next_event_at = istanza.deadline_at + timedelta(
        seconds=secondi_prossimo_evento_per_defcon(sessione.defcon)
    )
    sessione.ultimo_tick_motore_at = now
    sessione.save(
        update_fields=["next_event_at", "ultimo_tick_motore_at", "updated_at"]
    )
    return istanza


# ---------------------------------------------------------------------------
# Tick generale: chiamato dalle viste e/o da un job background
# ---------------------------------------------------------------------------


@dataclass
class TickResult:
    sessione: SessioneVolo
    nuovo_evento: Optional[EventoAttivoSessione]
    timeout_applicato: bool
    transizione_arrivata: bool


def tick_sessione_se_dovuto(
    sessione: SessioneVolo, *, force: bool = False
) -> Optional[TickResult]:
    """Esegue tick_sessione solo se e' trascorso l'intervallo tick effettivo."""
    sessione.refresh_from_db()
    if sessione.is_terminata:
        return TickResult(sessione, None, False, False)
    if not force and secondi_fino_prossimo_tick(sessione) > 0:
        return None
    return tick_sessione(sessione)


@transaction.atomic
def tick_sessione(sessione: SessioneVolo) -> TickResult:
    """
    Avanza lo stato di una sessione nel modo idempotente:
    - applica recoveries sottosistemi;
    - chiude eventi pending scaduti (timeout) e applica DEFCON;
    - genera nuovo evento se necessario;
    - marca arrivata quando la distanza target e' stata raggiunta.
    """
    sessione = SessioneVolo.objects.select_for_update().get(pk=sessione.pk)
    if sessione.is_terminata:
        return TickResult(sessione, None, False, False)

    pending_list = list(
        EventoAttivoSessione.objects.filter(
            sessione=sessione, esito=EVENTO_ESITO_PENDING
        ).order_by("-created_at")
    )
    if pending_list:
        for pending in pending_list:
            _programma_prossimo_check_evento_se_manca(pending, sessione)
        if not any(_evento_pronto_per_valutazione(p, sessione) for p in pending_list):
            return TickResult(sessione, None, False, False)

    applica_recoveries_pendenti(sessione)

    timeout = False
    if _sessione_ha_decollato(sessione):
        pending_list = list(
            EventoAttivoSessione.objects.filter(
                sessione=sessione, esito=EVENTO_ESITO_PENDING
            ).order_by("-created_at")
        )
        for pending in pending_list:
            if not _evento_pronto_per_valutazione(pending, sessione):
                continue
            esito_tick, _ = valuta_evento_tick(sessione, pending)
            pending.refresh_from_db()
            if pending.esito == EVENTO_ESITO_PENDING:
                _schedula_prossima_valutazione_evento(pending, sessione)
            timeout = timeout or (esito_tick == "timeout")
            if sessione.is_terminata:
                return TickResult(sessione, None, False, False)

    _avanza_energia_sessione(sessione)
    sessione.refresh_from_db()

    nuovo = genera_evento_se_dovuto(sessione)

    transizione = False
    if sessione.stato == SESSIONE_STATO_VOLO:
        distanza_target = float(sessione.distanza_target or 0.0)
        distanza_percorsa = float(sessione.distanza_percorsa or 0.0)
        if distanza_target > 0 and distanza_percorsa >= distanza_target:
            sessione.stato = SESSIONE_STATO_ARRIVATA
            sessione.ended_at = timezone.now()
            sessione.save(update_fields=["stato", "ended_at", "updated_at"])
            from .flight_log import log_arrivo

            log_arrivo(sessione)
            transizione = True

    sessione.ultimo_tick_motore_at = timezone.now()
    sessione.save(update_fields=["ultimo_tick_motore_at", "updated_at"])

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


# Crociera nominale: motore L5 (5×12) × portale L4 (0.15×4) = 36 unità/tick da 5 s.
CRUISE_VELOCITY_PER_TICK = 36.0


def calcola_distanza_target(
    prefettura_partenza,
    prefettura_arrivo,
    defcon_iniziale: int = 0,
    tick_secondi: float = 5.0,
) -> tuple[int, int]:
    """
    Distanza obiettivo da durata geografica e velocità di crociera di riferimento.

    Ritorna (distanza_target, durata_pianificata_secondi).
    """
    durata_sec = durata_viaggio_secondi(
        prefettura_partenza, prefettura_arrivo, defcon_iniziale
    )
    interval = max(0.5, float(tick_secondi or 5.0))
    num_tick = durata_sec / interval
    distanza = max(1, int(round(num_tick * CRUISE_VELOCITY_PER_TICK)))
    return distanza, durata_sec


# ---------------------------------------------------------------------------
# Valutazione codici a 3 caratteri
# ---------------------------------------------------------------------------


@dataclass
class ValutazioneCodice:
    esito: str  # ... 'precipizio' / 'sequenza_ok' / 'sequenza_ko' / 'invalido' / 'no_evento' / ...
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
    2. formato valido -> codice critico globale -> precipizio immediato.
    3. fase decollo/atterraggio -> sequenza obbligatoria.
    4. fase volo:
       - formato non valido -> defcon +1
       - sottosistema guasto sul primo char -> defcon +1
       - codice == soluzione esatta evento attivo -> defcon -1
       - codice match pattern precipizio evento attivo -> precipitazione immediata
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

    if codice_critico_globale_attivo(codice):
        nuovo = forza_precipizio(sessione)
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito="precipizio",
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note="Codice critico globale.",
        )
        return ValutazioneCodice(
            esito="precipizio",
            delta_defcon=nuovo - defcon_pre,
            nuovo_defcon=nuovo,
            descrizione="Codice critico: nave precipitata.",
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
    precipizi = [normalizza_codice(p) for p in (evento.codici_precipizio or [])]

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

    if any(matcha_pattern(p, codice) for p in precipizi):
        pending.esito = EVENTO_ESITO_PRECIPITAZIO
        pending.risolto_at = timezone.now()
        pending.codice_inserito = codice
        pending.save(
            update_fields=["esito", "risolto_at", "codice_inserito", "updated_at"]
        )
        nuovo = forza_precipizio(sessione)
        TentativoCodice.objects.create(
            sessione=sessione,
            evento_attivo=pending,
            codice=codice,
            esito="precipizio",
            defcon_pre=defcon_pre,
            defcon_post=nuovo,
            note="Pattern critico: precipitazione immediata.",
        )
        return ValutazioneCodice(
            esito="precipizio",
            delta_defcon=nuovo - defcon_pre,
            nuovo_defcon=nuovo,
            descrizione="Codice critico: nave precipitata.",
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
