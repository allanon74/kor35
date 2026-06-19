import React, { useState, useEffect } from 'react';
import { useCharacter } from '../CharacterContext';
import {
  staffUpdateOggettoBase,
  staffCreateOggettoBase,
  staffGetClassiOggetto,
  staffPropagaOggettoBaseIstanze,
} from '../../api';
import StatBaseInline from './inlines/StatBaseInline';
import StatModInline from './inlines/StatModInline';
import RichTextEditor from '../RichTextEditor'; // Importazione corretta
import EditorSaveActions from './EditorSaveActions';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import CatalogoAccademiaFlags from './CatalogoAccademiaFlags';
import FormulaBuilderModal from './FormulaBuilderModal';
import SearchableSelect from './SearchableSelect';

const TIPO_CHOICES = [
    {id:'FIS', nome:'Fisico'}, {id:'MAT', nome:'Materia'}, {id:'MOD', nome:'Mod'},
    {id:'INN', nome:'Innesto'}, {id:'MUT', nome:'Mutazione'}, {id:'AUM', nome:'Aumento'}, {id:'POT', nome:'Potenziamento'}
];
const SLOT_FISICI_CHOICES = [
  { id: 'head', nome: 'Testa' }, { id: 'neck', nome: 'Collo' }, { id: 'vest', nome: 'Veste' },
  { id: 'shoulders', nome: 'Spalle' }, { id: 'arms', nome: 'Braccia' }, { id: 'fingers', nome: 'Dita' },
  { id: 'feet', nome: 'Piedi' }, { id: 'belt', nome: 'Cintura' }, { id: 'armor', nome: 'Armatura' },
  { id: 'melee', nome: 'Armi Mischia' }, { id: 'ranged', nome: 'Armi Distanza' },
  { id: 'focus', nome: 'Focus' }, { id: 'shield', nome: 'Scudo' },
];
const parseSlots = (raw) => {
  if (!raw) return [];
  if (Array.isArray(raw)) return raw;
  return String(raw).split(',').map((s) => s.trim()).filter(Boolean);
};

const OggettoBaseEditor = ({ onBack, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [classi, setClassi] = useState([]);
  const [saving, setSaving] = useState(false);
  const [propagating, setPropagating] = useState(false);
  const [status, setStatus] = useState({ type: 'success', message: '' });
  const [isFormulaBuilderOpen, setIsFormulaBuilderOpen] = useState(false);
  
  const [formData, setFormData] = useState(initialData || {
    nome: '', 
    descrizione: '', 
    tipo_oggetto: 'FIS', 
    classe_oggetto: null, 
    costo: 0, 
    is_tecnologico: false, 
    is_pesante: false, 
    attacco_base: '',
    slot_fisici_possibili: [],
    in_vendita: true,
    escluso_negozio_ufficiale: false,
    non_vendibile: false,
    statistiche_base: [], 
    statistiche_modificatori: []
  });

  useEffect(() => {
    if (!initialData) return;
    setFormData((prev) => ({
      ...prev,
      ...initialData,
      slot_fisici_possibili: parseSlots(initialData.slot_fisici_possibili),
    }));
  }, [initialData]);

  useEffect(() => { staffGetClassiOggetto(onLogout).then(setClassi); }, []);

  // Gestione aggiornamento liste (statistiche base e mod)
  const updateInline = (key, index, field, value) => {
    const newList = [...formData[key]];
    if (index === -1) {
        // Creazione nuova riga
        const exists = newList.find(it => (it.statistica?.id || it.statistica) === value.statId);
        if (!exists) {
            const newRecord = { statistica: value.statId };
            if (key === 'statistiche_base') {
                newRecord.valore_base = value.value;
            } else {
                newRecord.valore = value.value;
                newRecord.tipo_modificatore = 'ADD'; 
            }
            newList.push(newRecord);
        }
    } else {
        // Aggiornamento riga esistente
        newList[index] = { ...newList[index], [field]: value };
    }
    setFormData({ ...formData, [key]: newList });
  };

  const handleSave = async (mode = 'save_close') => {
    try {
        setSaving(true);
        const getId = (item) => item?.id || item || null;
        
        // Funzione robusta per pulire le statistiche prima dell'invio
        const prepareStats = (list, isMod = false) => {
            return list.map(item => {
                const statId = typeof item.statistica === 'object' ? item.statistica.id : item.statistica;
                // Base object structure
                const cleanItem = { statistica: statId };
                
                if (isMod) {
                    cleanItem.valore = parseInt(item.valore || 0);
                    cleanItem.tipo_modificatore = item.tipo_modificatore || 'ADD';
                } else {
                    cleanItem.valore_base = parseInt(item.valore_base || 0);
                }
                return cleanItem;
            }).filter(i => i.statistica); // Rimuove entry vuote
        };

        const data = { 
            ...formData, 
            classe_oggetto: getId(formData.classe_oggetto),
            slot_fisici_possibili: (formData.slot_fisici_possibili || []).join(','),
            statistiche_base: prepareStats(formData.statistiche_base, false),
            statistiche_modificatori: prepareStats(formData.statistiche_modificatori, true)
        };

        const isSaveAsNew = mode === 'save_as_new';
        const isExisting = !!formData.id && !isSaveAsNew;
        const saved = isExisting
            ? await staffUpdateOggettoBase(formData.id, data, onLogout)
            : await staffCreateOggettoBase(data, onLogout);
        const recordName = saved?.nome || data.nome || 'Record';
        if (mode === 'save_as_new') setStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
        if (mode === 'save_continue') setStatus({ type: 'success', message: `"${recordName}" salvato.` });
        if (mode === 'save_new_blank') {
            setFormData({
                nome: '', descrizione: '', tipo_oggetto: 'FIS', classe_oggetto: null, costo: 0,
                is_tecnologico: false, is_pesante: false, attacco_base: '', in_vendita: true,
                escluso_negozio_ufficiale: false, non_vendibile: false,
                slot_fisici_possibili: [],
                statistiche_base: [], statistiche_modificatori: [],
            });
            setStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
        }
        if (mode === 'save_close') onBack();
        if (mode !== 'save_close' && mode !== 'save_new_blank' && saved?.id) {
            setFormData((prev) => ({
              ...prev,
              ...saved,
              slot_fisici_possibili: parseSlots(saved.slot_fisici_possibili),
            }));
        }
    } catch (e) { 
        console.error("Errore Salvataggio:", e);
        setStatus({ type: 'error', message: `Errore salvataggio: ${e.message || 'Controlla i dati.'}` });
    } finally {
        setSaving(false);
    }
  };

  const handlePropagaIstanze = async () => {
    if (!formData.id) return;
    try {
      setPropagating(true);
      const preview = await staffPropagaOggettoBaseIstanze(formData.id, { dryRun: true }, onLogout);
      const count = Number(preview?.count || 0);
      if (count === 0) {
        setStatus({
          type: 'success',
          message: 'Nessuna istanza Oggetto collegata a questo template.',
        });
        return;
      }
      const ok = window.confirm(
        `Propagare il template "${formData.nome}" su ${count} istanz${count === 1 ? 'a' : 'e'}?\n\n`
        + 'Verranno aggiornati nome, descrizione, tipo, classe, slot, flags, formula attacco e statistiche.\n'
        + 'Non verranno modificati: costo acquisto, equipaggiamento, cariche, potenziamenti montati, inventario.'
      );
      if (!ok) return;
      const result = await staffPropagaOggettoBaseIstanze(formData.id, { dryRun: false }, onLogout);
      const updated = Number(result?.updated || 0);
      setStatus({
        type: 'success',
        message: `Template propagato su ${updated} istanz${updated === 1 ? 'a' : 'e'}.`,
      });
    } catch (e) {
      console.error('Errore propagazione template:', e);
      setStatus({
        type: 'error',
        message: `Errore propagazione: ${e.message || 'operazione non riuscita'}`,
      });
    } finally {
      setPropagating(false);
    }
  };

  const handleApplyFormulaBuilder = ({ statsByParam, formulaText, customText, controlledParams, formulaBuilderSelezioni }) => {
    const statsOptions = (punteggiList || []).filter((p) => p.tipo === 'ST');
    const controlledSet = new Set(controlledParams || []);
    const byParam = new Map(statsOptions.map((s) => [s.parametro, s]));
    const current = formData.statistiche_base || [];
    const kept = current.filter((item) => {
      const statId = item.statistica?.id || item.statistica;
      const stat = statsOptions.find((s) => String(s.id) === String(statId));
      return !(stat?.parametro && controlledSet.has(stat.parametro));
    });
    const fromBuilder = Object.entries(statsByParam || {})
      .filter(([param, value]) => byParam.get(param) && Number(value) > 0)
      .map(([param, value]) => ({ statistica: byParam.get(param).id, valore_base: Number(value) }));
    const mergedFormula = [formulaText, customText].filter(Boolean).join(' ').trim();
    setFormData((prev) => ({
      ...prev,
      attacco_base: mergedFormula,
      statistiche_base: [...kept, ...fromBuilder],
      formula_builder_selezioni: formulaBuilderSelezioni || {},
    }));
  };

  const Select = ({ label, value, options, onChange, placeholder = '- SELEZIONA -' }) => (
    <div className="w-full">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">{label}</label>
      <SearchableSelect
        options={options}
        value={value || ''}
        onChange={onChange}
        placeholder={placeholder}
      />
    </div>
  );

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto border border-gray-700 shadow-2xl text-white overflow-y-auto max-h-[92vh]">
      
      {/* Header */}
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-blue-400 uppercase tracking-tighter">
            {formData.id ? `Edit Template: ${formData.nome}` : 'Nuovo Oggetto Base'}
        </h2>
        <EditorSaveActions
          onSave={() => handleSave('save_close')}
          onSaveAndContinue={() => handleSave('save_continue')}
          onSaveAsNew={formData.id ? () => handleSave('save_as_new') : null}
          onSaveAndNew={() => handleSave('save_new_blank')}
          onCancel={onBack}
          saving={saving}
          saveLabel="Salva"
          statusMessage={status.message}
          statusType={status.type}
        />
      </div>

      {/* Dati Principali */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-800 space-y-4">
        
        {/* Riga 1: Nome e Tipo */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
                <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Nome Template</label>
                <input className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm focus:border-blue-500 outline-none text-white font-bold" 
                    value={formData.nome} onChange={e => setFormData({...formData, nome: e.target.value})} />
            </div>
            <Select label="Tipo Oggetto" value={formData.tipo_oggetto} options={TIPO_CHOICES} onChange={v => setFormData({...formData, tipo_oggetto: v})} />
        </div>

        {/* Riga 2: Classe e Costo */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <Select label="Classe Oggetto" value={formData.classe_oggetto?.id || formData.classe_oggetto} options={classi} onChange={v => setFormData({...formData, classe_oggetto: v})} />
            <div>
                <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Costo (CR)</label>
                <input type="number" className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm focus:border-blue-500 outline-none text-amber-400 font-mono" 
                    value={formData.costo} onChange={e => setFormData({...formData, costo: e.target.value})} />
            </div>
        </div>
        {formData.tipo_oggetto === 'FIS' && (
          <div>
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-2">Slot fisici consentiti</label>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
              {SLOT_FISICI_CHOICES.map((slot) => {
                const checked = (formData.slot_fisici_possibili || []).includes(slot.id);
                return (
                  <label key={slot.id} className="flex items-center gap-2 p-2 rounded border border-gray-700 bg-gray-950 cursor-pointer">
                    <input
                      type="checkbox"
                      className="accent-blue-500 w-4 h-4"
                      checked={checked}
                      onChange={(e) => {
                        const current = new Set(formData.slot_fisici_possibili || []);
                        if (e.target.checked) current.add(slot.id);
                        else current.delete(slot.id);
                        setFormData({ ...formData, slot_fisici_possibili: Array.from(current) });
                      }}
                    />
                    {slot.nome}
                  </label>
                );
              })}
            </div>
          </div>
        )}

        {/* Riga 3: Flags */}
        <div className="flex flex-wrap gap-6 pt-2 border-t border-gray-800 mt-2">
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-blue-300 transition-colors">
                <input type="checkbox" className="accent-blue-500 w-4 h-4" checked={formData.in_vendita} onChange={e => setFormData({...formData, in_vendita: e.target.checked})} /> 
                In Accademia
            </label>
            <CatalogoAccademiaFlags formData={formData} setFormData={setFormData} />
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-red-300 transition-colors">
                <input type="checkbox" className="accent-red-500 w-4 h-4" checked={formData.is_pesante} onChange={e => setFormData({...formData, is_pesante: e.target.checked})} /> 
                Pesante (OGP)
            </label>
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-emerald-300 transition-colors">
                <input type="checkbox" className="accent-emerald-500 w-4 h-4" checked={formData.is_tecnologico} onChange={e => setFormData({...formData, is_tecnologico: e.target.checked})} /> 
                Tecnologico
            </label>
        </div>
      </div>

      {/* Attacco Base (Riga Isolata) */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-800">
            <label className="text-[10px] text-red-500 uppercase font-black block mb-1">Formula Attacco Base</label>
            <input className="w-full bg-gray-950 p-3 rounded border border-gray-700 text-sm focus:border-red-500 outline-none text-red-300 font-mono tracking-wide" 
                placeholder="Es. {forza} Danni Contundenti + 2"
                value={formData.attacco_base || ''} onChange={e => setFormData({...formData, attacco_base: e.target.value})} />
            <div className="mt-2 flex justify-end">
              <button
                type="button"
                onClick={() => setIsFormulaBuilderOpen(true)}
                className="px-3 py-1 rounded bg-blue-700 hover:bg-blue-600 text-xs font-bold uppercase tracking-wide"
              >
                Costruisci formula
              </button>
            </div>
            <p className="text-[9px] text-gray-600 mt-1 italic">Usa le parentesi graffe per le variabili dinamiche, es: &#123;forza&#125;</p>
      </div>

      {/* Descrizione (Rich Text) */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-800">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-2">Descrizione Dettagliata</label>
            <div className="bg-gray-950 rounded-lg border border-gray-700 overflow-hidden min-h-[150px]">
                <RichTextEditor 
                    value={formData.descrizione || ''} 
                    onChange={val => setFormData({...formData, descrizione: val})} 
                />
            </div>
      </div>

      {/* Statistiche Base (Piena Larghezza) */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-800">
          <h3 className="text-xs font-black uppercase text-indigo-400 mb-4 pb-2 border-b border-gray-800">Statistiche Base Richieste</h3>
          <StatBaseInline 
            items={formData.statistiche_base} 
            options={punteggiList.filter(p => p.tipo === 'ST')} 
            onChange={(i, f, v) => updateInline('statistiche_base', i, f, v)}
          />
      </div>
      
      {/* Modificatori (Piena Larghezza) */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-800">
          <h3 className="text-xs font-black uppercase text-emerald-400 mb-4 pb-2 border-b border-gray-800">Modificatori Applicati (Bonus/Malus)</h3>
          <StatModInline 
            items={formData.statistiche_modificatori} 
            options={punteggiList.filter(p => p.tipo === 'ST')} 
            auraOptions={punteggiList.filter(p => p.tipo === 'AU')} 
            elementOptions={punteggiList.filter(p => p.tipo === 'EL')}
            showSoloOggettoOspitante
            onAdd={() => setFormData({...formData, statistiche_modificatori: [...formData.statistiche_modificatori, {statistica:'', valore:0, tipo_modificatore:'ADD', solo_oggetto_ospitante: false}]})} 
            onChange={(i,f,v) => updateInline('statistiche_modificatori', i, f, v)}
            onRemove={i => setFormData({...formData, statistiche_modificatori: formData.statistiche_modificatori.filter((_,idx)=>idx!==i)})} 
          />
      </div>

      {formData.id && (
        <div className="bg-amber-950/20 p-4 rounded-xl border border-amber-700/40 space-y-3">
          <h3 className="text-xs font-black uppercase text-amber-300 tracking-widest">
            Propaga template alle istanze
          </h3>
          <p className="text-xs text-amber-100/80 leading-relaxed">
            Applica questo modello a tutti gli oggetti creati dal negozio con{' '}
            <code className="text-amber-200">oggetto_base_generatore</code> collegato a questo template.
            Utile dopo aver corretto formula, statistiche o descrizione nel listino.
          </p>
          <button
            type="button"
            onClick={handlePropagaIstanze}
            disabled={propagating || saving}
            className="px-4 py-2 rounded bg-amber-700 hover:bg-amber-600 disabled:opacity-50 text-xs font-bold uppercase tracking-wide"
          >
            {propagating ? 'Propagazione...' : 'Propaga alle istanze collegate'}
          </button>
        </div>
      )}

      <StaffMinigiocoQrSection qrcodeId={formData.qrcode_id} onLogout={onLogout} />

      <FormulaBuilderModal
        open={isFormulaBuilderOpen}
        onClose={() => setIsFormulaBuilderOpen(false)}
        onApply={handleApplyFormulaBuilder}
        onLogout={onLogout}
        statsOptions={punteggiList.filter((p) => p.tipo === 'ST')}
        statisticheBase={formData.statistiche_base || []}
        formulaValue={formData.attacco_base}
        entityName={formData.nome}
        defaultFormulaType="attack"
        savedSelections={formData.formula_builder_selezioni}
        savedFormulaType={formData.formula_builder_selezioni?.formula_type}
      />

export default OggettoBaseEditor;