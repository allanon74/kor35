import React, { useState, useEffect } from 'react';
import { staffCreateInventario, staffUpdateInventario, staffGetInventarioOggetti, staffAggiungiOggettoInventario, staffRimuoviOggettoInventario, staffGetOggettiSenzaPosizione, getOggettoDetail } from '../../api';
import RichTextEditor from '../RichTextEditor';

const InventarioEditor = ({ onBack, onLogout, initialData = null }) => {
  const [formData, setFormData] = useState(initialData || {
    nome: '',
    testo: ''
  });
  const [oggettiInventario, setOggettiInventario] = useState([]);
  const [oggettiSenzaPosizione, setOggettiSenzaPosizione] = useState([]);
  const [loadingOggetti, setLoadingOggetti] = useState(false);
  const [loadingSenzaPosizione, setLoadingSenzaPosizione] = useState(false);
  const [saving, setSaving] = useState(false);
  const [manualOggettoId, setManualOggettoId] = useState('');

  useEffect(() => {
    if (initialData) {
      setFormData({
        nome: initialData.nome || '',
        testo: initialData.testo || ''
      });
      if (initialData.id) {
        loadOggettiInventario();
      }
    }
    loadOggettiSenzaPosizione();
  }, [initialData]);

  const loadOggettiInventario = async () => {
    if (!initialData?.id) return;
    setLoadingOggetti(true);
    try {
      const data = await staffGetInventarioOggetti(initialData.id, onLogout);
      setOggettiInventario(data || []);
    } catch (error) {
      console.error("Errore caricamento oggetti inventario:", error);
    } finally {
      setLoadingOggetti(false);
    }
  };

  const loadOggettiSenzaPosizione = async () => {
    setLoadingSenzaPosizione(true);
    try {
      const data = await staffGetOggettiSenzaPosizione(onLogout);
      setOggettiSenzaPosizione(data || []);
    } catch (error) {
      console.error("Errore caricamento oggetti senza posizione:", error);
    } finally {
      setLoadingSenzaPosizione(false);
    }
  };

  const handleSave = async () => {
    try {
      setSaving(true);
      
      if (initialData?.id) {
        await staffUpdateInventario(initialData.id, formData, onLogout);
      } else {
        await staffCreateInventario(formData, onLogout);
      }
      
      alert("Salvato correttamente!"); 
      onBack();
    } catch (e) { 
      console.error(e);
      alert("Errore: " + e.message); 
    } finally {
      setSaving(false);
    }
  };

  const handleAggiungiOggetto = async (oggettoId) => {
    if (!initialData?.id) {
      alert("Salva prima l'inventario per aggiungere oggetti!");
      return;
    }
    try {
      await staffAggiungiOggettoInventario(initialData.id, oggettoId, onLogout);
      await loadOggettiInventario();
      await loadOggettiSenzaPosizione();
      alert("Oggetto aggiunto all'inventario!");
    } catch (error) {
      alert("Errore: " + error.message);
    }
  };

  const handleRimuoviOggetto = async (oggettoId) => {
    if (!initialData?.id) return;
    if (!window.confirm("Rimuovere questo oggetto dall'inventario? Verrà messo senza posizione.")) return;
    
    try {
      await staffRimuoviOggettoInventario(initialData.id, oggettoId, onLogout);
      await loadOggettiInventario();
      await loadOggettiSenzaPosizione();
      alert("Oggetto rimosso dall'inventario!");
    } catch (error) {
      alert("Errore: " + error.message);
    }
  };

  const handleAddOggettoManuale = async () => {
    if (!manualOggettoId.trim()) return;
    const id = parseInt(manualOggettoId.trim());
    if (isNaN(id)) {
      alert("ID oggetto non valido!");
      return;
    }

    try {
      const oggetto = await getOggettoDetail(id, onLogout);
      if (oggetto) {
        if (!oggettiSenzaPosizione.find(o => o.id === id)) {
          setOggettiSenzaPosizione(prev => [...prev, oggetto]);
        }
        setManualOggettoId('');
      }
    } catch (error) {
      alert("Impossibile recuperare l'oggetto. Verifica che l'ID sia corretto.");
    }
  };

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] border border-gray-700 shadow-2xl text-white">
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-emerald-400 uppercase tracking-tighter">
          {initialData?.id ? `Modifica: ${initialData.nome || 'Inventario'}` : 'Nuovo Inventario'}
        </h2>
        <div className="flex gap-3">
          <button 
            onClick={handleSave} 
            disabled={saving}
            className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-8 py-2 rounded-lg font-black text-sm"
          >
            {saving ? 'SALVATAGGIO...' : 'SALVA'}
          </button>
          <button 
            onClick={onBack} 
            className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-sm"
          >
            ANNULLA
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 bg-gray-900/40 p-4 rounded-xl">
        <div>
          <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Nome</label>
          <input 
            className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm" 
            value={formData.nome} 
            onChange={e => setFormData({...formData, nome: e.target.value})} 
            placeholder="Nome inventario"
          />
        </div>

        <RichTextEditor 
          label="Descrizione" 
          value={formData.testo} 
          onChange={v => setFormData({...formData, testo: v})} 
        />
      </div>

      {/* Gestione Oggetti (solo se inventario esistente) */}
      {initialData?.id && (
        <div className="grid grid-cols-2 gap-6">
          {/* Oggetti nell'inventario */}
          <div className="bg-gray-900/40 p-4 rounded-xl">
            <h3 className="text-sm font-bold text-gray-300 mb-3">Oggetti nell'Inventario</h3>
            {loadingOggetti ? (
              <div className="text-center p-4 text-gray-500">Caricamento...</div>
            ) : oggettiInventario.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Nessun oggetto</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {oggettiInventario.map(oggetto => (
                  <div key={oggetto.id} className="flex justify-between items-center p-2 bg-gray-800 rounded border border-gray-700">
                    <span className="text-sm text-white">{oggetto.nome}</span>
                    <button
                      onClick={() => handleRimuoviOggetto(oggetto.id)}
                      className="p-1 bg-red-600/20 text-red-400 hover:bg-red-600/40 rounded text-xs"
                    >
                      Rimuovi
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Oggetti senza posizione */}
          <div className="bg-gray-900/40 p-4 rounded-xl">
            <h3 className="text-sm font-bold text-gray-300 mb-3">Oggetti Senza Posizione</h3>
            
            {/* Input per aggiungere oggetto manualmente */}
            <div className="mb-2 flex gap-2">
              <input
                type="number"
                value={manualOggettoId}
                onChange={e => setManualOggettoId(e.target.value)}
                onKeyPress={e => e.key === 'Enter' && handleAddOggettoManuale()}
                placeholder="Inserisci ID oggetto..."
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-white text-sm"
              />
              <button
                onClick={handleAddOggettoManuale}
                className="px-3 py-2 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-white text-sm font-bold"
              >
                +
              </button>
            </div>

            {loadingSenzaPosizione ? (
              <div className="text-center p-4 text-gray-500">Caricamento...</div>
            ) : oggettiSenzaPosizione.length === 0 ? (
              <p className="text-xs text-gray-500 italic">Nessun oggetto senza posizione</p>
            ) : (
              <div className="space-y-2 max-h-60 overflow-y-auto">
                {oggettiSenzaPosizione.map(oggetto => (
                  <div key={oggetto.id} className="flex justify-between items-center p-2 bg-gray-800 rounded border border-gray-700">
                    <span className="text-sm text-white">{oggetto.nome}</span>
                    <button
                      onClick={() => handleAggiungiOggetto(oggetto.id)}
                      className="p-1 bg-green-600/20 text-green-400 hover:bg-green-600/40 rounded text-xs"
                    >
                      Aggiungi
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default InventarioEditor;
