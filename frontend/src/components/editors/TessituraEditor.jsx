import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useCharacter } from '../CharacterContext';
import { getStatisticheList, staffUpdateTessitura, staffCreateTessitura, staffGetAbilitaListAll, staffGetFormulaSemanticOptions } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import StatBaseInline from './inlines/StatBaseInline';
import RichTextEditor from '../RichTextEditor';
import EditorSaveActions from './EditorSaveActions';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import FormulaBuilderModal from './FormulaBuilderModal';
import CatalogoAccademiaFlags from './CatalogoAccademiaFlags';

/** Garantisce che l'abilità già salvata compaia nel select anche se fuori dalla prima pagina API. */
const mergeAbilitaTemporaneaOption = (rows, selected) => {
  const list = Array.isArray(rows) ? rows : [];
  if (!selected) return list;
  const id = selected?.id ?? selected;
  if (id == null || id === '') return list;
  const sid = String(id);
  if (list.some((r) => String(r.id) === sid)) return list;
  const nome =
    typeof selected === 'object' && selected.nome
      ? selected.nome
      : `Abilità #${id}`;
  return [
    ...list,
    { id, nome, nascondi_in_scheda_abilita: !!selected?.nascondi_in_scheda_abilita },
  ];
};

const formatAbilitaOptionLabel = (abilita) => {
  if (!abilita?.nome) return '';
  return abilita.nascondi_in_scheda_abilita
    ? `${abilita.nome} (nascosta in scheda)`
    : abilita.nome;
};

const mergeElementoPrincipaleOption = (rows, selected) => {
  const list = Array.isArray(rows) ? rows : [];
  if (!selected) return list;
  const id = selected?.id ?? selected;
  if (id == null || id === '') return list;
  const sid = String(id);
  if (list.some((r) => String(r.id) === sid)) return list;
  const nome =
    selected?.dichiarazione ||
    selected?.nome ||
    selected?.label ||
    `Elemento #${id}`;
  return [{ id, nome, dichiarazione: selected?.dichiarazione || '' }, ...list];
};

const TessituraEditor = ({ onBack, onCancel, onSave, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [statsOptions, setStatsOptions] = useState([]);
  const [abilitaOptions, setAbilitaOptions] = useState([]);
  const [elementoMattoniOptions, setElementoMattoniOptions] = useState([]);
  
  // FIX: Default Data Merging
  const defaultData = {
    nome: '', testo: '', formula: '',
    aura_richiesta: null,
    elemento_principale: null,
    componenti: [],
    statistiche_base: [],
    non_acquistabile: false,
    escluso_negozio_ufficiale: false,
    non_vendibile: false,
    usa_effetto_temporaneo: false,
    abilita_temporanea: null,
    durata_effetto_secondi: 0,
    oggetto_runtime_config_str: '',
  };

  const hydrateForm = (data) => {
    const merged = { ...defaultData, ...(data || {}) };
    if (merged.oggetto_runtime_config && !merged.oggetto_runtime_config_str) {
      merged.oggetto_runtime_config_str = JSON.stringify(merged.oggetto_runtime_config, null, 2);
    }
    return merged;
  };
  const [formData, setFormData] = useState(hydrateForm(initialData));
  const [saving, setSaving] = useState(false);
  const [status, setStatus] = useState({ type: 'success', message: '' });
  const [isFormulaBuilderOpen, setIsFormulaBuilderOpen] = useState(false);
  const [isRuntimeWizardOpen, setIsRuntimeWizardOpen] = useState(false);

  // Alias per chiusura
  const handleClose = onCancel || onBack;

  useEffect(() => {
    getStatisticheList(onLogout).then(setStatsOptions);
    let cancelled = false;
    (async () => {
      try {
        const [rows, semantic] = await Promise.all([
          staffGetAbilitaListAll(onLogout),
          staffGetFormulaSemanticOptions(onLogout),
        ]);
        if (cancelled) return;
        setAbilitaOptions(
          mergeAbilitaTemporaneaOption(rows, initialData?.abilita_temporanea)
        );
        setElementoMattoniOptions(semantic?.elementi_mattoni || []);
      } catch (e) {
        console.error('Errore caricamento risorse tessitura:', e);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [onLogout, initialData?.abilita_temporanea?.id]);

  useEffect(() => {
    setAbilitaOptions((prev) =>
      mergeAbilitaTemporaneaOption(prev, formData.abilita_temporanea)
    );
  }, [formData.abilita_temporanea]);

  useEffect(() => {
    setFormData(hydrateForm(initialData));
  }, [initialData]);

  // Calcolo livello property (numero componenti)
  const calculatedLevel = (formData.componenti || []).reduce((acc, curr) => acc + (parseInt(curr.valore) || 0), 0);

  const elementoSelectOptions = useMemo(() => {
    const base = (elementoMattoniOptions || []).map((m) => ({
      id: m.id,
      nome: m.label || m.dichiarazione || m.nome || `Elemento ${m.id}`,
      dichiarazione: m.dichiarazione || '',
      label: m.label || m.dichiarazione || m.nome || '',
    }));
    return mergeElementoPrincipaleOption(base, formData.elemento_principale);
  }, [elementoMattoniOptions, formData.elemento_principale]);

  const updateInline = (key, index, field, value) => {
    const newList = [...(formData[key] || [])];
    if (index === -1 && key === 'statistiche_base') {
      const exists = newList.find(it => (it.statistica?.id || it.statistica) === value.statId);
      if (!exists) newList.push({ statistica: value.statId, valore_base: value.value });
    } else {
      newList[index] = { ...newList[index], [field]: value };
    }
    setFormData({ ...formData, [key]: newList });
  };

  const handleSave = async (mode = 'save_close') => {
    try {
      setSaving(true);
      const dataToSend = { 
        ...formData,
        aura_richiesta: formData.aura_richiesta?.id || formData.aura_richiesta || null,
        elemento_principale: formData.elemento_principale?.id || formData.elemento_principale || null,
        abilita_temporanea: formData.abilita_temporanea?.id || formData.abilita_temporanea || null,
        statistiche_base: (formData.statistiche_base || []).map(sb => ({
          ...sb,
          statistica: sb.statistica?.id || sb.statistica
        }))
      };
      if (formData.oggetto_runtime_config_str && String(formData.oggetto_runtime_config_str).trim()) {
        try {
          dataToSend.oggetto_runtime_config = JSON.parse(formData.oggetto_runtime_config_str);
        } catch (_e) {
          setStatus({ type: 'warning', message: 'JSON non valido in Oggetto runtime config.' });
          return;
        }
      } else {
        dataToSend.oggetto_runtime_config = null;
      }
      delete dataToSend.oggetto_runtime_config_str;
      
      if (onSave) {
        // APPROVAL MODE
        await onSave(dataToSend);
      } else {
        // STANDARD MODE
        const isSaveAsNew = mode === 'save_as_new';
        const isExisting = !!formData.id && !isSaveAsNew;
        const saved = isExisting
          ? await staffUpdateTessitura(formData.id, dataToSend, onLogout)
          : await staffCreateTessitura(dataToSend, onLogout);
        const recordName = saved?.nome || dataToSend.nome || 'Record';
        if (mode === 'save_as_new') setStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
        if (mode === 'save_continue') setStatus({ type: 'success', message: `"${recordName}" salvato.` });
        if (mode === 'save_new_blank') {
          setFormData({ ...defaultData });
          setStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
        }
        if (mode === 'save_close' && handleClose) handleClose();
        if (mode !== 'save_close' && mode !== 'save_new_blank' && saved?.id) {
          setFormData((prev) => ({ ...prev, ...saved }));
        }
      }
    } catch (e) { 
        console.error(e);
        setStatus({ type: 'error', message: `Errore salvataggio: ${e.message || 'Errore sconosciuto'}` });
    } finally {
        setSaving(false);
    }
  };

  const handleApplyFormulaBuilder = ({ statsByParam, formulaText, customText, controlledParams, elementoPrincipaleId }) => {
    const controlledSet = new Set(controlledParams || []);
    const byParam = new Map((statsOptions || []).map((s) => [s.parametro, s]));
    const current = formData.statistiche_base || [];
    const kept = current.filter((item) => {
      const statId = item.statistica?.id || item.statistica;
      const stat = (statsOptions || []).find((s) => String(s.id) === String(statId));
      return !(stat?.parametro && controlledSet.has(stat.parametro));
    });
    const fromBuilder = Object.entries(statsByParam || {})
      .filter(([param, value]) => byParam.get(param) && Number(value) > 0)
      .map(([param, value]) => ({ statistica: byParam.get(param).id, valore_base: Number(value) }));
    const mergedFormula = [formulaText, customText].filter(Boolean).join(' ').trim();
    setFormData((prev) => ({
      ...prev,
      formula: mergedFormula,
      statistiche_base: [...kept, ...fromBuilder],
      ...(elementoPrincipaleId != null ? { elemento_principale: elementoPrincipaleId } : {}),
    }));
  };

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] text-white border border-gray-700 shadow-2xl">
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-cyan-400 uppercase tracking-tighter">
          {formData.id ? `Edit: ${formData.nome}` : 'Nuova Tessitura'}
        </h2>
        <EditorSaveActions
          onSave={() => handleSave('save_close')}
          onSaveAndContinue={onSave ? null : () => handleSave('save_continue')}
          onSaveAsNew={onSave || !formData.id ? null : () => handleSave('save_as_new')}
          onSaveAndNew={onSave ? null : () => handleSave('save_new_blank')}
          onCancel={handleClose}
          saving={saving}
          saveLabel={onSave ? 'Approva e crea' : 'Salva'}
          statusMessage={status.message}
          statusType={status.type}
        />
      </div>

      <div className="bg-gray-900/40 p-5 rounded-xl border border-gray-700/50 space-y-5 shadow-inner">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <SearchableSelect label="Aura Richiesta" value={formData.aura_richiesta?.id || formData.aura_richiesta} 
                  options={punteggiList.filter(p => p.tipo === 'AU')} 
                  onChange={v => setFormData({...formData, aura_richiesta: v ? parseInt(v, 10) : null})} />
          <SearchableSelect label="Elemento Principale" value={formData.elemento_principale?.id || formData.elemento_principale} 
                  options={elementoSelectOptions} 
                  onChange={v => setFormData({...formData, elemento_principale: v ? parseInt(v, 10) : null})} />
        </div>
        <div className="border border-purple-800/40 rounded-lg p-3 bg-purple-950/20 space-y-3">
          <label className="flex items-center gap-2 text-xs uppercase font-bold text-purple-200 tracking-wide">
            <input
              type="checkbox"
              checked={!!formData.usa_effetto_temporaneo}
              onChange={(e) => setFormData({ ...formData, usa_effetto_temporaneo: e.target.checked })}
            />
            Effetto temporaneo runtime
          </label>
          {formData.usa_effetto_temporaneo && (
            <>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <SearchableSelect
                  label="Abilita temporanea"
                  value={formData.abilita_temporanea?.id || formData.abilita_temporanea}
                  options={abilitaOptions}
                  formatOptionLabel={formatAbilitaOptionLabel}
                  onChange={(v) => setFormData({ ...formData, abilita_temporanea: v ? parseInt(v, 10) : null })}
                />
                <Input
                  label="Durata effetto (secondi)"
                  type="number"
                  value={formData.durata_effetto_secondi}
                  onChange={(v) => setFormData({ ...formData, durata_effetto_secondi: parseInt(v || '0', 10) || 0 })}
                />
              </div>
              <div className="space-y-2">
                <button
                  type="button"
                  onClick={() => setIsRuntimeWizardOpen(true)}
                  className="px-3 py-1 rounded bg-purple-700 hover:bg-purple-600 text-xs font-bold uppercase tracking-wide"
                >
                  Configura oggetto runtime (wizard)
                </button>
                <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">
                  Preview JSON (auto)
                </label>
                <textarea
                  className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-xs text-white font-mono min-h-[110px]"
                  value={formData.oggetto_runtime_config_str || ''}
                  readOnly
                  placeholder='Il wizard popola automaticamente questo JSON.'
                />
              </div>
            </>
          )}
        </div>
        <div>
          <Input label="Formula Tessitura (es. {caratt} + 1d10)" value={formData.formula} onChange={v => setFormData({...formData, formula: v})} />
          <div className="mt-2 flex justify-end">
            <button
              type="button"
              onClick={() => setIsFormulaBuilderOpen(true)}
              className="px-3 py-1 rounded bg-cyan-700 hover:bg-cyan-600 text-xs font-bold uppercase tracking-wide"
            >
              Costruisci formula
            </button>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-3">
            <Input label="Nome" value={formData.nome} onChange={v => setFormData({...formData, nome: v})} />
          </div>
          <div className="bg-black/20 p-2 rounded flex flex-col items-center justify-center gap-2">
             <div className="flex flex-col items-center">
               <span className="text-[9px] text-gray-500 uppercase font-black">Livello</span>
               <span className="text-xl font-bold text-cyan-400">{calculatedLevel}</span>
             </div>
             <label className="text-[10px] uppercase font-bold text-gray-300 flex items-center gap-2 cursor-pointer">
               <input
                 type="checkbox"
                 checked={!!formData.non_acquistabile}
                 onChange={(e) => setFormData({ ...formData, non_acquistabile: e.target.checked })}
               />
               Non acquistabile
             </label>
             <CatalogoAccademiaFlags formData={formData} setFormData={setFormData} syncTecnicaNonAcquistabile />
          </div>
        </div>
      </div>

      <RichTextEditor label="Descrizione Effetto" value={formData.testo} onChange={v => setFormData({...formData, testo: v})} />

      <CharacteristicInline 
        items={formData.componenti || []} 
        options={punteggiList.filter(p => p.tipo === 'CA')}
        onAdd={() => setFormData({...formData, componenti: [...(formData.componenti || []), {caratteristica:'', valore:1}]})}
        onChange={(i, f, v) => updateInline('componenti', i, f, v)}
        onRemove={(i) => setFormData({...formData, componenti: formData.componenti.filter((_, idx) => idx !== i)})}
      />

      <StatBaseInline 
        items={formData.statistiche_base || []} 
        options={statsOptions} 
        onChange={(i, f, v) => updateInline('statistiche_base', i, f, v)} 
      />

      <FormulaBuilderModal
        open={isFormulaBuilderOpen}
        onClose={() => setIsFormulaBuilderOpen(false)}
        onApply={handleApplyFormulaBuilder}
        onLogout={onLogout}
        statsOptions={statsOptions}
        statisticheBase={formData.statistiche_base || []}
        formulaValue={formData.formula}
        defaultFormulaType="weave"
        elementoPrincipaleId={formData.elemento_principale?.id || formData.elemento_principale}
        elementoOptions={elementoSelectOptions}
      />

      <StaffMinigiocoQrSection qrcodeId={formData.qrcode_id} onLogout={onLogout} />

      <RuntimeObjectWizardModal
        open={isRuntimeWizardOpen}
        onClose={() => setIsRuntimeWizardOpen(false)}
        onApply={(cfg) =>
          setFormData((prev) => ({
            ...prev,
            oggetto_runtime_config_str: JSON.stringify(cfg, null, 2),
          }))
        }
        onLogout={onLogout}
        statsOptions={statsOptions}
        initialConfigStr={formData.oggetto_runtime_config_str || ''}
      />
    </div>
  );
};

const SLOT_OPTIONS = [
  'head', 'neck', 'vest', 'shoulders', 'arms', 'fingers', 'feet',
  'belt', 'armor', 'melee', 'ranged', 'focus', 'shield',
];

const TIPO_OGGETTO_OPTIONS = [
  { id: 'FIS', nome: 'Fisico' },
  { id: 'MOD', nome: 'Mod' },
  { id: 'MAT', nome: 'Materia' },
  { id: 'INN', nome: 'Innesto' },
  { id: 'MUT', nome: 'Mutazione' },
  { id: 'POT', nome: 'Potenziamento' },
  { id: 'AUM', nome: 'Aumento' },
];

const RuntimeObjectWizardModal = ({
  open,
  onClose,
  onApply,
  onLogout,
  statsOptions = [],
  initialConfigStr = '',
}) => {
  const [draft, setDraft] = useState({
    nome: '',
    slot_key: 'melee',
    tipo_oggetto: 'FIS',
    descrizione_effetto: '',
    formula: '',
    statistiche_base: [],
    modificatori: [],
    cariche_massime: 0,
    durata_totale: 0,
  });
  const [isObjFormulaBuilderOpen, setIsObjFormulaBuilderOpen] = useState(false);
  const [wizardError, setWizardError] = useState('');

  useEffect(() => {
    if (!open) return;
    try {
      const parsed = initialConfigStr ? JSON.parse(initialConfigStr) : null;
      if (parsed && typeof parsed === 'object') {
        setDraft((prev) => ({
          ...prev,
          ...parsed,
          statistiche_base: Array.isArray(parsed.statistiche_base) ? parsed.statistiche_base : [],
          modificatori: Array.isArray(parsed.modificatori) ? parsed.modificatori : [],
        }));
      }
    } catch (_e) {
      // Se JSON invalido/non parsabile, manteniamo il draft vuoto.
    }
  }, [open, initialConfigStr]);

  if (!open) return null;

  const validateDraft = () => {
    if (!String(draft.nome || '').trim()) return 'Il nome oggetto runtime è obbligatorio.';
    if (!String(draft.slot_key || '').trim()) return 'Lo slot è obbligatorio.';
    if (!SLOT_OPTIONS.includes(String(draft.slot_key || '').trim())) return 'Lo slot selezionato non è valido.';
    if (!String(draft.tipo_oggetto || '').trim()) return 'La tipologia è obbligatoria.';
    const invalidBase = (draft.statistiche_base || []).some((x) => !x.stat_sigla);
    if (invalidBase) return 'Ogni statistica base deve avere una statistica selezionata.';
    const invalidMods = (draft.modificatori || []).some((x) => !x.stat_sigla);
    if (invalidMods) return 'Ogni modificatore deve avere una statistica selezionata.';
    return '';
  };

  const addStatBase = () => {
    setDraft((p) => ({
      ...p,
      statistiche_base: [...(p.statistiche_base || []), { stat_sigla: '', valore_base: 0 }],
    }));
  };

  const addMod = () => {
    setDraft((p) => ({
      ...p,
      modificatori: [...(p.modificatori || []), { stat_sigla: '', valore: 0, tipo_modificatore: 'ADD' }],
    }));
  };

  const updateListItem = (key, idx, patch) => {
    const list = [...(draft[key] || [])];
    list[idx] = { ...list[idx], ...patch };
    setDraft((p) => ({ ...p, [key]: list }));
  };

  const removeListItem = (key, idx) => {
    const list = (draft[key] || []).filter((_, i) => i !== idx);
    setDraft((p) => ({ ...p, [key]: list }));
  };

  const handleApplyObjectFormulaBuilder = ({ statsByParam, formulaText, customText, controlledParams }) => {
    const controlled = new Set(controlledParams || []);
    const byParam = new Map((statsOptions || []).map((s) => [s.parametro, s]));
    const keptStats = (draft.statistiche_base || []).filter((row) => {
      const s = (statsOptions || []).find((x) => x.sigla === row.stat_sigla);
      return !(s?.parametro && controlled.has(s.parametro));
    });
    const builtStats = Object.entries(statsByParam || {})
      .filter(([param, value]) => byParam.get(param) && Number(value) > 0)
      .map(([param, value]) => ({
        stat_sigla: byParam.get(param).sigla,
        valore_base: Number(value),
      }));
    setDraft((p) => ({
      ...p,
      formula: [formulaText, customText].filter(Boolean).join(' ').trim(),
      statistiche_base: [...keptStats, ...builtStats],
    }));
  };

  return (
    <div className="fixed inset-0 z-11000 bg-black/75 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto bg-gray-900 border border-purple-700/50 rounded-xl shadow-2xl">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-bold text-white">Wizard Oggetto Runtime</h3>
          <button onClick={onClose} className="px-3 py-1 rounded bg-gray-700 text-white text-sm">Chiudi</button>
        </div>
        <div className="p-4 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <Input label="Nome oggetto" value={draft.nome} onChange={(v) => setDraft((p) => ({ ...p, nome: v }))} />
            <SearchableSelect
              label="Slot"
              value={draft.slot_key}
              options={SLOT_OPTIONS.map((x) => ({ id: x, nome: x }))}
              onChange={(v) => setDraft((p) => ({ ...p, slot_key: v || 'melee' }))}
            />
            <Select
              label="Tipologia"
              value={draft.tipo_oggetto}
              options={TIPO_OGGETTO_OPTIONS}
              onChange={(v) => setDraft((p) => ({ ...p, tipo_oggetto: v || 'FIS' }))}
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <Input
              label="Cariche massime (opz.)"
              type="number"
              value={draft.cariche_massime}
              onChange={(v) => setDraft((p) => ({ ...p, cariche_massime: parseInt(v || '0', 10) || 0 }))}
            />
            <Input
              label="Durata totale sec (opz.)"
              type="number"
              value={draft.durata_totale}
              onChange={(v) => setDraft((p) => ({ ...p, durata_totale: parseInt(v || '0', 10) || 0 }))}
            />
          </div>

          <div>
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">Descrizione effetto</label>
            <textarea
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white min-h-[90px]"
              value={draft.descrizione_effetto || ''}
              onChange={(e) => setDraft((p) => ({ ...p, descrizione_effetto: e.target.value }))}
            />
          </div>

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="flex items-center justify-between">
              <label className="text-[10px] text-gray-500 uppercase font-black tracking-tighter">Formula</label>
              <button
                type="button"
                onClick={() => setIsObjFormulaBuilderOpen(true)}
                className="px-2 py-1 rounded bg-cyan-700 hover:bg-cyan-600 text-xs font-bold uppercase"
              >
                Builder formula oggetto
              </button>
            </div>
            <input
              className="w-full mt-2 bg-gray-950 p-2 rounded border border-gray-700 text-sm font-mono text-white"
              value={draft.formula || ''}
              onChange={(e) => setDraft((p) => ({ ...p, formula: e.target.value }))}
            />
          </div>

          <div className="border border-gray-700 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-gray-400 font-bold">Statistiche base oggetto</span>
              <button type="button" onClick={addStatBase} className="px-2 py-1 rounded bg-emerald-700 text-xs font-bold">+ Aggiungi</button>
            </div>
            {(draft.statistiche_base || []).map((row, idx) => (
              <div key={`sb-${idx}`} className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-7">
                  <SearchableSelect
                    label=""
                    value={row.stat_sigla}
                    options={(statsOptions || []).map((s) => ({ id: s.sigla, nome: `${s.sigla} - ${s.nome}` }))}
                    onChange={(v) => updateListItem('statistiche_base', idx, { stat_sigla: v })}
                  />
                </div>
                <div className="col-span-3">
                  <Input
                    label=""
                    type="number"
                    value={row.valore_base}
                    onChange={(v) => updateListItem('statistiche_base', idx, { valore_base: parseInt(v || '0', 10) || 0 })}
                  />
                </div>
                <div className="col-span-2">
                  <button type="button" onClick={() => removeListItem('statistiche_base', idx)} className="w-full px-2 py-2 rounded bg-red-700 text-xs font-bold">Rimuovi</button>
                </div>
              </div>
            ))}
          </div>

          <div className="border border-gray-700 rounded-lg p-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-[10px] uppercase tracking-wider text-gray-400 font-bold">Modificatori statistiche</span>
              <button type="button" onClick={addMod} className="px-2 py-1 rounded bg-amber-700 text-xs font-bold">+ Aggiungi</button>
            </div>
            {(draft.modificatori || []).map((row, idx) => (
              <div key={`mod-${idx}`} className="grid grid-cols-12 gap-2 items-center">
                <div className="col-span-5">
                  <SearchableSelect
                    label=""
                    value={row.stat_sigla}
                    options={(statsOptions || []).map((s) => ({ id: s.sigla, nome: `${s.sigla} - ${s.nome}` }))}
                    onChange={(v) => updateListItem('modificatori', idx, { stat_sigla: v })}
                  />
                </div>
                <div className="col-span-3">
                  <Input
                    label=""
                    type="number"
                    value={row.valore}
                    onChange={(v) => updateListItem('modificatori', idx, { valore: Number(v || 0) })}
                  />
                </div>
                <div className="col-span-2">
                  <Select
                    label=""
                    value={row.tipo_modificatore || 'ADD'}
                    options={[{ id: 'ADD', nome: 'ADD' }, { id: 'MOL', nome: 'MOL' }]}
                    onChange={(v) => updateListItem('modificatori', idx, { tipo_modificatore: v || 'ADD' })}
                  />
                </div>
                <div className="col-span-2">
                  <button type="button" onClick={() => removeListItem('modificatori', idx)} className="w-full px-2 py-2 rounded bg-red-700 text-xs font-bold">Rimuovi</button>
                </div>
              </div>
            ))}
          </div>

          <div className="border border-indigo-800/50 rounded-lg p-3 bg-indigo-950/20">
            <div className="text-[10px] uppercase tracking-wider text-indigo-300 font-bold mb-2">Anteprima in Game</div>
            <div className="rounded-lg border border-indigo-700/40 bg-black/25 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="text-sm font-bold text-indigo-100">{draft.nome || 'Oggetto runtime'}</div>
                <div className="text-[10px] uppercase tracking-wide text-indigo-300/90">
                  {draft.tipo_oggetto || 'FIS'} · slot {draft.slot_key || '-'}
                </div>
              </div>
              {draft.descrizione_effetto ? (
                <div className="text-xs text-gray-300 whitespace-pre-wrap">{draft.descrizione_effetto}</div>
              ) : (
                <div className="text-xs text-gray-500 italic">Nessuna descrizione effetto.</div>
              )}
              {draft.formula ? (
                <div className="text-xs font-mono text-emerald-300 break-all">Formula: {draft.formula}</div>
              ) : null}
              {Array.isArray(draft.modificatori) && draft.modificatori.length > 0 ? (
                <div className="text-xs text-gray-200">
                  <div className="font-bold text-gray-100 mb-1">Modificatori</div>
                  <ul className="space-y-1">
                    {draft.modificatori
                      .filter((m) => m.stat_sigla)
                      .map((m, i) => (
                        <li key={`prev-mod-${i}`} className="font-mono">
                          {m.stat_sigla} {m.tipo_modificatore || 'ADD'} {m.valore}
                        </li>
                      ))}
                  </ul>
                </div>
              ) : (
                <div className="text-xs text-gray-500 italic">Nessun modificatore statistico.</div>
              )}
              <div className="text-[11px] text-gray-400">
                Cariche max: <span className="font-mono text-gray-200">{Number(draft.cariche_massime || 0)}</span> · Durata:
                <span className="font-mono text-gray-200"> {Number(draft.durata_totale || 0)}s</span>
              </div>
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700 flex justify-end gap-2">
          {wizardError ? (
            <div className="mr-auto text-xs text-red-300 bg-red-900/30 border border-red-700/40 rounded px-2 py-1">
              {wizardError}
            </div>
          ) : null}
          <button type="button" onClick={onClose} className="px-4 py-2 bg-gray-700 rounded text-white text-sm">Annulla</button>
          <button
            type="button"
            onClick={() => {
              const err = validateDraft();
              if (err) {
                setWizardError(err);
                return;
              }
              setWizardError('');
              const cleaned = {
                nome: draft.nome || '',
                slot_key: draft.slot_key || 'melee',
                tipo_oggetto: draft.tipo_oggetto || 'FIS',
                descrizione_effetto: draft.descrizione_effetto || '',
                formula: draft.formula || '',
                statistiche_base: (draft.statistiche_base || []).filter((x) => x.stat_sigla),
                modificatori: (draft.modificatori || []).filter((x) => x.stat_sigla),
                cariche: { cariche_massime: Number(draft.cariche_massime || 0) },
                durata_totale: Number(draft.durata_totale || 0),
              };
              onApply?.(cleaned);
              onClose?.();
            }}
            className="px-4 py-2 bg-indigo-600 rounded text-white text-sm font-bold"
          >
            Applica al JSON runtime
          </button>
        </div>
      </div>
      <FormulaBuilderModal
        open={isObjFormulaBuilderOpen}
        onClose={() => setIsObjFormulaBuilderOpen(false)}
        onApply={handleApplyObjectFormulaBuilder}
        onLogout={onLogout}
        statsOptions={statsOptions}
        statisticheBase={(draft.statistiche_base || [])
          .map((row) => {
            const st = (statsOptions || []).find((s) => s.sigla === row.stat_sigla);
            if (!st) return null;
            return { statistica: st.id, valore_base: row.valore_base };
          })
          .filter(Boolean)}
        formulaValue={draft.formula}
        defaultFormulaType="attack"
      />
    </div>
  );
};

const Input = ({ label, value, onChange, type="text" }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <input type={type} className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-cyan-500 outline-none" value={value || ""} onChange={e => onChange(e.target.value)} />
    </div>
);

const Select = ({ label, value, options, onChange }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer focus:border-cyan-500 outline-none" value={value ? String(value) : ""} onChange={e => onChange(e.target.value)}>
        <option value="">- SELEZIONA -</option>
        {options.map(o => <option key={o.id} value={String(o.id)}>{o.nome}</option>)}
      </select>
    </div>
);

const SearchableSelect = ({
  label,
  value,
  options = [],
  onChange,
  placeholder = 'Cerca...',
  formatOptionLabel,
}) => {
    const wrapRef = useRef(null);
    const labelFor = (opt) => (formatOptionLabel ? formatOptionLabel(opt) : opt?.nome || '');
    const selectedOption = useMemo(
      () => (options || []).find((o) => String(o.id) === String(value ?? '')) || null,
      [options, value]
    );
    const [query, setQuery] = useState(() => (selectedOption ? labelFor(selectedOption) : ''));
    const [open, setOpen] = useState(false);

    useEffect(() => {
      setQuery(selectedOption ? labelFor(selectedOption) : '');
    }, [selectedOption?.id, selectedOption?.nome, formatOptionLabel]);

    useEffect(() => {
      const onDocClick = (ev) => {
        if (!wrapRef.current) return;
        if (!wrapRef.current.contains(ev.target)) setOpen(false);
      };
      document.addEventListener('mousedown', onDocClick);
      return () => document.removeEventListener('mousedown', onDocClick);
    }, []);

    const filtered = useMemo(() => {
      const q = String(query || '').trim().toLowerCase();
      if (!q) return options;
      return (options || []).filter((o) => labelFor(o).toLowerCase().includes(q));
    }, [options, query, formatOptionLabel]);

    const pick = (opt) => {
      setQuery(opt ? labelFor(opt) : '');
      onChange?.(opt ? String(opt.id) : '');
      setOpen(false);
    };

    return (
      <div className="w-full text-left" ref={wrapRef}>
        <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
        <div className="relative">
          <input
            type="text"
            className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-cyan-500 outline-none"
            value={query}
            placeholder={placeholder}
            onFocus={() => setOpen(true)}
            onChange={(e) => {
              setQuery(e.target.value);
              setOpen(true);
              if (!e.target.value) onChange?.('');
            }}
          />
          {open && (
            <div className="absolute z-30 mt-1 w-full rounded border border-gray-700 bg-gray-950 max-h-52 overflow-y-auto shadow-xl">
              {filtered.length === 0 ? (
                <div className="px-2 py-2 text-xs text-gray-500">Nessun risultato</div>
              ) : (
                filtered.map((opt) => (
                  <button
                    key={opt.id}
                    type="button"
                    className={`w-full text-left px-2 py-2 text-xs border-b border-gray-800 last:border-b-0 hover:bg-gray-800 ${
                      String(opt.id) === String(value ?? '') ? 'bg-cyan-900/25 text-cyan-100' : 'text-gray-200'
                    }`}
                    onClick={() => pick(opt)}
                  >
                    {labelFor(opt)}
                  </button>
                ))
              )}
            </div>
          )}
        </div>
      </div>
    );
};

export default TessituraEditor;