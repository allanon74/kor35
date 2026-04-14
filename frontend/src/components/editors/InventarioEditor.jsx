import React, { useState, useEffect } from 'react';
import { staffCreateInventario, staffUpdateInventario, staffGetInventarioOggetti, staffAggiungiOggettoInventario, staffRimuoviOggettoInventario, staffGetOggettiSenzaPosizione, getOggettoDetail } from '../../api';
import RichTextEditor from '../RichTextEditor';
import EditorSaveActions from './EditorSaveActions';

const InventarioEditor = ({ onBack, onLogout, initialData = null }) => {
  const [currentId, setCurrentId] = useState(initialData?.id || null);
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
  const [status, setStatus] = useState({ type: 'success', message: '' });

  useEffect(() => {
    if (initialData) {
      setCurrentId(initialData.id || null);
      setFormData({
        nome: initialData.nome || '',
        testo: initialData.testo || ''
      });
      if (initialData.id) {
        loadOggettiInventario();
      }
    } else {
      setCurrentId(null);
    }
    loadOggettiSenzaPosizione();
  }, [initialData]);

  const loadOggettiInventario = async () => {
    if (!currentId) return;
    setLoadingOggetti(true);
    try {
      const data = await staffGetInventarioOggetti(currentId, onLogout);
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

  const handleSave = async (mode = 'save_close') => {
    try {
      setSaving(true);
      
      const isSaveAsNew = mode === 'save_as_new';
      const isExisting = !!currentId && !isSaveAsNew;
      const saved = isExisting
        ? await staffUpdateInventario(currentId, formData, onLogout)
        : await staffCreateInventario(formData, onLogout);
      const recordName = saved?.nome || formData.nome || 'Record';
      if (mode === 'save_as_new') setStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
      if (mode === 'save_continue') setStatus({ type: 'success', message: `"${recordName}" salvato.` });
      if (mode === 'save_new_blank') {
        setCurrentId(null);
        setFormData({ nome: '', testo: '' });
        setOggettiInventario([]);
        setStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
      }
      if (mode === 'save_close') onBack();
      if (mode !== 'save_close' && mode !== 'save_new_blank' && saved?.id) {
        setCurrentId(saved.id);
        setFormData((prev) => ({ ...prev, nome: saved.nome ?? prev.nome, testo: saved.testo ?? prev.testo }));
      }
    } catch (e) { 
      console.error(e);
      setStatus({ type: 'error', message: `Errore salvataggio: ${e.message || 'Errore sconosciuto'}` });
      alert("Errore: " + e.message); 
    } finally {
      setSaving(false);
    }
  };

  const handleAggiungiOggetto = async (oggettoId) => {
    if (!currentId) {
      alert("Salva prima l'inventario per aggiungere oggetti!");
      return;
    }
    try {
      await staffAggiungiOggettoInventario(currentId, oggettoId, onLogout);
      await loadOggettiInventario();
      await loadOggettiSenzaPosizione();
      alert("Oggetto aggiunto all'inventario!");
    } catch (error) {
      alert("Errore: " + error.message);
    }
  };

  const handleRimuoviOggetto = async (oggettoId) => {
    if (!currentId) return;
    if (!window.confirm("Rimuovere questo oggetto dall'inventario? Verrà messo senza posizione.")) return;
    
    try {
      await staffRimuoviOggettoInventario(currentId, oggettoId, onLogout);
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
          {currentId ? `Modifica: ${formData.nome || 'Inventario'}` : 'Nuovo Inventario'}
        </h2>
        <EditorSaveActions
          onSave={() => handleSave('save_close')}
          onSaveAndContinue={() => handleSave('save_continue')}
          onSaveAsNew={currentId ? () => handleSave('save_as_new') : null}
          onSaveAndNew={() => handleSave('save_new_blank')}
          onCancel={onBack}
          saving={saving}
          saveLabel="Salva"
          statusMessage={status.message}
          statusType={status.type}
        />
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
      {currentId && (
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
