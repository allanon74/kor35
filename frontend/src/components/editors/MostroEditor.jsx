import React, { useState } from 'react';
import { staffUpdateMostroTemplate, staffCreateMostroTemplate } from '../../api'; // Assicurati di creare queste funzioni
import RichTextEditor from '../RichTextEditor';
import { Trash, Plus, GripVertical } from 'lucide-react';

const MostroEditor = ({ onBack, onLogout, initialData = null }) => {
  const [formData, setFormData] = useState(initialData || {
    nome: '', 
    punti_vita_base: 1, 
    armatura_base: 0, 
    guscio_base: 0,
    note_generali: '', 
    costume: '',
    attacchi: [] 
  });

  // Gestione Attacchi Inline
  const addAttacco = () => {
    setFormData({
        ...formData,
        attacchi: [...(formData.attacchi || []), { nome_attacco: '', descrizione_danno: '', ordine: (formData.attacchi?.length || 0) + 1 }]
    });
  };

  const updateAttacco = (index, field, value) => {
    const newAttacchi = [...formData.attacchi];
    newAttacchi[index] = { ...newAttacchi[index], [field]: value };
    setFormData({ ...formData, attacchi: newAttacchi });
  };

  const removeAttacco = (index) => {
    const newAttacchi = formData.attacchi.filter((_, i) => i !== index);
    setFormData({ ...formData, attacchi: newAttacchi });
  };

  const handleSave = async () => {
    try {
      // Se l'API richiede serializzatori nested scrivibili, invia tutto l'oggetto.
      // Altrimenti dovrai gestire il salvataggio degli attacchi separatamente.
      // Qui assumo che il backend accetti la lista "attacchi" nested nel JSON.
      
      if (formData.id) await staffUpdateMostroTemplate(formData.id, formData, onLogout);
      else await staffCreateMostroTemplate(formData, onLogout);
      
      alert("Salvato correttamente!"); 
      onBack();
    } catch (e) { 
        console.error(e);
        alert("Errore durante il salvataggio: " + e.message); 
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-5xl mx-auto overflow-y-auto max-h-[92vh] border border-gray-700 shadow-2xl text-white">
      {/* Header */}
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-red-400 uppercase tracking-tighter">
            {formData.id ? `Edit: ${formData.nome}` : 'Nuovo Template Mostro'}
        </h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-8 py-2 rounded-lg font-black text-sm shadow-lg">SALVA</button>
           <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-sm">ANNULLA</button>
        </div>
      </div>

      {/* Dati Base */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-900/40 p-4 rounded-xl border border-gray-700/50">
        <div className="md:col-span-4">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Nome Mostro / Tipologia</label>
            <input 
                className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm font-bold text-white focus:border-red-500 outline-none" 
                value={formData.nome} 
                onChange={e => setFormData({...formData, nome: e.target.value})} 
                placeholder="Es. Sgherro Cybernetico, Zombie..."
            />
        </div>
        
        <div className="bg-red-900/10 p-2 rounded border border-red-900/20">
            <label className="text-[10px] text-red-500 uppercase font-black block mb-1">Punti Vita Base</label>
            <input type="number" className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm font-mono" value={formData.punti_vita_base} onChange={e => setFormData({...formData, punti_vita_base: parseInt(e.target.value)})} />
        </div>
        <div className="bg-gray-700/10 p-2 rounded border border-gray-700/20">
            <label className="text-[10px] text-gray-400 uppercase font-black block mb-1">Armatura Base</label>
            <input type="number" className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm font-mono" value={formData.armatura_base} onChange={e => setFormData({...formData, armatura_base: parseInt(e.target.value)})} />
        </div>
        <div className="bg-indigo-900/10 p-2 rounded border border-indigo-900/20">
            <label className="text-[10px] text-indigo-400 uppercase font-black block mb-1">Guscio Base</label>
            <input type="number" className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm font-mono" value={formData.guscio_base} onChange={e => setFormData({...formData, guscio_base: parseInt(e.target.value)})} />
        </div>
      </div>

      {/* Rich Text Editors */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-2">
            <RichTextEditor 
                label="Costume & Tratti Visivi" 
                value={formData.costume} 
                onChange={v => setFormData({...formData, costume: v})} 
            />
          </div>
          <div className="space-y-2">
            <RichTextEditor 
                label="Note Generali & Comportamento" 
                value={formData.note_generali} 
                onChange={v => setFormData({...formData, note_generali: v})} 
            />
          </div>
      </div>

      {/* Sezione Attacchi */}
      <div className="bg-gray-900/40 p-4 rounded-xl border border-gray-700/50">
        <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-black uppercase text-amber-500">Attacchi & Capacità Offensive</h3>
            <button onClick={addAttacco} className="flex items-center gap-1 bg-amber-600/20 text-amber-500 px-3 py-1 rounded text-xs font-bold hover:bg-amber-600 hover:text-white transition-colors">
                <Plus size={14} /> AGGIUNGI ATTACCO
            </button>
        </div>
        
        <div className="space-y-2">
            {formData.attacchi && formData.attacchi.map((attacco, index) => (
                <div key={index} className="flex items-start gap-2 bg-gray-950 p-2 rounded border border-gray-800">
                    <div className="pt-2 text-gray-600 cursor-move"><GripVertical size={16}/></div>
                    <div className="flex-1 grid grid-cols-1 md:grid-cols-3 gap-2">
                        <input 
                            className="bg-gray-900 p-2 rounded border border-gray-700 text-xs font-bold text-amber-100 placeholder-gray-600" 
                            placeholder="Nome colpo (es. Artigli)"
                            value={attacco.nome_attacco}
                            onChange={e => updateAttacco(index, 'nome_attacco', e.target.value)}
                        />
                        <div className="md:col-span-2">
                            <input 
                                className="w-full bg-gray-900 p-2 rounded border border-gray-700 text-xs text-gray-300 font-mono placeholder-gray-600" 
                                placeholder="Effetto (es. 2 Fisici, Sbilanciare)"
                                value={attacco.descrizione_danno}
                                onChange={e => updateAttacco(index, 'descrizione_danno', e.target.value)}
                            />
                        </div>
                    </div>
                    <button onClick={() => removeAttacco(index)} className="p-2 text-red-700 hover:text-red-500 transition-colors">
                        <Trash size={16} />
                    </button>
                </div>
            ))}
            {(!formData.attacchi || formData.attacchi.length === 0) && (
                <div className="text-center py-4 text-gray-600 text-xs italic">Nessun attacco definito.</div>
            )}
        </div>
      </div>
    </div>
  );
};

export default MostroEditor;