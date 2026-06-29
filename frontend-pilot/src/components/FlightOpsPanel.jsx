import React, { useState } from 'react';
import { speakItalianAnnouncement } from '../pilotAlerts.js';

export function isAlimentazioneGroup(groupName) {
  return String(groupName || '').toLowerCase().includes('aliment');
}

const ALLARMI = [
  { id: 'giallo', label: 'Allarme Giallo', className: 'alarm-giallo' },
  { id: 'rosso', label: 'Allarme Rosso', className: 'alarm-rosso' },
  { id: 'nero', label: 'Allarme Nero', className: 'alarm-nero' },
  { id: 'blu', label: 'Allarme Blu', className: 'alarm-blu' },
];

/**
 * Comandi volo + allarme equipaggio nella colonna Alimentazione.
 */
export default function FlightOpsPanel({
  decolloEffettuato,
  allarmeEquipaggio = 'crociera',
  motoreLivello = 0,
  onTakeoff,
  onLanding,
  onEmergencyLanding,
  onSetAllarme,
  disabled = false,
}) {
  const [busy, setBusy] = useState(false);
  const motoreOff = Number(motoreLivello || 0) === 0;
  const inCrociera = allarmeEquipaggio === 'crociera';

  const run = async (fn) => {
    if (!fn || busy || disabled) return;
    setBusy(true);
    try {
      await fn();
    } finally {
      setBusy(false);
    }
  };

  const handleAllarme = async (id) => {
    if (!onSetAllarme) return;
    await run(async () => {
      const res = await onSetAllarme(id);
      if (res?.announcement) {
        await speakItalianAnnouncement(res.announcement);
      }
    });
  };

  return (
    <div className="flight-ops-panel" aria-label="Comandi volo e allarme equipaggio">
      <div className="flight-ops-section-label">Manovre</div>
      <div className="flight-ops-flight-btns">
        {!decolloEffettuato ? (
          <button
            type="button"
            className="flight-ops-btn flight-ops-decollo"
            disabled={disabled || busy || !motoreOff}
            title={motoreOff ? 'Avvia sequenza di decollo' : 'Motore principale deve essere a 0'}
            onClick={() => run(async () => {
              if (!window.confirm('Confermi la sequenza di decollo?')) return;
              await onTakeoff?.();
            })}
          >
            Decollo
          </button>
        ) : (
          <>
            <button
              type="button"
              className="flight-ops-btn flight-ops-landing"
              disabled={disabled || busy || !motoreOff}
              title={motoreOff ? 'Atterraggio programmato' : 'Motore principale deve essere a 0'}
              onClick={() => run(async () => {
                if (!window.confirm('Confermi l\'atterraggio?')) return;
                await onLanding?.();
              })}
            >
              Atterraggio
            </button>
            <button
              type="button"
              className="flight-ops-btn flight-ops-emergency"
              disabled={disabled || busy || !motoreOff}
              title={motoreOff ? 'Atterraggio di emergenza' : 'Motore principale deve essere a 0'}
              onClick={() => run(async () => {
                if (!window.confirm("Confermi l'atterraggio di emergenza?")) return;
                await onEmergencyLanding?.();
              })}
            >
              Atterraggio di emergenza
            </button>
          </>
        )}
      </div>

      <div className="flight-ops-section-label">Allarme equipaggio</div>
      <div className="flight-ops-alarm-grid">
        {ALLARMI.map((a) => (
          <button
            key={a.id}
            type="button"
            className={`flight-ops-alarm-btn ${a.className} ${allarmeEquipaggio === a.id ? 'active' : ''}`}
            disabled={disabled || busy}
            onClick={() => handleAllarme(a.id)}
          >
            {a.label}
          </button>
        ))}
      </div>
      <button
        type="button"
        className={`flight-ops-btn flight-ops-crociera ${inCrociera ? 'active' : ''}`}
        disabled={disabled || busy}
        onClick={() => handleAllarme('crociera')}
      >
        Crociera — nessun allarme
      </button>
      {!inCrociera ? (
        <div className="flight-ops-alarm-active" aria-live="polite">
          Stato: <strong>{allarmeEquipaggio.toUpperCase()}</strong>
        </div>
      ) : null}
    </div>
  );
}
