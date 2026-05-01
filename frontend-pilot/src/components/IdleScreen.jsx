import React, { useEffect, useState } from 'react';

/**
 * Schermata "nave a terra": il pilota seleziona prefettura di partenza/arrivo
 * e avvia il viaggio. Il backend calcola la durata effettiva (10/30/60 min,
 * +20% per ogni livello DEFCON di partenza).
 */
export default function IdleScreen({ prefetture, onStart, error, busy }) {
  const [partenzaId, setPartenzaId] = useState('');
  const [arrivoId, setArrivoId] = useState('');

  useEffect(() => {
    if (!partenzaId && prefetture.length) setPartenzaId(String(prefetture[0].id));
    if (!arrivoId && prefetture.length > 1) setArrivoId(String(prefetture[1].id));
  }, [prefetture]);

  return (
    <div className="center-screen">
      <h1>KOR-35 // PRECONTROLLO</h1>
      <p>Imposta rotta del viaggio. Lo stato della nave e' a terra.</p>
      <div className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.8rem' }}>
        <label>
          <div className="banner" style={{ padding: 0, border: 0, marginBottom: '0.3rem' }}>
            Prefettura partenza
          </div>
          <select value={partenzaId} onChange={(ev) => setPartenzaId(ev.target.value)} style={{ width: '100%' }}>
            <option value="">--</option>
            {prefetture.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome} ({p.regione || 's/r'})
              </option>
            ))}
          </select>
        </label>
        <label>
          <div className="banner" style={{ padding: 0, border: 0, marginBottom: '0.3rem' }}>
            Prefettura arrivo
          </div>
          <select value={arrivoId} onChange={(ev) => setArrivoId(ev.target.value)} style={{ width: '100%' }}>
            <option value="">--</option>
            {prefetture.map((p) => (
              <option key={p.id} value={p.id}>
                {p.nome} ({p.regione || 's/r'})
              </option>
            ))}
          </select>
        </label>
        <div className="row center">
          <button
            type="button"
            className="btn primary"
            disabled={busy || !partenzaId || !arrivoId}
            onClick={() => onStart(Number(partenzaId), Number(arrivoId))}
          >
            Avvia decollo
          </button>
        </div>
        {error && <div className="error">{error}</div>}
        <p className="note">
          Durata viaggio = 10 min stessa prefettura, 30 min stessa regione,
          60 min altrimenti. DEFCON al decollo allunga il volo.
        </p>
      </div>
    </div>
  );
}
