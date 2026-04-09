import React, { useState, useEffect } from 'react';
import { useCharacter } from '../CharacterContext';
import { staffUpdateOggetto, staffCreateOggetto, staffGetClassiOggetto, getPersonaggiList } from '../../api';
import CharacteristicInline from './inlines/CharacteristicInline';
import StatBaseInline from './inlines/StatBaseInline';
import StatModInline from './inlines/StatModInline';
import RichTextEditor from '../RichTextEditor';

const TIPO_CHOICES = [
    {id:'FIS', nome:'Fisico'}, {id:'MAT', nome:'Materia'}, {id:'MOD', nome:'Mod'},
    {id:'INN', nome:'Innesto'}, {id:'MUT', nome:'Mutazione'}, {id:'AUM', nome:'Aumento'}, {id:'POT', nome:'Potenziamento'}
];

const OggettoEditor = ({ onBack, onLogout, initialData = null }) => {
  const { punteggiList } = useCharacter();
  const [classi, setClassi] = useState([]);
  const [personaggi, setPersonaggi] = useState([]);

  const [formData, setFormData] = useState(initialData || {
    nome: '', testo: '', tipo_oggetto: 'FIS', aura: null, classe_oggetto: null,
    is_tecnologico: false, is_equipaggiato: false, is_pesante: false,
    inventario_corrente: null,
    attacco_base: '', componenti: [], statistiche_base: [], statistiche: []
  });

  useEffect(() => {
    const loadData = async () => {
        try {
            const [classiData, pgsData] = await Promise.all([
                staffGetClassiOggetto(onLogout),
                getPersonaggiList(onLogout, true)
            ]);
            setClassi(classiData || []);
            setPersonaggi(pgsData || []);
        } catch (error) {
            console.error("Errore caricamento dati editor:", error);
        }
    };
    loadData();
  }, [onLogout]);

  // Logica unificata per update inline
  const updateInline = (key, index, field, value) => {
    const newList = [...formData[key]];
    if (index === -1) {
      const exists = newList.find(it => (it.statistica?.id || it.statistica) === value.statId);
      if (!exists) {
          const newRecord = { statistica: value.statId };
          if (key === 'statistiche_base') newRecord.valore_base = value.value;
          else {
              newRecord.valore = value.value;
              newRecord.tipo_modificatore = 'ADD';
          }
          newList.push(newRecord);
      }
    } else {
      newList[index] = { ...newList[index], [field]: value };
    }
    setFormData({ ...formData, [key]: newList });
  };

  const handleSave = async () => {
    try {
      const getId = (item) => item?.id || item || null;
      
      const cleanAndDeduplicate = (list, keyField) => {
        const seen = new Set();
        return list
          .map(item => ({ ...item, [keyField]: getId(item[keyField]) }))
          .filter(item => {
            const id = item[keyField];
            if (!id || seen.has(id)) return false; 
            seen.add(id);
            return true;
          });
      };

      const data = { 
          ...formData, 
          aura: getId(formData.aura), 
          classe_oggetto: getId(formData.classe_oggetto),
          inventario_corrente: formData.inventario_corrente ? parseInt(formData.inventario_corrente) : null,
          
          statistiche_base: cleanAndDeduplicate(formData.statistiche_base, 'statistica'),
          statistiche: cleanAndDeduplicate(formData.statistiche, 'statistica'),
          componenti: cleanAndDeduplicate(formData.componenti, 'caratteristica')
      };

      if (formData.id) await staffUpdateOggetto(formData.id, data, onLogout);
      else await staffCreateOggetto(data, onLogout);
      
      alert("Salvato correttamente!"); 
      onBack();
    } catch (e) { 
        console.error(e);
        alert("Errore: " + e.message); 
    }
  };

  const Select = ({ label, value, options, onChange }) => (
    <div className="w-full">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">{label}</label>
      <select className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer" 
        value={value || ""} onChange={e => onChange(e.target.value)}>
        <option value="">- SELEZIONA -</option>
        {options.map(o => <option key={o.id} value={o.id}>{o.nome || o.label}</option>)}
      </select>
    </div>
  );

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] border border-gray-700 shadow-2xl text-white">
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-emerald-400 uppercase tracking-tighter">{formData.id ? `Edit: ${formData.nome}` : 'Nuovo Oggetto'}</h2>
        <div className="flex gap-3">
           <button onClick={handleSave} className="bg-emerald-600 hover:bg-emerald-500 px-8 py-2 rounded-lg font-black text-sm">SALVA</button>
           <button onClick={onBack} className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-sm">ANNULLA</button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 bg-gray-900/40 p-4 rounded-xl">
        <div className="md:col-span-2">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Nome</label>
            <input className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm" value={formData.nome} onChange={e => setFormData({...formData, nome: e.target.value})} />
        </div>
        
        <Select label="Tipo" value={formData.tipo_oggetto} options={TIPO_CHOICES} onChange={v => setFormData({...formData, tipo_oggetto: v})} />
        
        <Select 
            label="Proprietario (Inventario)" 
            value={formData.inventario_corrente} 
            options={personaggi} 
            onChange={v => setFormData({...formData, inventario_corrente: v})} 
        />

        <Select label="Aura" value={formData.aura?.id || formData.aura} options={punteggiList.filter(p => p.tipo === 'AU')} onChange={v => setFormData({...formData, aura: v})} />
        <Select label="Classe" value={formData.classe_oggetto?.id || formData.classe_oggetto} options={classi} onChange={v => setFormData({...formData, classe_oggetto: v})} />
        
        <div className="flex flex-col gap-2 pt-2">
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer"><input type="checkbox" checked={formData.is_tecnologico} onChange={e => setFormData({...formData, is_tecnologico: e.target.checked})} /> Tecnologico</label>
            <label className="flex items-center gap-2 text-xs font-bold cursor-pointer"><input type="checkbox" checked={formData.is_pesante} onChange={e => setFormData({...formData, is_pesante: e.target.checked})} /> Pesante (OGP)</label>
        </div>
        
        <div className="md:col-span-2">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Formula Attacco</label>
            <input className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm font-mono" value={formData.attacco_base} onChange={e => setFormData({...formData, attacco_base: e.target.value})} />
        </div>
      </div>

      <RichTextEditor label="Descrizione Narrativa" value={formData.testo} onChange={v => setFormData({...formData, testo: v})} />

      <div className="grid grid-cols-1 gap-6">
          <StatBaseInline 
            items={formData.statistiche_base} 
            options={punteggiList.filter(p => p.tipo === 'ST')} 
            onChange={(i, f, v) => updateInline('statistiche_base', i, f, v)}
          />
          
          <StatModInline 
            items={formData.statistiche} 
            options={punteggiList.filter(p => p.tipo === 'ST')} 
            auraOptions={punteggiList.filter(p => p.tipo === 'AU')} 
            elementOptions={punteggiList.filter(p => p.tipo === 'EL')} 
            onAdd={() => setFormData({...formData, statistiche: [...formData.statistiche, {statistica:'', valore:0, tipo_modificatore:'ADD'}]})} 
            onChange={(i,f,v) => updateInline('statistiche', i, f, v)} 
            onRemove={i => setFormData({...formData, statistiche: formData.statistiche.filter((_,idx)=>idx!==i)})} 
          />
      </div>

      <CharacteristicInline items={formData.componenti} options={punteggiList.filter(p => p.tipo === 'CA')} onAdd={() => setFormData({...formData, componenti: [...formData.componenti, {caratteristica:'', valore:1}]})} onChange={(i,f,v) => {const n=[...formData.componenti]; n[i][f]=v; setFormData({...formData, componenti:n});}} onRemove={i => setFormData({...formData, componenti: formData.componenti.filter((_,idx)=>idx!==i)})} />
    </div>
  );
};

export default OggettoEditor;