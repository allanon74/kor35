import React, { useState } from 'react';
import { speakAllarmeEquipaggio } from '../pilotAlerts.js';

export function isAlimentazioneGroup(groupName) {
  return String(groupName || '').toLowerCase().includes('aliment');
}

const ALLARMI = [
  { id: 'giallo', title: 'Allarme Giallo', className: 'alarm-giallo' },
  { id: 'rosso', title: 'Allarme Rosso', className: 'alarm-rosso' },
  { id: 'nero', title: 'Allarme Nero', className: 'alarm-nero' },
  { id: 'blu', title: 'Allarme Blu', className: 'alarm-blu' },
  { id: 'crociera', title: 'Nessun allarme — crociera', className: 'alarm-verde' },
];

/**
 * Comandi volo + allarme equipaggio nella colonna Alimentazione (compatto).
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
        await speakAllarmeEquipaggio(res.announcement, id);
      }
    });
  };

  return (
    <div className="flight-ops-panel" aria-label="Comandi volo e allarme equipaggio">
      <div className="flight-ops-flight-btns">
        {!decolloEffettuato ? (
          <button
            type="button"
            className="flight-ops-btn flight-ops-decollo"
            disabled={disabled || busy || !motoreOff}
            title={motoreOff ? 'Decollo' : 'Motore principale a 0'}
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
              title="Atterraggio"
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
              title="Atterraggio di emergenza"
              onClick={() => run(async () => {
                if (!window.confirm("Confermi l'atterraggio di emergenza?")) return;
                await onEmergencyLanding?.();
              })}
            >
              Emergenza
            </button>
          </>
        )}
      </div>

      <div className="flight-ops-alarm-row" role="group" aria-label="Allarme equipaggio">
        {ALLARMI.map((a) => (
          <button
            key={a.id}
            type="button"
            className={`flight-ops-alarm-btn ${a.className} ${allarmeEquipaggio === a.id ? 'active' : ''}`}
            disabled={disabled || busy}
            title={a.title}
            aria-label={a.title}
            aria-pressed={allarmeEquipaggio === a.id}
            onClick={() => handleAllarme(a.id)}
          />
        ))}
      </div>
    </div>
  );
}
