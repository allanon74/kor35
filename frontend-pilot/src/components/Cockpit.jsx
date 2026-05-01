import React, { useEffect, useState } from 'react';
import { useExclusiveKeyboard } from '../useKeyboard.js';

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

function Subsystems({ sottosistemi }) {
  if (!sottosistemi || !sottosistemi.length) {
    return <p className="note">Nessun sottosistema registrato in questa sessione.</p>;
  }
  return (
    <div className="subsys-list">
      {sottosistemi.map((s) => (
        <div key={s.id} className={`subsys ${s.online ? 'online' : 'offline'}`}>
          <span className="codice">{s.codice}</span>
          <span>{s.nome}</span>
          <div style={{ fontSize: '0.7rem', marginTop: '0.2rem' }}>
            {s.online ? 'ONLINE' : 'GUASTO'}
          </div>
        </div>
      ))}
    </div>
  );
}

function HistoryPanel({ tentativi }) {
  if (!tentativi || !tentativi.length) {
    return <p className="note">Nessun tentativo ancora.</p>;
  }
  return (
    <div className="history">
      {tentativi.map((t) => {
        const delta = t.defcon_post - t.defcon_pre;
        const cls = delta > 0 ? 'delta-ko' : delta < 0 ? 'delta-ok' : '';
        return (
          <div key={t.id} className="row">
            <span className="codice">{t.codice}</span>
            <span className="esito">{t.esito}</span>
            <span className={cls}>
              {delta > 0 ? `+${delta}` : delta}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/**
 * Cockpit di volo. Mostra DEFCON, evento attivo, sottosistemi, storia.
 * Cattura tastiera in modo esclusivo: solo input codici 3-char.
 */
export default function Cockpit({
  state, online, lastValutazione,
  onCommand, onAbort, onLogout, tentativi,
}) {
  const sessione = state.sessione || {};
  const evento = state.evento_attivo;
  const defcon = sessione.defcon || 0;
  const defconMax = state.defcon_max || 5;
  const seqDecollo = state.sequenze?.decollo;
  const seqAtter = state.sequenze?.atterraggio;

  const isCrashed = sessione.stato === 'crashed';
  const inputEnabled = !isCrashed && sessione.stato !== 'arrivata';

  const { buffer } = useExclusiveKeyboard({
    enabled: inputEnabled,
    onSubmit: (code) => onCommand(code),
  });

  if (isCrashed) {
    return (
      <div className="center-screen crash-screen">
        <h1>// CRASH //</h1>
        <p>La nave ha superato la gravita' critica e e' precipitata.</p>
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
        <p>Sequenza di atterraggio completata. Buon viaggio.</p>
        <div className="row" style={{ marginTop: '2rem' }}>
          <button type="button" className="btn primary" onClick={onLogout}>Logout pilota</button>
        </div>
      </div>
    );
  }

  const sottosistemiOffline = (state.sottosistemi || []).filter((s) => !s.online);

  return (
    <div className="cockpit">
      <div className="defcon-strip">
        <div>
          <div className="label">DEFCON</div>
          <div className={`value ${defconClass(defcon, defconMax)}`}>
            {defcon > defconMax ? 'CRASH' : defcon}
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
      </div>

      {sottosistemiOffline.map((s) => (
        <div key={s.id} className="alert-bar">
          ⚠ Sottosistema {s.nome} ({s.codice}) GUASTO
        </div>
      ))}

      {sessione.stato === 'decollo' && (
        <div className="alert-bar" style={{ background: '#3a4d6f' }}>
          DECOLLO - inserisci la sequenza ({seqDecollo?.idx_corrente || 0}/{seqDecollo?.lunghezza || 0})
        </div>
      )}
      {sessione.stato === 'atterraggio' && (
        <div className="alert-bar" style={{ background: '#3a4d6f' }}>
          ATTERRAGGIO - inserisci la sequenza ({seqAtter?.idx_corrente || 0}/{seqAtter?.lunghezza || 0})
        </div>
      )}

      <div className="middle-grid">
        <div className="panel">
          <h3>Evento</h3>
          {evento ? (
            <div className="event-box pending">
              <h2>{evento.nome}</h2>
              <CountdownBox deadlineISO={evento.deadline_at} />
              <div className="descr">{evento.descrizione}</div>
            </div>
          ) : (
            <p className="note">Nessun evento attivo. Mantieni la rotta.</p>
          )}
        </div>
        <div className="panel">
          <h3>Sottosistemi</h3>
          <Subsystems sottosistemi={state.sottosistemi} />
          <h3 style={{ marginTop: '1rem' }}>Ultimi codici</h3>
          <HistoryPanel tentativi={tentativi} />
        </div>
      </div>

      <div className="input-strip">
        <div className="label">CMD</div>
        <div className="digits">
          {[0, 1, 2].map((i) => (
            <div key={i} className="digit">{buffer[i] || '_'}</div>
          ))}
        </div>
        <div className={`feedback ${
          lastValutazione?.delta_defcon < 0 ? 'ok'
            : lastValutazione?.delta_defcon > 0 ? 'ko' : ''
        }`}>
          {!online && '[OFFLINE LOCALE] '}
          {lastValutazione?.descrizione || 'Inserisci 3 caratteri (lettera/cifra, lettera/cifra, cifra).'}
        </div>
        <button type="button" className="btn danger" onClick={onAbort}>Abort</button>
      </div>
    </div>
  );
}
