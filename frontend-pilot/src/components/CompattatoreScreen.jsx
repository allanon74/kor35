import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';

export default function CompattatoreScreen({ onLogout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedMattone, setSelectedMattone] = useState('');
  const [lastRisonanza, setLastRisonanza] = useState(null);
  const [lastQuantico, setLastQuantico] = useState(null);
  const [quanticoOpen, setQuanticoOpen] = useState(false);
  const [quanticoNome, setQuanticoNome] = useState('');
  const [quanticoQrId, setQuanticoQrId] = useState('');
  const [quanticoPgId, setQuanticoPgId] = useState('');

  const refresh = useCallback(async () => {
    try {
      const res = await api.compattatoreState();
      setData(res);
      setError('');
    } catch (e) {
      setError(e.message || 'Errore caricamento compattatore.');
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const runOp = async (tipo) => {
    if (!selectedMattone) {
      setError('Seleziona un componente dalla stiva.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      let res;
      if (tipo === 'compressione') res = await api.compattatoreCompressione(selectedMattone);
      else if (tipo === 'decompressione') res = await api.compattatoreDecompressione(selectedMattone);
      else res = await api.compattatoreRisonanza(selectedMattone);
      setData(res);
      if (res?.risonanza) setLastRisonanza(res.risonanza);
    } catch (e) {
      setError(e.message || 'Operazione non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  const runQuantico = async () => {
    setBusy(true);
    setError('');
    try {
      const body = {};
      if (quanticoQrId.trim()) {
        body.qr_id = quanticoQrId.trim();
        if (quanticoPgId.trim()) body.personaggio_id = quanticoPgId.trim();
      } else if (quanticoNome.trim()) {
        body.nome_oggetto = quanticoNome.trim();
      } else {
        setError('Inserisci il nome oggetto oppure un ID QR.');
        setBusy(false);
        return;
      }
      const res = await api.compattatoreQuantico(body);
      setData(res);
      if (res?.quantico) setLastQuantico(res.quantico);
      setQuanticoOpen(false);
      setQuanticoNome('');
      setQuanticoQrId('');
      setQuanticoPgId('');
    } catch (e) {
      setError(e.message || 'Compattatore Quantico non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  const righe = data?.stiva?.righe || [];
  const catalogo = righe.length ? righe : [];
  const quanticoOn = Boolean(data?.quantico_abilitato);
  const quanticoReady = Boolean(data?.quantico_disponibile);

  return (
    <div className="card compattatore-screen" style={{ maxWidth: 960, margin: '0 auto' }}>
      <h1 style={{ marginTop: 0 }}>Compattatore quantico</h1>
      {!data?.abilitato ? (
        <p className="error">Console compattatore disabilitata in configurazione staff.</p>
      ) : null}
      {!data?.operativo ? (
        <p className="error">Non operativo — verifica sottosistema Z (online, energia &gt; 0).</p>
      ) : (
        <p style={{ color: '#9ccc65' }}>
          Operativo · energia {data.livello_energia}/9 · accumulo {Math.round(data.energia_accumulata || 0)}/9
          {data.operazione_disponibile ? ' · PRONTO' : ' · carica in corso'}
        </p>
      )}

      <div style={{ display: 'flex', gap: '0.75rem', flexWrap: 'wrap', margin: '1rem 0' }}>
        <button type="button" className="btn" disabled={busy || !data?.operazione_disponibile} onClick={() => runOp('compressione')}>
          Compressione 2:1
        </button>
        <button type="button" className="btn" disabled={busy || !data?.operazione_disponibile} onClick={() => runOp('decompressione')}>
          Decompressione 1:2
        </button>
        <button type="button" className="btn" disabled={busy || !data?.operazione_disponibile} onClick={() => runOp('risonanza')}>
          Risonanza
        </button>
        <button
          type="button"
          className="btn"
          disabled={busy || !quanticoReady}
          title={quanticoOn ? 'Sacrificio oggetto → componenti' : 'FUORI USO — attivare da staff per l\'evento'}
          onClick={() => quanticoOn && setQuanticoOpen((v) => !v)}
        >
          {quanticoOn ? 'Compattatore Quantico' : 'Compattatore Quantico — FUORI USO'}
        </button>
      </div>

      {quanticoOpen && quanticoOn ? (
        <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem', background: '#1a2332' }}>
          <h2 style={{ marginTop: 0, fontSize: '1rem' }}>Sacrificio quantico</h2>
          <p style={{ fontSize: '0.85rem', color: '#9ca3af', marginTop: 0 }}>
            L&apos;oggetto viene eliminato (se QR + personaggio) e si generano 1–5 componenti dal nome.
          </p>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
            Nome oggetto (testo)
            <input
              type="text"
              className="mono"
              style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              value={quanticoNome}
              onChange={(e) => setQuanticoNome(e.target.value)}
              placeholder="Es. Reattore instabile"
            />
          </label>
          <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.85rem' }}>
            ID QR (opzionale — con personaggio elimina dall&apos;inventario)
            <input
              type="text"
              className="mono"
              style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              value={quanticoQrId}
              onChange={(e) => setQuanticoQrId(e.target.value)}
            />
          </label>
          <label style={{ display: 'block', marginBottom: '0.75rem', fontSize: '0.85rem' }}>
            ID personaggio (obbligatorio con QR per eliminare oggetto)
            <input
              type="text"
              className="mono"
              style={{ display: 'block', width: '100%', marginTop: '0.25rem' }}
              value={quanticoPgId}
              onChange={(e) => setQuanticoPgId(e.target.value)}
            />
          </label>
          <button type="button" className="btn" disabled={busy || !quanticoReady} onClick={runQuantico}>
            Esegui compattazione quantica
          </button>
        </div>
      ) : null}

      {error ? <div className="error">{error}</div> : null}

      {lastQuantico ? (
        <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem', background: '#1a2332' }}>
          <h2 style={{ marginTop: 0, fontSize: '1rem' }}>Ultimo Compattatore Quantico</h2>
          <p className="mono" style={{ fontSize: '0.85rem' }}>
            {lastQuantico.nome_input}
            {' → '}
            {lastQuantico.numero_unit}
            {' unità in stiva'}
          </p>
          {lastQuantico.oggetto_eliminato ? (
            <p style={{ fontSize: '0.8rem', color: '#f87171' }}>
              Oggetto eliminato:
              {' '}
              {lastQuantico.oggetto_eliminato}
            </p>
          ) : null}
          <ul style={{ fontSize: '0.8rem', color: '#9ccc65', margin: '0.5rem 0 0', paddingLeft: '1.2rem' }}>
            {(lastQuantico.unita || []).map((u, i) => (
              <li key={`q-${i}`}>
                [{u.indice_componente}]
                {' '}
                {u.colore_nome}
                {' '}
                (da «
                {u.lettera_fonte}
                »)
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      {lastRisonanza ? (
        <div className="card" style={{ marginBottom: '1rem', padding: '0.75rem', background: '#1a2332' }}>
          <h2 style={{ marginTop: 0, fontSize: '1rem' }}>Ultima risonanza</h2>
          <p className="mono" style={{ fontSize: '0.85rem' }}>
            Slot A: {lastRisonanza.slot_a?.esito === 'glitch' ? lastRisonanza.slot_a?.nome : lastRisonanza.slot_a?.colore_nome || '—'}
            {' · '}
            Slot B: {lastRisonanza.slot_b?.esito === 'glitch' ? lastRisonanza.slot_b?.nome : lastRisonanza.slot_b?.colore_nome || '—'}
          </p>
          {lastRisonanza.glitch?.length ? (
            <p className="error" style={{ fontSize: '0.85rem' }}>
              Glitch: {lastRisonanza.glitch.map((g) => g.nome).join(', ')}
            </p>
          ) : null}
          {lastRisonanza.bonus?.length ? (
            <p style={{ color: '#9ccc65', fontSize: '0.85rem' }}>
              Bonus: {lastRisonanza.bonus.map((b) => b.tipo).join(', ')}
            </p>
          ) : null}
        </div>
      ) : null}

      <h2>Stiva</h2>
      <div style={{ display: 'grid', gap: '0.35rem' }}>
        {catalogo.length === 0 ? (
          <p style={{ color: '#888' }}>Stiva vuota — carica componenti da staff.</p>
        ) : (
          catalogo.map((r) => (
            <label key={r.mattone_id} style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
              <input
                type="radio"
                name="mattone"
                value={r.mattone_id}
                checked={selectedMattone === r.mattone_id}
                onChange={() => setSelectedMattone(r.mattone_id)}
              />
              <span className="mono">
                [{r.indice_componente}] {r.nome} · {r.colore_nome} × {r.quantita}
              </span>
            </label>
          ))
        )}
      </div>

      {onLogout ? (
        <p style={{ marginTop: '1.5rem' }}>
          <button type="button" className="btn" onClick={onLogout}>Logout console</button>
        </p>
      ) : null}
    </div>
  );
}
