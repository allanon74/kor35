import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { api } from '../api.js';
import { PREVIEW_SCIENTIFICA } from '../kioskPreview.js';
import { initialTab } from '../viewport.js';

const KIOSK_TABS = [
  ['spettro', 'Spettro'],
  ['scan', 'Scan'],
  ['matrice', 'Matrice'],
  ['interventi', 'Interventi'],
];

function FenomenoPicker({ fenomeni, selectedId, onSelect }) {
  if (!fenomeni || fenomeni.length < 2) return null;
  return (
    <div className="sci-event-picker" role="group" aria-label="Fenomeno da analizzare">
      {fenomeni.map((f) => (
        <button
          key={f.id}
          type="button"
          className={`sci-event-chip${f.id === selectedId ? ' is-active' : ''}`}
          onClick={() => onSelect(f.id)}
        >
          {f.nome}
        </button>
      ))}
    </div>
  );
}

function SoluzioneAcquisita({ indizio }) {
  if (!indizio) return null;
  const voci = Array.isArray(indizio.voci) && indizio.voci.length
    ? indizio.voci
    : (indizio.messaggio ? [indizio.messaggio] : []);
  if (!voci.length) return null;
  return (
    <div className="sci-scan-result">
      <span className="sci-scan-kicker">Soluzione acquisita</span>
      <ul className="sci-delta-list">
        {voci.map((voce) => <li key={voce}>{voce}</li>)}
      </ul>
    </div>
  );
}

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
  busy,
  compact = false,
  onIntervento,
}) {
  const catalogo = interventi?.catalogo || [];
  if (!interventi?.abilitati) {
    return (
      <section className="sci-panel">
        <h2>Interventi attivi</h2>
        <p className="sci-muted">Interventi disabilitati in runtime staff.</p>
      </section>
    );
  }

  return (
    <section className={`sci-panel${compact ? ' sci-interventi-kiosk' : ''}`}>
      {compact ? null : <h2>Interventi attivi</h2>}
      <p className="sci-muted sci-interventi-meta">
        {interventi.interventi_rimanenti_volo ?? 0}
        {' '}
        rimasti · coerenza
        {' '}
        {matrice?.coerenza ?? 0}
        {compact ? ' · il componente esce a caso dalla stiva' : ' · componente pescato a caso dalla stiva'}
      </p>
      <div className="sci-interventi-list">
        {catalogo.map((iv) => (
          <button
            key={iv.tipo}
            type="button"
            className="sci-btn sci-btn--primary sci-intervento-btn"
            disabled={busy || !iv.disponibile}
            title={iv.motivo_indisponibile || iv.descrizione || ''}
            onClick={() => onIntervento(iv.tipo, [])}
          >
            <span className="sci-intervento-btn-label">{iv.label}</span>
            <span className="sci-intervento-btn-cost">
              {iv.coerenza > 0 ? `${iv.coerenza} coerenza` : 'gratis'}
              {iv.componenti > 0 ? ` · ${iv.componenti}` : ''}
            </span>
          </button>
        ))}
      </div>
    </section>
  );
}

export default function ScientificaScreen({
  onLogout,
  onBack = null,
  navigazioneStatSigla = '0SC',
  compact = false,
  preview = false,
}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [selectedMattone, setSelectedMattone] = useState('');
  const [tab, setTab] = useState(() => initialTab(KIOSK_TABS.map(([id]) => id), 'spettro'));
  const [eventoId, setEventoId] = useState('');
  const eventoIdRef = useRef('');

  const refresh = useCallback(async () => {
    if (preview) {
      setData(PREVIEW_SCIENTIFICA);
      setError('');
      return;
    }
    try {
      const res = await api.scientificaState(eventoIdRef.current);
      setData(res);
      setError('');
      const ids = (res?.fenomeni || []).map((f) => f.id);
      const current = eventoIdRef.current;
      const next = ids.includes(current) ? current : (res?.evento_selezionato || ids[0] || '');
      if (next !== current) {
        eventoIdRef.current = next;
        setEventoId(next);
      }
    } catch (e) {
      setError(e.message || 'Errore caricamento console scientifica.');
    }
  }, [preview]);

  const selectEvento = (id) => {
    eventoIdRef.current = id;
    setEventoId(id);
    if (!preview) refresh();
  };

  useEffect(() => {
    refresh();
    if (preview) return undefined;
    const id = setInterval(refresh, 4000);
    return () => clearInterval(id);
  }, [preview, refresh]);

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
    if (preview) {
      setError('Anteprima layout: scan non inviato.');
      return;
    }
    if (!selectedMattone) {
      setError('Seleziona un componente dalla stiva.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await api.scientificaScanProfondo([
        { mattone_id: selectedMattone, quantita: 1 },
      ], eventoIdRef.current);
      setData(res);
      setSelectedMattone('');
    } catch (e) {
      setError(e.message || 'Scan profondo non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  const setFase = async (codice, fase) => {
    if (preview) return;
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
    if (preview) {
      setError('Anteprima layout: intervento non inviato.');
      return;
    }
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

  const show = (id) => !compact || tab === id;

  return (
    <div className={`scientifica-console${compact ? ' is-kiosk800' : ''}`}>
      <header className="scientifica-hud">
        <div className="scientifica-hud-brand">
          <span className="scientifica-hud-kicker">KOR-35 // LAB CAMPO</span>
          <h1 className="scientifica-hud-title">Console Scientifica</h1>
        </div>
        <div className="scientifica-hud-status">
          {data && !data.abilitato ? (
            <span className="sci-pill sci-pill--off">Console disabilitata</span>
          ) : !data ? (
            <span className="sci-pill sci-pill--off">{error ? 'Accesso negato' : '…'}</span>
          ) : !data.sessione_attiva ? (
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
        {compact && onBack ? (
          <button type="button" className="sci-btn sci-btn--ghost kiosk800-back" onClick={onBack}>
            Scelta
          </button>
        ) : null}
      </header>

      {compact ? (
        <nav className="kiosk800-tabs" aria-label="Sezioni scientifica">
          {KIOSK_TABS.map(([id, label]) => (
            <button
              key={id}
              type="button"
              className={`kiosk800-tab${tab === id ? ' is-active' : ''}`}
              onClick={() => setTab(id)}
            >
              {label}
            </button>
          ))}
        </nav>
      ) : null}

      {error ? <div className="scientifica-alert error">{error}</div> : null}

      {compact && data?.abilitato && matrice ? (
        <section className="sci-panel sci-panel--coerenza sci-coerenza-slim">
          <CoerenzaMeter matrice={matrice} />
        </section>
      ) : null}

      <div className={compact ? 'kiosk800-scroll' : undefined}>

      {data && !data.abilitato ? (
        <p className="sci-muted sci-panel">Abilita la console in staff → Console di bordo.</p>
      ) : null}

      {!compact && data?.abilitato && matrice ? (
        <section className="sci-panel sci-panel--coerenza">
          <CoerenzaMeter matrice={matrice} />
        </section>
      ) : null}

      {data?.abilitato && data?.sessione_attiva && show('matrice') ? (
        <MatricePanel matrice={matrice} busy={busy} onFase={setFase} />
      ) : null}

      {data?.abilitato && !data?.sessione_attiva && show('spettro') ? (
        <section className="sci-panel">
          <h2>Spettrografia</h2>
          <p className="sci-muted">
            Nessuna sessione di volo attiva. Avvia un viaggio dalla Console Navigazione per analizzare i fenomeni.
          </p>
        </section>
      ) : null}

      {data?.abilitato && data?.sessione_attiva && !spettro && show('spettro') ? (
        <section className="sci-panel">
          <h2>Spettrografia</h2>
          <p className="sci-muted">
            Volo in corso — nessun evento randomico in attesa. Il laboratorio resta in standby.
          </p>
        </section>
      ) : null}

      {spettro && (show('spettro') || show('scan')) ? (
        <div className="scientifica-grid">
          <section className="sci-panel" hidden={!show('spettro')}>
            <FenomenoPicker
              fenomeni={data?.fenomeni}
              selectedId={eventoId || data?.evento_selezionato}
              onSelect={selectEvento}
            />
            <h2>Spettrografia — {spettro.evento_nome}</h2>
            {spettro.evento_descrizione ? (
              <p className="sci-event-desc">{spettro.evento_descrizione}</p>
            ) : null}
            <h3 className="sci-subtitle">Firma spettrale</h3>
            <SpectralBands bands={spettro.firma_spettrale} />
            <h3 className="sci-subtitle">Sistemi da regolare</h3>
            {(spettro.indizi_sistemi || []).length ? (
              <ul className="sci-delta-list">
                {spettro.indizi_sistemi.map((row) => (
                  <li key={row.codice}>
                    <strong>{row.codice}</strong>
                    {row.nome ? ` — ${row.nome}` : ''}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="sci-muted">Nessun sistema da segnalare su questo fenomeno.</p>
            )}
            <p className="sci-muted">Lo spettro ne indica al massimo due. Livello e manovra escono dallo scan profondo.</p>
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

          <section className="sci-panel" hidden={!show('scan')}>
            <FenomenoPicker
              fenomeni={data?.fenomeni}
              selectedId={eventoId || data?.evento_selezionato}
              onSelect={selectEvento}
            />
            <h2>Scan profondo{spettro.evento_nome ? ` — ${spettro.evento_nome}` : ''}</h2>
            <p className="sci-muted">
              Consuma 1 componente stiva per rivelare la soluzione ST/SP di questo fenomeno (
              {scan.scans_rimanenti_volo ?? 0}
              {' '}
              rimanenti questo volo).
            </p>
            <SoluzioneAcquisita indizio={spettro.scan_profondo?.indizio} />
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

      {data?.abilitato && data?.sessione_attiva && interventi && show('interventi') ? (
        <InterventiPanel
          interventi={interventi}
          matrice={matrice}
          busy={busy}
          compact={compact}
          onIntervento={runIntervento}
        />
      ) : null}

      </div>

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
