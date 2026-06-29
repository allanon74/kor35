import React, { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import FlightOpsPanel, { isAlimentazioneGroup } from './FlightOpsPanel.jsx';
import {
  announceDefconChange,
  playCriticalEventAlarmTick,
  playCriticalEventBurst,
  playMinorEventAlert,
} from '../pilotAlerts.js';

function defconClass(defcon, defconMax) {
  if (defcon > defconMax) return 'defcon-crash';
  return `defcon-${Math.min(5, Math.max(0, defcon))}`;
}

function CountdownBox({ deadlineISO }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 250);
    return () => clearInterval(id);
  }, []);
  if (!deadlineISO) return null;
  const remaining = Math.max(0, Math.ceil((new Date(deadlineISO).getTime() - now) / 1000));
  return <div className="countdown">{String(remaining).padStart(2, '0')}s</div>;
}

function ratio(value, max) {
  const safeMax = Number(max || 0);
  if (safeMax <= 0) return 0;
  return Math.max(0, Math.min(100, Math.round((Number(value || 0) / safeMax) * 100)));
}

function formatDiaryTime(iso) {
  if (!iso) return '';
  try {
    return new Date(iso).toLocaleTimeString('it-IT', {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    });
  } catch (_) {
    return '';
  }
}

function categoriaDiarioLabel(cat) {
  const map = {
    volo_iniziato: 'Inizio',
    decollo: 'Decollo',
    evento_comparso: 'Evento',
    evento_valutato: 'Valutazione',
    precipizio: 'Precipizio',
    guasto: 'Guasto',
    arrivo: 'Arrivo',
    arrivo_emergenza: 'Emergenza',
  };
  return map[cat] || cat;
}

function FlightDiary({ sessioneId }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    api.diario(sessioneId)
      .then((res) => {
        if (!cancelled) setData(res);
      })
      .catch(() => {
        if (!cancelled) setData({ sessione: null, voci: [] });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [sessioneId]);

  const voci = data?.voci || [];
  const riepilogo = data?.sessione;

  return (
    <div className="flight-diary">
      <h2>Diario di volo</h2>
      {riepilogo?.crash_spiegazione ? (
        <p className="flight-diary-summary">{riepilogo.crash_spiegazione}</p>
      ) : null}
      {loading ? <p className="flight-diary-muted">Caricamento cronologia…</p> : null}
      {!loading && voci.length === 0 ? (
        <p className="flight-diary-muted">Nessuna voce registrata per questo volo.</p>
      ) : null}
      {!loading && voci.length > 0 ? (
        <ol className="flight-diary-list">
          {voci.map((v) => (
            <li key={v.id} className={`flight-diary-item cat-${v.categoria}`}>
              <span className="flight-diary-time">{formatDiaryTime(v.created_at)}</span>
              <span className="flight-diary-cat">{categoriaDiarioLabel(v.categoria)}</span>
              <span className="flight-diary-msg">{v.messaggio}</span>
              {v.defcon_pre != null && v.defcon_post != null && v.defcon_pre !== v.defcon_post ? (
                <span className="flight-diary-defcon">
                  DEFCON {v.defcon_pre} → {v.defcon_post}
                </span>
              ) : null}
            </li>
          ))}
        </ol>
      ) : null}
    </div>
  );
}

function Gauge({ label, value, max, color = '#00e5ff', unit = '' }) {
  const pct = ratio(value, max);
  const r = 24;
  const c = 2 * Math.PI * r;
  const dash = c - (c * pct) / 100;
  return (
    <div className="lcars-gauge">
      <svg viewBox="0 0 64 64" className="lcars-gauge-svg">
        <circle cx="32" cy="32" r={r} className="lcars-gauge-bg" />
        <circle
          cx="32"
          cy="32"
          r={r}
          className="lcars-gauge-fg"
          stroke={color}
          strokeDasharray={c}
          strokeDashoffset={dash}
        />
      </svg>
      <div className="lcars-gauge-center">
        <div className="lcars-gauge-percent">{pct}%</div>
        {unit ? <div className="lcars-gauge-unit">{unit}</div> : null}
      </div>
      <div className="lcars-gauge-label">{label}</div>
    </div>
  );
}

function groupTheme(groupName) {
  const key = String(groupName || '').toLowerCase();
  if (key.includes('propuls')) return { theme: 'theme-propulsione', icon: 'NAV', accent: '#9ad1ff' };
  if (key.includes('difesa')) return { theme: 'theme-difesa', icon: 'DEF', accent: '#c9b0ff' };
  if (key.includes('aliment')) return { theme: 'theme-alimentazione', icon: 'PWR', accent: '#a8ffc8' };
  if (key.includes('intern')) return { theme: 'theme-interni', icon: 'INT', accent: '#ffd5a1' };
  if (key.includes('esotic')) return { theme: 'theme-esotici', icon: 'EXO', accent: '#f8a8ff' };
  return { theme: 'theme-default', icon: 'SYS', accent: '#d6e9ff' };
}

function tileLevelClass(level) {
  const l = Number(level || 0);
  if (l <= 0) return 'lvl-off';
  if (l <= 3) return 'lvl-low';
  if (l <= 6) return 'lvl-mid';
  if (l === 7) return 'lvl-high';
  if (l >= 8) return 'lvl-critical';
  return 'lvl-mid';
}

/** Classe colore per pulsanti livello nel modal (touch). */
function powerButtonTierClass(level) {
  const l = Number(level || 0);
  if (l <= 0) return 'power-btn-tier-off';
  if (l <= 3) return 'power-btn-tier-low';
  if (l <= 6) return 'power-btn-tier-mid';
  if (l === 7) return 'power-btn-tier-high';
  return 'power-btn-tier-crit';
}

const POWER_LEVELS = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9];

/** Sei direzioni in una sola riga: marcia, rollio, assetto verticale (usa tutta la larghezza del modal). */
const PROPULSOR_DIRECTIONS = [
  { value: 'avanti', label: 'Avanti', arrow: '↑' },
  { value: 'indietro', label: 'Indietro', arrow: '↓' },
  { value: 'sinistra', label: 'Sinistra', arrow: '←' },
  { value: 'destra', label: 'Destra', arrow: '→' },
  { value: 'su', label: 'Su', arrow: '⇑' },
  { value: 'giu', label: 'Giù', arrow: '⇓' },
];

/** Un solo pulsante: tap alterna stato, etichetta e aspetto “premuto” rosso quando attivo. */
function TouchLatchToggle({
  pressed,
  onToggle,
  labelIdle,
  labelActive,
  hint,
  disabled,
}) {
  return (
    <div className={`touch-latch-row ${disabled ? 'disabled' : ''}`}>
      {hint ? <span className="touch-latch-hint">{hint}</span> : null}
      <button
        type="button"
        className={`touch-latch-btn ${pressed ? 'pressed' : ''}`}
        aria-pressed={pressed}
        disabled={disabled}
        onClick={() => onToggle(!pressed)}
      >
        {pressed ? labelActive : labelIdle}
      </button>
    </div>
  );
}

function levelColor(level) {
  const l = Number(level || 0);
  if (l <= 0) return '#f2f4f8'; // spento
  if (l <= 3) return '#63e6a5'; // normale
  if (l <= 6) return '#ffd670'; // ottimale
  return '#ff7b7b'; // overload
}

function PowerDial({ level, colorOverride }) {
  const l = Math.max(0, Math.min(9, Number(level || 0)));
  const color = colorOverride || levelColor(l);
  const segments = Array.from({ length: 9 }, (_, i) => i < l);
  return (
    <div className="power-dial" aria-label={`Livello potenza ${l}`}>
      <svg viewBox="0 0 64 64" className="power-dial-svg">
        <g transform="translate(32 32)">
          <circle cx="0" cy="0" r="29" fill="#080b12" stroke="rgba(255,255,255,0.16)" strokeWidth="1.4" />
          {segments.map((on, idx) => {
            const angle = -90 + idx * 40;
            return (
              <rect
                key={idx}
                x="-2.2"
                y="-27"
                width="4.4"
                height="9"
                rx="1.8"
                transform={`rotate(${angle})`}
                fill={on ? color : 'rgba(159,175,200,0.22)'}
              />
            );
          })}
          <circle cx="0" cy="0" r="17" fill="#0b1018" stroke="rgba(255,255,255,0.22)" strokeWidth="1.5" />
        </g>
      </svg>
      <div className="power-dial-center">{l}</div>
    </div>
  );
}

function statusIcon(subsystem) {
  if (subsystem.espulso) return { icon: '⏏', title: 'Espulsione attiva' };
  if (subsystem.invertito) return { icon: '⇄', title: 'Inversione attiva' };
  if (subsystem.supporta_direzioni) {
    const map = {
      avanti: '↑',
      indietro: '↓',
      su: '⇧',
      giu: '⇩',
      destra: '→',
      sinistra: '←',
    };
    return { icon: map[subsystem.direzione] || '↑', title: `Direzione ${subsystem.direzione || 'avanti'}` };
  }
  return { icon: '•', title: 'Stato standard' };
}

function eventUrgencyScore(ev) {
  let score = 0;
  if (ev?.precipita_a_scadenza) score += 1000;
  const deadlineMs = ev?.deadline_at ? new Date(ev.deadline_at).getTime() : NaN;
  if (Number.isFinite(deadlineMs)) {
    const sec = Math.max(0, Math.floor((deadlineMs - Date.now()) / 1000));
    score += Math.max(0, 180 - sec);
  }
  return score;
}

function Subsystems({ sottosistemi, energia }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), 500);
    return () => clearInterval(id);
  }, []);
  if (!sottosistemi || !sottosistemi.length) {
    return <p className="note">Nessun sottosistema registrato in questa sessione.</p>;
  }
  return (
    <div className="subsys-list">
      {sottosistemi.map((s) => (
        <div
          key={s.id}
          className={`subsys ${s.online ? 'online' : 'offline'} ${!s.online ? 'fault-pulse' : ''}`}
          style={s.online && s.colore_livello_attuale ? { background: s.colore_livello_attuale } : undefined}
        >
          <span>{s.nome}</span>
          <div className="subsys-mid">
            {String(s.tipo || '').toLowerCase() === 'batteria' ? (
              <div>
                {Math.round(Number(energia?.storage_attuale || 0))} / {Math.round(Number(energia?.storage_massimo || 0))}
              </div>
            ) : null}
            {String(s.tipo || '').toLowerCase() === 'serbatoio' ? (
              <div>
                {Math.round(Number(energia?.carburante_attuale || 0))} / {Math.round(Number(energia?.carburante_massimo || 0))}
              </div>
            ) : null}
            {!s.online && s.recovery_at ? (() => {
              const remain = Math.max(0, Math.ceil((new Date(s.recovery_at).getTime() - now) / 1000));
              const total = Math.max(1, Number(s.durata_ripristino_secondi || 60));
              const done = Math.max(0, Math.min(100, Math.round(((total - remain) / total) * 100)));
              return (
                <div style={{ marginTop: '0.2rem' }}>
                  <div>In riparazione {remain}s</div>
                  <div style={{ width: '100%', height: '6px', border: '1px solid #355', borderRadius: '8px' }}>
                    <div style={{ width: `${done}%`, height: '100%', background: '#6fdc8c' }} />
                  </div>
                </div>
              );
            })() : null}
          </div>
          <div className="subsys-status">{s.online ? 'ONLINE' : 'GUASTO'}</div>
        </div>
      ))}
    </div>
  );
}

/**
 * Cockpit di volo. Mostra DEFCON, evento attivo, sottosistemi, storia.
 * Cattura tastiera in modo esclusivo: solo input codici 3-char.
 */
export default function Cockpit({
  state, online,
  onAbort, onEmergencyLanding, onTakeoff, onLanding, onSetAllarme,
  onLogout, onResetSession, mode = 'both', onSubsystemSet,
  error, commandStatus,
}) {
  const sessione = state.sessione || {};
  const decolloEffettuato = Boolean(state.decollo_effettuato);
  const eventiAttivi = Array.isArray(state.eventi_attivi)
    ? state.eventi_attivi
    : (state.evento_attivo ? [state.evento_attivo] : []);
  const eventiOrdinati = [...eventiAttivi].sort(
    (a, b) => eventUrgencyScore(b) - eventUrgencyScore(a)
  );
  const eventiCriticiCount = eventiOrdinati.filter((ev) => Boolean(ev.precipita_a_scadenza)).length;
  const eventiNormaliCount = Math.max(0, eventiOrdinati.length - eventiCriticiCount);
  const evento = eventiAttivi[0] || null;
  const defcon = sessione.defcon || 0;
  const defconMax = state.defcon_max || 5;
  const statiAllerta = state.stati_allerta || [];
  const statoAbbattuta = statiAllerta.find((s) => s.equivale_nave_abbattuta);
  const statoCorrente =
    statiAllerta.find((s) => s.livello === defcon) ||
    (defcon > defconMax ? statoAbbattuta : null);
  const isCrashed = sessione.stato === 'crashed';
  const [selectedSubsystem, setSelectedSubsystem] = useState(null);
  const [editingLevel, setEditingLevel] = useState(0);
  const [editingDirection, setEditingDirection] = useState('avanti');
  const [editingInvert, setEditingInvert] = useState(false);
  const [editingExpel, setEditingExpel] = useState(false);
  const audioCtxRef = useRef(null);
  const beepTimerRef = useRef(null);
  const criticalEventAlarmRef = useRef(null);
  const criticalAlarmPhaseRef = useRef(false);
  const prevDefconRef = useRef(null);
  const prevEventIdsRef = useRef(new Set());
  const eventAlertsReadyRef = useRef(false);
  const sottosistemiOffline = (state.sottosistemi || []).filter((s) => !s.online);
  const groupedSystems = state.sistemi || {};
  const hasCriticalEvent = eventiOrdinati.some((ev) => Boolean(ev.precipita_a_scadenza));
  const energia = state.energia || {};
  const distanzaPercorsa = Number(energia.distanza_percorsa || 0);
  const distanzaTarget = Number(energia.distanza_target || 0);
  const distanzaPct = ratio(distanzaPercorsa, distanzaTarget);
  const tickAlive = Boolean(state?.tick_runtime?.enabled && state?.tick_runtime?.alive);
  const alarmAudioEnabled = Boolean(state?.tick_runtime?.alarm_audio_enabled);
  const hasCriticalSubsystem = (state.sottosistemi || []).some((s) => Number(s.livello_target || 0) >= 8 && s.online);
  const motore = (state.sottosistemi || []).find((s) => s.tipo === 'motore');
  const motoreLivello = Number(motore?.livello_target || 0);
  const allarmeEquipaggio = state.allarme_equipaggio || 'crociera';
  const hasAlimentazioneColumn = Object.keys(groupedSystems).some(isAlimentazioneGroup);
  const flightOpsPanel = (
    <FlightOpsPanel
      decolloEffettuato={decolloEffettuato}
      allarmeEquipaggio={allarmeEquipaggio}
      motoreLivello={motoreLivello}
      onTakeoff={onTakeoff}
      onLanding={onLanding}
      onEmergencyLanding={onEmergencyLanding}
      onSetAllarme={onSetAllarme}
      disabled={!online}
    />
  );

  useEffect(() => {
    const shouldBeep = tickAlive && alarmAudioEnabled && hasCriticalSubsystem;
    if (!shouldBeep) {
      if (beepTimerRef.current) {
        clearInterval(beepTimerRef.current);
        beepTimerRef.current = null;
      }
      return undefined;
    }

    const playBeep = () => {
      const AudioCtx = window.AudioContext || window.webkitAudioContext;
      if (!AudioCtx) return;
      if (!audioCtxRef.current) {
        audioCtxRef.current = new AudioCtx();
      }
      const ctx = audioCtxRef.current;
      if (ctx.state === 'suspended') {
        ctx.resume().catch(() => {});
      }
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.value = 880;
      gain.gain.value = 0.02;
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start();
      osc.stop(ctx.currentTime + 0.09);
    };

    playBeep();
    beepTimerRef.current = setInterval(playBeep, 1200);
    return () => {
      if (beepTimerRef.current) {
        clearInterval(beepTimerRef.current);
        beepTimerRef.current = null;
      }
    };
  }, [tickAlive, alarmAudioEnabled, hasCriticalSubsystem]);

  useEffect(() => {
    if (prevDefconRef.current === null) {
      prevDefconRef.current = defcon;
      return;
    }
    if (prevDefconRef.current === defcon) return;
    if (alarmAudioEnabled) {
      announceDefconChange(defcon);
    }
    prevDefconRef.current = defcon;
  }, [defcon, alarmAudioEnabled]);

  useEffect(() => {
    const currentIds = new Set(eventiOrdinati.map((ev) => String(ev.id)));
    if (!eventAlertsReadyRef.current) {
      prevEventIdsRef.current = currentIds;
      eventAlertsReadyRef.current = true;
      return;
    }
    const prevIds = prevEventIdsRef.current;
    const newEvents = eventiOrdinati.filter((ev) => !prevIds.has(String(ev.id)));
    if (newEvents.length && alarmAudioEnabled) {
      const hasNewCritical = newEvents.some((ev) => Boolean(ev.precipita_a_scadenza));
      if (hasNewCritical) {
        playCriticalEventBurst();
      } else {
        playMinorEventAlert();
      }
    }
    prevEventIdsRef.current = currentIds;
  }, [eventiOrdinati, alarmAudioEnabled]);

  useEffect(() => {
    const shouldAlarm = alarmAudioEnabled && hasCriticalEvent;
    if (!shouldAlarm) {
      if (criticalEventAlarmRef.current) {
        clearInterval(criticalEventAlarmRef.current);
        criticalEventAlarmRef.current = null;
      }
      return undefined;
    }
    criticalEventAlarmRef.current = setInterval(() => {
      criticalAlarmPhaseRef.current = !criticalAlarmPhaseRef.current;
      playCriticalEventAlarmTick(criticalAlarmPhaseRef.current);
    }, 850);
    return () => {
      if (criticalEventAlarmRef.current) {
        clearInterval(criticalEventAlarmRef.current);
        criticalEventAlarmRef.current = null;
      }
    };
  }, [alarmAudioEnabled, hasCriticalEvent]);

  const openSubsystem = (sub) => {
    setSelectedSubsystem(sub);
    setEditingLevel(Number(sub.livello_target ?? 0));
    setEditingDirection(sub.direzione || 'avanti');
    setEditingInvert(Boolean(sub.invertito));
    setEditingExpel(Boolean(sub.espulso));
  };

  const saveSubsystem = async () => {
    if (!selectedSubsystem || !onSubsystemSet) return;
    await onSubsystemSet({
      sottosistema_id: selectedSubsystem.sottosistema_id || selectedSubsystem.id,
      livello: editingLevel,
      direzione: selectedSubsystem.supporta_direzioni ? editingDirection : undefined,
      invertito: selectedSubsystem.supporta_inversione ? editingInvert : undefined,
      espulso: selectedSubsystem.supporta_espulsione ? editingExpel : undefined,
    });
    setSelectedSubsystem(null);
  };

  const showStatus = mode !== 'control';
  const showControl = mode !== 'status';
  const isCombinedLayout = mode === 'combined';
  const crashReason = String(sessione.crash_reason || '');
  const crashMessage = crashReason === 'end_of_energy'
    ? "Energia esaurita: carburante e batterie a zero, produzione nulla."
    : "La nave ha superato la gravita' critica e e' precipitata.";

  if (isCrashed) {
    return (
      <div
        className="center-screen crash-screen"
        style={
          statoAbbattuta?.colore
            ? { background: `linear-gradient(160deg, ${statoAbbattuta.colore} 0%, #0f0f12 55%)` }
            : undefined
        }
      >
        <h1>// {statoAbbattuta?.nome?.toUpperCase() || 'CRASH'} //</h1>
        <p>{crashMessage}</p>
        <FlightDiary sessioneId={sessione.id} />
        <div className="row" style={{ marginTop: '2rem', gap: '0.75rem', justifyContent: 'center' }}>
          <button type="button" className="btn primary" onClick={onResetSession}>Nuovo volo</button>
          <button type="button" className="btn" onClick={onLogout}>Logout pilota</button>
        </div>
      </div>
    );
  }

  if (sessione.stato === 'arrivata') {
    return (
      <div className="center-screen">
        <h1>// ARRIVO //</h1>
        <p>Destinazione raggiunta. Buon viaggio.</p>
        <FlightDiary sessioneId={sessione.id} />
        <div className="row" style={{ marginTop: '2rem', gap: '0.75rem', justifyContent: 'center' }}>
          <button type="button" className="btn primary" onClick={onResetSession}>Nuovo volo</button>
          <button type="button" className="btn" onClick={onLogout}>Logout pilota</button>
        </div>
      </div>
    );
  }

  return (
    <div
      className={[
        'cockpit',
        'cockpit-lcars',
        mode === 'control' ? 'cockpit-control' : '',
        isCombinedLayout ? 'cockpit-combined' : '',
      ].filter(Boolean).join(' ')}
    >
      {!decolloEffettuato ? (
        <div className="note" style={{ margin: '0.4rem 0.6rem', padding: '0.45rem 0.65rem', border: '1px solid #4a5a20', background: 'rgba(80,96,32,0.25)', borderRadius: 6 }}>
          PRE-VOLO — regola i sottosistemi; usa <strong>Decollo</strong> nella colonna Alimentazione (motore a 0).
        </div>
      ) : null}
      {isCombinedLayout ? (
        <>
          <div className="cockpit-combined-status">
            {showStatus ? (
              <>
                <div className="defcon-strip">
                  <div className="lcars-corner left" />
                  <div>
                    <div className="label">DEFCON</div>
                    <div
                      className={`value ${statoCorrente ? '' : defconClass(defcon, defconMax)}`}
                      style={
                        statoCorrente
                          ? {
                              backgroundColor: statoCorrente.colore || '#444',
                              color: '#fff',
                            }
                          : undefined
                      }
                      title={statoCorrente?.nome || ''}
                    >
                      {defcon > defconMax ? 'CRASH' : defcon}
                      {statoCorrente ? (
                        <span style={{ display: 'block', fontSize: '0.65rem', fontWeight: 500, marginTop: '0.15rem', opacity: 0.95 }}>
                          {statoCorrente.nome}
                        </span>
                      ) : null}
                    </div>
                  </div>
                  <div style={{ textAlign: 'center' }}>
                    <div className="label">Stato</div>
                    <div style={{ fontSize: '1.3rem', letterSpacing: '0.2em' }}>
                      {sessione.stato?.toUpperCase()}
                    </div>
                  </div>
                  <div style={{ textAlign: 'right' }}>
                    <div className="label">Volo</div>
                    <div>
                      {sessione.partenza_nome || '—'} {' → '} {sessione.arrivo_nome || '—'}
                    </div>
                  </div>
                  <div className="lcars-corner right" />
                </div>

                {hasCriticalEvent ? (
                  <div className="alert-bar alert-bar-critical-event" role="alert" aria-live="assertive">
                    ⚠ Evento Critico ⚠
                  </div>
                ) : null}

                {sottosistemiOffline.map((s) => (
                  <div key={s.id} className="alert-bar">
                    ⚠ Sottosistema {s.nome} GUASTO
                  </div>
                ))}

                <div className="middle-grid">
                  <div className="panel lcars-panel">
                    <h3>Eventi Attivi ({eventiOrdinati.length})</h3>
                    {eventiOrdinati.length ? (
                      <div className="event-summary">
                        <span className="event-summary-critical">Critici: {eventiCriticiCount}</span>
                        <span className="event-summary-normal">Normali: {eventiNormaliCount}</span>
                      </div>
                    ) : null}
                    {eventiOrdinati.length ? (
                      <div className="event-list">
                        {eventiOrdinati.map((ev) => (
                          <div
                            key={ev.id}
                            className={`event-box pending lcars-event-box ${
                              ev.precipita_a_scadenza ? 'event-critical' : 'event-normal'
                            }`}
                          >
                            <h2>{ev.nome}</h2>
                            <CountdownBox deadlineISO={ev.deadline_at} />
                            <div className="descr">{ev.descrizione}</div>
                            <div className="event-meta">
                              {ev.precipita_a_scadenza ? 'Scadenza critica — esito CA se non risolto' : 'Risolvi entro il countdown'}
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="note">Nessun evento attivo. Mantieni la rotta.</p>
                    )}
                  </div>
                  <div className="panel lcars-panel">
                    <div className="hud-strip lcars-hud">
                      <Gauge label="Carburante" value={energia.carburante_attuale} max={energia.carburante_massimo} color="#66f5a4" />
                      <Gauge label="Batterie" value={energia.storage_attuale} max={energia.storage_massimo} color="#76c7ff" />
                      <Gauge label="Produzione" value={energia.produzione} max={Math.max(1, energia.consumo || 1)} color="#ffd06b" />
                      <Gauge label="Consumo" value={energia.consumo} max={Math.max(1, energia.produzione || 1)} color="#ff8f70" />
                      <div className="radar-box">
                        <div className={`radar-ping ${hasCriticalEvent ? 'alert critical' : evento ? 'alert' : ''}`} />
                        <div className="radar-text">
                          {hasCriticalEvent ? 'Evento critico' : evento ? 'Evento in corso' : 'Spazio stabile'}
                        </div>
                      </div>
                      <div className="distance-box">
                        <div className="distance-label">Rotta</div>
                        <div className="distance-values">{Math.round(distanzaPercorsa)} / {Math.round(distanzaTarget || 0)}</div>
                        <div className="distance-track">
                          <div className="distance-fill" style={{ width: `${distanzaPct}%` }} />
                        </div>
                      </div>
                    </div>
                    <div className="status-legend" aria-label="Legenda livelli sottosistemi">
                      <span><i style={{ background: '#ffffff' }} />OFF</span>
                      <span><i style={{ background: '#8a2be2' }} />L1</span>
                      <span><i style={{ background: '#2f8cff' }} />L3</span>
                      <span><i style={{ background: '#9ccc65' }} />L5</span>
                      <span><i style={{ background: '#ffb74d' }} />L7</span>
                      <span><i style={{ background: '#ff3b30' }} />L9</span>
                    </div>
                    <h3>Stato Sottosistemi</h3>
                    <Subsystems sottosistemi={state.sottosistemi} energia={energia} />
                  </div>
                </div>

                <div className="input-strip">
                  <div className="label">COMANDI DI SICUREZZA</div>
                  <div className="feedback">
                    {!online && '[OFFLINE LOCALE] '}
                    Regola i sottosistemi dalla plancia touch per mantenere la nave stabile.
                  </div>
                  <button type="button" className="btn danger" onClick={onAbort}>Abort</button>
                </div>
              </>
            ) : null}
          </div>
          <div className="cockpit-combined-control cockpit-control">
            {showControl ? (
              <div className="panel control-deck lcars-panel">
                <div className="command-clusters">
                  {Object.entries(groupedSystems).map(([groupName, subs]) => {
                    const clickableSubs = (subs || [])
                      .filter(
                        (s) => !['batteria', 'serbatoio'].includes(String(s.tipo || '').toLowerCase())
                      )
                      .sort((a, b) => {
                        const oa = Number(a.ordine ?? 0);
                        const ob = Number(b.ordine ?? 0);
                        if (oa !== ob) return oa - ob;
                        return String(a.nome || '').localeCompare(String(b.nome || ''), 'it', {
                          sensitivity: 'base',
                        });
                      });
                    if (!clickableSubs.length) return null;
                    return (
                      <div key={groupName} className={`system-column station-card ${groupTheme(groupName).theme}`}>
                        <div className="system-title">
                          <span className="system-icon">{groupTheme(groupName).icon}</span>
                          <span className="system-name">{groupName}</span>
                        </div>
                        <div className="hex-cloud">
                          {clickableSubs.map((s) => (
                            (() => {
                              const lvl = Number(s.livello_target || 0);
                              const inRepair = Boolean(!s.online && s.recovery_at);
                              const iconData = statusIcon(s);
                              return (
                                <button
                                  key={s.id}
                                  type="button"
                                  className={`subsystem-tile lcars-button ${s.online ? 'online' : 'offline'} ${tileLevelClass(lvl)} ${lvl >= 8 ? 'danger-pulse' : ''} ${inRepair ? 'repairing' : ''} ${(lvl >= 8 && tickAlive) ? 'tick-danger-ring' : ''}`}
                                  onClick={() => openSubsystem(s)}
                                  disabled={!s.online}
                                >
                                  <div className="tile-head-row">
                                    <span className="tile-name">{s.nome}</span>
                                    <div className="tile-indicators" title={iconData.title}>
                                      <PowerDial level={lvl} colorOverride={s.colore_livello_attuale || undefined} />
                                      <span className="tile-mode-icon">{iconData.icon}</span>
                                    </div>
                                  </div>
                                  <div className="tile-meta" />
                                  <div className="tile-badges">
                                    {s.invertito ? <span className="badge warn">INV</span> : null}
                                    {s.espulso ? <span className="badge danger">ESP</span> : null}
                                    {inRepair ? <span className="badge repair">RIP</span> : null}
                                    {!s.online ? <span className="badge danger">GUASTO</span> : null}
                                  </div>
                                </button>
                              );
                            })()
                          ))}
                        </div>
                        {isAlimentazioneGroup(groupName) ? flightOpsPanel : null}
                        <div className="system-footer">
                          <div className="system-summary-row">
                            <span>Attivi {clickableSubs.filter((s) => s.online).length}/{clickableSubs.length}</span>
                            <span>
                              Potenza media {clickableSubs.length ? Math.round(clickableSubs.reduce((acc, s) => acc + Number(s.livello_target || 0), 0) / clickableSubs.length) : 0}
                            </span>
                          </div>
                          <div className="system-power-track">
                            <div
                              className="system-power-fill"
                              style={{
                                width: `${clickableSubs.length ? Math.round((clickableSubs.reduce((acc, s) => acc + Number(s.livello_target || 0), 0) / (clickableSubs.length * 9)) * 100) : 0}%`,
                              }}
                            />
                          </div>
                          <div className="system-lcars-strips">
                            <span />
                            <span />
                            <span />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  {!hasAlimentazioneColumn ? (
                    <div className={`system-column station-card ${groupTheme('Alimentazione').theme}`}>
                      <div className="system-title">
                        <span className="system-icon">{groupTheme('Alimentazione').icon}</span>
                        <span className="system-name">Alimentazione</span>
                      </div>
                      {flightOpsPanel}
                    </div>
                  ) : null}
                  {!Object.keys(groupedSystems).length ? (
                    <div className="note">Nessun sottosistema disponibile in sessione. Prova un nuovo Decollo.</div>
                  ) : null}
                </div>
              </div>
            ) : null}
          </div>
        </>
      ) : (
        <>
      {showStatus ? <div className="defcon-strip">
        <div className="lcars-corner left" />
        <div>
          <div className="label">DEFCON</div>
          <div
            className={`value ${statoCorrente ? '' : defconClass(defcon, defconMax)}`}
            style={
              statoCorrente
                ? {
                    backgroundColor: statoCorrente.colore || '#444',
                    color: '#fff',
                  }
                : undefined
            }
            title={statoCorrente?.nome || ''}
          >
            {defcon > defconMax ? 'CRASH' : defcon}
            {statoCorrente ? (
              <span style={{ display: 'block', fontSize: '0.65rem', fontWeight: 500, marginTop: '0.15rem', opacity: 0.95 }}>
                {statoCorrente.nome}
              </span>
            ) : null}
          </div>
        </div>
        <div style={{ textAlign: 'center' }}>
          <div className="label">Stato</div>
          <div style={{ fontSize: '1.3rem', letterSpacing: '0.2em' }}>
            {sessione.stato?.toUpperCase()}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div className="label">Volo</div>
          <div>
            {sessione.partenza_nome || '—'} {' → '} {sessione.arrivo_nome || '—'}
          </div>
        </div>
        <div className="lcars-corner right" />
      </div> : null}

      {showStatus && hasCriticalEvent ? (
        <div className="alert-bar alert-bar-critical-event" role="alert" aria-live="assertive">
          ⚠ Evento Critico ⚠
        </div>
      ) : null}

      {showStatus && sottosistemiOffline.map((s) => (
        <div key={s.id} className="alert-bar">
          ⚠ Sottosistema {s.nome} GUASTO
        </div>
      ))}


      {showStatus ? <div className="middle-grid">
        <div className="panel lcars-panel">
          <h3>Eventi Attivi ({eventiOrdinati.length})</h3>
          {eventiOrdinati.length ? (
            <div className="event-summary">
              <span className="event-summary-critical">Critici: {eventiCriticiCount}</span>
              <span className="event-summary-normal">Normali: {eventiNormaliCount}</span>
            </div>
          ) : null}
          {eventiOrdinati.length ? (
            <div className="event-list">
              {eventiOrdinati.map((ev) => (
                <div
                  key={ev.id}
                  className={`event-box pending lcars-event-box ${
                    ev.precipita_a_scadenza ? 'event-critical' : 'event-normal'
                  }`}
                >
                  <h2>{ev.nome}</h2>
                  <CountdownBox deadlineISO={ev.deadline_at} />
                  <div className="descr">{ev.descrizione}</div>
                  <div className="event-meta">
                    {ev.precipita_a_scadenza ? 'Scadenza critica — esito CA se non risolto' : 'Risolvi entro il countdown'}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="note">Nessun evento attivo. Mantieni la rotta.</p>
          )}
        </div>
        <div className="panel lcars-panel">
          <div className="hud-strip lcars-hud">
            <Gauge label="Carburante" value={energia.carburante_attuale} max={energia.carburante_massimo} color="#66f5a4" />
            <Gauge label="Batterie" value={energia.storage_attuale} max={energia.storage_massimo} color="#76c7ff" />
            <Gauge label="Produzione" value={energia.produzione} max={Math.max(1, energia.consumo || 1)} color="#ffd06b" />
            <Gauge label="Consumo" value={energia.consumo} max={Math.max(1, energia.produzione || 1)} color="#ff8f70" />
            <div className="radar-box">
              <div className={`radar-ping ${hasCriticalEvent ? 'alert critical' : evento ? 'alert' : ''}`} />
              <div className="radar-text">
                {hasCriticalEvent ? 'Evento critico' : evento ? 'Evento in corso' : 'Spazio stabile'}
              </div>
            </div>
            <div className="distance-box">
              <div className="distance-label">Rotta</div>
              <div className="distance-values">{Math.round(distanzaPercorsa)} / {Math.round(distanzaTarget || 0)}</div>
              <div className="distance-track">
                <div className="distance-fill" style={{ width: `${distanzaPct}%` }} />
              </div>
            </div>
          </div>
          <div className="status-legend" aria-label="Legenda livelli sottosistemi">
            <span><i style={{ background: '#ffffff' }} />OFF</span>
            <span><i style={{ background: '#8a2be2' }} />L1</span>
            <span><i style={{ background: '#2f8cff' }} />L3</span>
            <span><i style={{ background: '#9ccc65' }} />L5</span>
            <span><i style={{ background: '#ffb74d' }} />L7</span>
            <span><i style={{ background: '#ff3b30' }} />L9</span>
          </div>
          <h3>Stato Sottosistemi</h3>
          <Subsystems sottosistemi={state.sottosistemi} energia={energia} />
        </div>
      </div> : null}

      {showControl ? (
        <div className="panel control-deck lcars-panel">
          <div className="command-clusters">
            {Object.entries(groupedSystems).map(([groupName, subs]) => {
                const clickableSubs = (subs || [])
                  .filter(
                    (s) => !['batteria', 'serbatoio'].includes(String(s.tipo || '').toLowerCase())
                  )
                  .sort((a, b) => {
                    const oa = Number(a.ordine ?? 0);
                    const ob = Number(b.ordine ?? 0);
                    if (oa !== ob) return oa - ob;
                    return String(a.nome || '').localeCompare(String(b.nome || ''), 'it', {
                      sensitivity: 'base',
                    });
                  });
                if (!clickableSubs.length) return null;
                return (
              <div key={groupName} className={`system-column station-card ${groupTheme(groupName).theme}`}>
                <div className="system-title">
                  <span className="system-icon">{groupTheme(groupName).icon}</span>
                  <span className="system-name">{groupName}</span>
                </div>
                <div className="hex-cloud">
                  {clickableSubs.map((s) => (
                    (() => {
                      const lvl = Number(s.livello_target || 0);
                      const inRepair = Boolean(!s.online && s.recovery_at);
                      const iconData = statusIcon(s);
                      return (
                    <button
                      key={s.id}
                      type="button"
                      className={`subsystem-tile lcars-button ${s.online ? 'online' : 'offline'} ${tileLevelClass(lvl)} ${lvl >= 8 ? 'danger-pulse' : ''} ${inRepair ? 'repairing' : ''} ${(lvl >= 8 && tickAlive) ? 'tick-danger-ring' : ''}`}
                      onClick={() => openSubsystem(s)}
                      disabled={!s.online}
                    >
                      <div className="tile-head-row">
                        <span className="tile-name">{s.nome}</span>
                        <div className="tile-indicators" title={iconData.title}>
                          <PowerDial level={lvl} colorOverride={s.colore_livello_attuale || undefined} />
                          <span className="tile-mode-icon">{iconData.icon}</span>
                        </div>
                      </div>
                      <div className="tile-meta">
                      </div>
                      <div className="tile-badges">
                        {s.invertito ? <span className="badge warn">INV</span> : null}
                        {s.espulso ? <span className="badge danger">ESP</span> : null}
                        {inRepair ? <span className="badge repair">RIP</span> : null}
                        {!s.online ? <span className="badge danger">GUASTO</span> : null}
                      </div>
                    </button>
                      );
                    })()
                  ))}
                </div>
                {isAlimentazioneGroup(groupName) ? flightOpsPanel : null}
                <div className="system-footer">
                  <div className="system-summary-row">
                    <span>Attivi {clickableSubs.filter((s) => s.online).length}/{clickableSubs.length}</span>
                    <span>
                      Potenza media {clickableSubs.length ? Math.round(clickableSubs.reduce((acc, s) => acc + Number(s.livello_target || 0), 0) / clickableSubs.length) : 0}
                    </span>
                  </div>
                  <div className="system-power-track">
                    <div
                      className="system-power-fill"
                      style={{
                        width: `${clickableSubs.length ? Math.round((clickableSubs.reduce((acc, s) => acc + Number(s.livello_target || 0), 0) / (clickableSubs.length * 9)) * 100) : 0}%`,
                      }}
                    />
                  </div>
                  <div className="system-lcars-strips">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
                );
              })}
            {!hasAlimentazioneColumn ? (
              <div className={`system-column station-card ${groupTheme('Alimentazione').theme}`}>
                <div className="system-title">
                  <span className="system-icon">{groupTheme('Alimentazione').icon}</span>
                  <span className="system-name">Alimentazione</span>
                </div>
                {flightOpsPanel}
              </div>
            ) : null}
            {!Object.keys(groupedSystems).length ? (
              <div className="note">Nessun sottosistema disponibile in sessione. Prova un nuovo Decollo.</div>
            ) : null}
          </div>
        </div>
      ) : null}

      {showStatus ? <div className="input-strip">
        <div className="label">COMANDI DI SICUREZZA</div>
        <div className="feedback">
          {!online && '[OFFLINE LOCALE] '}
          Regola i sottosistemi dalla plancia touch per mantenere la nave stabile.
        </div>
        <button type="button" className="btn danger" onClick={onAbort}>Abort</button>
      </div> : null}
        </>
      )}

      {selectedSubsystem ? (
        <>
          <div
            className="subsystem-modal-backdrop"
            role="presentation"
            onClick={() => setSelectedSubsystem(null)}
          />
          <div
            className="panel subsystem-modal lcars-panel subsystem-modal-touch"
            style={{ borderColor: '#ffb86b' }}
            role="dialog"
            aria-modal="true"
            aria-labelledby="subsystem-modal-title"
          >
            <div className="modal-touch-layout">
              <header className="modal-touch-header">
                <div className="modal-touch-title-block">
                  <h3 id="subsystem-modal-title">Regolazione {selectedSubsystem.nome}</h3>
                  <div className="modal-touch-chip">{selectedSubsystem.tipo || 'standard'}</div>
                </div>
                <div className="modal-touch-preview" aria-hidden="true">
                  <PowerDial
                    level={editingLevel}
                    colorOverride={selectedSubsystem.colore_livello_attuale || undefined}
                  />
                  <div className="modal-touch-level-readout">{editingLevel}</div>
                </div>
              </header>

              <section className="modal-touch-section">
                <div className="modal-touch-section-label">Livello potenza</div>
                <div className="power-level-grid" role="group" aria-label="Selezione livello da 0 a 9">
                  {POWER_LEVELS.map((n) => (
                    <button
                      key={n}
                      type="button"
                      className={`power-level-btn ${powerButtonTierClass(n)} ${editingLevel === n ? 'active' : ''}`}
                      aria-pressed={editingLevel === n}
                      onClick={() => setEditingLevel(n)}
                    >
                      {n === 0 ? 'OFF' : n}
                    </button>
                  ))}
                </div>
              </section>

              {selectedSubsystem.supporta_direzioni ? (
                <section className="modal-touch-section">
                  <div className="modal-touch-section-label">Direzione propulsori</div>
                  <div className="direction-strip" role="group" aria-label="Direzione propulsori: sei direzioni">
                    {PROPULSOR_DIRECTIONS.map(({ value, label, arrow }) => (
                      <button
                        key={value}
                        type="button"
                        className={`direction-touch-btn direction-strip-btn ${editingDirection === value ? 'active' : ''}`}
                        aria-pressed={editingDirection === value}
                        aria-label={`${label}, direzione ${value}`}
                        title={label}
                        onClick={() => setEditingDirection(value)}
                      >
                        <span className="direction-strip-arrow" aria-hidden>{arrow}</span>
                        <span className="direction-strip-label">{label}</span>
                      </button>
                    ))}
                  </div>
                </section>
              ) : null}

              <div className="modal-touch-footer">
                <div className="modal-touch-footer-main">
                  <div className="modal-touch-toggles-line">
                    {selectedSubsystem.supporta_inversione ? (
                      <TouchLatchToggle
                        pressed={editingInvert}
                        onToggle={setEditingInvert}
                        hint="Inverti effetto"
                        labelIdle="Normale"
                        labelActive="Invertito"
                      />
                    ) : null}
                    {selectedSubsystem.supporta_espulsione ? (
                      <TouchLatchToggle
                        pressed={editingExpel}
                        onToggle={setEditingExpel}
                        hint="Espulsione"
                        labelIdle="Espulsione disattiva"
                        labelActive="Espulsione attiva"
                      />
                    ) : null}
                    <button
                      type="button"
                      className="btn modal-touch-close-btn"
                      onClick={() => setSelectedSubsystem(null)}
                    >
                      Chiudi
                    </button>
                  </div>
                  <button
                    type="button"
                    className="btn primary modal-touch-send-tall"
                    onClick={saveSubsystem}
                  >
                    Invia comando
                  </button>
                </div>
              </div>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
