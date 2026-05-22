import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Trash2, Sparkles, ChevronRight } from 'lucide-react';
import RichTextEditor from '../RichTextEditor';
import {
  listCreazioneGuidataFlussi,
  getCreazioneGuidataFlusso,
  createCreazioneGuidataFlusso,
  updateCreazioneGuidataFlusso,
  creaSandboxCreazioneGuidataFlusso,
  pubblicaCreazioneGuidataSandbox,
  getCreazioneGuidataImpostazioni,
  patchCreazioneGuidataImpostazioni,
  deleteCreazioneGuidataFlusso,
  createCreazioneGuidataPasso,
  updateCreazioneGuidataPasso,
  deleteCreazioneGuidataPasso,
  createCreazioneGuidataScelta,
  updateCreazioneGuidataScelta,
  deleteCreazioneGuidataScelta,
  staffGetEre,
  staffGetAbilitaListAll,
} from '../../api';
import AbilitaMultiPicker from './AbilitaMultiPicker';

const TIPO_AZIONE_OPTIONS = [
  { value: 'naviga', label: 'Naviga (passo successivo)' },
  { value: 'imposta_campo', label: 'Imposta campo personaggio' },
  { value: 'aggiungi_abilita', label: 'Aggiungi abilità suggerite' },
  { value: 'combo', label: 'Combinata (campo + abilità + navigazione)' },
  { value: 'fine', label: 'Fine percorso' },
];

const PRESENTAZIONE_OPTIONS = [
  { value: 'pulsanti', label: 'Pulsanti' },
  { value: 'si_no', label: 'Sì / No' },
  { value: 'radio', label: 'Radio (scelta unica)' },
  { value: 'radio_abilita', label: 'Radio abilità' },
];

const REWIND_OPTIONS = [
  { value: 'ramo', label: 'Ramo (torna indietro nel percorso)' },
  { value: 'toggle', label: 'Toggle (sì/no: solo cambia abilità)' },
];

const CAMPO_OPTIONS = [
  { value: 'era', label: 'Era' },
  { value: 'prefettura', label: 'Prefettura' },
  { value: 'prefettura_esterna', label: 'Prefettura esterna' },
  { value: 'tipologia', label: 'Tipologia personaggio' },
];

function parsePayloadJson(raw) {
  if (!raw || !String(raw).trim()) return {};
  return JSON.parse(String(raw));
}

export default function CreazioneGuidataStaffManager({ onLogout }) {
  const [flussi, setFlussi] = useState([]);
  const [selectedFlussoId, setSelectedFlussoId] = useState(null);
  const [flussoDetail, setFlussoDetail] = useState(null);
  const [selectedPassoId, setSelectedPassoId] = useState(null);
  const [ere, setEre] = useState([]);
  const [abilitaOptions, setAbilitaOptions] = useState([]);
  const [status, setStatus] = useState('');
  const [loading, setLoading] = useState(true);

  const [flussoForm, setFlussoForm] = useState({
    slug: '',
    titolo: '',
    attivo: false,
    modalita_test: false,
    flusso_produzione: null,
    passo_iniziale: null,
  });
  const [sandboxBusy, setSandboxBusy] = useState(false);
  const [apertaGiocatori, setApertaGiocatori] = useState(false);
  const [impostazioniLoading, setImpostazioniLoading] = useState(true);
  const [passoForm, setPassoForm] = useState({
    slug: '',
    titolo: '',
    contenuto: '',
    ordine: 0,
    opzioni_ui: {
      presentazione: 'pulsanti',
      gruppo_id: '',
      modalita_rewind: 'ramo',
      widget_fondo: null,
    },
  });
  const [sceltaForm, setSceltaForm] = useState({
    etichetta: '',
    descrizione: '',
    ordine: 0,
    tipo_azione: 'naviga',
    passo_destinazione: null,
    payloadJson: '{}',
    payloadField: 'era',
    payloadSyncId: '',
    payloadAbilitaSyncIds: [],
    gruppoId: '',
    modalitaRewind: '',
  });

  const loadFlussi = useCallback(async () => {
    setLoading(true);
    try {
      const data = await listCreazioneGuidataFlussi(onLogout);
      setFlussi(Array.isArray(data) ? data : (data?.results || []));
    } catch (e) {
      setStatus(e?.message || 'Errore caricamento flussi');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  const loadFlussoDetail = useCallback(async (id) => {
    if (!id) {
      setFlussoDetail(null);
      return;
    }
    try {
      const data = await getCreazioneGuidataFlusso(id, onLogout);
      setFlussoDetail(data);
      setFlussoForm({
        slug: data.slug || '',
        titolo: data.titolo || '',
        attivo: !!data.attivo,
        modalita_test: !!data.modalita_test,
        flusso_produzione: data.flusso_produzione || null,
        passo_iniziale: data.passo_iniziale || null,
      });
    } catch (e) {
      setStatus(e?.message || 'Errore caricamento flusso');
    }
  }, [onLogout]);

  useEffect(() => {
    setImpostazioniLoading(true);
    getCreazioneGuidataImpostazioni(onLogout)
      .then((d) => setApertaGiocatori(!!d?.aperta_giocatori))
      .catch(() => setApertaGiocatori(false))
      .finally(() => setImpostazioniLoading(false));
    loadFlussi();
    staffGetEre(onLogout).then((d) => setEre(Array.isArray(d) ? d : [])).catch(() => {});
    staffGetAbilitaListAll(onLogout)
      .then((rows) => setAbilitaOptions(Array.isArray(rows) ? rows : []))
      .catch(() => setAbilitaOptions([]));
  }, [loadFlussi, onLogout]);

  useEffect(() => {
    loadFlussoDetail(selectedFlussoId);
  }, [selectedFlussoId, loadFlussoDetail]);

  const passi = useMemo(() => {
    const list = flussoDetail?.passi || [];
    return [...list].sort((a, b) => (a.ordine || 0) - (b.ordine || 0));
  }, [flussoDetail]);

  const selectedPasso = useMemo(
    () => passi.find((p) => p.id === selectedPassoId) || null,
    [passi, selectedPassoId],
  );

  useEffect(() => {
    if (selectedPasso) {
      const oui = selectedPasso.opzioni_ui && typeof selectedPasso.opzioni_ui === 'object'
        ? selectedPasso.opzioni_ui
        : {};
      setPassoForm({
        slug: selectedPasso.slug || '',
        titolo: selectedPasso.titolo || '',
        contenuto: selectedPasso.contenuto || '',
        ordine: selectedPasso.ordine || 0,
        opzioni_ui: {
          presentazione: oui.presentazione || 'pulsanti',
          gruppo_id: oui.gruppo_id || '',
          modalita_rewind: oui.modalita_rewind || 'ramo',
          widget_fondo: oui.widget_fondo || null,
        },
      });
    }
  }, [selectedPasso]);

  const prefettureFlat = useMemo(
    () => ere.flatMap((e) => (e.prefetture || []).map((p) => ({ ...p, era_nome: e.nome }))),
    [ere],
  );

  const buildPayloadFromForm = () => {
    const tipo = sceltaForm.tipo_azione;
    const base = {};
    if (sceltaForm.gruppoId) base.gruppo_id = sceltaForm.gruppoId;
    if (sceltaForm.modalitaRewind) base.modalita_rewind = sceltaForm.modalitaRewind;

    const abilitaIds = (sceltaForm.payloadAbilitaSyncIds || [])
      .map((s) => String(s).trim())
      .filter(Boolean);

    if (tipo === 'imposta_campo') {
      if (sceltaForm.payloadField === 'prefettura_esterna') {
        return { ...base, field: 'prefettura_esterna', value: true };
      }
      return { ...base, field: sceltaForm.payloadField, sync_id: sceltaForm.payloadSyncId || null };
    }
    if (tipo === 'aggiungi_abilita') {
      return { ...base, abilita_sync_ids: abilitaIds };
    }
    if (tipo === 'combo') {
      const combo = { ...base };
      if (abilitaIds.length) combo.abilita_sync_ids = abilitaIds;
      if (sceltaForm.payloadField && sceltaForm.payloadField !== 'prefettura_esterna') {
        combo.field = sceltaForm.payloadField;
        combo.sync_id = sceltaForm.payloadSyncId || null;
      } else if (sceltaForm.payloadField === 'prefettura_esterna') {
        combo.field = 'prefettura_esterna';
        combo.value = true;
      }
      try {
        const extra = parsePayloadJson(sceltaForm.payloadJson);
        Object.assign(combo, extra);
      } catch {
        /* ignore */
      }
      return combo;
    }
    try {
      return { ...base, ...parsePayloadJson(sceltaForm.payloadJson) };
    } catch {
      return base;
    }
  };

  const handleCreaSandbox = async () => {
    if (!selectedFlussoId || flussoForm.modalita_test) return;
    if (
      !window.confirm(
        'Crea o aggiorna la sandbox test clonando lo stato attuale della produzione. Le modifiche in test non toccano i giocatori finché non pubblichi.',
      )
    ) {
      return;
    }
    setSandboxBusy(true);
    try {
      const sandbox = await creaSandboxCreazioneGuidataFlusso(selectedFlussoId, onLogout);
      setStatus('Sandbox test pronta. Modifica il flusso test, poi usa Pubblica su produzione.');
      await loadFlussi();
      if (sandbox?.id) {
        setSelectedFlussoId(sandbox.id);
        await loadFlussoDetail(sandbox.id);
      }
    } catch (e) {
      setStatus(e?.message || 'Errore creazione sandbox');
    } finally {
      setSandboxBusy(false);
    }
  };

  const handlePubblicaSandbox = async () => {
    if (!selectedFlussoId || !flussoForm.modalita_test || !flussoForm.flusso_produzione) return;
    if (
      !window.confirm(
        'Pubblicare le modifiche della sandbox sul flusso di PRODUZIONE? I giocatori vedranno il nuovo percorso al prossimo utilizzo.',
      )
    ) {
      return;
    }
    setSandboxBusy(true);
    try {
      await pubblicaCreazioneGuidataSandbox(selectedFlussoId, onLogout);
      setStatus('Pubblicato su produzione.');
      await loadFlussi();
      if (flussoForm.flusso_produzione) {
        setSelectedFlussoId(flussoForm.flusso_produzione);
        await loadFlussoDetail(flussoForm.flusso_produzione);
      }
    } catch (e) {
      setStatus(e?.message || 'Errore pubblicazione');
    } finally {
      setSandboxBusy(false);
    }
  };

  const saveFlusso = async () => {
    try {
      let flussoId = selectedFlussoId;
      if (flussoId) {
        await updateCreazioneGuidataFlusso(flussoId, flussoForm, onLogout);
      } else {
        const created = await createCreazioneGuidataFlusso(flussoForm, onLogout);
        flussoId = created.id;
        setSelectedFlussoId(flussoId);
      }
      setStatus('Flusso salvato.');
      await loadFlussi();
      await loadFlussoDetail(flussoId);
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio flusso');
    }
  };

  const savePasso = async () => {
    if (!selectedFlussoId) return;
    try {
      const body = { ...passoForm, flusso: selectedFlussoId };
      if (selectedPassoId) {
        await updateCreazioneGuidataPasso(selectedPassoId, body, onLogout);
      } else {
        const created = await createCreazioneGuidataPasso(body, onLogout);
        setSelectedPassoId(created.id);
      }
      setStatus('Passo salvato.');
      await loadFlussoDetail(selectedFlussoId);
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio passo');
    }
  };

  const saveScelta = async () => {
    if (!selectedPassoId) return;
    try {
      const payload = buildPayloadFromForm();
      const body = {
        passo: selectedPassoId,
        etichetta: sceltaForm.etichetta,
        descrizione: sceltaForm.descrizione,
        ordine: sceltaForm.ordine,
        tipo_azione: sceltaForm.tipo_azione,
        passo_destinazione: sceltaForm.passo_destinazione || null,
        payload,
      };
      if (sceltaForm.id) {
        await updateCreazioneGuidataScelta(sceltaForm.id, body, onLogout);
      } else {
        await createCreazioneGuidataScelta(body, onLogout);
      }
      setSceltaForm((f) => ({
        ...f,
        id: null,
        etichetta: '',
        descrizione: '',
        payloadAbilitaSyncIds: [],
      }));
      setStatus('Scelta salvata.');
      await loadFlussoDetail(selectedFlussoId);
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio scelta');
    }
  };

  const editScelta = (s) => {
    setSceltaForm({
      id: s.id,
      etichetta: s.etichetta,
      descrizione: s.descrizione || '',
      ordine: s.ordine || 0,
      tipo_azione: s.tipo_azione,
      passo_destinazione: s.passo_destinazione,
      payloadJson: JSON.stringify(s.payload || {}, null, 2),
      payloadField: s.payload?.field || 'era',
      payloadSyncId: s.payload?.sync_id || '',
      payloadAbilitaSyncIds: (s.payload?.abilita_sync_ids || []).map(String),
      gruppoId: s.payload?.gruppo_id || '',
      modalitaRewind: s.payload?.modalita_rewind || '',
    });
  };

  const updateOpzioniUi = (patch) => {
    setPassoForm((f) => ({
      ...f,
      opzioni_ui: { ...(f.opzioni_ui || {}), ...patch },
    }));
  };

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100 p-4 overflow-hidden">
      <div className="flex items-center gap-2 mb-4 shrink-0">
        <Sparkles className="text-violet-400" />
        <h2 className="text-xl font-bold">Creazione guidata personaggio</h2>
      </div>

      <div className="mb-4 rounded-xl border border-gray-600 bg-gray-800/80 p-3 flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-sm font-bold text-gray-100">Pulsante per i giocatori</p>
          <p className="text-xs text-gray-400 max-w-xl">
            Se disattivo, i giocatori normali non vedono «Creazione guidata» in StartPage. Staff e master
            possono comunque aprire la sandbox test dal wizard (flag Flusso test).
          </p>
        </div>
        <label className="flex items-center gap-2 text-sm shrink-0 cursor-pointer">
          <input
            type="checkbox"
            disabled={impostazioniLoading}
            checked={apertaGiocatori}
            onChange={async (e) => {
              const next = e.target.checked;
              setApertaGiocatori(next);
              try {
                await patchCreazioneGuidataImpostazioni(next, onLogout);
                setStatus(
                  next
                    ? 'Creazione guidata visibile ai giocatori.'
                    : 'Creazione guidata nascosta ai giocatori (solo staff/test).',
                );
              } catch (err) {
                setApertaGiocatori(!next);
                setStatus(err?.message || 'Errore salvataggio impostazione');
              }
            }}
            className="rounded"
          />
          <span className={apertaGiocatori ? 'text-emerald-300' : 'text-amber-300'}>
            {apertaGiocatori ? 'Visibile ai giocatori' : 'Nascosta ai giocatori'}
          </span>
        </label>
      </div>

      {status ? <p className="text-sm text-amber-200 mb-2">{status}</p> : null}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
        <div className="border border-gray-700 rounded-xl p-3 overflow-y-auto space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold uppercase text-gray-400">Flussi</h3>
            <button
              type="button"
              className="p-1 rounded bg-violet-800 hover:bg-violet-700"
              onClick={() => {
                setSelectedFlussoId(null);
                setFlussoDetail(null);
                setFlussoForm({
                  slug: '',
                  titolo: '',
                  attivo: false,
                  modalita_test: false,
                  flusso_produzione: null,
                  passo_iniziale: null,
                });
              }}
            >
              <Plus size={16} />
            </button>
          </div>
          {loading ? <p className="text-sm text-gray-500">Caricamento...</p> : null}
          {flussi.map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => {
                setSelectedFlussoId(f.id);
                setSelectedPassoId(null);
              }}
              className={`w-full text-left px-3 py-2 rounded border ${
                selectedFlussoId === f.id ? 'border-violet-500 bg-violet-950/40' : 'border-gray-700 bg-gray-800'
              }`}
            >
              <span className="font-semibold block">{f.titolo}</span>
              <span className="text-xs text-gray-500">
                {f.slug}
                {f.attivo ? ' · attivo' : ''}
                {f.modalita_test ? ' · sandbox' : ' · produzione'}
                {f.sandbox_modifiche_pending ? ' · da pubblicare' : ''}
              </span>
            </button>
          ))}

          <div className="pt-3 border-t border-gray-700 space-y-2">
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
              placeholder="slug"
              value={flussoForm.slug}
              onChange={(e) => setFlussoForm({ ...flussoForm, slug: e.target.value })}
            />
            <input
              className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
              placeholder="Titolo"
              value={flussoForm.titolo}
              onChange={(e) => setFlussoForm({ ...flussoForm, titolo: e.target.value })}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!flussoForm.attivo}
                onChange={(e) => setFlussoForm({ ...flussoForm, attivo: e.target.checked })}
              />
              Attivo
            </label>
            {!flussoForm.modalita_test ? (
              <div className="rounded-lg border border-amber-700/50 bg-amber-950/20 p-2 space-y-2 text-xs text-amber-100/90">
                <p>
                  <strong>Produzione</strong> — visibile ai giocatori quando è attivo. Modifica la sandbox test e
                  pubblica quando sei pronto.
                </p>
                {flussoDetail?.sandbox_modifiche_pending ? (
                  <p className="text-amber-300 font-semibold">Sandbox con modifiche non ancora pubblicate.</p>
                ) : null}
                <button
                  type="button"
                  disabled={sandboxBusy || !selectedFlussoId}
                  onClick={handleCreaSandbox}
                  className="w-full py-1.5 rounded bg-amber-800 hover:bg-amber-700 text-sm font-bold disabled:opacity-50"
                >
                  {flussoDetail?.sandbox_test_id ? 'Aggiorna sandbox da produzione' : 'Crea sandbox test'}
                </button>
                {flussoDetail?.sandbox_test_id ? (
                  <button
                    type="button"
                    disabled={sandboxBusy}
                    onClick={() => {
                      setSelectedFlussoId(flussoDetail.sandbox_test_id);
                      loadFlussoDetail(flussoDetail.sandbox_test_id);
                    }}
                    className="w-full py-1.5 rounded bg-gray-700 hover:bg-gray-600 text-sm"
                  >
                    Apri sandbox test
                  </button>
                ) : null}
              </div>
            ) : (
              <div className="rounded-lg border border-violet-700/50 bg-violet-950/20 p-2 space-y-2 text-xs text-violet-100/90">
                <p>
                  <strong>Sandbox test</strong>
                  {flussoDetail?.flusso_produzione_titolo
                    ? ` → collegata a «${flussoDetail.flusso_produzione_titolo}»`
                    : ''}
                  . I giocatori non vedono questo flusso finché non pubblichi.
                </p>
                {flussoForm.flusso_produzione ? (
                  <button
                    type="button"
                    disabled={sandboxBusy}
                    onClick={handlePubblicaSandbox}
                    className="w-full py-1.5 rounded bg-emerald-800 hover:bg-emerald-700 text-sm font-bold disabled:opacity-50"
                  >
                    Pubblica su produzione
                  </button>
                ) : (
                  <p className="text-rose-300">Sandbox scollegata: usa «Crea sandbox» dal flusso di produzione.</p>
                )}
              </div>
            )}
            <select
              className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
              value={flussoForm.passo_iniziale || ''}
              onChange={(e) => setFlussoForm({ ...flussoForm, passo_iniziale: e.target.value ? Number(e.target.value) : null })}
            >
              <option value="">Passo iniziale...</option>
              {passi.map((p) => (
                <option key={p.id} value={p.id}>{p.titolo} ({p.slug})</option>
              ))}
            </select>
            <button type="button" onClick={saveFlusso} className="w-full py-2 rounded bg-violet-700 hover:bg-violet-600 text-sm font-bold">
              Salva flusso
            </button>
            {selectedFlussoId ? (
              <button
                type="button"
                className="w-full py-2 rounded bg-red-900/50 text-red-200 text-sm flex items-center justify-center gap-1"
                onClick={async () => {
                  if (!window.confirm('Eliminare il flusso e tutti i passi?')) return;
                  await deleteCreazioneGuidataFlusso(selectedFlussoId, onLogout);
                  setSelectedFlussoId(null);
                  loadFlussi();
                }}
              >
                <Trash2 size={14} /> Elimina flusso
              </button>
            ) : null}
          </div>
        </div>

        <div className="border border-gray-700 rounded-xl p-3 overflow-y-auto space-y-2">
          <div className="flex justify-between items-center">
            <h3 className="text-sm font-bold uppercase text-gray-400">Passi</h3>
            {selectedFlussoId ? (
              <button
                type="button"
                className="p-1 rounded bg-gray-700"
                onClick={() => {
                  setSelectedPassoId(null);
                  setPassoForm({ slug: '', titolo: '', contenuto: '', ordine: passi.length });
                }}
              >
                <Plus size={16} />
              </button>
            ) : null}
          </div>
          {!selectedFlussoId ? <p className="text-sm text-gray-500">Seleziona un flusso</p> : null}
          {passi.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => setSelectedPassoId(p.id)}
              className={`w-full text-left px-3 py-2 rounded border flex items-center justify-between ${
                selectedPassoId === p.id ? 'border-indigo-500 bg-indigo-950/30' : 'border-gray-700'
              }`}
            >
              <span>{p.titolo}</span>
              <ChevronRight size={14} className="text-gray-500" />
            </button>
          ))}

          {selectedFlussoId ? (
            <div className="pt-3 border-t border-gray-700 space-y-2">
              <input className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" placeholder="slug passo" value={passoForm.slug} onChange={(e) => setPassoForm({ ...passoForm, slug: e.target.value })} />
              <input className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" placeholder="Titolo passo" value={passoForm.titolo} onChange={(e) => setPassoForm({ ...passoForm, titolo: e.target.value })} />
              <input type="number" className="w-24 bg-gray-800 border border-gray-600 rounded p-2 text-sm" value={passoForm.ordine} onChange={(e) => setPassoForm({ ...passoForm, ordine: parseInt(e.target.value || '0', 10) })} />
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                value={passoForm.opzioni_ui?.presentazione || 'pulsanti'}
                onChange={(e) => updateOpzioniUi({ presentazione: e.target.value })}
              >
                {PRESENTAZIONE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <input
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                placeholder="gruppo_id passo (es. talenti_combat)"
                value={passoForm.opzioni_ui?.gruppo_id || ''}
                onChange={(e) => updateOpzioniUi({ gruppo_id: e.target.value })}
              />
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                value={passoForm.opzioni_ui?.modalita_rewind || 'ramo'}
                onChange={(e) => updateOpzioniUi({ modalita_rewind: e.target.value })}
              >
                {REWIND_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <label className="flex items-center gap-2 text-sm text-gray-300">
                <input
                  type="checkbox"
                  checked={passoForm.opzioni_ui?.widget_fondo?.tipo === 'modello_aura'}
                  onChange={(e) =>
                    updateOpzioniUi({
                      widget_fondo: e.target.checked
                        ? {
                            tipo: 'modello_aura',
                            aura_sigle: ['MAG', 'SAC', 'ARC', 'PSI'],
                            caratteristica_per_aura: {
                              MAG: 'Magia',
                              SAC: 'Sacra',
                              ARC: 'Arcana',
                              PSI: 'Psionica',
                            },
                            messaggio_bloccato:
                              'Hai zero talenti di {nome} e non puoi sceglierla.',
                          }
                        : null,
                    })
                  }
                />
                Widget fondo: modello di aura
              </label>
              <div className="min-h-[120px] border border-gray-600 rounded bg-white text-black">
                <RichTextEditor value={passoForm.contenuto} onChange={(html) => setPassoForm({ ...passoForm, contenuto: html })} />
              </div>
              <button type="button" onClick={savePasso} className="w-full py-2 rounded bg-indigo-700 text-sm font-bold">Salva passo</button>
              {selectedPassoId ? (
                <button
                  type="button"
                  className="w-full py-2 rounded bg-red-900/40 text-red-200 text-sm"
                  onClick={async () => {
                    if (!window.confirm('Eliminare passo e scelte?')) return;
                    await deleteCreazioneGuidataPasso(selectedPassoId, onLogout);
                    setSelectedPassoId(null);
                    loadFlussoDetail(selectedFlussoId);
                  }}
                >
                  Elimina passo
                </button>
              ) : null}
            </div>
          ) : null}
        </div>

        <div className="border border-gray-700 rounded-xl p-3 overflow-y-auto space-y-2">
          <h3 className="text-sm font-bold uppercase text-gray-400">Scelte</h3>
          {!selectedPasso ? <p className="text-sm text-gray-500">Seleziona un passo</p> : null}
          {selectedPasso?.scelte?.map((s) => (
            <button
              key={s.id}
              type="button"
              onClick={() => editScelta(s)}
              className="w-full text-left px-3 py-2 rounded border border-gray-700 bg-gray-800 hover:border-gray-500"
            >
              <span className="font-semibold block">{s.etichetta}</span>
              <span className="text-xs text-gray-500">{s.tipo_azione}</span>
            </button>
          ))}

          {selectedPasso ? (
            <div className="pt-3 border-t border-gray-700 space-y-2">
              <input className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" placeholder="Etichetta" value={sceltaForm.etichetta} onChange={(e) => setSceltaForm({ ...sceltaForm, etichetta: e.target.value })} />
              <input className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" placeholder="Descrizione breve" value={sceltaForm.descrizione} onChange={(e) => setSceltaForm({ ...sceltaForm, descrizione: e.target.value })} />
              <select className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" value={sceltaForm.tipo_azione} onChange={(e) => setSceltaForm({ ...sceltaForm, tipo_azione: e.target.value })}>
                {TIPO_AZIONE_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <input
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                placeholder="gruppo_id scelta (override passo)"
                value={sceltaForm.gruppoId}
                onChange={(e) => setSceltaForm({ ...sceltaForm, gruppoId: e.target.value })}
              />
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                value={sceltaForm.modalitaRewind || ''}
                onChange={(e) => setSceltaForm({ ...sceltaForm, modalitaRewind: e.target.value })}
              >
                <option value="">Rewind: eredita dal passo</option>
                {REWIND_OPTIONS.map((o) => (
                  <option key={o.value} value={o.value}>{o.label}</option>
                ))}
              </select>
              <select
                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm"
                value={sceltaForm.passo_destinazione || ''}
                onChange={(e) => setSceltaForm({ ...sceltaForm, passo_destinazione: e.target.value ? Number(e.target.value) : null })}
              >
                <option value="">Passo destinazione (opz.)</option>
                {passi.map((p) => (
                  <option key={p.id} value={p.id}>{p.titolo}</option>
                ))}
              </select>

              {(sceltaForm.tipo_azione === 'imposta_campo' || sceltaForm.tipo_azione === 'combo') ? (
                <>
                  <select className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" value={sceltaForm.payloadField} onChange={(e) => setSceltaForm({ ...sceltaForm, payloadField: e.target.value })}>
                    {CAMPO_OPTIONS.map((o) => (
                      <option key={o.value} value={o.value}>{o.label}</option>
                    ))}
                  </select>
                  {sceltaForm.payloadField === 'era' ? (
                    <select className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" value={sceltaForm.payloadSyncId} onChange={(e) => setSceltaForm({ ...sceltaForm, payloadSyncId: e.target.value })}>
                      <option value="">Era...</option>
                      {ere.map((era) => (
                        <option key={era.sync_id || era.id} value={era.sync_id || era.id}>{era.nome}</option>
                      ))}
                    </select>
                  ) : null}
                  {sceltaForm.payloadField === 'prefettura' ? (
                    <select className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-sm" value={sceltaForm.payloadSyncId} onChange={(e) => setSceltaForm({ ...sceltaForm, payloadSyncId: e.target.value })}>
                      <option value="">Prefettura...</option>
                      {prefettureFlat.map((p) => (
                        <option key={p.sync_id || p.id} value={p.sync_id || p.id}>{p.nome} ({p.era_nome})</option>
                      ))}
                    </select>
                  ) : null}
                </>
              ) : null}

              {(sceltaForm.tipo_azione === 'aggiungi_abilita' || sceltaForm.tipo_azione === 'combo') ? (
                <AbilitaMultiPicker
                  options={abilitaOptions}
                  selectedSyncIds={sceltaForm.payloadAbilitaSyncIds || []}
                  onChange={(ids) => setSceltaForm({ ...sceltaForm, payloadAbilitaSyncIds: ids })}
                />
              ) : null}

              {(sceltaForm.tipo_azione === 'naviga'
                || sceltaForm.tipo_azione === 'fine'
                || sceltaForm.tipo_azione === 'combo') ? (
                <textarea
                  className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-xs font-mono min-h-16"
                  value={sceltaForm.payloadJson}
                  onChange={(e) => setSceltaForm({ ...sceltaForm, payloadJson: e.target.value })}
                />
              ) : null}

              <button type="button" onClick={saveScelta} className="w-full py-2 rounded bg-emerald-700 text-sm font-bold">Salva scelta</button>
              {sceltaForm.id ? (
                <button
                  type="button"
                  className="w-full py-2 rounded bg-red-900/40 text-red-200 text-sm"
                  onClick={async () => {
                    await deleteCreazioneGuidataScelta(sceltaForm.id, onLogout);
                    setSceltaForm({ ...sceltaForm, id: null, etichetta: '', descrizione: '' });
                    loadFlussoDetail(selectedFlussoId);
                  }}
                >
                  Elimina scelta
                </button>
              ) : null}
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
}
