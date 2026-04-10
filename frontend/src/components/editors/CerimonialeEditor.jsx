import React, { useState } from 'react';
import { useCharacter } from '../CharacterContext';
import { staffUpdateCerimoniale, staffCreateCerimoniale } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import RichTextEditor from '../RichTextEditor';

// Aggiunto onCancel e onSave ai props
const CerimonialeEditor = ({ onBack, onCancel, onSave, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  
  // FIX: Uniamo initialData ai default per non perdere i campi non presenti nella proposta
  const defaultData = {
    nome: '', testo: '', formula_attacco: '',
    aura_richiesta: null,
    prerequisiti: '',
    svolgimento: '',
    effetto: '',
    liv: 1,
    componenti: []
  };

  const [formData, setFormData] = useState({ ...defaultData, ...initialData });

  // Gestione alias per chiusura
  const handleClose = onCancel || onBack;

  const updateInline = (key, index, field, value) => {
    const newList = [...(formData[key] || [])]; // Protezione array vuoto
    newList[index] = { ...newList[index], [field]: value };
    setFormData({ ...formData, [key]: newList });
  };

  const handleSave = async () => {
    try {
      const dataToSend = { 
        ...formData,
        aura_richiesta: formData.aura_richiesta?.id || formData.aura_richiesta || null
      };

      if (onSave) {
        // MODALITÀ APPROVAZIONE PROPOSTA
        // Passiamo i dati al padre (StaffProposalTab) che gestirà la chiamata API di approvazione
        await onSave(dataToSend);
      } else {
        // MODALITÀ EDITOR STANDARD
        if (formData.id) await staffUpdateCerimoniale(formData.id, dataToSend, onLogout);
        else await staffCreateCerimoniale(dataToSend, onLogout);
        alert("Cerimoniale salvato!");
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
        <h2 className="text-xl font-bold text-amber-400 uppercase tracking-tighter">
          {formData.id ? `Edit Cerimoniale: ${formData.nome}` : 'Nuovo Cerimoniale'}
        </h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-8 py-2 rounded-lg font-black text-sm text-white">
             {onSave ? 'APPROVA & CREA' : 'SALVA'}
           </button>
           {handleClose && (
               <button onClick={handleClose} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-sm text-white">ANNULLA</button>
           )}
        </div>
      </div>

      <div className="bg-gray-900/40 p-5 rounded-xl border border-gray-700/50 space-y-5">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <Select label="Aura" value={formData.aura_richiesta?.id || formData.aura_richiesta} 
                    options={punteggiList.filter(p => p.tipo === 'AU')} 
                    onChange={v => setFormData({...formData, aura_richiesta: v ? parseInt(v, 10) : null})} />
            <div className="md:col-span-2">
                <Input label="Nome Cerimoniale" value={formData.nome} onChange={v => setFormData({...formData, nome: v})} />
            </div>
            <Input label="Livello (liv)" type="number" value={formData.liv} onChange={v => setFormData({...formData, liv: v})} />
        </div>
      </div>

      <RichTextEditor label="Effetto Tecnico / Formula (HTML)" value={formData.effetto} onChange={v => setFormData({...formData, effetto: v})} />
      <RichTextEditor label="Prerequisiti e Materiali" value={formData.prerequisiti} onChange={v => setFormData({...formData, prerequisiti: v})} />
      <RichTextEditor label="Svolgimento e Testo Narrativo" value={formData.testo} onChange={v => setFormData({...formData, testo: v})} />

      <CharacteristicInline 
        items={formData.componenti || []} 
        options={punteggiList.filter(p => p.tipo === 'CA')}
        onAdd={() => setFormData({...formData, componenti: [...(formData.componenti || []), {caratteristica:'', valore:1}]})}
        onChange={(i, f, v) => updateInline('componenti', i, f, v)}
        onRemove={(i) => setFormData({...formData, componenti: formData.componenti.filter((_, idx) => idx !== i)})}
      />
    </div>
  );
};

// Helper locali...
const Input = ({ label, value, onChange, type="text" }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <input type={type} className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-amber-500 outline-none shadow-inner" value={value || ""} onChange={e => onChange(e.target.value)} />
    </div>
);

const Select = ({ label, value, options, onChange }) => (
    <div className="w-full text-left">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1 tracking-tighter">{label}</label>
      <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer focus:border-amber-500 outline-none" value={value ? String(value) : ""} onChange={e => onChange(e.target.value)}>
        <option value="">- SELEZIONA -</option>
        {options.map(o => <option key={o.id} value={String(o.id)}>{o.nome}</option>)}
      </select>
    </div>
);

export default CerimonialeEditor;