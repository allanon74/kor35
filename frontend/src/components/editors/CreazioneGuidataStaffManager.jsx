import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Plus, Trash2, Sparkles, Pencil, ChevronRight } from 'lucide-react';
import RichTextEditor from '../RichTextEditor';
import StaffEditorModal from './StaffEditorModal';
import AbilitaMultiPicker from './AbilitaMultiPicker';
import {
  PRESENTAZIONE_OPTIONS,
  REWIND_OPTIONS,
  CAMPO_OPTIONS,
  emptyFlussoForm,
  flussoFormFromDetail,
  emptyPassoForm,
  passoFormFrom,
  emptySceltaForm,
  sceltaFormFrom,
  buildPayloadFromSceltaForm,
  buildTipoAzioneFromSceltaForm,
  formatSceltaAzioneSummary,
} from './creazioneGuidataStaffForms';
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

const inputCls =
  'w-full bg-gray-800 border border-gray-600 rounded-lg p-2 text-sm text-gray-100';
const selectCls = inputCls;
const checkLabelCls = 'flex items-center gap-2 text-sm text-gray-200 cursor-pointer';
const fieldsetCls = 'rounded-lg border border-gray-700 bg-gray-800/50 p-3 space-y-2';
const legendCls = 'text-[10px] uppercase font-bold text-gray-500 tracking-wide px-1';

function ListRow({ active, onSelect, onEdit, title, subtitle, badges }) {
  return (
    <div
      className={`flex items-stretch gap-1 rounded-lg border overflow-hidden ${
        active ? 'border-violet-500 bg-violet-950/40' : 'border-gray-700 bg-gray-800/80'
      }`}
    >
      <button type="button" onClick={onSelect} className="flex-1 text-left px-3 py-2 min-w-0">
        <span className="font-semibold block truncate text-gray-100">{title}</span>
        {subtitle ? <span className="text-xs text-gray-500 block truncate">{subtitle}</span> : null}
        {badges ? <span className="text-[10px] text-gray-400 mt-0.5 block">{badges}</span> : null}
      </button>
      {onEdit ? (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="shrink-0 px-2 flex items-center text-gray-400 hover:bg-gray-700 hover:text-white"
          title="Modifica"
        >
          <Pencil size={16} />
        </button>
      ) : null}
    </div>
  );
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
  const [sandboxBusy, setSandboxBusy] = useState(false);
  const [apertaGiocatori, setApertaGiocatori] = useState(false);
  const [impostazioniLoading, setImpostazioniLoading] = useState(true);
  const [modalSaving, setModalSaving] = useState(false);

  const [modal, setModal] = useState(null);
  const [flussoForm, setFlussoForm] = useState(emptyFlussoForm);
  const [passoForm, setPassoForm] = useState(emptyPassoForm());
  const [sceltaForm, setSceltaForm] = useState(emptySceltaForm);

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

  const scelteSorted = useMemo(() => {
    const list = selectedPasso?.scelte || [];
    return [...list].sort((a, b) => (a.ordine || 0) - (b.ordine || 0));
  }, [selectedPasso]);

  const prefettureFlat = useMemo(
    () => ere.flatMap((e) => (e.prefetture || []).map((p) => ({ ...p, era_nome: e.nome }))),
    [ere],
  );

  const closeModal = () => setModal(null);

  const openFlussoModal = (mode, detail = null) => {
    setFlussoForm(mode === 'edit' && detail ? flussoFormFromDetail(detail) : emptyFlussoForm());
    setModal({ kind: 'flusso', mode });
  };

  const openPassoModal = (mode, passo = null) => {
    setPassoForm(mode === 'edit' && passo ? passoFormFrom(passo) : emptyPassoForm(passi.length));
    setModal({ kind: 'passo', mode, passoId: passo?.id || null });
  };

  const openSceltaModal = (mode, scelta = null) => {
    const ordine = scelteSorted.length;
    setSceltaForm(mode === 'edit' && scelta ? sceltaFormFrom(scelta) : { ...emptySceltaForm(), ordine });
    setModal({ kind: 'scelta', mode, sceltaId: scelta?.id || null });
  };

  const updateOpzioniUi = (patch) => {
    setPassoForm((f) => ({
      ...f,
      opzioni_ui: { ...(f.opzioni_ui || {}), ...patch },
    }));
  };

  const handleCreaSandbox = async () => {
    if (!selectedFlussoId || flussoDetail?.modalita_test) return;
    if (
      !window.confirm(
        'Crea o aggiorna la sandbox test clonando lo stato attuale della produzione?',
      )
    ) {
      return;
    }
    setSandboxBusy(true);
    try {
      const sandbox = await creaSandboxCreazioneGuidataFlusso(selectedFlussoId, onLogout);
      setStatus('Sandbox test pronta.');
      await loadFlussi();
      if (sandbox?.id) {
        setSelectedFlussoId(sandbox.id);
      }
    } catch (e) {
      setStatus(e?.message || 'Errore sandbox');
    } finally {
      setSandboxBusy(false);
    }
  };

  const handlePubblicaSandbox = async () => {
    if (!flussoDetail?.modalita_test || !flussoDetail?.flusso_produzione) return;
    if (!window.confirm('Pubblicare la sandbox sul flusso di PRODUZIONE?')) return;
    setSandboxBusy(true);
    try {
      await pubblicaCreazioneGuidataSandbox(selectedFlussoId, onLogout);
      setStatus('Pubblicato su produzione.');
      await loadFlussi();
      setSelectedFlussoId(flussoDetail.flusso_produzione);
    } catch (e) {
      setStatus(e?.message || 'Errore pubblicazione');
    } finally {
      setSandboxBusy(false);
    }
  };

  const saveFlussoModal = async () => {
    setModalSaving(true);
    try {
      let flussoId = modal?.mode === 'edit' ? selectedFlussoId : null;
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
      closeModal();
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio flusso');
    } finally {
      setModalSaving(false);
    }
  };

  const savePassoModal = async () => {
    if (!selectedFlussoId) return;
    setModalSaving(true);
    try {
      const body = { ...passoForm, flusso: selectedFlussoId };
      if (modal?.mode === 'edit' && modal.passoId) {
        await updateCreazioneGuidataPasso(modal.passoId, body, onLogout);
        setSelectedPassoId(modal.passoId);
      } else {
        const created = await createCreazioneGuidataPasso(body, onLogout);
        setSelectedPassoId(created.id);
      }
      setStatus('Passo salvato.');
      await loadFlussoDetail(selectedFlussoId);
      closeModal();
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio passo');
    } finally {
      setModalSaving(false);
    }
  };

  const saveSceltaModal = async () => {
    if (!selectedPassoId) return;
    setModalSaving(true);
    try {
      const body = {
        passo: selectedPassoId,
        etichetta: sceltaForm.etichetta,
        descrizione: sceltaForm.descrizione,
        ordine: sceltaForm.ordine,
        tipo_azione: buildTipoAzioneFromSceltaForm(sceltaForm),
        passo_destinazione: sceltaForm.navigazioneFine
          ? null
          : (sceltaForm.passo_destinazione || null),
        payload: buildPayloadFromSceltaForm(sceltaForm),
      };
      if (modal?.mode === 'edit' && modal.sceltaId) {
        await updateCreazioneGuidataScelta(modal.sceltaId, body, onLogout);
      } else {
        await createCreazioneGuidataScelta(body, onLogout);
      }
      setStatus('Scelta salvata.');
      await loadFlussoDetail(selectedFlussoId);
      closeModal();
    } catch (e) {
      setStatus(e?.message || 'Errore salvataggio scelta');
    } finally {
      setModalSaving(false);
    }
  };

  const deleteFlusso = async (id) => {
    if (!window.confirm('Eliminare il flusso e tutti i passi?')) return;
    await deleteCreazioneGuidataFlusso(id, onLogout);
    if (selectedFlussoId === id) {
      setSelectedFlussoId(null);
      setSelectedPassoId(null);
    }
    await loadFlussi();
    setStatus('Flusso eliminato.');
  };

  const deletePasso = async (id) => {
    if (!window.confirm('Eliminare passo e scelte?')) return;
    await deleteCreazioneGuidataPasso(id, onLogout);
    if (selectedPassoId === id) setSelectedPassoId(null);
    await loadFlussoDetail(selectedFlussoId);
    setStatus('Passo eliminato.');
  };

  const deleteScelta = async (id) => {
    if (!window.confirm('Eliminare questa scelta?')) return;
    await deleteCreazioneGuidataScelta(id, onLogout);
    await loadFlussoDetail(selectedFlussoId);
    setStatus('Scelta eliminata.');
  };

  const renderSceltaFields = () => (
    <>
      <input
        className={inputCls}
        placeholder="Etichetta pulsante"
        value={sceltaForm.etichetta}
        onChange={(e) => setSceltaForm({ ...sceltaForm, etichetta: e.target.value })}
      />
      <input
        className={inputCls}
        placeholder="Descrizione breve (opzionale)"
        value={sceltaForm.descrizione}
        onChange={(e) => setSceltaForm({ ...sceltaForm, descrizione: e.target.value })}
      />
      <div>
        <label className="text-[10px] uppercase text-gray-500">Ordine</label>
        <input
          type="number"
          className={inputCls}
          value={sceltaForm.ordine}
          onChange={(e) =>
            setSceltaForm({ ...sceltaForm, ordine: parseInt(e.target.value || '0', 10) })
          }
        />
      </div>

      <fieldset className={fieldsetCls}>
        <legend className={legendCls}>Navigazione</legend>
        <label className={checkLabelCls}>
          <input
            type="radio"
            name="scelta-navigazione"
            checked={!sceltaForm.navigazioneFine}
            onChange={() => setSceltaForm({ ...sceltaForm, navigazioneFine: false })}
            className="rounded-full"
          />
          Naviga al prossimo step
        </label>
        <label className={checkLabelCls}>
          <input
            type="radio"
            name="scelta-navigazione"
            checked={!!sceltaForm.navigazioneFine}
            onChange={() => setSceltaForm({ ...sceltaForm, navigazioneFine: true })}
            className="rounded-full"
          />
          Fine percorso
        </label>
      </fieldset>

      <fieldset className={fieldsetCls}>
        <legend className={legendCls}>Effetti opzionali</legend>
        <label className={checkLabelCls}>
          <input
            type="checkbox"
            checked={!!sceltaForm.flagImpostaCampo}
            onChange={(e) =>
              setSceltaForm({ ...sceltaForm, flagImpostaCampo: e.target.checked })
            }
            className="rounded"
          />
          Imposta campo personaggio
        </label>
        <label className={checkLabelCls}>
          <input
            type="checkbox"
            checked={!!sceltaForm.flagAggiungiAbilita}
            onChange={(e) =>
              setSceltaForm({ ...sceltaForm, flagAggiungiAbilita: e.target.checked })
            }
            className="rounded"
          />
          Aggiungi abilità suggerite
        </label>
      </fieldset>
      <input
        className={inputCls}
        placeholder="gruppo_id (override passo)"
        value={sceltaForm.gruppoId}
        onChange={(e) => setSceltaForm({ ...sceltaForm, gruppoId: e.target.value })}
      />
      <select
        className={selectCls}
        value={sceltaForm.modalitaRewind || ''}
        onChange={(e) => setSceltaForm({ ...sceltaForm, modalitaRewind: e.target.value })}
      >
        <option value="">Rewind: eredita dal passo</option>
        {REWIND_OPTIONS.map((o) => (
          <option key={o.value} value={o.value}>
            {o.label}
          </option>
        ))}
      </select>
      {!sceltaForm.navigazioneFine ? (
        <select
          className={selectCls}
          value={sceltaForm.passo_destinazione || ''}
          onChange={(e) =>
            setSceltaForm({
              ...sceltaForm,
              passo_destinazione: e.target.value ? Number(e.target.value) : null,
            })
          }
        >
          <option value="">Passo destinazione (opz.)</option>
          {passi.map((p) => (
            <option key={p.id} value={p.id}>
              {p.titolo}
            </option>
          ))}
        </select>
      ) : null}
      {sceltaForm.flagImpostaCampo ? (
        <div className={`${fieldsetCls} space-y-2`}>
          <p className={legendCls}>Campo personaggio</p>
          <select
            className={selectCls}
            value={sceltaForm.payloadField}
            onChange={(e) => setSceltaForm({ ...sceltaForm, payloadField: e.target.value })}
          >
            {CAMPO_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          {sceltaForm.payloadField === 'era' ? (
            <select
              className={selectCls}
              value={sceltaForm.payloadSyncId}
              onChange={(e) => setSceltaForm({ ...sceltaForm, payloadSyncId: e.target.value })}
            >
              <option value="">Seleziona era...</option>
              {ere.map((era) => (
                <option key={era.sync_id || era.id} value={era.sync_id || era.id}>
                  {era.nome}
                </option>
              ))}
            </select>
          ) : null}
          {sceltaForm.payloadField === 'prefettura' ? (
            <select
              className={selectCls}
              value={sceltaForm.payloadSyncId}
              onChange={(e) => setSceltaForm({ ...sceltaForm, payloadSyncId: e.target.value })}
            >
              <option value="">Seleziona prefettura...</option>
              {prefettureFlat.map((p) => (
                <option key={p.sync_id || p.id} value={p.sync_id || p.id}>
                  {p.nome} ({p.era_nome})
                </option>
              ))}
            </select>
          ) : null}
        </div>
      ) : null}
      {sceltaForm.flagAggiungiAbilita ? (
        <div className={fieldsetCls}>
          <AbilitaMultiPicker
            options={abilitaOptions}
            selectedSyncIds={sceltaForm.payloadAbilitaSyncIds || []}
            onChange={(ids) => setSceltaForm({ ...sceltaForm, payloadAbilitaSyncIds: ids })}
          />
        </div>
      ) : null}
      {!sceltaForm.navigazioneFine ? (
        <div>
          <label className="text-[10px] uppercase text-gray-500">Payload JSON (avanzato)</label>
          <textarea
            className={`${inputCls} font-mono text-xs min-h-24`}
            value={sceltaForm.payloadJson}
            onChange={(e) => setSceltaForm({ ...sceltaForm, payloadJson: e.target.value })}
          />
        </div>
      ) : null}
    </>
  );

  return (
    <div className="h-full flex flex-col bg-gray-900 text-gray-100 p-4 overflow-hidden">
      <div className="flex items-center gap-2 mb-4 shrink-0">
        <Sparkles className="text-violet-400" />
        <h2 className="text-xl font-bold">Creazione guidata personaggio</h2>
      </div>

      <div className="mb-4 rounded-xl border border-gray-600 bg-gray-800/80 p-3 flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div>
          <p className="text-sm font-bold text-gray-100">Pulsante per i giocatori</p>
          <p className="text-xs text-gray-400 max-w-xl">
            Se disattivo, i giocatori non vedono «Creazione guidata» in StartPage.
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
                setStatus(next ? 'Visibile ai giocatori.' : 'Nascosta ai giocatori.');
              } catch (err) {
                setApertaGiocatori(!next);
                setStatus(err?.message || 'Errore impostazione');
              }
            }}
            className="rounded"
          />
          <span className={apertaGiocatori ? 'text-emerald-300' : 'text-amber-300'}>
            {apertaGiocatori ? 'Visibile ai giocatori' : 'Nascosta ai giocatori'}
          </span>
        </label>
      </div>

      {status ? <p className="text-sm text-amber-200 mb-2 shrink-0">{status}</p> : null}

      <div className="flex-1 grid grid-cols-1 lg:grid-cols-3 gap-4 min-h-0 overflow-hidden">
        {/* Flussi */}
        <div className="border border-gray-700 rounded-xl flex flex-col min-h-0 overflow-hidden">
          <div className="flex justify-between items-center px-3 py-2 border-b border-gray-700 shrink-0">
            <h3 className="text-sm font-bold uppercase text-gray-400">Flussi</h3>
            <button
              type="button"
              className="p-1.5 rounded bg-violet-800 hover:bg-violet-700"
              title="Nuovo flusso"
              onClick={() => openFlussoModal('create')}
            >
              <Plus size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {loading ? <p className="text-sm text-gray-500 p-2">Caricamento...</p> : null}
            {flussi.map((f) => (
              <ListRow
                key={f.id}
                active={selectedFlussoId === f.id}
                onSelect={() => {
                  setSelectedFlussoId(f.id);
                  setSelectedPassoId(null);
                }}
                onEdit={async () => {
                  setSelectedFlussoId(f.id);
                  setSelectedPassoId(null);
                  try {
                    const data = await getCreazioneGuidataFlusso(f.id, onLogout);
                    setFlussoDetail(data);
                    setFlussoForm(flussoFormFromDetail(data));
                    setModal({ kind: 'flusso', mode: 'edit' });
                  } catch (e) {
                    setStatus(e?.message || 'Errore caricamento flusso');
                  }
                }}
                title={f.titolo}
                subtitle={f.slug}
                badges={[
                  f.attivo ? 'attivo' : 'inattivo',
                  f.modalita_test ? 'sandbox' : 'produzione',
                  f.sandbox_modifiche_pending ? '· da pubblicare' : '',
                ]
                  .filter(Boolean)
                  .join(' · ')}
              />
            ))}
          </div>
          {selectedFlussoId && flussoDetail ? (
            <div className="p-2 border-t border-gray-700 shrink-0 space-y-1">
              {!flussoDetail.modalita_test ? (
                <>
                  <button
                    type="button"
                    disabled={sandboxBusy}
                    onClick={handleCreaSandbox}
                    className="w-full py-1.5 text-xs rounded bg-amber-800 hover:bg-amber-700 disabled:opacity-50"
                  >
                    {flussoDetail.sandbox_test_id ? 'Aggiorna sandbox' : 'Crea sandbox test'}
                  </button>
                  {flussoDetail.sandbox_test_id ? (
                    <button
                      type="button"
                      className="w-full py-1.5 text-xs rounded bg-gray-700 hover:bg-gray-600"
                      onClick={() => setSelectedFlussoId(flussoDetail.sandbox_test_id)}
                    >
                      Vai alla sandbox
                    </button>
                  ) : null}
                </>
              ) : (
                <button
                  type="button"
                  disabled={sandboxBusy}
                  onClick={handlePubblicaSandbox}
                  className="w-full py-1.5 text-xs rounded bg-emerald-800 hover:bg-emerald-700 font-bold disabled:opacity-50"
                >
                  Pubblica su produzione
                </button>
              )}
              <button
                type="button"
                className="w-full py-1.5 text-xs rounded bg-red-900/40 text-red-200 flex items-center justify-center gap-1"
                onClick={() => deleteFlusso(selectedFlussoId)}
              >
                <Trash2 size={12} /> Elimina flusso
              </button>
            </div>
          ) : null}
        </div>

        {/* Passi */}
        <div className="border border-gray-700 rounded-xl flex flex-col min-h-0 overflow-hidden">
          <div className="flex justify-between items-center px-3 py-2 border-b border-gray-700 shrink-0">
            <h3 className="text-sm font-bold uppercase text-gray-400">Passi</h3>
            <button
              type="button"
              disabled={!selectedFlussoId}
              className="p-1.5 rounded bg-indigo-800 hover:bg-indigo-700 disabled:opacity-40"
              title="Nuovo passo"
              onClick={() => openPassoModal('create')}
            >
              <Plus size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {!selectedFlussoId ? (
              <p className="text-sm text-gray-500 p-2">Seleziona un flusso</p>
            ) : (
              passi.map((p) => (
                <ListRow
                  key={p.id}
                  active={selectedPassoId === p.id}
                  onSelect={() => setSelectedPassoId(p.id)}
                  onEdit={() => openPassoModal('edit', p)}
                  title={p.titolo}
                  subtitle={p.slug}
                  badges={`${(p.scelte || []).length} scelte · ordine ${p.ordine ?? 0}`}
                />
              ))
            )}
          </div>
          {selectedPassoId ? (
            <div className="p-2 border-t border-gray-700 shrink-0">
              <button
                type="button"
                className="w-full py-1.5 text-xs rounded bg-red-900/40 text-red-200"
                onClick={() => deletePasso(selectedPassoId)}
              >
                Elimina passo selezionato
              </button>
            </div>
          ) : null}
        </div>

        {/* Scelte */}
        <div className="border border-gray-700 rounded-xl flex flex-col min-h-0 overflow-hidden">
          <div className="flex justify-between items-center px-3 py-2 border-b border-gray-700 shrink-0">
            <h3 className="text-sm font-bold uppercase text-gray-400">Scelte</h3>
            <button
              type="button"
              disabled={!selectedPassoId}
              className="p-1.5 rounded bg-emerald-800 hover:bg-emerald-700 disabled:opacity-40"
              title="Nuova scelta"
              onClick={() => openSceltaModal('create')}
            >
              <Plus size={16} />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
            {!selectedPasso ? (
              <p className="text-sm text-gray-500 p-2">Seleziona un passo</p>
            ) : scelteSorted.length === 0 ? (
              <p className="text-sm text-gray-500 p-2">Nessuna scelta — aggiungine una.</p>
            ) : (
              scelteSorted.map((s) => (
                <button
                  key={s.id}
                  type="button"
                  onClick={() => openSceltaModal('edit', s)}
                  className="w-full text-left px-3 py-2 rounded-lg border border-gray-700 bg-gray-800 hover:border-emerald-600/60 flex items-center justify-between gap-2"
                >
                  <span className="min-w-0">
                    <span className="font-semibold block truncate">{s.etichetta}</span>
                    <span className="text-xs text-gray-500">{formatSceltaAzioneSummary(s)}</span>
                  </span>
                  <ChevronRight size={14} className="text-gray-500 shrink-0" />
                </button>
              ))
            )}
          </div>
          {selectedPasso ? (
            <p className="px-3 py-2 text-xs text-gray-500 border-t border-gray-700 shrink-0">
              Passo: <strong className="text-gray-300">{selectedPasso.titolo}</strong>
            </p>
          ) : null}
        </div>
      </div>

      {modal?.kind === 'flusso' && (
        <StaffEditorModal
          title={modal.mode === 'edit' ? 'Modifica flusso' : 'Nuovo flusso'}
          onClose={closeModal}
          onSave={saveFlussoModal}
          saving={modalSaving}
          footerExtra={
            modal.mode === 'edit' && selectedFlussoId ? (
              <button
                type="button"
                className="px-3 py-2 text-sm text-red-300 hover:bg-red-900/30 rounded-lg"
                onClick={() => {
                  closeModal();
                  deleteFlusso(selectedFlussoId);
                }}
              >
                Elimina
              </button>
            ) : null
          }
        >
          <input
            className={inputCls}
            placeholder="slug (univoco)"
            value={flussoForm.slug}
            onChange={(e) => setFlussoForm({ ...flussoForm, slug: e.target.value })}
          />
          <input
            className={inputCls}
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
            Flusso attivo (produzione)
          </label>
          <select
            className={selectCls}
            value={flussoForm.passo_iniziale || ''}
            onChange={(e) =>
              setFlussoForm({
                ...flussoForm,
                passo_iniziale: e.target.value ? Number(e.target.value) : null,
              })
            }
          >
            <option value="">Passo iniziale (dopo aver creato i passi)</option>
            {passi.map((p) => (
              <option key={p.id} value={p.id}>
                {p.titolo} ({p.slug})
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-500">
            La sandbox test si crea dal pannello flussi, non da qui.
          </p>
        </StaffEditorModal>
      )}

      {modal?.kind === 'passo' && (
        <StaffEditorModal
          title={modal.mode === 'edit' ? 'Modifica passo' : 'Nuovo passo'}
          onClose={closeModal}
          onSave={savePassoModal}
          saving={modalSaving}
          wide
          footerExtra={
            modal.mode === 'edit' && modal.passoId ? (
              <button
                type="button"
                className="px-3 py-2 text-sm text-red-300 hover:bg-red-900/30 rounded-lg"
                onClick={() => {
                  closeModal();
                  deletePasso(modal.passoId);
                }}
              >
                Elimina
              </button>
            ) : null
          }
        >
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            <input
              className={inputCls}
              placeholder="slug passo"
              value={passoForm.slug}
              onChange={(e) => setPassoForm({ ...passoForm, slug: e.target.value })}
            />
            <input
              type="number"
              className={inputCls}
              placeholder="Ordine"
              value={passoForm.ordine}
              onChange={(e) =>
                setPassoForm({ ...passoForm, ordine: parseInt(e.target.value || '0', 10) })
              }
            />
          </div>
          <input
            className={inputCls}
            placeholder="Titolo passo"
            value={passoForm.titolo}
            onChange={(e) => setPassoForm({ ...passoForm, titolo: e.target.value })}
          />
          <select
            className={selectCls}
            value={passoForm.opzioni_ui?.presentazione || 'pulsanti'}
            onChange={(e) => updateOpzioniUi({ presentazione: e.target.value })}
          >
            {PRESENTAZIONE_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
            ))}
          </select>
          <input
            className={inputCls}
            placeholder="gruppo_id passo"
            value={passoForm.opzioni_ui?.gruppo_id || ''}
            onChange={(e) => updateOpzioniUi({ gruppo_id: e.target.value })}
          />
          <select
            className={selectCls}
            value={passoForm.opzioni_ui?.modalita_rewind || 'ramo'}
            onChange={(e) => updateOpzioniUi({ modalita_rewind: e.target.value })}
          >
            {REWIND_OPTIONS.map((o) => (
              <option key={o.value} value={o.value}>
                {o.label}
              </option>
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
                        messaggio_bloccato: 'Hai zero talenti di {nome} e non puoi sceglierla.',
                      }
                    : null,
                })
              }
            />
            Widget fondo: modello di aura
          </label>
          <div>
            <label className="text-[10px] uppercase text-gray-500 mb-1 block">Contenuto wiki</label>
            <div className="min-h-[200px] border border-gray-600 rounded-lg bg-white text-black">
              <RichTextEditor
                value={passoForm.contenuto}
                onChange={(html) => setPassoForm({ ...passoForm, contenuto: html })}
              />
            </div>
          </div>
        </StaffEditorModal>
      )}

      {modal?.kind === 'scelta' && (
        <StaffEditorModal
          title={modal.mode === 'edit' ? 'Modifica scelta' : 'Nuova scelta'}
          onClose={closeModal}
          onSave={saveSceltaModal}
          saving={modalSaving}
          wide
          footerExtra={
            modal.mode === 'edit' && modal.sceltaId ? (
              <button
                type="button"
                className="px-3 py-2 text-sm text-red-300 hover:bg-red-900/30 rounded-lg"
                onClick={() => {
                  closeModal();
                  deleteScelta(modal.sceltaId);
                }}
              >
                Elimina
              </button>
            ) : null
          }
        >
          {selectedPasso ? (
            <p className="text-xs text-indigo-300/90 bg-indigo-950/30 rounded px-2 py-1">
              Passo: {selectedPasso.titolo}
            </p>
          ) : null}
          {renderSceltaFields()}
        </StaffEditorModal>
      )}
    </div>
  );
}
