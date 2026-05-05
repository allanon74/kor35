import React, { useEffect, useRef, useState } from 'react';

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
  const ticks = Number(ev?.ticks_rimanenti);
  if (Number.isFinite(ticks)) score += Math.max(0, 200 - ticks);
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
  onAbort, onEmergencyLanding, onLogout, mode = 'both', onSubsystemSet,
  error, commandStatus,
}) {
  const sessione = state.sessione || {};
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

  const sottosistemiOffline = (state.sottosistemi || []).filter((s) => !s.online);
  const groupedSystems = state.sistemi || {};
  const energia = state.energia || {};
  const distanzaPercorsa = Number(energia.distanza_percorsa || 0);
  const distanzaTarget = Number(energia.distanza_target || 0);
  const distanzaPct = ratio(distanzaPercorsa, distanzaTarget);
  const tickAlive = Boolean(state?.tick_runtime?.enabled && state?.tick_runtime?.alive);
  const alarmAudioEnabled = Boolean(state?.tick_runtime?.alarm_audio_enabled);
  const hasCriticalSubsystem = (state.sottosistemi || []).some((s) => Number(s.livello_target || 0) >= 8 && s.online);

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
        <div className="row" style={{ marginTop: '2rem' }}>
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
        <div className="row" style={{ marginTop: '2rem' }}>
          <button type="button" className="btn primary" onClick={onLogout}>Logout pilota</button>
        </div>
      </div>
    );
  }

  return (
    <div className={`cockpit cockpit-lcars ${mode === 'control' ? 'cockpit-control' : ''}`}>
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
                    {Number.isFinite(Number(ev.ticks_rimanenti))
                      ? `Tick residui: ${ev.ticks_rimanenti}`
                      : 'Durata persistente'}
                    {ev.precipita_a_scadenza ? ' - Esito critico a scadenza' : ''}
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
              <div className={`radar-ping ${evento ? 'alert' : ''}`} />
              <div className="radar-text">{evento ? 'Evento in corso' : 'Spazio stabile'}</div>
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
            {Object.entries(groupedSystems)
              .sort(([a], [b]) => String(a).localeCompare(String(b)))
              .map(([groupName, subs]) => {
                const clickableSubs = (subs || []).filter(
                  (s) => !['batteria', 'serbatoio'].includes(String(s.tipo || '').toLowerCase())
                );
                if (!clickableSubs.length) return null;
                return (
              <div key={groupName} className={`system-column station-card ${groupTheme(groupName).theme}`}>
                <div className="system-title">
                  <span className="system-icon">{groupTheme(groupName).icon}</span>
                  <span className="system-name">{groupName}</span>
                </div>
                <div className="hex-cloud">
                  {[...clickableSubs].sort((a, b) => String(a.nome || '').localeCompare(String(b.nome || ''))).map((s) => (
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

      {selectedSubsystem ? (
        <div className="panel subsystem-modal lcars-panel" style={{ borderColor: '#ffb86b' }}>
          <h3>Regolazione {selectedSubsystem.nome}</h3>
          <div className="modal-lcars-grid">
            <div className="modal-rail">
              <div className="rail-chip">{selectedSubsystem.tipo || 'standard'}</div>
              <div className="rail-level">{editingLevel}</div>
              <div className="rail-label">Potenza</div>
            </div>
            <div className="modal-core">
              <label className="modal-field">
                Livello potenza
                <input
                  type="range"
                  min={0}
                  max={9}
                  value={editingLevel}
                  onChange={(e) => setEditingLevel(Number(e.target.value))}
                />
              </label>
              {selectedSubsystem.supporta_direzioni ? (
                <label className="modal-field">
                  Direzione propulsori
                  <select value={editingDirection} onChange={(e) => setEditingDirection(e.target.value)}>
                    <option value="avanti">Avanti</option>
                    <option value="indietro">Indietro</option>
                    <option value="su">Su</option>
                    <option value="giu">Giu</option>
                    <option value="destra">Destra</option>
                    <option value="sinistra">Sinistra</option>
                  </select>
                </label>
              ) : null}
              <div className="modal-toggles">
                {selectedSubsystem.supporta_inversione ? (
                  <label><input type="checkbox" checked={editingInvert} onChange={(e) => setEditingInvert(e.target.checked)} /> Inverti effetto</label>
                ) : null}
                {selectedSubsystem.supporta_espulsione ? (
                  <label><input type="checkbox" checked={editingExpel} onChange={(e) => setEditingExpel(e.target.checked)} /> Espulsione</label>
                ) : null}
              </div>
              <div className="modal-actions">
                <button type="button" className="btn primary" onClick={saveSubsystem}>Invia comando</button>
                {(selectedSubsystem.tipo === 'motore' && Number(editingLevel || 0) === 0) ? (
                  <button
                    type="button"
                    className="btn danger"
                    onClick={async () => {
                      if (!onEmergencyLanding) return;
                      if (!window.confirm("Confermi l'atterraggio di emergenza?")) return;
                      await onEmergencyLanding();
                      setSelectedSubsystem(null);
                    }}
                  >
                    Atterraggio di emergenza
                  </button>
                ) : null}
                <button type="button" className="btn" onClick={() => setSelectedSubsystem(null)}>Chiudi</button>
              </div>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
