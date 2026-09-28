import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { FileSignature, Loader2 } from 'lucide-react';
import {
  staffContrattiCreaModello,
  staffContrattiEliminaModello,
  staffContrattiGetModelli,
  staffContrattiGetRuntime,
  staffContrattiRuntimeAzione,
  staffContrattiSalvaModello,
} from '../../api';
import { anteprimaModello } from '../../lib/contrattoTesto';

const PRESET = [
  ['talento', 'Talento'],
  ['creatore', 'Creatore'],
  ['pubblicitario', 'Pubblicitario'],
  ['protettore', 'Protettore'],
  ['mercenario', 'Mercenario'],
  ['agente', 'Agente'],
];

const TIPI_PARAM = ['INTERO', 'DECIMALE', 'PERCENTUALE', 'TESTO', 'SCELTA', 'PERSONAGGIO'];

function vuoto(korpId) {
  return {
    id: '',
    nome: 'Nuovo contratto',
    attivo: true,
    korp: korpId || '',
    chiave_esclusivita: '',
    durata_modo: 'GIORNI',
    durata_giorni: 90,
    testo: '{{proponente}} propone a {{cliente}} fino al {{scadenza}}.\n{{parametri}}',
    parametri: [],
    effetti: [],
    voci: [],
  };
}

function campoEffetto(effetto, campo, onChange) {
  const valore = effetto.config?.[campo.key];
  if (campo.tipo === 'multi') {
    const scelti = Array.isArray(valore) ? valore : [];
    return (
      <div className="flex flex-wrap gap-2">
        {(campo.scelte || []).map((scelta) => (
          <label key={scelta} className="flex items-center gap-1 text-xs text-gray-300">
            <input
              type="checkbox"
              checked={scelti.includes(scelta)}
              onChange={(e) => {
                const next = e.target.checked ? [...scelti, scelta] : scelti.filter((x) => x !== scelta);
                onChange({ ...effetto.config, [campo.key]: next });
              }}
            />
            {scelta}
          </label>
        ))}
      </div>
    );
  }
  if (campo.tipo === 'scelta') {
    return (
      <select
        className="w-full rounded border border-gray-700 bg-gray-950 p-1 text-sm"
        value={valore || ''}
        onChange={(e) => onChange({ ...effetto.config, [campo.key]: e.target.value })}
      >
        <option value="">—</option>
        {(campo.scelte || []).map((scelta) => (
          <option key={scelta} value={scelta}>{scelta}</option>
        ))}
      </select>
    );
  }
  return (
    <input
      className="w-full rounded border border-gray-700 bg-gray-950 p-1 text-sm"
      value={valore ?? ''}
      placeholder="numero oppure {{param:chiave}}"
      onChange={(e) => onChange({ ...effetto.config, [campo.key]: e.target.value })}
    />
  );
}

export default function ContrattiManager({ onLogout }) {
  const [catalogo, setCatalogo] = useState(null);
  const [runtime, setRuntime] = useState([]);
  const [bozza, setBozza] = useState(null);
  const [errore, setErrore] = useState('');
  const [busy, setBusy] = useState(false);
  const [vista, setVista] = useState('modelli');

  const carica = useCallback(async () => {
    setErrore('');
    try {
      const [modelli, vivi] = await Promise.all([
        staffContrattiGetModelli(onLogout),
        staffContrattiGetRuntime(onLogout),
      ]);
      setCatalogo(modelli);
      setRuntime(Array.isArray(vivi) ? vivi : []);
    } catch (e) {
      setErrore(e.message || 'Catalogo contratti non disponibile.');
    }
  }, [onLogout]);

  useEffect(() => {
    carica();
  }, [carica]);

  const testoAnteprima = useMemo(() => {
    if (!bozza?.testo) return '';
    const korp = (catalogo?.korp || []).find((k) => String(k.id) === String(bozza.korp));
    return anteprimaModello({ ...bozza, korp_nome: korp?.nome || bozza.korp_nome || '' });
  }, [bozza, catalogo]);

  const effettiMeta = useMemo(() => {
    const mappa = {};
    (catalogo?.effetti || []).forEach((riga) => {
      mappa[riga.codice] = riga;
    });
    return mappa;
  }, [catalogo]);

  const salva = async () => {
    if (!bozza?.korp) {
      setErrore('Scegli la Korp.');
      return;
    }
    setBusy(true);
    setErrore('');
    try {
      const payload = { ...bozza, korp: bozza.korp };
      const salvato = bozza.id
        ? await staffContrattiSalvaModello(bozza.id, payload, onLogout)
        : await staffContrattiCreaModello(payload, onLogout);
      setBozza(salvato);
      await carica();
    } catch (e) {
      setErrore(e.message || 'Salvataggio non riuscito.');
    } finally {
      setBusy(false);
    }
  };

  const creaPreset = async (codice) => {
    if (!bozza?.korp && !catalogo?.korp?.[0]) {
      setErrore('Serve almeno una Korp.');
      return;
    }
    const korp = bozza?.korp || catalogo.korp[0].id;
    setBusy(true);
    setErrore('');
    try {
      const creato = await staffContrattiCreaModello({ preset: codice, korp }, onLogout);
      setBozza(creato);
      setVista('modelli');
      await carica();
    } catch (e) {
      setErrore(e.message || 'Preset non creato.');
    } finally {
      setBusy(false);
    }
  };

  const elimina = async () => {
    if (!bozza?.id) return;
    setBusy(true);
    try {
      await staffContrattiEliminaModello(bozza.id, onLogout);
      setBozza(null);
      await carica();
    } catch (e) {
      setErrore(e.message || 'Eliminazione non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  const azioneRuntime = async (payload) => {
    setBusy(true);
    setErrore('');
    try {
      await staffContrattiRuntimeAzione(payload, onLogout);
      await carica();
    } catch (e) {
      setErrore(e.message || 'Azione staff non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  if (!catalogo) {
    return (
      <div className="flex h-full items-center justify-center text-gray-400">
        {errore || <Loader2 className="animate-spin" />}
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto bg-gray-950 p-4 text-gray-100">
      <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <FileSignature className="text-amber-300" />
          <div>
            <h1 className="text-xl font-black">Contratti</h1>
            <p className="text-xs text-gray-400">
              I sei nomi sono preset. Un modello è nome, testo, parametri ed effetti. Gli slot si impostano in Carriere e KORP (base Korp, bonus carica). La statistica SCT (parametro SCT) è già in tabella: un’abilità o un oggetto la aumentano.
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <button type="button" className={`rounded px-3 py-1 text-sm ${vista === 'modelli' ? 'bg-amber-800' : 'bg-gray-800'}`} onClick={() => setVista('modelli')}>Modelli</button>
          <button type="button" className={`rounded px-3 py-1 text-sm ${vista === 'runtime' ? 'bg-amber-800' : 'bg-gray-800'}`} onClick={() => setVista('runtime')}>In corso</button>
        </div>
      </header>
      {errore ? <p className="mb-3 text-sm text-red-300">{errore}</p> : null}

      {vista === 'runtime' ? (
        <div className="space-y-3">
          {runtime.length === 0 ? <p className="text-sm text-gray-500">Nessun contratto.</p> : null}
          {runtime.map((c) => (
            <article key={c.id} className="rounded border border-gray-800 bg-gray-900 p-3 text-sm">
              <div className="flex flex-wrap justify-between gap-2">
                <strong>{c.nome}</strong>
                <span className="text-gray-400">{c.stato} · {c.proponente?.nome} → {c.cliente?.nome || '—'}</span>
              </div>
              <div className="mt-2 flex flex-wrap gap-2">
                {c.azioni?.attiva ? (
                  <button type="button" disabled={busy} className="rounded bg-indigo-800 px-2 py-1 text-xs" onClick={() => azioneRuntime({ azione: 'attiva', contratto_id: c.id })}>Attiva (staff)</button>
                ) : null}
                {(c.adempimenti || []).map((a) => (
                  <span key={a.id} className="flex items-center gap-1">
                    <span className="text-xs text-gray-400">{a.codice} {a.stato} {a.dovuto}</span>
                    {a.stato === 'IN_ATTESA' ? (
                      <button type="button" disabled={busy} className="rounded bg-emerald-900 px-2 py-1 text-xs" onClick={() => azioneRuntime({ azione: 'conferma', adempimento_id: a.id })}>Conferma</button>
                    ) : null}
                    {a.stato === 'DEBITO' ? (
                      <button type="button" disabled={busy} className="rounded bg-amber-900 px-2 py-1 text-xs" onClick={() => azioneRuntime({ azione: 'salda', adempimento_id: a.id })}>Salda</button>
                    ) : null}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="grid gap-4 lg:grid-cols-[280px_1fr]">
          <aside className="space-y-2">
            <div className="flex flex-wrap gap-1">
              {PRESET.map(([codice, label]) => (
                <button key={codice} type="button" disabled={busy} className="rounded bg-gray-800 px-2 py-1 text-xs" onClick={() => creaPreset(codice)}>{label}</button>
              ))}
            </div>
            <button
              type="button"
              className="w-full rounded bg-gray-800 px-2 py-1 text-sm"
              onClick={() => setBozza(vuoto(catalogo.korp?.[0]?.id))}
            >
              Modello vuoto
            </button>
            {(catalogo.modelli || []).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setBozza(m)}
                className={`block w-full rounded border px-2 py-2 text-left text-sm ${bozza?.id === m.id ? 'border-amber-600 bg-amber-950/40' : 'border-gray-800 bg-gray-900'}`}
              >
                {m.nome}
                <span className="block text-xs text-gray-500">{m.korp_nome} · {m.attivo ? 'attivo' : 'spento'}</span>
              </button>
            ))}
            <div className="pt-3 text-xs text-gray-500">
              {(catalogo.korp || []).map((k) => (
                <p key={k.id}>{k.nome}: {k.sottoscrive_contratti ? `sottoscrive, base ${k.slot_contratto_base}` : 'non sottoscrive'}</p>
              ))}
            </div>
          </aside>

          {bozza ? (
            <form
              className="space-y-3"
              onSubmit={(e) => {
                e.preventDefault();
                salva();
              }}
            >
              <input className="w-full rounded border border-gray-700 bg-gray-900 p-2" value={bozza.nome} onChange={(e) => setBozza({ ...bozza, nome: e.target.value })} />
              <div className="grid gap-2 sm:grid-cols-2">
                <select className="rounded border border-gray-700 bg-gray-900 p-2" value={bozza.korp ? String(bozza.korp) : ''} onChange={(e) => setBozza({ ...bozza, korp: Number(e.target.value) })}>
                  <option value="">Korp</option>
                  {(catalogo.korp || []).map((k) => (
                    <option key={k.id} value={k.id}>{k.nome}</option>
                  ))}
                </select>
                <input className="rounded border border-gray-700 bg-gray-900 p-2" placeholder="Chiave esclusività (vuota = nessuna)" value={bozza.chiave_esclusivita || ''} onChange={(e) => setBozza({ ...bozza, chiave_esclusivita: e.target.value })} />
                <select className="rounded border border-gray-700 bg-gray-900 p-2" value={bozza.durata_modo} onChange={(e) => setBozza({ ...bozza, durata_modo: e.target.value })}>
                  <option value="GIORNI">Giorni</option>
                  <option value="FINE_EVENTO">Fine evento</option>
                </select>
                <input type="number" className="rounded border border-gray-700 bg-gray-900 p-2" value={bozza.durata_giorni} onChange={(e) => setBozza({ ...bozza, durata_giorni: Number(e.target.value) })} />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!bozza.attivo} onChange={(e) => setBozza({ ...bozza, attivo: e.target.checked })} />
                Attivo
              </label>
              <textarea className="h-32 w-full rounded border border-gray-700 bg-gray-900 p-2 text-sm" value={bozza.testo || ''} onChange={(e) => setBozza({ ...bozza, testo: e.target.value })} />
              <div className="rounded border border-gray-800 bg-gray-900/70 p-3">
                <p className="mb-1 text-xs uppercase tracking-wide text-gray-500">Anteprima</p>
                <p className="whitespace-pre-wrap text-sm text-gray-200">{testoAnteprima}</p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold">Parametri</h2>
                  <button type="button" className="text-xs text-amber-300" onClick={() => setBozza({ ...bozza, parametri: [...(bozza.parametri || []), { chiave: '', etichetta: '', tipo: 'DECIMALE', chi_compila: 'STAFF', valore: '', vincoli: {} }] })}>Aggiungi</button>
                </div>
                {(bozza.parametri || []).map((p, index) => (
                  <div key={`${p.chiave}-${index}`} className="grid gap-1 rounded border border-gray-800 p-2 sm:grid-cols-5">
                    <input placeholder="chiave" className="rounded bg-gray-950 p-1 text-sm" value={p.chiave} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, chiave: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                    <input placeholder="etichetta" className="rounded bg-gray-950 p-1 text-sm" value={p.etichetta} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, etichetta: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                    <select className="rounded bg-gray-950 p-1 text-sm" value={p.tipo} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, tipo: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }}>
                      {TIPI_PARAM.map((t) => <option key={t}>{t}</option>)}
                    </select>
                    <select className="rounded bg-gray-950 p-1 text-sm" value={p.chi_compila} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, chi_compila: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }}>
                      <option value="STAFF">STAFF</option>
                      <option value="PROPONENTE">PROPONENTE</option>
                    </select>
                    <input placeholder="default" className="rounded bg-gray-950 p-1 text-sm" value={p.valore ?? ''} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, valore: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold">Effetti del modello</h2>
                  <select
                    className="rounded bg-gray-900 p-1 text-xs"
                    value=""
                    onChange={(e) => {
                      if (!e.target.value) return;
                      setBozza({ ...bozza, effetti: [...(bozza.effetti || []), { codice: e.target.value, config: {} }] });
                    }}
                  >
                    <option value="">Aggiungi effetto</option>
                    {(catalogo.effetti || []).map((r) => (
                      <option key={r.codice} value={r.codice}>{r.label}</option>
                    ))}
                  </select>
                </div>
                {(bozza.effetti || []).map((effetto, index) => {
                  const meta = effettiMeta[effetto.codice];
                  return (
                    <div key={`${effetto.codice}-${index}`} className="space-y-1 rounded border border-gray-800 p-2">
                      <div className="flex justify-between text-sm">
                        <strong>{meta?.label || effetto.codice}</strong>
                        <button type="button" className="text-xs text-red-300" onClick={() => setBozza({ ...bozza, effetti: bozza.effetti.filter((_, i) => i !== index) })}>Rimuovi</button>
                      </div>
                      <p className="text-xs text-gray-500">{meta?.descrizione}</p>
                      {(meta?.campi || []).map((campo) => (
                        <label key={campo.key} className="block text-xs text-gray-400">
                          {campo.key}
                          {campoEffetto(effetto, campo, (config) => {
                            const effetti = [...bozza.effetti];
                            effetti[index] = { ...effetto, config };
                            setBozza({ ...bozza, effetti });
                          })}
                        </label>
                      ))}
                    </div>
                  );
                })}
              </div>

              <div className="flex gap-2">
                <button type="submit" disabled={busy} className="rounded bg-amber-700 px-3 py-2 text-sm font-semibold disabled:opacity-50">Salva</button>
                {bozza.id ? (
                  <button type="button" disabled={busy} className="rounded bg-gray-800 px-3 py-2 text-sm" onClick={elimina}>Disattiva o elimina</button>
                ) : null}
              </div>
            </form>
          ) : (
            <p className="text-sm text-gray-500">Scegli un preset, un modello vuoto, oppure un modello esistente.</p>
          )}
        </div>
      )}
    </div>
  );
}
