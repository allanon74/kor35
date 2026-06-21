"""
Simulazione volo con evento «Sciame di Meteore» — eseguire con:
  python manage.py shell < pilotaggio/scripts/simula_volo_meteore.py
"""
from __future__ import annotations

from datetime import timedelta

from django.utils import timezone

from pilotaggio.engine import (
    genera_evento_se_dovuto,
    intervallo_tick_effettivo_sessione,
    secondi_durata_totale_evento,
    secondi_fino_prossimo_tick,
    secondi_tick_durante_evento,
    tick_sessione,
    tick_sessione_se_dovuto,
    valuta_evento_tick,
    _eval_outcome_regole,
    _stati_by_key_sessione,
)
from pilotaggio.models import (
    EVENTO_ESITO_PENDING,
    SESSIONE_STATO_VOLO,
    EventoAttivoSessione,
    EventoNave,
    SessioneVolo,
    StatoSottosistemaSessione,
)
from pilotaggio.views import _ensure_runtime_subsystems
from personaggi.models import Personaggio


def _livelli(sessione):
    out = {}
    for st in StatoSottosistemaSessione.objects.select_related("sottosistema").filter(
        sessione=sessione
    ):
        cod = (st.sottosistema.codice or "?").upper()
        out[cod] = st.livello_attuale
    return out


def _fmt_evento(istanza):
    if not istanza:
        return "nessuno"
    sec = max(0, (istanza.deadline_at - timezone.now()).total_seconds())
    return (
        f"{istanza.evento.nome} ticks={istanza.ticks_rimanenti} "
        f"countdown={sec:.0f}s esito={istanza.esito}"
    )


def _crea_sessione():
    pg = Personaggio.objects.create(nome=f"Sim Pilota {timezone.now():%H%M%S}")
    sessione = SessioneVolo.objects.create(
        pilota=pg,
        stato=SESSIONE_STATO_VOLO,
        defcon=0,
        durata_pianificata_secondi=3600,
        started_at=timezone.now(),
        tick_secondi=5,
        distanza_target=50000.0,
    )
    _ensure_runtime_subsystems(sessione)
    return sessione


def _forza_meteore(sessione):
    evento = EventoNave.objects.get(nome="Sciame di Meteore")
    ticks = 3
    durata = secondi_durata_totale_evento(ticks, sessione.defcon)
    now = timezone.now()
    return EventoAttivoSessione.objects.create(
        sessione=sessione,
        evento=evento,
        deadline_at=now + timedelta(seconds=durata),
        ticks_rimanenti=ticks,
        precipita_a_scadenza=bool(evento.scadenza_critica),
    )


def sezione(titolo):
    print()
    print("=" * 72)
    print(titolo)
    print("=" * 72)


def main():
    evento_cat = EventoNave.objects.get(nome="Sciame di Meteore")
    tick_ev = secondi_tick_durante_evento(0)
    sezione("CONFIG «Sciame di Meteore»")
    print(f"  durata_tick catalogo: {evento_cat.durata_tick!r}")
    print(f"  scadenza_critica: {evento_cat.scadenza_critica}")
    print(f"  ca_effetto: {(evento_cat.regole_json or {}).get('ca_effetto')}")
    print(f"  tick DEFCON 0: {tick_ev}s → 3 tick ≈ {3 * tick_ev}s countdown")

    sezione("1) Stato iniziale tipico (sottosistemi a livello 0)")
    sessione = _crea_sessione()
    istanza = _forza_meteore(sessione)
    regole = evento_cat.regole_json or {}
    stati = _stati_by_key_sessione(sessione)
    ca_viva = _eval_outcome_regole(regole, "ca", stati, "")
    st_viva = _eval_outcome_regole(regole, "st", stati, "")
    sp_viva = _eval_outcome_regole(regole, "sp", stati, "")
    print(f"  Livelli: {_livelli(sessione)}")
    print(f"  Regola CA soddisfatta (A=0 o E=0): {ca_viva}")
    print(f"  Regola ST soddisfatta: {st_viva}")
    print(f"  Regola SP soddisfatta: {sp_viva}")
    print(f"  Evento: {_fmt_evento(istanza)}")

    esito, defcon = valuta_evento_tick(sessione, istanza)
    sessione.refresh_from_db()
    istanza.refresh_from_db()
    print(f"  Dopo 1° tick motore: esito={esito!r} defcon={defcon} stato={sessione.stato}")
    if esito == "ca":
        print("  → CA attiva con sottosistemi a 0: precipizio (comportamento atteso)")
    else:
        print(f"  Evento: {_fmt_evento(istanza)}")

    sezione("2) Poll rapidi (simula console ogni 3s, SENZA avanzare il clock)")
    sessione = _crea_sessione()
    istanza = _forza_meteore(sessione)
    sessione.ultimo_tick_motore_at = timezone.now()
    sessione.save(update_fields=["ultimo_tick_motore_at"])
    ticks_eseguiti = 0
    for i in range(12):
        res = tick_sessione_se_dovuto(sessione)
        if res is not None:
            ticks_eseguiti += 1
        sessione.refresh_from_db()
        istanza.refresh_from_db()
    print(f"  12 poll → tick motore eseguiti: {ticks_eseguiti} (atteso: 0)")
    print(f"  ticks_rimanenti: {istanza.ticks_rimanenti} (atteso: 3)")
    print(f"  stato nave: {sessione.stato} (atteso: volo)")

    sezione("3) Volo simulato: 3 tick evento con intervallo corretto")
    sessione = _crea_sessione()
    istanza = _forza_meteore(sessione)
    intervallo = intervallo_tick_effettivo_sessione(sessione)
    print(f"  Intervallo tick durante evento: {intervallo}s")
    print(f"  Countdown iniziale: {(istanza.deadline_at - timezone.now()).total_seconds():.0f}s")
    print()
    for n in range(1, 5):
        sessione.ultimo_tick_motore_at = timezone.now() - timedelta(seconds=intervallo + 0.5)
        sessione.save(update_fields=["ultimo_tick_motore_at"])
        res = tick_sessione_se_dovuto(sessione)
        sessione.refresh_from_db()
        istanza.refresh_from_db()
        pending = EventoAttivoSessione.objects.filter(
            sessione=sessione, esito=EVENTO_ESITO_PENDING
        ).first()
        ev = pending or istanza
        countdown = max(0, (ev.deadline_at - timezone.now()).total_seconds()) if ev else 0
        print(
            f"  Tick #{n}: stato={sessione.stato} defcon={sessione.defcon} "
            f"ticks_rim={getattr(ev, 'ticks_rimanenti', '-')} "
            f"countdown={countdown:.0f}s esito={getattr(ev, 'esito', '-')}"
        )
        if sessione.stato != SESSIONE_STATO_VOLO:
            print(f"  → Nave terminata al tick #{n} (reason={sessione.crash_reason})")
            break
        if not pending:
            print(f"  → Evento chiuso con esito {istanza.esito}")
            break

    sezione("4) Risoluzione ST (pilota soddisfa soluzione totale)")
    sessione = _crea_sessione()
    istanza = _forza_meteore(sessione)
    # ST meteore: A>5 + D 1-3 + ... — semplificato: A=6, D=2, E=3
    for cod, lvl in [("A", 6), ("D", 2), ("E", 3)]:
        st = StatoSottosistemaSessione.objects.get(
            sessione=sessione, sottosistema__codice=cod
        )
        st.livello_attuale = lvl
        st.livello_target = lvl
        st.save()
    sessione.defcon = 2
    sessione.save()
    sessione.ultimo_tick_motore_at = timezone.now() - timedelta(seconds=intervallo + 1)
    sessione.save(update_fields=["ultimo_tick_motore_at"])
    tick_sessione_se_dovuto(sessione)
    sessione.refresh_from_db()
    istanza.refresh_from_db()
    print(f"  Livelli: {_livelli(sessione)}")
    print(f"  Esito evento: {istanza.esito} | defcon: {sessione.defcon} | stato: {sessione.stato}")

    print()
    print("Simulazione completata.")


main()
