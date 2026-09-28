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
import {
  StaffToolPageTitle,
  StaffToolShell,
  StaffToolSubnav,
  staffDangerBtnClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';

const STATO_LABEL = {
  IN_ATTESA: 'In attesa',
  STIPULATO: 'Stipulato',
  SCADUTO: 'Scaduto',
  RIFIUTATO: 'Rifiutato',
  RISOLTO: 'Risolto',
  ANNULLATO: 'Annullato',
};

const campoClass = 'min-h-11 w-full rounded-lg border border-gray-600 bg-gray-900 px-3 py-2 text-base sm:text-sm';

const PRESET = [
  ['talento', 'Talento'],
  ['creatore', 'Creatore'],
  ['pubblicitario', 'Pubblicitario'],
  ['protettore', 'Protettore'],
  ['mercenario', 'Mercenario'],
  ['agente', 'Agente'],
];

const TIPI_PARAM = ['INTERO', 'DECIMALE', 'PERCENTUALE', 'TESTO', 'SCELTA', 'PERSONAGGIO'];

function caricheDellaKorp(catalogo, korpId) {
  return (catalogo?.cariche || [])
    .filter((c) => (c.carriere_ids || []).some((id) => String(id) === String(korpId)))
    .slice()
    .sort((a, b) => (a.ordine || 0) - (b.ordine || 0) || String(a.nome).localeCompare(String(b.nome), 'it'));
}

function vuoto(korpId) {
  return {
    id: '',
    nome: 'Nuovo contratto',
    attivo: true,
    korp: korpId || '',
    chiave_esclusivita: '',
    prototipo: '',
    carica_minima: '',
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
        className={campoClass}
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
      className={campoClass}
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
  const [confermaId, setConfermaId] = useState('');

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
      if (payload.azione === 'elimina') setConfermaId('');
      await carica();
    } catch (e) {
      setErrore(e.message || 'Azione staff non riuscita.');
    } finally {
      setBusy(false);
    }
  };

  if (!catalogo) {
    return (
      <StaffToolShell className="flex h-full items-center justify-center">
        {errore ? <p className="text-sm text-red-300">{errore}</p> : <Loader2 className="animate-spin text-gray-400" />}
      </StaffToolShell>
    );
  }

  return (
    <StaffToolShell className="h-full space-y-4 overflow-y-auto overflow-x-hidden pb-8">
      <StaffToolPageTitle
        icon={<FileSignature size={22} />}
        title="Contratti"
        description="Modelli della Korp e contratti in corso. Gli slot si impostano in Carriere e KORP."
      />
      <StaffToolSubnav
        className="mt-0"
        tabs={[
          { id: 'modelli', label: 'Modelli' },
          { id: 'runtime', label: 'In corso' },
        ]}
        active={vista}
        onChange={(id) => {
          setVista(id);
          setConfermaId('');
        }}
      />
      {errore ? <p className="rounded-lg border border-red-800 bg-red-950/40 p-3 text-sm text-red-300">{errore}</p> : null}

      {vista === 'runtime' ? (
        <div className="space-y-3">
          {runtime.length === 0 ? <p className="text-sm text-gray-500">Nessun contratto.</p> : null}
          {runtime.map((c) => (
            <article key={c.id} className={`${staffPanelClass} space-y-3 text-sm`}>
              <div className="min-w-0">
                <h3 className="break-words text-base font-semibold">{c.nome}</h3>
                <p className="mt-1 text-gray-400">
                  {STATO_LABEL[c.stato] || c.stato}
                  {' · '}
                  {c.proponente?.nome || '—'}
                  {' → '}
                  {c.cliente?.nome || 'in attesa'}
                </p>
              </div>
              <div className="flex flex-col gap-2 sm:flex-row sm:flex-wrap">
                {c.azioni?.attiva ? (
                  <button type="button" disabled={busy} className={`${staffSecondaryBtnClass} min-h-11 justify-center`} onClick={() => azioneRuntime({ azione: 'attiva', contratto_id: c.id })}>Attiva</button>
                ) : null}
                {(c.adempimenti || []).map((a) => (
                  <div key={a.id} className="flex flex-col gap-2 rounded-lg border border-gray-700 p-2 sm:flex-row sm:items-center">
                    <span className="text-xs text-gray-400">{a.codice} {a.stato} {a.dovuto}</span>
                    {a.stato === 'IN_ATTESA' ? (
                      <button type="button" disabled={busy} className={`${staffSecondaryBtnClass} min-h-11 justify-center`} onClick={() => azioneRuntime({ azione: 'conferma', adempimento_id: a.id })}>Conferma</button>
                    ) : null}
                    {a.stato === 'DEBITO' ? (
                      <button type="button" disabled={busy} className={`${staffSecondaryBtnClass} min-h-11 justify-center`} onClick={() => azioneRuntime({ azione: 'salda', adempimento_id: a.id })}>Salda</button>
                    ) : null}
                  </div>
                ))}
                {confermaId === c.id ? (
                  <div className="flex w-full flex-col gap-2 sm:flex-row">
                    <button
                      type="button"
                      disabled={busy}
                      className={`${staffDangerBtnClass} min-h-11 flex-1 justify-center`}
                      onClick={() => azioneRuntime({ azione: 'elimina', contratto_id: c.id })}
                    >
                      Cancella definitivamente
                    </button>
                    <button type="button" className={`${staffSecondaryBtnClass} min-h-11 flex-1 justify-center`} onClick={() => setConfermaId('')}>
                      Annulla
                    </button>
                  </div>
                ) : (
                  <button type="button" disabled={busy} className={`${staffDangerBtnClass} min-h-11 justify-center`} onClick={() => setConfermaId(c.id)}>
                    Cancella
                  </button>
                )}
              </div>
              {confermaId === c.id ? (
                <p className="text-xs text-amber-200">Il contratto sparisce e lo slot del proponente si libera. I crediti già movimentati restano.</p>
              ) : null}
            </article>
          ))}
        </div>
      ) : (
        <div className="grid min-w-0 gap-4 lg:grid-cols-[280px_1fr]">
          <aside className={`${staffPanelClass} space-y-3`}>
            <div className="flex flex-wrap gap-2">
              {PRESET.map(([codice, label]) => (
                <button key={codice} type="button" disabled={busy} className={`${staffSecondaryBtnClass} min-h-11`} onClick={() => creaPreset(codice)}>Aggiungi {label}</button>
              ))}
            </div>
            <p className="text-xs text-gray-500">Ogni clic aggiunge un modello nuovo. Dello stesso tipo puoi averne più di uno, poi ne cambi nome e numeri.</p>
            <button
              type="button"
              className={`${staffSecondaryBtnClass} min-h-11 w-full justify-center`}
              onClick={() => setBozza(vuoto(catalogo.korp?.[0]?.id))}
            >
              Modello vuoto
            </button>
            {(catalogo.modelli || []).map((m) => (
              <button
                key={m.id}
                type="button"
                onClick={() => setBozza(m)}
                className={`block min-h-11 w-full rounded-lg border px-3 py-2 text-left text-sm ${bozza?.id === m.id ? 'border-indigo-500 bg-indigo-950/40' : 'border-gray-700 bg-gray-950'}`}
              >
                {m.nome}
                <span className="block text-xs text-gray-500">
                  {m.korp_nome}
                  {m.prototipo ? ` · ${m.prototipo}` : ''}
                  {m.carica_minima_nome ? ` · da ${m.carica_minima_nome} in su` : ' · tutte le cariche'}
                  {` · ${m.attivo ? 'attivo' : 'spento'}`}
                </span>
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
              className={`${staffPanelClass} min-w-0 space-y-4`}
              onSubmit={(e) => {
                e.preventDefault();
                salva();
              }}
            >
              <input className={campoClass} value={bozza.nome} onChange={(e) => setBozza({ ...bozza, nome: e.target.value })} aria-label="Nome modello" />
              <label className="block text-xs text-gray-400">
                Tipo
                <input
                  className={`${campoClass} mt-1`}
                  value={bozza.prototipo || ''}
                  placeholder="talento, creatore, oppure vuoto"
                  onChange={(e) => setBozza({ ...bozza, prototipo: e.target.value })}
                />
              </label>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
                <select className={campoClass} value={bozza.korp ? String(bozza.korp) : ''} onChange={(e) => {
                  const korp = Number(e.target.value);
                  const ammesse = caricheDellaKorp(catalogo, korp).map((c) => String(c.id));
                  const minima = ammesse.includes(String(bozza.carica_minima)) ? bozza.carica_minima : '';
                  setBozza({ ...bozza, korp, carica_minima: minima });
                }}>
                  <option value="">Korp</option>
                  {(catalogo.korp || []).map((k) => (
                    <option key={k.id} value={k.id}>{k.nome}</option>
                  ))}
                </select>
                <label className="block text-xs text-gray-400">
                  Carica minima
                  <select
                    className={`${campoClass} mt-1`}
                    value={bozza.carica_minima ? String(bozza.carica_minima) : ''}
                    onChange={(e) => setBozza({ ...bozza, carica_minima: e.target.value ? Number(e.target.value) : '' })}
                  >
                    <option value="">Tutte le cariche</option>
                    {caricheDellaKorp(catalogo, bozza.korp).map((c) => (
                      <option key={c.id} value={c.id}>{c.nome} (ordine {c.ordine ?? 0})</option>
                    ))}
                  </select>
                </label>
                <p className="rounded border border-gray-800 bg-gray-900 p-2 text-xs text-gray-400 sm:col-span-2">
                  Il cliente può stipularne uno per questo modello. Un altro modello, anche dello stesso tipo, è un contratto diverso. La carica minima usa il campo Ordine: conta da quel numero in su. Senza selezione, vale per ogni membro della Korp.
                </p>
                <select className={campoClass} value={bozza.durata_modo} onChange={(e) => setBozza({ ...bozza, durata_modo: e.target.value })}>
                  <option value="GIORNI">Giorni</option>
                  <option value="FINE_EVENTO">Fine evento</option>
                </select>
                <input type="number" className={campoClass} value={bozza.durata_giorni} onChange={(e) => setBozza({ ...bozza, durata_giorni: Number(e.target.value) })} />
              </div>
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={!!bozza.attivo} onChange={(e) => setBozza({ ...bozza, attivo: e.target.checked })} />
                Attivo
              </label>
              <textarea className={`${campoClass} h-40`} value={bozza.testo || ''} onChange={(e) => setBozza({ ...bozza, testo: e.target.value })} />
              <div className="rounded border border-gray-800 bg-gray-900/70 p-3">
                <p className="mb-1 text-xs uppercase tracking-wide text-gray-500">Anteprima</p>
                <p className="whitespace-pre-wrap text-sm text-gray-200">{testoAnteprima}</p>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <h2 className="font-semibold">Parametri</h2>
                  <button type="button" className={staffSecondaryBtnClass} onClick={() => setBozza({ ...bozza, parametri: [...(bozza.parametri || []), { chiave: '', etichetta: '', tipo: 'DECIMALE', chi_compila: 'STAFF', valore: '', vincoli: {} }] })}>Aggiungi</button>
                </div>
                {(bozza.parametri || []).map((p, index) => (
                  <div key={`${p.chiave}-${index}`} className="grid grid-cols-1 gap-2 rounded-lg border border-gray-700 p-3 sm:grid-cols-2">
                    <input placeholder="chiave" aria-label="Chiave parametro" className={campoClass} value={p.chiave} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, chiave: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                    <input placeholder="etichetta" aria-label="Etichetta parametro" className={campoClass} value={p.etichetta} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, etichetta: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                    <select aria-label="Tipo parametro" className={campoClass} value={p.tipo} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, tipo: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }}>
                      {TIPI_PARAM.map((t) => <option key={t}>{t}</option>)}
                    </select>
                    <select aria-label="Chi compila" className={campoClass} value={p.chi_compila} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, chi_compila: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }}>
                      <option value="STAFF">STAFF</option>
                      <option value="PROPONENTE">PROPONENTE</option>
                    </select>
                    <input placeholder="valore" aria-label="Valore parametro" className={`${campoClass} sm:col-span-2`} value={p.valore ?? ''} onChange={(e) => {
                      const parametri = [...bozza.parametri];
                      parametri[index] = { ...p, valore: e.target.value };
                      setBozza({ ...bozza, parametri });
                    }} />
                  </div>
                ))}
              </div>

              <div className="space-y-2">
                <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
                  <h2 className="font-semibold">Effetti del modello</h2>
                  <select
                    className={campoClass}
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
                        <button type="button" className="min-h-11 px-2 text-sm text-red-300" onClick={() => setBozza({ ...bozza, effetti: bozza.effetti.filter((_, i) => i !== index) })}>Rimuovi</button>
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

              <div className="flex flex-col gap-2 sm:flex-row">
                <button type="submit" disabled={busy} className={`${staffPrimaryBtnClass} min-h-11 flex-1 justify-center disabled:opacity-50`}>Salva</button>
                {bozza.id ? (
                  <button type="button" disabled={busy} className={`${staffSecondaryBtnClass} min-h-11 flex-1 justify-center`} onClick={elimina}>Disattiva o elimina</button>
                ) : null}
              </div>
            </form>
          ) : (
            <p className="text-sm text-gray-500">Scegli un preset, un modello vuoto, oppure un modello esistente.</p>
          )}
        </div>
      )}
    </StaffToolShell>
  );
}
