import React, { useState, useEffect } from 'react';
import { useCharacter } from '../CharacterContext';
import { staffUpdateOggettoBase, staffCreateOggettoBase, staffGetClassiOggetto } from '../../api';
import StatBaseInline from './inlines/StatBaseInline';
import StatModInline from './inlines/StatModInline';
import RichTextEditor from '../RichTextEditor'; // Importazione corretta
import { ArrowLeft, Save } from 'lucide-react';

const TIPO_CHOICES = [
    {id:'FIS', nome:'Fisico'}, {id:'MAT', nome:'Materia'}, {id:'MOD', nome:'Mod'},
    {id:'INN', nome:'Innesto'}, {id:'MUT', nome:'Mutazione'}, {id:'AUM', nome:'Aumento'}, {id:'POT', nome:'Potenziamento'}
];

const OggettoBaseEditor = ({ onBack, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [classi, setClassi] = useState([]);
  
  const [formData, setFormData] = useState(initialData || {
    nome: '', 
    descrizione: '', 
    tipo_oggetto: 'FIS', 
    classe_oggetto: null, 
    costo: 0, 
    is_tecnologico: false, 
    is_pesante: false, 
    attacco_base: '',
    in_vendita: true,
    statistiche_base: [], 
    statistiche_modificatori: []
  });

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

  const handleSave = async () => {
    try {
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
            statistiche_base: prepareStats(formData.statistiche_base, false),
            statistiche_modificatori: prepareStats(formData.statistiche_modificatori, true)
        };

        if (formData.id) await staffUpdateOggettoBase(formData.id, data, onLogout);
        else await staffCreateOggettoBase(data, onLogout);
        
        alert("Salvato correttamente!");
        onBack();
    } catch (e) { 
        console.error("Errore Salvataggio:", e);
        alert("Errore salvataggio: " + (e.message || "Controlla i dati.")); 
    }
  };

  const Select = ({ label, value, options, onChange }) => (
    <div className="w-full">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">{label}</label>
      <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white focus:border-blue-500 outline-none" 
        value={value || ""} onChange={e => onChange(e.target.value)}>
        <option value="">- SELEZIONA -</option>
        {options.map(o => <option key={o.id} value={o.id}>{o.nome || o.label}</option>)}
      </select>
    </div>
  );

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto border border-gray-700 shadow-2xl text-white overflow-y-auto max-h-[92vh]">
      
      {/* Header */}
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-blue-400 uppercase tracking-tighter">
            {formData.id ? `Edit Template: ${formData.nome}` : 'Nuovo Oggetto Base'}
        </h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-blue-600 hover:bg-blue-500 px-6 py-2 rounded-lg font-black text-xs uppercase shadow-lg transition-all flex items-center gap-2">
                <Save size={16}/> Salva
           </button>
           <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-xs uppercase transition-all flex items-center gap-2">
                <ArrowLeft size={16}/> Indietro
           </button>
        </div>
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

        {/* Riga 3: Flags */}
        <div className="flex flex-wrap gap-6 pt-2 border-t border-gray-800 mt-2">
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer hover:text-blue-300 transition-colors">
                <input type="checkbox" className="accent-blue-500 w-4 h-4" checked={formData.in_vendita} onChange={e => setFormData({...formData, in_vendita: e.target.checked})} /> 
                In Vendita (Shop)
            </label>
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
            onAdd={() => setFormData({...formData, statistiche_modificatori: [...formData.statistiche_modificatori, {statistica:'', valore:0, tipo_modificatore:'ADD'}]})} 
            onChange={(i,f,v) => updateInline('statistiche_modificatori', i, f, v)}
            onRemove={i => setFormData({...formData, statistiche_modificatori: formData.statistiche_modificatori.filter((_,idx)=>idx!==i)})} 
          />
      </div>

    </div>
  );
};

export default OggettoBaseEditor;