import React, { useEffect, useState } from 'react';

/**
 * Schermata "nave spenta": stato 0 (disattiva).
 * Il pilota preme decollo e avvia il viaggio.
 */
function etichettaPercorso(p) {
  const partenza = String(p?.partenza || '').trim();
  const arrivo = String(p?.arrivo || '').trim();
  if (partenza && arrivo) return `${partenza} → ${arrivo}`;
  return p?.nome || partenza || arrivo || 'Rotta';
}

export default function IdleScreen({ percorsi = [], onStart, error, busy }) {
  const [percorsoId, setPercorsoId] = useState('');

  useEffect(() => {
    if (!percorsoId && percorsi.length) setPercorsoId(String(percorsi[0].id));
  }, [percorsi, percorsoId]);

  const selezionato = percorsi.find((p) => String(p.id) === String(percorsoId));

  return (
    <div className="center-screen">
      <h1>KOR-35 // PRECONTROLLO</h1>
      <p>Stato nave: 0 - DISATTIVA. Scegli il percorso e accedi alla plancia per i controlli pre-volo.</p>
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
        <label>
          <div className="banner" style={{ padding: 0, border: 0, marginBottom: '0.3rem' }}>
            Rotta
          </div>
          <select value={percorsoId} onChange={(ev) => setPercorsoId(ev.target.value)} style={{ width: '100%' }}>
            <option value="">--</option>
            {percorsi.map((p) => (
              <option key={p.id} value={p.id}>
                {etichettaPercorso(p)} ({p.distanza_minima}–{p.distanza_massima})
              </option>
            ))}
          </select>
        </label>
        <div className="row center">
          <button
            type="button"
            className="btn primary"
            disabled={busy || !percorsoId}
            onClick={() => onStart(percorsoId)}
          >
            Prepara missione
          </button>
        </div>
        {error && <div className="error">{error}</div>}
        <p className="note">
          {selezionato
            ? `La distanza del viaggio sarà un valore a caso tra ${selezionato.distanza_minima} e ${selezionato.distanza_massima}.`
            : 'Nessuna rotta disponibile: configurala dalla dashboard staff, tab Pilotaggio → Rotte.'}
          {' '}Dalla plancia regola i sottosistemi, poi usa <strong>Decollo</strong> sul propulsore principale.
        </p>
      </div>
    </div>
  );
}
