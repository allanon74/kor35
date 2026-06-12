import React, { useState, useEffect } from 'react';
import { getWikiTierList, getWikiImageList, getWidgetButtonsList, getWikiTierWidgetList, getWikiTierCollectionWidgetList, getWikiMattoniWidgetList, createWikiImage, updateWikiImage, createWidgetButtons, updateWidgetButtons, createWikiTierWidget, updateWikiTierWidget, createWikiTierCollectionWidget, updateWikiTierCollectionWidget, createWikiMattoniWidget, updateWikiMattoniWidget, createWikiPage, updateWikiPage, getWikiImageUrl, getEre, getStaffManualePdfList } from '../../api';
import RichTextEditor from '../RichTextEditor';
import { Lock, Eye, X, Edit, FileText } from 'lucide-react';
import ButtonWidgetEditorModal from './ButtonWidgetEditorModal';
import TierWidgetEditorModal from './TierWidgetEditorModal'; 
import TierCollectionWidgetEditorModal from './TierCollectionWidgetEditorModal';
import MattoniWidgetEditorModal from './MattoniWidgetEditorModal';
import WikiCoverEditor from './WikiCoverEditor';
import WikiWidgetHelperPanel from './WikiWidgetHelperPanel';
import WikiImageUploadModal from './WikiImageUploadModal';
import { getWidgetToken, getUsedWidgetIds } from './wikiWidgetTokens';

export default function WikiPageEditorModal({ onClose, onSuccess, initialData = null }) {
  const [formData, setFormData] = useState({
    titolo: '',
    slug: '',
    parent: '',
    contenuto: '',
    public: false,
    visibile_solo_staff: false,
    includi_in_pdf: false,
    pdf_solo_indice: false,
    pdf_forza_nuova_pagina: false,
    pdf_titolo_capitolo: '',
    ordine: 0,
    banner_y: 50, // Default centro verticale (0-100)
    ...initialData
  });

  const [availableManualiPdf, setAvailableManualiPdf] = useState([]);
  const buildInitialManualiMeta = (data) => {
    const meta = {};
    const config = data?.manuali_pdf_config;
    if (Array.isArray(config)) {
      config.forEach((c) => {
        if (c?.manuale_id) {
          meta[c.manuale_id] = {
            ordine: c.ordine ?? 0,
            inizio_capitolo: c.inizio_capitolo !== false,
          };
        }
      });
    }
    const raw = data?.manuali_pdf;
    if (Array.isArray(raw)) {
      raw.forEach((m) => {
        const id = typeof m === 'object' && m != null ? m.id : m;
        if (id && !meta[id]) meta[id] = { ordine: 0, inizio_capitolo: true };
      });
    }
    return meta;
  };
  const [manualiPdfMeta, setManualiPdfMeta] = useState(() => buildInitialManualiMeta(initialData));
  const [selectedManualiIds, setSelectedManualiIds] = useState(() => {
    const raw = initialData?.manuali_pdf;
    if (!Array.isArray(raw)) return [];
    return raw.map((m) => (typeof m === 'object' && m != null ? m.id : m)).filter(Boolean);
  });
  
  // Gestione file immagine
  const [imageFile, setImageFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(
      initialData?.immagine ? getWikiImageUrl(initialData.slug) : null
  );

  const isEditing = !!initialData?.id;
  const [loading, setLoading] = useState(false);

  // Widget Helper logic
  const [showWidgetHelper, setShowWidgetHelper] = useState(false);
  const [availableTiers, setAvailableTiers] = useState([]);
  const [tierSearch, setTierSearch] = useState('');
  const [availableTierWidgets, setAvailableTierWidgets] = useState([]);
  const [availableTierCollectionWidgets, setAvailableTierCollectionWidgets] = useState([]);
  const [availableImages, setAvailableImages] = useState([]);
  const [availableButtonWidgets, setAvailableButtonWidgets] = useState([]);
  const [availableMattoniWidgets, setAvailableMattoniWidgets] = useState([]);
  const [availableEre, setAvailableEre] = useState([]);
  const [widgetHelperTab, setWidgetHelperTab] = useState('tier'); // 'tier', 'ere', 'tierCollection', 'image', 'buttons', 'mattoni'

  // State per il modal widget tier (crea/modifica)
  const [showTierWidgetEditor, setShowTierWidgetEditor] = useState(false);
  const [editingTierWidget, setEditingTierWidget] = useState(null);
  const [showTierCollectionWidgetEditor, setShowTierCollectionWidgetEditor] = useState(false);
  const [editingTierCollectionWidget, setEditingTierCollectionWidget] = useState(null);

  // State per il modal del widget buttons
  const [showButtonWidgetEditor, setShowButtonWidgetEditor] = useState(false);
  const [editingButtonWidget, setEditingButtonWidget] = useState(null);

  const [showMattoniWidgetEditor, setShowMattoniWidgetEditor] = useState(false);
  const [editingMattoniWidget, setEditingMattoniWidget] = useState(null);
  
  // State per il modal edit immagine
  const [showImageEditor, setShowImageEditor] = useState(false);
  const [editingImage, setEditingImage] = useState(null);
  
  // Upload Image form state
  const [showUploadImage, setShowUploadImage] = useState(false);
  const [uploadingImage, setUploadingImage] = useState(false);
  const [newImageData, setNewImageData] = useState({
    titolo: '',
    descrizione: '',
    immagine: null,
    larghezza_max: 800,
    allineamento: 'center'
  });
  const [newImagePreview, setNewImagePreview] = useState(null);
  const resetNewImageForm = () => {
    setNewImageData({
      titolo: '',
      descrizione: '',
      immagine: null,
      larghezza_max: 800,
      allineamento: 'center'
    });
    setNewImagePreview(null);
  };


  const usedWidgetIds = getUsedWidgetIds(formData.contenuto);

  useEffect(() => {
    getStaffManualePdfList()
      .then((data) => setAvailableManualiPdf(Array.isArray(data) ? data : []))
      .catch((err) => console.error('Err loading manuali PDF', err));
  }, []);

  useEffect(() => {
    if (showWidgetHelper) {
        // Carica Tier e Widget Tier
        getWikiTierList()
            .then(data => setAvailableTiers(data))
            .catch(err => console.error("Err loading tiers", err));
        getEre()
            .then(data => setAvailableEre(data || []))
            .catch(err => console.error("Err loading ere", err));
        getWikiTierWidgetList()
            .then(data => setAvailableTierWidgets(data || []))
            .catch(err => console.error("Err loading tier widgets", err));
        getWikiTierCollectionWidgetList()
            .then(data => setAvailableTierCollectionWidgets(data || []))
            .catch(err => console.error("Err loading tier collection widgets", err));

        // Carica Immagini
        getWikiImageList()
            .then(data => setAvailableImages(data))
            .catch(err => console.error("Err loading images", err));
        
        // Carica Widget Buttons
        getWidgetButtonsList()
            .then(data => setAvailableButtonWidgets(data))
            .catch(err => console.error("Err loading button widgets", err));

        getWikiMattoniWidgetList()
            .then(data => setAvailableMattoniWidgets(data || []))
            .catch(err => console.error("Err loading mattoni widgets", err));
    }
  }, [showWidgetHelper]);

  const insertWidget = (code) => {
    const widgetHtml = `<p><strong>${code}</strong></p><p>&nbsp;</p>`;
    setFormData(prev => ({
        ...prev,
        contenuto: (prev.contenuto || '') + widgetHtml
    }));
    setShowWidgetHelper(false);
  };

  const handleNewImageFileChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      setNewImageData(prev => ({ ...prev, immagine: file }));
      setNewImagePreview(URL.createObjectURL(file));
    }
  };

  const handleUploadImage = async (e) => {
    e.preventDefault();
    if (!newImageData.immagine || !newImageData.titolo.trim()) {
      alert('Inserisci almeno un titolo e seleziona un\'immagine');
      return;
    }

    setUploadingImage(true);
    try {
      const formData = new FormData();
      formData.append('titolo', newImageData.titolo);
      formData.append('descrizione', newImageData.descrizione || '');
      formData.append('immagine', newImageData.immagine);
      formData.append('larghezza_max', newImageData.larghezza_max);
      formData.append('allineamento', newImageData.allineamento);

      const response = await createWikiImage(formData);
      
      // Aggiorna la lista delle immagini
      const updatedList = await getWikiImageList();
      setAvailableImages(updatedList);
      
      // Inserisci automaticamente il widget della nuova immagine
      insertWidget(`{{WIDGET_IMAGE:${getWidgetToken(response)}}}`);
      
      // Reset form
      resetNewImageForm();
      setShowUploadImage(false);
      
    } catch (error) {
      console.error("Errore caricamento immagine:", error);
      alert("Errore durante il caricamento dell'immagine. Controlla la console.");
    } finally {
      setUploadingImage(false);
    }
  };

  const handleImageChange = (e) => {
      const file = e.target.files[0];
      if (file) {
          setImageFile(file);
          setPreviewUrl(URL.createObjectURL(file));
          setFormData(prev => ({ ...prev, banner_y: 50 })); 
      }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);

    try {
        const data = new FormData();
        data.append('titolo', formData.titolo);
        data.append('contenuto', formData.contenuto || ''); 
        data.append('public', formData.public);
        data.append('visibile_solo_staff', formData.visibile_solo_staff);
        data.append('includi_in_pdf', formData.includi_in_pdf ? 'true' : 'false');
        data.append('pdf_solo_indice', formData.pdf_solo_indice ? 'true' : 'false');
        data.append('pdf_forza_nuova_pagina', formData.pdf_forza_nuova_pagina ? 'true' : 'false');
        if (formData.pdf_titolo_capitolo) {
            data.append('pdf_titolo_capitolo', formData.pdf_titolo_capitolo);
        }
        data.append('ordine', formData.ordine);
        data.append('banner_y', formData.banner_y);
        if (formData.includi_in_pdf) {
            selectedManualiIds.forEach((id) => data.append('manuali_pdf', String(id)));
            const config = selectedManualiIds.map((manualeId) => ({
                manuale_id: manualeId,
                ordine: manualiPdfMeta[manualeId]?.ordine ?? 0,
                inizio_capitolo: manualiPdfMeta[manualeId]?.inizio_capitolo !== false,
            }));
            data.append('manuali_pdf_config', JSON.stringify(config));
        } else {
            data.append('manuali_pdf', '');
            data.append('manuali_pdf_config', '[]');
        }

        if (formData.slug) data.append('slug', formData.slug);
        if (formData.parent) data.append('parent', formData.parent);
        
        if (imageFile) {
            data.append('immagine', imageFile);
        }

        let response;
        if (isEditing) {
             response = await updateWikiPage(initialData.id, data);
        } else {
             response = await createWikiPage(data);
        }

        const newSlug = response.slug || formData.slug; 
        onSuccess(newSlug);

    } catch (error) {
        console.error("Errore salvataggio:", error);
        alert("Errore durante il salvataggio. Controlla la console.");
    } finally {
        setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/80 z-50 flex items-center justify-center p-0 md:p-4">
      <div className="bg-white md:rounded-lg shadow-xl w-full max-w-6xl h-full md:h-auto md:max-h-[95vh] flex flex-col">
        
        {/* HEADER */}
        <div className="p-3 md:p-4 border-b flex justify-between items-center bg-gray-100 md:rounded-t-lg shrink-0">
            <h2 className="font-bold text-lg md:text-xl text-gray-800 flex items-center gap-2 truncate">
                {isEditing ? '✏️ Modifica Pagina' : '📄 Nuova Pagina Wiki'}
            </h2>
            <button onClick={onClose} className="text-gray-500 hover:text-red-600 font-bold text-xl px-2">✕</button>
        </div>

        {/* BODY SCROLLABILE */}
        <div className="p-4 overflow-y-auto flex-1 flex flex-col md:flex-row gap-6">
            
            {/* COLONNA SINISTRA: IMPOSTAZIONI */}
            <div className="w-full md:w-1/3 space-y-6">
                
                {/* 1. Titolo e Slug */}
                <div className="space-y-4">
                    <div>
                        <label className="block text-xs font-bold text-gray-700 mb-1">Titolo Pagina</label>
                        <input 
                            type="text" 
                            className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none text-sm" 
                            value={formData.titolo}
                            onChange={e => setFormData({...formData, titolo: e.target.value})}
                            required 
                        />
                    </div>
                    
                    <div className="grid grid-cols-2 gap-2">
                        <div>
                            <label className="block text-xs font-bold text-gray-700 mb-1">Slug URL</label>
                            <input 
                                type="text" 
                                className="w-full border border-gray-300 p-2 rounded bg-gray-50 text-gray-600 text-sm" 
                                value={formData.slug}
                                onChange={e => setFormData({...formData, slug: e.target.value})}
                                placeholder="auto-generato"
                            />
                        </div>
                        <div>
                            <label className="block text-xs font-bold text-gray-700 mb-1">Ordine</label>
                            <input 
                                type="number" 
                                className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-indigo-500 outline-none text-sm" 
                                value={formData.ordine || 0}
                                onChange={(e) => setFormData({...formData, ordine: parseInt(e.target.value) || 0})}
                            />
                        </div>
                    </div>
                </div>

                {/* 2. Immagine con MINI MAPPA */}
                <WikiCoverEditor
                    previewUrl={previewUrl}
                    bannerY={formData.banner_y}
                    onBannerYChange={(value) => setFormData((prev) => ({ ...prev, banner_y: value }))}
                    onImageFileChange={handleImageChange}
                />

                {/* 3. Visibilità */}
                <div className="space-y-3 border rounded-lg p-3 bg-gray-50">
                    <label className="block text-xs font-bold text-gray-700">Impostazioni di Visibilità</label>
                    
                    <div className={`flex items-center gap-3 p-2 rounded border transition-colors ${formData.public ? 'bg-yellow-50 border-yellow-300' : 'bg-white border-gray-200'}`}>
                        <input 
                            type="checkbox" 
                            id="is_public"
                            className="w-4 h-4 text-yellow-600 rounded focus:ring-yellow-500"
                            checked={formData.public} 
                            onChange={e => setFormData({...formData, public: e.target.checked})}
                        />
                        <label htmlFor="is_public" className="text-sm font-bold text-gray-800 cursor-pointer flex items-center gap-2">
                            <Eye size={16} className="text-gray-500"/> Pubblica Online
                        </label>
                    </div>

                    <div className={`flex items-center gap-3 p-2 rounded border transition-colors ${formData.visibile_solo_staff ? 'bg-indigo-50 border-indigo-300' : 'bg-white border-gray-200'}`}>
                        <input 
                            type="checkbox" 
                            id="is_staff"
                            className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                            checked={formData.visibile_solo_staff} 
                            onChange={e => setFormData({...formData, visibile_solo_staff: e.target.checked})}
                        />
                        <label htmlFor="is_staff" className="text-sm font-bold text-indigo-900 cursor-pointer flex items-center gap-2">
                            <Lock size={16} /> Visibile solo allo Staff
                        </label>
                    </div>
                </div>

                <div className="space-y-3 border rounded-lg p-3 bg-rose-50/80 border-rose-200">
                    <label className="block text-xs font-bold text-rose-900 flex items-center gap-2">
                        <FileText size={14} /> Pubblicazione PDF
                    </label>
                    <div className="flex items-center gap-3 p-2 rounded border bg-white border-rose-200">
                        <input
                            type="checkbox"
                            id="includi_in_pdf"
                            className="w-4 h-4 text-rose-700 rounded"
                            checked={!!formData.includi_in_pdf}
                            onChange={(e) => setFormData({ ...formData, includi_in_pdf: e.target.checked })}
                        />
                        <label htmlFor="includi_in_pdf" className="text-sm font-bold text-gray-800 cursor-pointer">
                            Includi nei manuali PDF
                        </label>
                    </div>
                    {formData.includi_in_pdf && (
                        <>
                            <div className="space-y-1 max-h-32 overflow-y-auto">
                                {availableManualiPdf.length === 0 ? (
                                    <p className="text-xs text-gray-500">Nessun manuale configurato (scheda staff Manuali PDF).</p>
                                ) : (
                                    availableManualiPdf.map((m) => {
                                        const selected = selectedManualiIds.includes(m.id);
                                        const meta = manualiPdfMeta[m.id] || { ordine: 0, inizio_capitolo: true };
                                        return (
                                        <div key={m.id} className="p-2 rounded border border-rose-100 bg-white space-y-2">
                                            <label className="flex items-center gap-2 text-sm cursor-pointer">
                                                <input
                                                    type="checkbox"
                                                    checked={selected}
                                                    onChange={(e) => {
                                                        if (e.target.checked) {
                                                            setSelectedManualiIds((prev) => [...prev, m.id]);
                                                            setManualiPdfMeta((prev) => ({
                                                                ...prev,
                                                                [m.id]: prev[m.id] || { ordine: 0, inizio_capitolo: true },
                                                            }));
                                                        } else {
                                                            setSelectedManualiIds((prev) => prev.filter((x) => x !== m.id));
                                                        }
                                                    }}
                                                />
                                                <span className="font-medium">{m.titolo}</span>
                                                <span className="text-xs text-gray-400">({m.slug})</span>
                                            </label>
                                            {selected && (
                                                <div className="flex flex-wrap items-center gap-3 pl-6 text-xs">
                                                    <label className="flex items-center gap-1">
                                                        <span className="text-gray-500 font-bold">Ordine PDF</span>
                                                        <input
                                                            type="number"
                                                            className="w-20 border border-gray-300 rounded px-2 py-1"
                                                            value={meta.ordine ?? 0}
                                                            onChange={(e) => setManualiPdfMeta((prev) => ({
                                                                ...prev,
                                                                [m.id]: {
                                                                    ...meta,
                                                                    ordine: parseInt(e.target.value, 10) || 0,
                                                                },
                                                            }))}
                                                        />
                                                    </label>
                                                    <label className="flex items-center gap-1 cursor-pointer">
                                                        <input
                                                            type="checkbox"
                                                            checked={meta.inizio_capitolo !== false}
                                                            onChange={(e) => setManualiPdfMeta((prev) => ({
                                                                ...prev,
                                                                [m.id]: { ...meta, inizio_capitolo: e.target.checked },
                                                            }))}
                                                        />
                                                        Inizio capitolo
                                                    </label>
                                                </div>
                                            )}
                                        </div>
                                        );
                                    })
                                )}
                            </div>
                            <label className="block text-xs font-bold text-gray-600">Titolo capitolo PDF (opzionale)</label>
                            <input
                                type="text"
                                className="w-full border border-gray-300 p-2 rounded text-sm"
                                value={formData.pdf_titolo_capitolo || ''}
                                onChange={(e) => setFormData({ ...formData, pdf_titolo_capitolo: e.target.value })}
                                placeholder="Uguale al titolo pagina se vuoto"
                            />
                            <label className="flex items-center gap-2 text-xs">
                                <input
                                    type="checkbox"
                                    checked={!!formData.pdf_solo_indice}
                                    onChange={(e) => setFormData({ ...formData, pdf_solo_indice: e.target.checked })}
                                />
                                Solo voce in indice (senza corpo)
                            </label>
                            <label className="flex items-center gap-2 text-xs">
                                <input
                                    type="checkbox"
                                    checked={!!formData.pdf_forza_nuova_pagina}
                                    onChange={(e) => setFormData({ ...formData, pdf_forza_nuova_pagina: e.target.checked })}
                                />
                                Forza nuova pagina all&apos;inizio del capitolo
                            </label>
                        </>
                    )}
                </div>

                <WikiWidgetHelperPanel
                    showWidgetHelper={showWidgetHelper}
                    setShowWidgetHelper={setShowWidgetHelper}
                    widgetHelperTab={widgetHelperTab}
                    setWidgetHelperTab={setWidgetHelperTab}
                    usedWidgetIds={usedWidgetIds}
                    availableTierWidgets={availableTierWidgets}
                    availableTiers={availableTiers}
                    availableEre={availableEre}
                    availableTierCollectionWidgets={availableTierCollectionWidgets}
                    availableImages={availableImages}
                    availableButtonWidgets={availableButtonWidgets}
                    availableMattoniWidgets={availableMattoniWidgets}
                    tierSearch={tierSearch}
                    setTierSearch={setTierSearch}
                    showUploadImage={showUploadImage}
                    insertWidget={insertWidget}
                    onCreateTierWidget={() => {
                        setEditingTierWidget(null);
                        setShowTierWidgetEditor(true);
                    }}
                    onEditTierWidget={(w) => {
                        setEditingTierWidget(w);
                        setShowTierWidgetEditor(true);
                    }}
                    onCreateTierCollectionWidget={() => {
                        setEditingTierCollectionWidget(null);
                        setShowTierCollectionWidgetEditor(true);
                    }}
                    onEditTierCollectionWidget={(w) => {
                        setEditingTierCollectionWidget(w);
                        setShowTierCollectionWidgetEditor(true);
                    }}
                    onCreateImage={() => {
                        setWidgetHelperTab('image');
                        setShowUploadImage(true);
                    }}
                    onEditImage={(img) => {
                        setEditingImage(img);
                        setShowImageEditor(true);
                    }}
                    onCreateButtonWidget={() => setShowButtonWidgetEditor(true)}
                    onEditButtonWidget={(widget) => {
                        setEditingButtonWidget(widget);
                        setShowButtonWidgetEditor(true);
                    }}
                    onCreateMattoniWidget={() => {
                        setEditingMattoniWidget(null);
                        setShowMattoniWidgetEditor(true);
                    }}
                    onEditMattoniWidget={(w) => {
                        setEditingMattoniWidget(w);
                        setShowMattoniWidgetEditor(true);
                    }}
                />
            </div>

            {/* COLONNA DESTRA: EDITOR */}
            <div className="w-full md:w-2/3 flex flex-col min-h-[400px]">
                <label className="block text-xs font-bold text-gray-700 mb-2">Contenuto Pagina</label>
                
                <div className="flex-1 border border-gray-300 rounded-lg overflow-hidden bg-white">
                    <RichTextEditor 
                        value={formData.contenuto} 
                        onChange={(newContent) => setFormData({...formData, contenuto: newContent})}
                        placeholder="Scrivi qui il contenuto della pagina..."
                        className="h-full min-h-[300px]"
                    />
                </div>
            </div>

        </div>

        {/* FOOTER AZIONI */}
        <div className="p-3 md:p-4 border-t bg-gray-50 md:rounded-b-lg flex justify-end gap-3 shrink-0">
            <button 
                onClick={onClose} 
                disabled={loading}
                className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded font-medium disabled:opacity-50"
            >
                Annulla
            </button>
            <button 
                onClick={handleSubmit}
                disabled={loading}
                className="px-5 py-2 text-sm bg-red-700 text-white font-bold rounded hover:bg-red-800 shadow disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
                {loading && <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>}
                {isEditing ? 'Salva Modifiche' : 'Crea Pagina'}
            </button>
        </div>

      </div>

      <WikiImageUploadModal
        isOpen={showUploadImage}
        uploadingImage={uploadingImage}
        newImageData={newImageData}
        newImagePreview={newImagePreview}
        onClose={() => setShowUploadImage(false)}
        onSubmit={handleUploadImage}
        onImageFileChange={handleNewImageFileChange}
        setNewImageData={setNewImageData}
        resetForm={resetNewImageForm}
      />

      {/* MODAL EDITOR WIDGET BUTTONS */}
      {showButtonWidgetEditor && (
        <ButtonWidgetEditorModal
          initialData={editingButtonWidget}
          onClose={() => {
            setShowButtonWidgetEditor(false);
            setEditingButtonWidget(null);
          }}
          onSave={async (widgetData) => {
            try {
              let response;
              if (editingButtonWidget) {
                response = await updateWidgetButtons(editingButtonWidget.id, widgetData);
              } else {
                response = await createWidgetButtons(widgetData);
                insertWidget(`{{WIDGET_BUTTONS:${getWidgetToken(response)}}}`);
              }
              const updatedList = await getWidgetButtonsList();
              setAvailableButtonWidgets(updatedList);
              setShowButtonWidgetEditor(false);
              setEditingButtonWidget(null);
            } catch (error) {
              console.error("Errore salvataggio widget buttons:", error);
              alert("Errore durante il salvataggio del widget. Controlla la console.");
            }
          }}
        />
      )}

      {/* MODAL EDITOR WIDGET TIER */}
      {showTierWidgetEditor && (
        <TierWidgetEditorModal
          initialData={editingTierWidget}
          onClose={() => {
            setShowTierWidgetEditor(false);
            setEditingTierWidget(null);
          }}
          onSave={async (payload, existingId) => {
            try {
              let response;
              if (existingId) {
                response = await updateWikiTierWidget(existingId, payload);
              } else {
                response = await createWikiTierWidget(payload);
                insertWidget(`{{WIDGET_TIER:${getWidgetToken(response)}}}`);
              }
              const list = await getWikiTierWidgetList();
              setAvailableTierWidgets(list || []);
              setShowTierWidgetEditor(false);
              setEditingTierWidget(null);
            } catch (error) {
              console.error("Errore salvataggio widget tier:", error);
              throw error;
            }
          }}
        />
      )}

      {/* MODAL EDITOR WIDGET COLLEZIONE TIER */}
      {showTierCollectionWidgetEditor && (
        <TierCollectionWidgetEditorModal
          initialData={editingTierCollectionWidget}
          onClose={() => {
            setShowTierCollectionWidgetEditor(false);
            setEditingTierCollectionWidget(null);
          }}
          onSave={async (payload, existingId) => {
            try {
              let response;
              if (existingId) {
                response = await updateWikiTierCollectionWidget(existingId, payload);
              } else {
                response = await createWikiTierCollectionWidget(payload);
                insertWidget(`{{WIDGET_TIER_COLLECTION:${getWidgetToken(response)}}}`);
              }
              const list = await getWikiTierCollectionWidgetList();
              setAvailableTierCollectionWidgets(list || []);
              setShowTierCollectionWidgetEditor(false);
              setEditingTierCollectionWidget(null);
            } catch (error) {
              console.error("Errore salvataggio widget collezione tier:", error);
              throw error;
            }
          }}
        />
      )}

      {/* MODAL EDITOR WIDGET MATTONI */}
      {showMattoniWidgetEditor && (
        <MattoniWidgetEditorModal
          initialData={editingMattoniWidget}
          onClose={() => {
            setShowMattoniWidgetEditor(false);
            setEditingMattoniWidget(null);
          }}
          onSave={async (payload, existingId) => {
            try {
              let response;
              if (existingId) {
                response = await updateWikiMattoniWidget(existingId, payload);
              } else {
                response = await createWikiMattoniWidget(payload);
                insertWidget(`{{WIDGET_MATTONI:${getWidgetToken(response)}}}`);
              }
              const list = await getWikiMattoniWidgetList();
              setAvailableMattoniWidgets(list || []);
              setShowMattoniWidgetEditor(false);
              setEditingMattoniWidget(null);
            } catch (error) {
              console.error("Errore salvataggio widget mattoni:", error);
              throw error;
            }
          }}
        />
      )}
      
      {/* MODAL EDITOR IMMAGINE */}
      {showImageEditor && editingImage && (
        <div className="fixed inset-0 bg-black/90 z-70 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b flex justify-between items-center bg-blue-50 rounded-t-lg">
              <h3 className="font-bold text-lg text-gray-800 flex items-center gap-2">
                <Edit size={20} className="text-blue-600" />
                Modifica Immagine Wiki
              </h3>
              <button 
                onClick={() => {
                  setShowImageEditor(false);
                  setEditingImage(null);
                }}
                className="text-gray-500 hover:text-red-600 font-bold text-xl px-2"
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <form 
              onSubmit={async (e) => {
                e.preventDefault();
                try {
                  const formData = new FormData();
                  formData.append('titolo', editingImage.titolo);
                  formData.append('descrizione', editingImage.descrizione || '');
                  formData.append('larghezza_max', editingImage.larghezza_max);
                  formData.append('allineamento', editingImage.allineamento);
                  
                  if (editingImage.newImageFile) {
                    formData.append('immagine', editingImage.newImageFile);
                  }

                  await updateWikiImage(editingImage.id, formData);
                  
                  // Ricarica la lista
                  const updatedList = await getWikiImageList();
                  setAvailableImages(updatedList);
                  
                  setShowImageEditor(false);
                  setEditingImage(null);
                } catch (error) {
                  console.error("Errore aggiornamento immagine:", error);
                  alert("Errore durante l'aggiornamento. Controlla la console.");
                }
              }}
              className="p-4 overflow-y-auto flex-1 space-y-4"
            >
              {/* Titolo */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Titolo *</label>
                <input
                  type="text"
                  value={editingImage.titolo}
                  onChange={(e) => setEditingImage(prev => ({ ...prev, titolo: e.target.value }))}
                  className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  required
                />
              </div>

              {/* Descrizione */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Descrizione</label>
                <textarea
                  value={editingImage.descrizione || ''}
                  onChange={(e) => setEditingImage(prev => ({ ...prev, descrizione: e.target.value }))}
                  className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  rows="3"
                />
              </div>

              {/* Cambio Immagine */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">Sostituisci Immagine (opzionale)</label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={(e) => {
                    const file = e.target.files[0];
                    if (file) {
                      setEditingImage(prev => ({ ...prev, newImageFile: file }));
                    }
                  }}
                  className="block w-full text-xs text-gray-500 file:mr-2 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-100 file:text-blue-700 file:font-bold hover:file:bg-blue-200"
                />
              </div>

              {/* Larghezza e Allineamento */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Larghezza Max (px)</label>
                  <input
                    type="number"
                    value={editingImage.larghezza_max}
                    onChange={(e) => setEditingImage(prev => ({ ...prev, larghezza_max: parseInt(e.target.value) || 0 }))}
                    className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                    min="0"
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">Allineamento</label>
                  <select
                    value={editingImage.allineamento}
                    onChange={(e) => setEditingImage(prev => ({ ...prev, allineamento: e.target.value }))}
                    className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-blue-500 outline-none text-sm"
                  >
                    <option value="left">Sinistra</option>
                    <option value="center">Centro</option>
                    <option value="right">Destra</option>
                    <option value="full">Larghezza piena</option>
                  </select>
                </div>
              </div>

              {/* Bottoni */}
              <div className="flex justify-end gap-3 pt-4 border-t">
                <button
                  type="button"
                  onClick={() => {
                    setShowImageEditor(false);
                    setEditingImage(null);
                  }}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded font-medium"
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 text-sm bg-blue-600 text-white font-bold rounded hover:bg-blue-700 shadow"
                >
                  Salva Modifiche
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}