import React, { useCallback, useEffect, useState } from 'react';
import { api } from '../api.js';
import StivaCompattatoreGrid from './StivaCompattatoreGrid.jsx';
import CompattatoreElementPicker from './CompattatoreElementPicker.jsx';
import CompattatoreQrInput from './CompattatoreQrInput.jsx';

function ResultScreen({ title, children, variant = 'default', empty }) {
  return (
    <div className={`comp-result-screen comp-result-screen--${variant}`}>
      <div className="comp-result-screen-header">
        <span className="comp-result-screen-title">{title}</span>
        <span className="comp-result-screen-led" aria-hidden="true" />
      </div>
      <div className="comp-result-screen-body">
        {empty ? <p className="comp-result-empty">{empty}</p> : children}
      </div>
    </div>
  );
}

export default function CompattatoreScreen({ onLogout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedMattone, setSelectedMattone] = useState('');
  const [lastRisonanza, setLastRisonanza] = useState(null);
  const [lastClassicNote, setLastClassicNote] = useState('');
  const [lastQuantico, setLastQuantico] = useState(null);
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
      setError('Seleziona un componente sorgente.');
      return;
    }
    setBusy(true);
    setError('');
    setLastClassicNote('');
    try {
      let res;
      if (tipo === 'compressione') res = await api.compattatoreCompressione(selectedMattone);
      else if (tipo === 'decompressione') res = await api.compattatoreDecompressione(selectedMattone);
      else res = await api.compattatoreRisonanza(selectedMattone);
      setData(res);
      if (res?.risonanza) {
        setLastRisonanza(res.risonanza);
      } else {
        const labels = {
          compressione: 'Compressione 2:1 completata.',
          decompressione: 'Decompressione 1:2 completata.',
        };
        setLastClassicNote(labels[tipo] || 'Operazione completata.');
      }
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
        setError('Inserisci il nome oggetto oppure acquisisci un QR.');
        setBusy(false);
        return;
      }
      const res = await api.compattatoreQuantico(body);
      setData(res);
      if (res?.quantico) setLastQuantico(res.quantico);
      setQuanticoNome('');
      setQuanticoQrId('');
      setQuanticoPgId('');
    } catch (e) {
      setError(e.message || 'Compattatore Quantico non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  const quanticoOn = Boolean(data?.quantico_abilitato);
  const quanticoReady = Boolean(data?.quantico_disponibile);
  const opReady = Boolean(data?.operazione_disponibile);
  const energiaPct = Math.min(100, ((data?.energia_accumulata || 0) / (data?.energia_soglia_operazione || 9)) * 100);

  return (
    <div className="compattatore-console">
      <header className="compattatore-hud">
        <div className="compattatore-hud-brand">
          <span className="compattatore-hud-kicker">KOR-35 // NODO Z</span>
          <h1 className="compattatore-hud-title">Compattatore quantico</h1>
        </div>
        <div className="compattatore-hud-status">
          {!data?.abilitato ? (
            <span className="comp-hud-pill comp-hud-pill--off">Console disabilitata</span>
          ) : !data?.operativo ? (
            <span className="comp-hud-pill comp-hud-pill--off">Sottosistema Z offline</span>
          ) : (
            <>
              <span className={`comp-hud-pill ${opReady ? 'comp-hud-pill--ok' : 'comp-hud-pill--charge'}`}>
                {opReady ? 'PRONTO' : 'CARICA'}
              </span>
              <div className="comp-energy-meter" title="Energia accumulata">
                <span className="comp-energy-label">
                  EN
                  {' '}
                  {Math.round(data?.energia_accumulata || 0)}
                  /
                  {data?.energia_soglia_operazione || 9}
                </span>
                <div className="comp-energy-track">
                  <div className="comp-energy-fill" style={{ width: `${energiaPct}%` }} />
                </div>
              </div>
            </>
          )}
        </div>
      </header>

      {error ? <div className="compattatore-alert error">{error}</div> : null}

      <div className="compattatore-columns">
        <section className="compattatore-panel compattatore-panel--classic">
          <div className="compattatore-panel-corner compattatore-panel-corner--tl" aria-hidden="true" />
          <div className="compattatore-panel-corner compattatore-panel-corner--br" aria-hidden="true" />
          <h2 className="compattatore-panel-title">Motore classico</h2>
          <p className="compattatore-panel-sub">Compressione · decompressione · risonanza</p>

          <div className="comp-op-row">
            <button
              type="button"
              className="comp-btn comp-btn--op"
              disabled={busy || !opReady}
              onClick={() => runOp('compressione')}
            >
              <span className="comp-btn-kicker">2:1</span>
              Compressione
            </button>
            <button
              type="button"
              className="comp-btn comp-btn--op"
              disabled={busy || !opReady}
              onClick={() => runOp('decompressione')}
            >
              <span className="comp-btn-kicker">1:2</span>
              Decompressione
            </button>
            <button
              type="button"
              className="comp-btn comp-btn--op comp-btn--risonanza"
              disabled={busy || !opReady}
              onClick={() => runOp('risonanza')}
            >
              <span className="comp-btn-kicker">◇◇</span>
              Risonanza
            </button>
          </div>

          <CompattatoreElementPicker
            righe={data?.stiva?.righe || []}
            selectedMattone={selectedMattone}
            onSelectMattone={setSelectedMattone}
          />

          <ResultScreen
            title="Output motore"
            variant="classic"
            empty={!lastRisonanza && !lastClassicNote ? 'In attesa di operazione…' : null}
          >
            {lastClassicNote ? (
              <p className="comp-result-line comp-result-line--ok">{lastClassicNote}</p>
            ) : null}
            {lastRisonanza ? (
              <>
                <p className="comp-result-line">
                  <strong>Slot A</strong>
                  {' '}
                  {lastRisonanza.slot_a?.esito === 'glitch'
                    ? lastRisonanza.slot_a?.nome
                    : lastRisonanza.slot_a?.colore_nome || '—'}
                </p>
                <p className="comp-result-line">
                  <strong>Slot B</strong>
                  {' '}
                  {lastRisonanza.slot_b?.esito === 'glitch'
                    ? lastRisonanza.slot_b?.nome
                    : lastRisonanza.slot_b?.colore_nome || '—'}
                </p>
                {lastRisonanza.glitch?.length ? (
                  <p className="comp-result-line comp-result-line--warn">
                    Glitch:
                    {' '}
                    {lastRisonanza.glitch.map((g) => g.nome).join(', ')}
                  </p>
                ) : null}
                {lastRisonanza.bonus?.length ? (
                  <p className="comp-result-line comp-result-line--ok">
                    Bonus:
                    {' '}
                    {lastRisonanza.bonus.map((b) => b.tipo).join(', ')}
                  </p>
                ) : null}
              </>
            ) : null}
          </ResultScreen>
        </section>

        <section className={`compattatore-panel compattatore-panel--quantico ${!quanticoOn ? 'is-disabled' : ''}`}>
          <div className="compattatore-panel-corner compattatore-panel-corner--tl" aria-hidden="true" />
          <div className="compattatore-panel-corner compattatore-panel-corner--br" aria-hidden="true" />
          <h2 className="compattatore-panel-title">Compattatore quantico</h2>
          <p className="compattatore-panel-sub">
            {quanticoOn ? 'Sacrificio oggetto → componenti (1–5)' : 'Fuori uso — attivare da staff'}
          </p>

          <label className="comp-field">
            <span className="comp-field-label">Nome oggetto (testo libero)</span>
            <input
              type="text"
              className="comp-sci-input"
              value={quanticoNome}
              disabled={busy || !quanticoOn || !quanticoReady}
              placeholder="Es. Reattore instabile"
              onChange={(e) => setQuanticoNome(e.target.value)}
            />
          </label>

          <div className="comp-or-divider">
            <span>oppure</span>
          </div>

          <CompattatoreQrInput
            qrId={quanticoQrId}
            personaggioId={quanticoPgId}
            disabled={busy || !quanticoOn || !quanticoReady}
            onQrIdChange={setQuanticoQrId}
            onPersonaggioIdChange={setQuanticoPgId}
          />

          <button
            type="button"
            className="comp-btn comp-btn--quantico"
            disabled={busy || !quanticoReady}
            onClick={runQuantico}
          >
            Esegui compattazione quantica
          </button>

          <ResultScreen
            title="Output quantico"
            variant="quantico"
            empty={!lastQuantico ? 'Nessun sacrificio registrato.' : null}
          >
            {lastQuantico ? (
              <>
                <p className="comp-result-line comp-result-line--highlight">
                  {lastQuantico.nome_input}
                  {' → '}
                  <strong>{lastQuantico.numero_unit}</strong>
                  {' '}
                  unità
                </p>
                {lastQuantico.oggetto_eliminato ? (
                  <p className="comp-result-line comp-result-line--warn">
                    Oggetto eliminato:
                    {' '}
                    {lastQuantico.oggetto_eliminato}
                  </p>
                ) : null}
                <ul className="comp-result-units">
                  {(lastQuantico.unita || []).map((u, i) => (
                    <li key={`q-${i}`}>
                      <span className="comp-result-unit-idx">[{u.indice_componente}]</span>
                      {u.colore_nome}
                    </li>
                  ))}
                </ul>
              </>
            ) : null}
          </ResultScreen>
        </section>
      </div>

      <section className="compattatore-stiva-deck">
        <div className="compattatore-stiva-deck-header">
          <h2 className="compattatore-stiva-title">Stiva componenti</h2>
          <span className="compattatore-stiva-sub">Coppie opposte · rischio annichilamento</span>
        </div>
        <StivaCompattatoreGrid
          stiva={data?.stiva}
          selectable={false}
        />
      </section>

      {onLogout ? (
        <footer className="compattatore-footer">
          <button type="button" className="comp-btn comp-btn--ghost" onClick={onLogout}>
            Logout console
          </button>
        </footer>
      ) : null}
    </div>
  );
}
