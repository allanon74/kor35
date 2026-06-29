import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { api } from '../api.js';

function SpectralBands({ bands }) {
  if (!bands?.length) {
    return <p className="sci-muted">Nessuna firma rilevabile.</p>;
  }
  return (
    <div className="sci-bands">
      {bands.map((b) => (
        <div key={b.gruppo} className="sci-band-row">
          <span className="sci-band-label">{b.gruppo}</span>
          <div className="sci-band-track">
            <div
              className="sci-band-fill"
              style={{ width: `${b.intensita}%`, background: b.colore }}
            />
          </div>
          <span className="sci-band-pct">{Math.round(b.intensita)}%</span>
        </div>
      ))}
    </div>
  );
}

function RiskBadge({ rischio }) {
  if (!rischio) return null;
  const cls = `sci-risk sci-risk--${rischio.livello || 'moderato'}`;
  return (
    <div className={cls}>
      <strong>{rischio.etichetta}</strong>
      <p>{rischio.descrizione}</p>
    </div>
  );
}

function CoerenzaMeter({ matrice }) {
  if (!matrice) return null;
  const pct = matrice.coerenza_cap
    ? Math.min(100, (matrice.coerenza / matrice.coerenza_cap) * 100)
    : 0;
  const caricaPct = matrice.carica_intervento_soglia
    ? Math.min(100, (matrice.carica_intervento / matrice.carica_intervento_soglia) * 100)
    : 0;
  return (
    <div className="sci-coerenza">
      <div className="sci-coerenza-head">
        <span>Coerenza di campo</span>
        <strong>
          {matrice.coerenza}
          /
          {matrice.coerenza_cap}
        </strong>
      </div>
      <div className="sci-coerenza-track">
        <div className="sci-coerenza-fill" style={{ width: `${pct}%` }} />
      </div>
      <div className="sci-coerenza-head sci-coerenza-head--sub">
        <span>
          Carica interventi
          {matrice.energia_esotici_per_tick != null ? (
            <>
              {' '}
              ·
              {' '}
              {matrice.energia_esotici_per_tick}
              {' '}
              energia/tick R/S/T
            </>
          ) : null}
        </span>
        <strong>
          {matrice.carica_intervento ?? 0}
          /
          {matrice.carica_intervento_soglia ?? 100}
        </strong>
      </div>
      <div className="sci-coerenza-track sci-coerenza-track--carica">
        <div
          className={`sci-coerenza-fill sci-coerenza-fill--carica${matrice.carica_pronta ? ' sci-coerenza-fill--ready' : ''}`}
          style={{ width: `${caricaPct}%` }}
        />
      </div>
      {matrice.risonanza_tripla ? (
        <span className="sci-risonanza-badge">Risonanza tripla attiva (+1 coerenza/tick)</span>
      ) : null}
      {!matrice.esotici_alimentano_coerenza ? (
        <p className="sci-muted">
          R/S/T sotto soglia energia (
          {matrice.energia_minima_richiesta ?? '—'}
          ) — nessun accumulo.
        </p>
      ) : (
        <p className="sci-muted">
          Più energia inviata ai nuclei esotici → coerenza e carica interventi più veloci.
        </p>
      )}
    </div>
  );
}

function MatricePanel({ matrice, busy, onFase }) {
  if (!matrice?.nuclei?.length) return null;
  return (
    <section className="sci-panel">
      <h2>Matrice R/S/T</h2>
      <p className="sci-muted">
        Imposta le fasi di risonanza. Il pilota mantiene i nuclei esotici online per alimentare la coerenza.
      </p>
      <div className="sci-matrice-grid">
        {matrice.nuclei.map((n) => (
          <div key={n.codice} className="sci-nucleo-card">
            <div className="sci-nucleo-head">
              <span className="sci-nucleo-code">{n.codice}</span>
              <span className="sci-nucleo-name">{n.nome}</span>
            </div>
            <div className="sci-nucleo-meta">
              <span className={n.online ? 'sci-nucleo-on' : 'sci-nucleo-off'}>
                {n.online ? `L${n.livello} · ${n.energia_per_tick ?? 0} en/tick` : 'OFF'}
              </span>
              <span className="sci-nucleo-fase">
                Fase
                {' '}
                {n.fase}
              </span>
            </div>
            <div className="sci-fase-controls">
              {[0, 1, 2].map((f) => (
                <button
                  key={f}
                  type="button"
                  className={`sci-fase-btn${n.fase === f ? ' sci-fase-btn--active' : ''}`}
                  disabled={busy}
                  onClick={() => onFase(n.codice, f)}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

function InterventiPanel({
  interventi,
  matrice,
  stivaRighe,
  busy,
  onIntervento,
}) {
  const [selectedByTipo, setSelectedByTipo] = useState({});

  const catalogo = interventi?.catalogo || [];
  if (!interventi?.abilitati) {
    return (
      <section className="sci-panel">
        <h2>Interventi attivi</h2>
        <p className="sci-muted">Interventi disabilitati in runtime staff.</p>
      </section>
    );
  }

  const mattoneOptions = (stivaRighe || []).filter((r) => (r.quantita || 0) > 0);

  const runIntervento = (tipo, nComp) => {
    const mid = selectedByTipo[tipo];
    const componenti = nComp > 0 && mid
      ? [{ mattone_id: mid, quantita: nComp }]
      : [];
    onIntervento(tipo, componenti);
  };

  return (
    <section className="sci-panel">
      <h2>Interventi attivi</h2>
      <p className="sci-muted">
        {interventi.interventi_rimanenti_volo ?? 0}
        {' '}
        interventi rimanenti questo volo · coerenza disponibile:
        {' '}
        {matrice?.coerenza ?? 0}
      </p>
      <div className="sci-interventi-list">
        {catalogo.map((iv) => (
          <div key={iv.tipo} className="sci-intervento-row">
            <div className="sci-intervento-info">
              <strong>{iv.label}</strong>
              <p>{iv.descrizione}</p>
              <span className="sci-intervento-cost">
                {iv.coerenza > 0 ? `${iv.coerenza} coerenza` : 'Gratuito'}
                {iv.componenti > 0 ? ` · ${iv.componenti} comp.` : ''}
              </span>
            </div>
            {iv.componenti > 0 && iv.disponibile ? (
              <select
                className="sci-intervento-select"
                value={selectedByTipo[iv.tipo] || ''}
                disabled={busy}
                onChange={(e) => setSelectedByTipo((p) => ({ ...p, [iv.tipo]: e.target.value }))}
              >
                <option value="">— componente —</option>
                {mattoneOptions.map((r) => (
                  <option key={r.mattone_id} value={r.mattone_id}>
                    {r.nome || r.indice_componente}
                    {' '}
                    (×
                    {r.quantita}
                    )
                  </option>
                ))}
              </select>
            ) : null}
            <button
              type="button"
              className="sci-btn sci-btn--primary sci-btn--compact"
              disabled={busy || !iv.disponibile}
              title={iv.motivo_indisponibile || ''}
              onClick={() => runIntervento(iv.tipo, iv.componenti)}
            >
              Esegui
            </button>
            {!iv.disponibile && iv.motivo_indisponibile ? (
              <span className="sci-intervento-blocked">{iv.motivo_indisponibile}</span>
            ) : null}
          </div>
        ))}
      </div>
    </section>
  );
}

export default function ScientificaScreen({ onLogout, navigazioneStatSigla = '0SC' }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedMattone, setSelectedMattone] = useState('');

  const refresh = useCallback(async () => {
    try {
      const res = await api.scientificaState();
      setData(res);
      setError('');
    } catch (e) {
      setError(e.message || 'Errore caricamento console scientifica.');
    }
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [refresh]);

  const spettro = data?.spettrografia;
  const scan = data?.scan_profondo || {};
  const matrice = data?.matrice;
  const interventi = data?.interventi;
  const stivaRighe = scan.stiva?.righe || [];

  const mattoneOptions = useMemo(
    () => stivaRighe.filter((r) => (r.quantita || 0) > 0),
    [stivaRighe],
  );

  const runScan = async () => {
    if (!selectedMattone) {
      setError('Seleziona un componente dalla stiva.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await api.scientificaScanProfondo([
        { mattone_id: selectedMattone, quantita: 1 },
      ]);
      setData(res);
      setSelectedMattone('');
    } catch (e) {
      setError(e.message || 'Scan profondo non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  const setFase = async (codice, fase) => {
    setBusy(true);
    setError('');
    try {
      const res = await api.scientificaFase(codice, fase);
      setData(res);
    } catch (e) {
      setError(e.message || 'Impostazione fase non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  const runIntervento = async (tipo, componenti) => {
    setBusy(true);
    setError('');
    try {
      const res = await api.scientificaIntervento(tipo, componenti);
      setData(res);
    } catch (e) {
      setError(e.message || 'Intervento non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="scientifica-console">
      <header className="scientifica-hud">
        <div className="scientifica-hud-brand">
          <span className="scientifica-hud-kicker">KOR-35 // LAB CAMPO</span>
          <h1 className="scientifica-hud-title">Console Scientifica</h1>
        </div>
        <div className="scientifica-hud-status">
          {!data?.abilitato ? (
            <span className="sci-pill sci-pill--off">Console disabilitata</span>
          ) : !data?.sessione_attiva ? (
            <span className="sci-pill sci-pill--off">Nessun volo attivo</span>
          ) : !data?.evento_pending ? (
            <span className="sci-pill sci-pill--idle">In attesa fenomeno</span>
          ) : (
            <span className="sci-pill sci-pill--ok">Fenomeno attivo</span>
          )}
          {data?.sessione_attiva ? (
            <span className="sci-defcon">DEFCON {data.defcon ?? '—'}</span>
          ) : null}
        </div>
      </header>

      {error ? <div className="scientifica-alert error">{error}</div> : null}

      {!data?.abilitato ? (
        <p className="sci-muted sci-panel">Abilita la console in staff → Console di bordo.</p>
      ) : null}

      {data?.abilitato && matrice ? (
        <section className="sci-panel sci-panel--coerenza">
          <CoerenzaMeter matrice={matrice} />
        </section>
      ) : null}

      {data?.abilitato && data?.sessione_attiva ? (
        <MatricePanel matrice={matrice} busy={busy} onFase={setFase} />
      ) : null}

      {data?.abilitato && !data?.sessione_attiva ? (
        <section className="sci-panel">
          <h2>Spettrografia</h2>
          <p className="sci-muted">
            Nessuna sessione di volo attiva. Avvia un viaggio dalla Console Navigazione per analizzare i fenomeni.
          </p>
        </section>
      ) : null}

      {data?.abilitato && data?.sessione_attiva && !spettro ? (
        <section className="sci-panel">
          <h2>Spettrografia</h2>
          <p className="sci-muted">
            Volo in corso — nessun evento randomico in attesa. Il laboratorio resta in standby.
          </p>
        </section>
      ) : null}

      {spettro ? (
        <div className="scientifica-grid">
          <section className="sci-panel">
            <h2>Spettrografia — {spettro.evento_nome}</h2>
            {spettro.evento_descrizione ? (
              <p className="sci-event-desc">{spettro.evento_descrizione}</p>
            ) : null}
            <h3 className="sci-subtitle">Firma spettrale</h3>
            <SpectralBands bands={spettro.firma_spettrale} />
            <h3 className="sci-subtitle">Delta navigazione</h3>
            <ul className="sci-delta-list">
              {(spettro.delta_navigazione || []).map((d) => (
                <li key={d}>{d}</li>
              ))}
            </ul>
            <RiskBadge rischio={spettro.rischio_ca} />
            {spettro.stato_soluzione ? (
              <p className="sci-soluzione">
                <strong>{spettro.stato_soluzione.etichetta}:</strong>
                {' '}
                {spettro.stato_soluzione.descrizione}
              </p>
            ) : null}
            {spettro.cronometro ? (
              <div className="sci-chrono">
                {spettro.cronometro.ticks_rimanenti != null ? (
                  <span>
                    Tick rimanenti:
                    {' '}
                    <strong>{spettro.cronometro.ticks_rimanenti}</strong>
                  </span>
                ) : null}
                {spettro.cronometro.secondi_fino_prossima_valutazione != null ? (
                  <span>
                    Prossima valutazione:
                    {' '}
                    <strong>
                      {spettro.cronometro.secondi_fino_prossima_valutazione}
                      s
                    </strong>
                  </span>
                ) : null}
              </div>
            ) : null}
          </section>

          <section className="sci-panel">
            <h2>Scan profondo</h2>
            <p className="sci-muted">
              Consuma 1 componente stiva per rivelare un indizio SP/ST nascosto (
              {scan.scans_rimanenti_volo ?? 0}
              {' '}
              rimanenti questo volo).
            </p>
            {spettro.scan_profondo?.indizio ? (
              <div className="sci-scan-result">
                <span className="sci-scan-kicker">Indizio acquisito</span>
                <p>{spettro.scan_profondo.indizio.messaggio}</p>
                {spettro.scan_profondo.indizio.sezione ? (
                  <span className="sci-scan-meta">
                    Sezione
                    {' '}
                    {String(spettro.scan_profondo.indizio.sezione).toUpperCase()}
                  </span>
                ) : null}
              </div>
            ) : null}
            {scan.disponibile ? (
              <>
                <label className="sci-select-wrap">
                  <span>Campione stiva</span>
                  <select
                    value={selectedMattone}
                    disabled={busy}
                    onChange={(e) => setSelectedMattone(e.target.value)}
                  >
                    <option value="">— seleziona —</option>
                    {mattoneOptions.map((r) => (
                      <option key={r.mattone_id} value={r.mattone_id}>
                        {r.nome || r.indice_componente}
                        {' '}
                        (×
                        {r.quantita}
                        )
                      </option>
                    ))}
                  </select>
                </label>
                <button
                  type="button"
                  className="sci-btn sci-btn--primary"
                  disabled={busy || mattoneOptions.length === 0}
                  onClick={runScan}
                >
                  Inietta campione — scan profondo
                </button>
              </>
            ) : (
              <p className="sci-muted">
                {!scan.abilitato
                  ? 'Scan profondo disabilitato in runtime staff.'
                  : spettro.scan_profondo?.eseguito_su_questo_evento
                    ? 'Scan già eseguito su questo fenomeno.'
                    : (scan.scans_rimanenti_volo ?? 0) <= 0
                      ? 'Limite scan per volo raggiunto.'
                      : 'Scan non disponibile.'}
              </p>
            )}
          </section>
        </div>
      ) : null}

      {data?.abilitato && data?.sessione_attiva && interventi ? (
        <InterventiPanel
          interventi={interventi}
          matrice={matrice}
          stivaRighe={stivaRighe}
          busy={busy}
          onIntervento={runIntervento}
        />
      ) : null}

      <footer className="scientifica-footer">
        <p className="sci-muted">
          Accesso:
          {' '}
          {navigazioneStatSigla}
          {' '}
          &gt; 0 · Spettrografia + matrice R/S/T
        </p>
        {onLogout ? (
          <button type="button" className="sci-btn sci-btn--ghost" onClick={onLogout}>
            Logout console
          </button>
        ) : null}
      </footer>
    </div>
  );
}
