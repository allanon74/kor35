import React, { useState, useEffect } from 'react';
import { useCharacter } from '../CharacterContext';
import { getStatisticheList, staffUpdateTessitura, staffCreateTessitura } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import StatBaseInline from './inlines/StatBaseInline';
import RichTextEditor from '../RichTextEditor';

const TessituraEditor = ({ onBack, onCancel, onSave, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [statsOptions, setStatsOptions] = useState([]);
  
  // FIX: Default Data Merging
  const defaultData = {
    nome: '', testo: '', formula: '',
    aura_richiesta: null,
    elemento_principale: null,
    componenti: [],
    statistiche_base: []
  };

  const [formData, setFormData] = useState({ ...defaultData, ...initialData });

  // Alias per chiusura
  const handleClose = onCancel || onBack;

  useEffect(() => {
    getStatisticheList(onLogout).then(setStatsOptions);
  }, [onLogout]);

  // Calcolo livello property (numero componenti)
  const calculatedLevel = (formData.componenti || []).reduce((acc, curr) => acc + (parseInt(curr.valore) || 0), 0);

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
      const dataToSend = { 
        ...formData,
        aura_richiesta: formData.aura_richiesta?.id || formData.aura_richiesta || null,
        elemento_principale: formData.elemento_principale?.id || formData.elemento_principale || null,
        statistiche_base: (formData.statistiche_base || []).map(sb => ({
          ...sb,
          statistica: sb.statistica?.id || sb.statistica
        }))
      };
      
      if (onSave) {
        // APPROVAL MODE
        await onSave(dataToSend);
      } else {
        // STANDARD MODE
        if (formData.id) await staffUpdateTessitura(formData.id, dataToSend, onLogout);
        else await staffCreateTessitura(dataToSend, onLogout);
        alert("Tessitura salvata!");
        if (handleClose) handleClose();
      }
    } catch (e) { 
        console.error(e);
        alert("Errore: " + (e.message || "Errore sconosciuto")); 
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] text-white border border-gray-700 shadow-2xl">
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-cyan-400 uppercase tracking-tighter">
          {formData.id ? `Edit: ${formData.nome}` : 'Nuova Tessitura'}
        </h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-8 py-2 rounded-lg font-black text-sm text-white">
             {onSave ? 'APPROVA & CREA' : 'SALVA'}
           </button>
           {handleClose && (
             <button onClick={handleClose} className="bg-gray-700 px-6 py-2 rounded-lg font-bold text-sm text-white">ANNULLA</button>
           )}
        </div>
      </div>

      <div className="bg-gray-900/40 p-5 rounded-xl border border-gray-700/50 space-y-5 shadow-inner">
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Select label="Aura Richiesta" value={formData.aura_richiesta?.id || formData.aura_richiesta} 
                  options={punteggiList.filter(p => p.tipo === 'AU')} 
                  onChange={v => setFormData({...formData, aura_richiesta: v ? parseInt(v, 10) : null})} />
          <Select label="Elemento Principale" value={formData.elemento_principale?.id || formData.elemento_principale} 
                  options={punteggiList.filter(p => p.tipo === 'EL')} 
                  onChange={v => setFormData({...formData, elemento_principale: v ? parseInt(v, 10) : null})} />
        </div>
        <Input label="Formula Tessitura (es. {caratt} + 1d10)" value={formData.formula} onChange={v => setFormData({...formData, formula: v})} />
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="md:col-span-3">
            <Input label="Nome" value={formData.nome} onChange={v => setFormData({...formData, nome: v})} />
          </div>
          <div className="bg-black/20 p-2 rounded flex flex-col items-center justify-center">
             <span className="text-[9px] text-gray-500 uppercase font-black">Livello</span>
             <span className="text-xl font-bold text-cyan-400">{calculatedLevel}</span>
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

export default TessituraEditor;