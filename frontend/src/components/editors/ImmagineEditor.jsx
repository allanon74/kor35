import React, { useState, useEffect } from 'react';
import { createWikiImage, updateWikiImage, getMediaUrl } from '../../api';
import RichTextEditor from '../RichTextEditor';
import EditorSaveActions from './EditorSaveActions';

const ALLINEAMENTO_CHOICES = [
    { id: 'left', nome: 'Sinistra' },
    { id: 'center', nome: 'Centro' },
    { id: 'right', nome: 'Destra' },
    { id: 'full', nome: 'Larghezza piena' },
];

const ImmagineEditor = ({ onBack, onLogout, initialData = null }) => {
  const [currentId, setCurrentId] = useState(initialData?.id || null);
  const [formData, setFormData] = useState(initialData || {
    titolo: '',
    descrizione: '',
    allineamento: 'center',
    larghezza_max: 800,
    immagine: null
  });
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (initialData) {
      setCurrentId(initialData.id || null);
      setFormData({
        titolo: initialData.titolo || '',
        descrizione: initialData.descrizione || '',
        allineamento: initialData.allineamento || 'center',
        larghezza_max: initialData.larghezza_max || 800,
        immagine: initialData.immagine || null
      });
      if (initialData.immagine) {
        setPreviewUrl(getMediaUrl(initialData.immagine));
      }
    } else {
      setCurrentId(null);
    }
  }, [initialData]);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setImageFile(file);
      setPreviewUrl(URL.createObjectURL(file));
    }
  };

  const handleSave = async (mode = 'save_close') => {
    try {
      setSaving(true);
      
      const formDataToSend = new FormData();
      formDataToSend.append('titolo', formData.titolo || '');
      formDataToSend.append('descrizione', formData.descrizione || '');
      formDataToSend.append('allineamento', formData.allineamento);
      formDataToSend.append('larghezza_max', formData.larghezza_max.toString());
      
      // Se c'è un nuovo file, aggiungilo
      if (imageFile) {
        formDataToSend.append('immagine', imageFile);
      }

      const isSaveAsNew = mode === 'save_as_new';
      const isExisting = !!currentId && !isSaveAsNew;
      if (isExisting) {
        await updateWikiImage(currentId, formDataToSend, onLogout);
      } else {
        const created = await createWikiImage(formDataToSend, onLogout);
        if (mode !== 'save_close' && created?.id) {
          setCurrentId(created.id);
        }
      }
      
      alert("Salvato correttamente!"); 
      if (mode === 'save_close') onBack();
    } catch (e) { 
      console.error(e);
      alert("Errore: " + e.message); 
    } finally {
      setSaving(false);
    }
  };

  const Select = ({ label, value, options, onChange }) => (
    <div className="w-full">
      <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">{label}</label>
      <select 
        className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white cursor-pointer" 
        value={value || ""} 
        onChange={e => onChange(e.target.value)}
      >
        {options.map(o => (
          <option key={o.id} value={o.id}>{o.nome}</option>
        ))}
      </select>
    </div>
  );

  return (
    <div className="bg-gray-800 p-6 rounded-xl space-y-6 max-w-7xl mx-auto overflow-y-auto max-h-[92vh] border border-gray-700 shadow-2xl text-white">
      <div className="flex justify-between items-center border-b border-gray-700 pb-4">
        <h2 className="text-xl font-bold text-emerald-400 uppercase tracking-tighter">
          {currentId ? `Modifica: ${formData.titolo || 'Immagine'}` : 'Nuova Immagine Wiki'}
        </h2>
        <EditorSaveActions
          onSave={() => handleSave('save_close')}
          onSaveAndContinue={() => handleSave('save_continue')}
          onSaveAsNew={currentId ? () => handleSave('save_as_new') : null}
          onCancel={onBack}
          saving={saving}
          saveLabel="Salva"
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* Colonna sinistra: Form */}
        <div className="space-y-4">
          <div>
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Titolo</label>
            <input 
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm" 
              value={formData.titolo} 
              onChange={e => setFormData({...formData, titolo: e.target.value})} 
              placeholder="Titolo dell'immagine (opzionale)"
            />
          </div>

          <RichTextEditor 
            label="Descrizione" 
            value={formData.descrizione} 
            onChange={v => setFormData({...formData, descrizione: v})} 
          />

          <div className="grid grid-cols-2 gap-4">
            <Select 
              label="Allineamento" 
              value={formData.allineamento} 
              options={ALLINEAMENTO_CHOICES} 
              onChange={v => setFormData({...formData, allineamento: v})} 
            />
            
            <div>
              <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Larghezza Max (px)</label>
              <input 
                type="number"
                min="0"
                className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm" 
                value={formData.larghezza_max} 
                onChange={e => setFormData({...formData, larghezza_max: parseInt(e.target.value) || 0})} 
                placeholder="0 = originale"
              />
              <p className="text-[9px] text-gray-600 mt-1">0 = dimensione originale</p>
            </div>
          </div>

          <div>
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">
              {currentId ? 'Nuova Immagine (lascia vuoto per mantenere quella esistente)' : 'Immagine'}
            </label>
            <input 
              type="file"
              accept="image/*"
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-cyan-600 file:text-white hover:file:bg-cyan-500 cursor-pointer" 
              onChange={handleImageChange}
            />
            {!imageFile && currentId && (
              <p className="text-[9px] text-gray-600 mt-1">L'immagine attuale verrà mantenuta se non selezioni un nuovo file.</p>
            )}
          </div>
        </div>

        {/* Colonna destra: Anteprima */}
        <div className="space-y-4">
          <div>
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-2">Anteprima</label>
            <div className="bg-gray-900 rounded-lg border border-gray-700 p-4 min-h-[300px] flex items-center justify-center">
              {previewUrl ? (
                <div className="w-full space-y-2">
                  <img 
                    src={previewUrl} 
                    alt="Anteprima"
                    className="w-full h-auto rounded border border-gray-700"
                    style={{
                      maxWidth: formData.larghezza_max > 0 ? `${formData.larghezza_max}px` : '100%'
                    }}
                  />
                  <div className="text-xs text-gray-500 text-center">
                    Allineamento: {ALLINEAMENTO_CHOICES.find(c => c.id === formData.allineamento)?.nome}
                    {formData.larghezza_max > 0 && ` • Max: ${formData.larghezza_max}px`}
                  </div>
                </div>
              ) : (
                <div className="text-gray-600 text-sm text-center">
                  Seleziona un'immagine per vedere l'anteprima
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ImmagineEditor;
