import React, { useState, useEffect } from 'react';
import { useCharacter } from '../CharacterContext';
import { getStatisticheList, staffCreateInfusione, staffUpdateInfusione, getBodySlots } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import StatBaseInline from './inlines/StatBaseInline';
import StatModInline from './inlines/StatModInline';
import MultiSelectBodySlots from './MultiSelectBodySlots';
import RichTextEditor from '../RichTextEditor';

const InfusioneEditor = ({ onBack, onCancel, onSave, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [statsOptions, setStatsOptions] = useState([]);
  const allBodySlots = getBodySlots();
  
  // FIX: Unione corretta con defaults per evitare 'undefined' su array mancanti
  const defaultData = {
    nome: '', testo: '', formula_attacco: '',
    aura_richiesta: null, aura_infusione: null,
    tipo_risultato: 'POT', is_pesante: false,
    statistica_cariche: null, metodo_ricarica: '',
    costo_ricarica_crediti: 0, durata_attivazione: 0,
    slot_corpo_permessi: '', 
    componenti: [],
    statistiche_base: [],
    modificatori: []
  };

  const [formData, setFormData] = useState({ ...defaultData, ...initialData });

  // Alias per chiusura
  const handleClose = onCancel || onBack;

  const hasChargesData = !!(
    formData.statistica_cariche || 
    formData.costo_ricarica_crediti > 0 || 
    formData.durata_attivazione > 0 || 
    (formData.metodo_ricarica && formData.metodo_ricarica !== '')
  );
  const [isChargesOpen, setIsChargesOpen] = useState(hasChargesData);

  useEffect(() => {
    getStatisticheList(onLogout).then(setStatsOptions);
  }, [onLogout]);

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

  const handleSave = async () => {
    try {
      // 1. DEDUPLICAZIONE MODIFICATORI
      const modsMap = new Map();
      (formData.modificatori || []).forEach(mod => {
        const sId = mod.statistica?.id || mod.statistica;
        if (sId) {
          modsMap.set(sId, { 
            ...mod, 
            statistica: sId,
            id: undefined 
          });
        }
      });

      // 2. DEDUPLICAZIONE STATISTICHE BASE
      const baseMap = new Map();
      (formData.statistiche_base || []).forEach(sb => {
        const sId = sb.statistica?.id || sb.statistica;
        if (sId) {
          baseMap.set(sId, { 
            statistica: sId, 
            valore_base: sb.valore_base,
            id: undefined 
          });
        }
      });

      const dataToSend = { 
        ...formData,
        statistica_cariche: formData.statistica_cariche?.id || formData.statistica_cariche || null,
        aura_richiesta: formData.aura_richiesta?.id || formData.aura_richiesta || null,
        aura_infusione: formData.aura_infusione?.id || formData.aura_infusione || null,
        modificatori: Array.from(modsMap.values()),
        statistiche_base: Array.from(baseMap.values())
      };
      
      if (onSave) {
        // APPROVAL MODE
        await onSave(dataToSend);
      } else {
        // STANDARD MODE
        if (formData.id) await staffUpdateInfusione(formData.id, dataToSend, onLogout);
        else await staffCreateInfusione(dataToSend, onLogout);
        alert("Infusione salvata correttamente!");
        if (handleClose) handleClose();
      }
    } catch (e) {
      console.error(e);
      alert("Errore salvataggio: " + (e.message || "Controlla i dati."));
    }
  };

  const currentCaricheId = formData.statistica_cariche?.id || formData.statistica_cariche;

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] text-white shadow-2xl border border-gray-700">
      
      {/* HEADER */}
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-indigo-400 uppercase tracking-tighter">
          {formData.id ? `Editing: ${formData.nome}` : 'Nuova Infusione'}
        </h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-8 py-2 rounded-lg font-black text-sm transition-all shadow-lg text-white">
             {onSave ? 'APPROVA & CREA' : 'SALVA TECNICA'}
           </button>
           {handleClose && (
             <button onClick={handleClose} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-sm transition-all text-white">ANNULLA</button>
           )}
        </div>
      </div>

      {/* 2. IDENTITÀ, AURE E FORMULA */}
      <div className="bg-gray-900/40 p-5 rounded-xl border border-gray-700/50 shadow-inner space-y-5">
        
        {/* RIGA 1: AURE */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Select 
            label="Aura Richiesta (Requisito)" 
            value={formData.aura_richiesta?.id || formData.aura_richiesta} 
            options={punteggiList.filter(p => p.tipo === 'AU')} 
            onChange={v => setFormData({...formData, aura_richiesta: v ? parseInt(v, 10) : null})} 
          />
          <Select 
            label="Aura Infusione (Occupazione Slot)" 
            value={formData.aura_infusione?.id || formData.aura_infusione} 
            options={punteggiList.filter(p => p.tipo === 'AU')} 
            onChange={v => setFormData({...formData, aura_infusione: v ? parseInt(v, 10) : null})} 
          />
        </div>

        {/* RIGA 2: Formula Attacco */}
        <div className="bg-indigo-500/5 p-3 rounded-lg border border-indigo-500/20">
            <Input label="Formula Attacco (Parametri e Dadi)" placeholder="es. @for + 1d10 + @potenza_materia" value={formData.formula_attacco} onChange={v => setFormData({...formData, formula_attacco: v})} />
        </div>
        
        {/* RIGA 3: Nome, Tipo e Flag */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-2">
            <Input label="Nome Infusione" value={formData.nome} onChange={v => setFormData({...formData, nome: v})} />
          </div>
          <Select label="Tipo Risultato" value={formData.tipo_risultato} 
                  options={[{id: 'POT', nome: 'Potenziamento'}, {id: 'AUM', nome: 'Aumento Corporeo'}]} 
                  onChange={v => setFormData({...formData, tipo_risultato: v})} />
          <div className="flex items-center gap-3 pt-6 justify-center bg-black/20 rounded-lg">
              <input type="checkbox" className="w-5 h-5 rounded accent-indigo-500 cursor-pointer" id="is_pesante" checked={formData.is_pesante} onChange={e => setFormData({...formData, is_pesante: e.target.checked})} />
              <label htmlFor="is_pesante" className="text-[10px] font-black uppercase text-gray-400 tracking-widest cursor-pointer">Oggetto Pesante</label>
          </div>
        </div>
      </div>

      {/* 3. DESCRIZIONE */}
      <RichTextEditor label="Descrizione Narrativa e Tecnica" value={formData.testo} onChange={v => setFormData({...formData, testo: v})} />

      {/* 4. SLOT CORPOREI */}
      {formData.tipo_risultato === 'AUM' && (
        <div className="animate-in fade-in slide-in-from-top-2 duration-300">
            <MultiSelectBodySlots value={formData.slot_corpo_permessi} allSlots={allBodySlots} onChange={v => setFormData({...formData, slot_corpo_permessi: v})} />
        </div>
      )}

      {/* 5. SEZIONE CARICHE */}
      <div className="border border-indigo-500/20 rounded-xl overflow-hidden shadow-lg">
        <button onClick={() => setIsChargesOpen(!isChargesOpen)} className="w-full flex justify-between items-center p-4 bg-indigo-900/20 hover:bg-indigo-900/30 transition-colors">
          <h3 className="text-xs font-black uppercase tracking-widest text-indigo-300">{isChargesOpen ? '▼' : '▶'} Gestione Cariche e Ricarica</h3>
          <span className="text-[9px] text-indigo-500 uppercase">{isChargesOpen ? 'Chiudi' : 'Espandi'}</span>
        </button>
        {isChargesOpen && (
          <div className="p-5 bg-indigo-900/5 space-y-4 border-t border-indigo-500/10 animate-in slide-in-from-top-2 duration-200">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <Select label="Statistica Cariche" value={currentCaricheId} options={statsOptions} onChange={v => setFormData({...formData, statistica_cariche: v ? parseInt(v, 10) : null})} />
                <Input label="Costo Ricarica (Crediti)" type="number" value={formData.costo_ricarica_crediti} onChange={v => setFormData({...formData, costo_ricarica_crediti: v})} />
                <Input label="Durata Attivazione (sec)" type="number" value={formData.durata_attivazione} onChange={v => setFormData({...formData, durata_attivazione: v})} />
            </div>
            <RichTextEditor label="Metodo e Note di Ricarica" value={formData.metodo_ricarica} onChange={v => setFormData({...formData, metodo_ricarica: v})} />
          </div>
        )}
      </div>

      {/* 6. COMPONENTI CARATTERISTICHE */}
      <CharacteristicInline 
        items={formData.componenti || []} 
        options={punteggiList.filter(p => p.tipo === 'CA')}
        onAdd={() => setFormData({...formData, componenti: [...(formData.componenti || []), {caratteristica:'', valore:1}]})}
        onChange={(i, f, v) => updateInline('componenti', i, f, v)}
        onRemove={(i) => setFormData({...formData, componenti: formData.componenti.filter((_, idx) => idx !== i)})}
      />

      {/* 7. STATISTICHE BASE */}
      <StatBaseInline 
        items={formData.statistiche_base || []} 
        options={statsOptions} 
        onChange={(i, f, v) => updateInline('statistiche_base', i, f, v)} 
      />

      {/* 8. MODIFICATORI */}
      <StatModInline 
        items={formData.modificatori || []} 
        options={statsOptions}
        auraOptions={punteggiList.filter(p => p.tipo === 'AU')}
        elementOptions={punteggiList.filter(p => p.tipo === 'EL')}
        onAdd={() => setFormData({...formData, modificatori: [...(formData.modificatori || []), {statistica: null, valore: 0, tipo_modificatore:'ADD', usa_limitazione_aura: false, limit_a_aure: [], usa_limitazione_elemento: false, limit_a_elementi: [], usa_condizione_text: false, condizione_text: ''}]})}
        onChange={(i, f, v) => updateInline('modificatori', i, f, v)}
        onRemove={(i) => setFormData({...formData, modificatori: formData.modificatori.filter((_, idx) => idx !== i)})}
      />
    </div>
  );
};

const Input = ({ label, value, onChange, type="text", placeholder="" }) => (
  <div className="w-full text-left">
    <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
    <input type={type} placeholder={placeholder} className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-indigo-500 outline-none shadow-inner" value={value || ""} onChange={e => onChange(e.target.value)} />
  </div>
);

const Select = ({ label, value, options, onChange }) => (
  <div className="w-full text-left">
    <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
    <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer focus:border-indigo-500 outline-none" value={value ? String(value) : ""} onChange={e => onChange(e.target.value)}>
      <option value="">- SELEZIONA -</option>
      {options.map(o => <option key={o.id} value={String(o.id)}>{o.nome}</option>)}
    </select>
  </div>
);

export default InfusioneEditor;