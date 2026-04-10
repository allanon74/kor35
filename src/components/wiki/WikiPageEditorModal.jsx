import React, { useState, useEffect, useRef } from 'react';
import { getWikiTierList, getWikiImageList, getWidgetButtonsList, getWikiTierWidgetList, getWikiMattoniWidgetList, createWikiImage, updateWikiImage, createWidgetButtons, updateWidgetButtons, createWikiTierWidget, updateWikiTierWidget, createWikiMattoniWidget, updateWikiMattoniWidget, createWikiPage, updateWikiPage, getWikiImageUrl } from '../../api';
import RichTextEditor from '../RichTextEditor';
import { Lock, Eye, GripVertical, Image as ImageIcon, Upload, X, MousePointerClick, Edit } from 'lucide-react';
import ButtonWidgetEditorModal from './ButtonWidgetEditorModal';
import TierWidgetEditorModal from './TierWidgetEditorModal'; 
import MattoniWidgetEditorModal from './MattoniWidgetEditorModal';

export default function WikiPageEditorModal({ onClose, onSuccess, initialData = null }) {
  const [formData, setFormData] = useState({
    titolo: '',
    slug: '',
    parent: '',
    contenuto: '',
    public: false,
    visibile_solo_staff: false,
    ordine: 0,
    banner_y: 50, // Default centro verticale (0-100)
    ...initialData
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
  const [availableImages, setAvailableImages] = useState([]);
  const [availableButtonWidgets, setAvailableButtonWidgets] = useState([]);
  const [availableMattoniWidgets, setAvailableMattoniWidgets] = useState([]);
  const [widgetHelperTab, setWidgetHelperTab] = useState('tier'); // 'tier', 'image', 'buttons', 'mattoni'

  // State per il modal widget tier (crea/modifica)
  const [showTierWidgetEditor, setShowTierWidgetEditor] = useState(false);
  const [editingTierWidget, setEditingTierWidget] = useState(null);

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

  // Dragging Logic
  const [isDragging, setIsDragging] = useState(false);
  const [dragStartY, setDragStartY] = useState(0);
  const [initialBannerY, setInitialBannerY] = useState(50);

  // Refs per calcolo visivo
  const previewRef = useRef(null);

  const getWidgetToken = (item) => String(item?.sync_id || item?.id || '').trim();

  // Funzione per estrarre i token widget usati nel contenuto (id legacy o sync_id UUID)
  const getUsedWidgetIds = () => {
    const content = formData.contenuto || '';
    const usedIds = {
      tiers: [],
      images: [],
      buttons: [],
      mattoni: [],
    };

    // Cerca pattern {{WIDGET_TIER:TOKEN}}
    const tierMatches = content.matchAll(/\{\{WIDGET_TIER:([A-Za-z0-9-]+)\}\}/g);
    for (const match of tierMatches) {
      usedIds.tiers.push(String(match[1]));
    }

    // Cerca pattern {{WIDGET_IMAGE:TOKEN}} o {{WIDGET_IMMAGINE:TOKEN}}
    const imageMatches = content.matchAll(/\{\{WIDGET_(?:IMAGE|IMMAGINE):([A-Za-z0-9-]+)\}\}/g);
    for (const match of imageMatches) {
      usedIds.images.push(String(match[1]));
    }

    // Cerca pattern {{WIDGET_BUTTONS:TOKEN}} o {{WIDGET_PULSANTI:TOKEN}}
    const buttonMatches = content.matchAll(/\{\{WIDGET_(?:BUTTONS|PULSANTI):([A-Za-z0-9-]+)\}\}/g);
    for (const match of buttonMatches) {
      usedIds.buttons.push(String(match[1]));
    }

    const mattoniMatches = content.matchAll(/\{\{WIDGET_MATTONI:([A-Za-z0-9-]+)\}\}/g);
    for (const match of mattoniMatches) {
      usedIds.mattoni.push(String(match[1]));
    }

    return usedIds;
  };

  // Funzione per ordinare una lista mettendo prima gli elementi usati
  const sortByUsage = (items, usedIds) => {
    return [...items].sort((a, b) => {
      const aUsed = usedIds.includes(getWidgetToken(a));
      const bUsed = usedIds.includes(getWidgetToken(b));
      
      if (aUsed && !bUsed) return -1;
      if (!aUsed && bUsed) return 1;
      return 0;
    });
  };

  useEffect(() => {
    if (showWidgetHelper) {
        // Carica Tier e Widget Tier
        getWikiTierList()
            .then(data => setAvailableTiers(data))
            .catch(err => console.error("Err loading tiers", err));
        getWikiTierWidgetList()
            .then(data => setAvailableTierWidgets(data || []))
            .catch(err => console.error("Err loading tier widgets", err));

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
      setNewImageData({
        titolo: '',
        descrizione: '',
        immagine: null,
        larghezza_max: 800,
        allineamento: 'center'
      });
      setNewImagePreview(null);
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

  // --- GESTIONE DRAG MAIN PREVIEW ---
  const handleMouseDown = (e) => {
    e.preventDefault();
    setIsDragging(true);
    setDragStartY(e.clientY);
    setInitialBannerY(formData.banner_y || 50);
  };

  const handleMouseMove = (e) => {
    if (!isDragging) return;
    const deltaY = e.clientY - dragStartY;
    // Sensibilità: più bassa per essere precisi
    const sensitivity = 0.4; 
    
    // NOTA: Se trascino il mouse GIÙ, voglio vedere la parte SOPRA dell'immagine.
    // CSS object-position 0% = Top, 100% = Bottom.
    // Quindi Drag Giù (delta positivo) -> deve diminuire la percentuale.
    let newY = initialBannerY - (deltaY * sensitivity);
    
    // Clamp tra 0 e 100
    if (newY < 0) newY = 0;
    if (newY > 100) newY = 100;
    
    setFormData(prev => ({ ...prev, banner_y: Math.round(newY) }));
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  // --- GESTIONE CLICK SU MINI-MAPPA ---
  const handleMiniMapClick = (e) => {
      // Calcola click relativo alla barra laterale
      const rect = e.currentTarget.getBoundingClientRect();
      const clickY = e.clientY - rect.top;
      const percentage = (clickY / rect.height) * 100;
      
      // Aggiorna posizione
      setFormData(prev => ({ 
          ...prev, 
          banner_y: Math.max(0, Math.min(100, Math.round(percentage))) 
      }));
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
        data.append('ordine', formData.ordine);
        data.append('banner_y', formData.banner_y);

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
                <div className="border rounded-lg p-3 bg-gray-50">
                    <label className="text-xs font-bold text-gray-700 mb-2 flex justify-between items-center">
                        <span>Copertina & Posizionamento</span>
                    </label>
                    
                    <div className="flex gap-2 h-40">
                        {/* A. ANTEPRIMA PRINCIPALE (CROP) */}
                        <div 
                            ref={previewRef}
                            className="flex-1 bg-gray-900 rounded overflow-hidden border border-gray-400 relative group cursor-ns-resize shadow-inner select-none"
                            onMouseDown={handleMouseDown}
                            onMouseMove={handleMouseMove}
                            onMouseUp={handleMouseUp}
                            onMouseLeave={handleMouseUp}
                        >
                            {previewUrl ? (
                                <>
                                    <img 
                                        src={previewUrl} 
                                        alt="Anteprima" 
                                        className="w-full h-full object-cover pointer-events-none"
                                        style={{ objectPosition: `center ${formData.banner_y}%` }} 
                                    />
                                    
                                    {/* GRIGLIA TERZI (Statico, mostra dove cadono gli elementi) */}
                                    <div className="absolute inset-0 pointer-events-none opacity-30">
                                        <div className="w-full h-1/3 border-b border-white absolute top-0"></div>
                                        <div className="w-full h-1/3 border-b border-white absolute top-1/3"></div>
                                        <div className="h-full w-1/3 border-r border-white absolute left-0"></div>
                                        <div className="h-full w-1/3 border-r border-white absolute left-1/3"></div>
                                    </div>

                                    {/* Icona Grip */}
                                    <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
                                        <div className="bg-black/50 p-1 rounded-full text-white">
                                            <GripVertical size={20} />
                                        </div>
                                    </div>
                                </>
                            ) : (
                                <div className="w-full h-full flex flex-col items-center justify-center text-gray-400 gap-1">
                                    <ImageIcon size={24}/>
                                    <span className="text-[10px]">No Img</span>
                                </div>
                            )}
                        </div>

                        {/* B. MINI MAPPA (INTERA) */}
                        <div 
                            className="w-12 bg-gray-200 rounded border border-gray-300 relative overflow-hidden cursor-pointer"
                            onClick={handleMiniMapClick}
                            title="Clicca per posizionare"
                        >
                            {previewUrl && (
                                <>
                                    {/* Immagine intera fittata in verticale */}
                                    <img 
                                        src={previewUrl} 
                                        alt="Minimap" 
                                        className="w-full h-full object-cover opacity-50"
                                    />
                                    
                                    {/* RETTANGOLO SELEZIONE (Il taglio visibile) */}
                                    {/* Nota: Non sapendo l'altezza esatta del viewport rispetto all'immagine, 
                                        usiamo un box di altezza fissa o percentuale approssimativa che si muove */}
                                    <div 
                                        className="absolute w-full h-1/4 border-2 border-yellow-500 bg-yellow-500/20 box-border transition-all duration-75"
                                        style={{ 
                                            // Centriamo il box sulla percentuale scelta
                                            top: `${formData.banner_y}%`, 
                                            transform: 'translateY(-50%)' 
                                        }}
                                    ></div>
                                </>
                            )}
                        </div>
                    </div>

                    <div className="mt-3">
                        <input 
                            type="file" 
                            accept="image/*"
                            onChange={handleImageChange}
                            className="block w-full text-xs text-gray-500 file:mr-2 file:py-1 file:px-2 file:rounded file:border-0 file:bg-indigo-100 file:text-indigo-700"
                        />
                        <p className="text-[10px] text-gray-500 mt-1">
                            Trascina l'immagine a sinistra o clicca sulla barra a destra per regolare il taglio.
                        </p>
                    </div>
                </div>

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

                {/* 4. Widget Helper */}
                <div className="bg-blue-50 p-3 rounded border border-blue-200">
                    <button 
                        type="button"
                        onClick={() => setShowWidgetHelper(!showWidgetHelper)}
                        className="w-full bg-blue-600 text-white px-3 py-2 rounded text-xs hover:bg-blue-700 transition flex justify-between items-center"
                    >
                        <span>🧩 Inserisci Widget</span>
                        <span>{showWidgetHelper ? '▲' : '▼'}</span>
                    </button>
                    
                    {/* Reminder Modifica Widget */}
                    <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-[10px] text-yellow-800">
                        <strong>💡 Modifica Widget:</strong> Per modificare un widget già inserito, vai alla sezione corrispondente (Tier/Immagini/Pulsanti) e modifica l'elemento. Le modifiche si rifletteranno automaticamente nella pagina.
                    </div>
                    
                    {showWidgetHelper && (
                        <div className="mt-2 bg-white rounded border border-gray-300 shadow-inner">
                            {/* Tab Selector */}
                            <div className="flex border-b border-gray-200">
                                <button
                                    type="button"
                                    onClick={() => setWidgetHelperTab('tier')}
                                    className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${
                                        widgetHelperTab === 'tier'
                                            ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    📊 Tier
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setWidgetHelperTab('image')}
                                    className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${
                                        widgetHelperTab === 'image'
                                            ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    🖼️ Immagini
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setWidgetHelperTab('buttons')}
                                    className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${
                                        widgetHelperTab === 'buttons'
                                            ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    🔘 Pulsanti
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setWidgetHelperTab('mattoni')}
                                    className={`flex-1 px-3 py-2 text-xs font-bold transition-colors ${
                                        widgetHelperTab === 'mattoni'
                                            ? 'bg-blue-100 text-blue-700 border-b-2 border-blue-600'
                                            : 'text-gray-600 hover:bg-gray-50'
                                    }`}
                                >
                                    🧱 Mattoni
                                </button>
                            </div>
                            
                            {/* Content Area */}
                            <div className="max-h-40 md:max-h-60 overflow-y-auto">
                                {widgetHelperTab === 'tier' && (
                                    <>
                                        {/* Widget Tier già usati in pagina: modifica */}
                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const usedTierIds = usedIds.tiers || [];
                                            const widgetIdsSet = new Set((availableTierWidgets || []).map(w => w.id));
                                            const usedWidgets = usedTierIds.filter(id => widgetIdsSet.has(id));
                                            if (usedWidgets.length === 0) return null;
                                            return (
                                                <div className="p-2 border-b border-gray-200 bg-amber-50">
                                                    <p className="text-xs font-bold text-gray-700 mb-1">Widget Tier in questa pagina</p>
                                                    {usedWidgets.map(id => {
                                                        const w = availableTierWidgets.find(x => x.id === id);
                                                        return (
                                                            <div key={id} className="flex justify-between items-center gap-1 py-1">
                                                                <span className="text-xs truncate">{w?.tier_nome || `#${id}`}</span>
                                                                <div className="flex items-center gap-1 shrink-0">
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => {
                                                                            setEditingTierWidget(w || { id });
                                                                            setShowTierWidgetEditor(true);
                                                                        }}
                                                                        className="p-1 text-indigo-600 hover:bg-indigo-100 rounded"
                                                                        title="Modifica widget tier"
                                                                    >
                                                                        <Edit size={12} />
                                                                    </button>
                                                                    <span className="text-[10px] px-1 rounded bg-gray-100">ID:{id}</span>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            );
                                        })()}
                                        {/* Crea nuovo widget tier */}
                                        <div className="p-2 border-b border-gray-200 bg-indigo-50">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setEditingTierWidget(null);
                                                    setShowTierWidgetEditor(true);
                                                }}
                                                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                                            >
                                                <MousePointerClick size={14} />
                                                Crea / Configura Widget Tier
                                            </button>
                                        </div>
                                        {/* Lista widget tier: inserisci o modifica */}
                                        {availableTierWidgets.length > 0 && (
                                            <div className="p-1 border-b border-gray-200">
                                                <p className="text-xs font-bold text-gray-600 mb-1">Widget Tier esistenti</p>
                                                {(() => {
                                                    const usedIds = getUsedWidgetIds();
                                                    const sorted = sortByUsage(availableTierWidgets, usedIds.tiers);
                                                    return sorted.map(w => {
                                                        const isUsed = usedIds.tiers.includes(w.id);
                                                        return (
                                                            <div
                                                                key={w.id}
                                                                className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group ${
                                                                    isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''
                                                                }`}
                                                            >
                                                                <button
                                                                    type="button"
                                                                    onClick={() => insertWidget(`{{WIDGET_TIER:${getWidgetToken(w)}}}`)}
                                                                    className="flex-1 flex items-center gap-2 truncate"
                                                                >
                                                                    <span className={`font-bold truncate ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>
                                                                        {isUsed && <span className="text-green-600">✓ </span>}
                                                                        {w.tier_nome || `Widget #${w.id}`}
                                                                    </span>
                                                                </button>
                                                                <div className="flex items-center gap-1 shrink-0">
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => { setEditingTierWidget(w); setShowTierWidgetEditor(true); }}
                                                                        className="p-1 text-indigo-600 hover:bg-indigo-100 rounded"
                                                                        title="Modifica"
                                                                    >
                                                                        <Edit size={12} />
                                                                    </button>
                                                                    <span className="text-[10px] px-1 rounded bg-gray-100">ID:{w.id}</span>
                                                                </div>
                                                            </div>
                                                        );
                                                    });
                                                })()}
                                            </div>
                                        )}
                                        {/* Tier semplici (inserimento diretto per id tier) */}
                                        <div className="p-2 border-b border-gray-200 bg-gray-50 sticky top-0 z-10">
                                            <p className="text-xs font-bold text-gray-600 mb-1">Inserisci tier semplice (senza opzioni)</p>
                                            <input
                                                type="text"
                                                placeholder="Cerca tier per nome..."
                                                value={tierSearch}
                                                onChange={(e) => setTierSearch(e.target.value)}
                                                className="w-full px-2 py-1.5 text-xs border border-gray-300 rounded focus:ring-2 focus:ring-blue-500 outline-none"
                                            />
                                        </div>
                                        {availableTiers.length === 0 && <p className="p-2 text-xs text-gray-500">Caricamento...</p>}
                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const searchLower = (tierSearch || '').trim().toLowerCase();
                                            const sortedTiers = [...availableTiers]
                                                .filter(t => !searchLower || (t.nome || '').toLowerCase().includes(searchLower))
                                                .sort((a, b) => (a.nome || '').localeCompare(b.nome || ''));
                                            return sortedTiers.map(tier => {
                                                const isUsed = usedIds.tiers.includes(tier.id);
                                                return (
                                                    <button
                                                        key={tier.id}
                                                        type="button"
                                                        onClick={() => insertWidget(`{{WIDGET_TIER:${getWidgetToken(tier)}}}`)}
                                                        className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center ${
                                                            isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''
                                                        }`}
                                                    >
                                                        <span className={`font-bold truncate pr-2 flex items-center gap-2 ${isUsed ? 'text-green-700' : 'text-gray-700'}`}>
                                                            {isUsed && <span className="text-green-600">✓</span>}
                                                            {tier.nome}
                                                        </span>
                                                        <span className={`text-[10px] px-1 rounded ${isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'}`}>
                                                            ID:{tier.id}
                                                        </span>
                                                    </button>
                                                );
                                            });
                                        })()}
                                    </>
                                )}
                                
                                {widgetHelperTab === 'image' && (
                                    <>
                                        {/* Pulsante Carica Nuova Immagine */}
                                        <div className="p-2 border-b border-gray-200 bg-green-50">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setWidgetHelperTab('image');
                                                    setShowUploadImage(true);
                                                }}
                                                className="w-full bg-green-600 hover:bg-green-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                                            >
                                                <Upload size={14} />
                                                Carica Nuova Immagine
                                            </button>
                                        </div>
                                        
                                        {/* Lista Immagini */}
                                        {availableImages.length === 0 && !showUploadImage && (
                                            <p className="p-2 text-xs text-gray-500">Nessuna immagine disponibile</p>
                                        )}
                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const sortedImages = sortByUsage(availableImages, usedIds.images);
                                            
                                            return sortedImages.map(img => {
                                                const isUsed = usedIds.images.includes(img.id);
                                                return (
                                                    <div 
                                                        key={img.id}
                                                        className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${
                                                            isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''
                                                        }`}
                                                    >
                                                        <button
                                                            type="button"
                                                            onClick={() => insertWidget(`{{WIDGET_IMAGE:${getWidgetToken(img)}}}`)}
                                                            className="flex-1 flex items-center gap-2 truncate"
                                                        >
                                                            <ImageIcon size={14} className={`shrink-0 ${
                                                                isUsed ? 'text-green-600' : 'text-gray-400'
                                                            }`} />
                                                            <span className={`font-bold group-hover:text-blue-800 truncate ${
                                                                isUsed ? 'text-green-700' : 'text-gray-700'
                                                            }`}>
                                                                {isUsed && <span className="text-green-600">✓ </span>}
                                                                {img.titolo || `Immagine #${img.id}`}
                                                            </span>
                                                        </button>
                                                        <div className="flex items-center gap-1 shrink-0">
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    setEditingImage(img);
                                                                    setShowImageEditor(true);
                                                                }}
                                                                className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors"
                                                                title="Modifica immagine"
                                                            >
                                                                <Edit size={12} />
                                                            </button>
                                                            <span className={`text-[10px] px-1 rounded ${
                                                                isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'
                                                            }`}>
                                                                ID:{img.id}
                                                            </span>
                                                        </div>
                                                    </div>
                                                );
                                            });
                                        })()}
                                    </>
                                )}
                                
                                {widgetHelperTab === 'buttons' && (
                                    <>
                                        {/* Pulsante Crea Nuovo Widget Buttons */}
                                        <div className="p-2 border-b border-gray-200 bg-purple-50">
                                            <button
                                                type="button"
                                                onClick={() => setShowButtonWidgetEditor(true)}
                                                className="w-full bg-purple-600 hover:bg-purple-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                                            >
                                                <MousePointerClick size={14} />
                                                Crea Nuovo Widget Pulsanti
                                            </button>
                                        </div>
                                        
                                        {/* Lista Widget Buttons */}
                                        {availableButtonWidgets.length === 0 && (
                                            <p className="p-2 text-xs text-gray-500">Nessun widget pulsanti disponibile</p>
                                        )}
                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const sortedWidgets = sortByUsage(availableButtonWidgets, usedIds.buttons);
                                            
                                            return sortedWidgets.map(widget => {
                                                const isUsed = usedIds.buttons.includes(widget.id);
                                                return (
                                                    <div
                                                        key={widget.id}
                                                        className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${
                                                            isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''
                                                        }`}
                                                    >
                                                        <button
                                                            type="button"
                                                            onClick={() => insertWidget(`{{WIDGET_BUTTONS:${getWidgetToken(widget)}}}`)}
                                                            className="flex-1 flex items-center gap-2 truncate"
                                                        >
                                                            <MousePointerClick size={14} className={`shrink-0 ${
                                                                isUsed ? 'text-purple-600' : 'text-purple-500'
                                                            }`} />
                                                            <span className={`font-bold group-hover:text-blue-800 truncate ${
                                                                isUsed ? 'text-green-700' : 'text-gray-700'
                                                            }`}>
                                                                {isUsed && <span className="text-green-600">✓ </span>}
                                                                {widget.title || `Widget #${widget.id}`}
                                                            </span>
                                                        </button>
                                                        <div className="flex items-center gap-1 shrink-0">
                                                            <button
                                                                type="button"
                                                                onClick={() => {
                                                                    setEditingButtonWidget(widget);
                                                                    setShowButtonWidgetEditor(true);
                                                                }}
                                                                className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors"
                                                                title="Modifica widget"
                                                            >
                                                                <Edit size={12} />
                                                            </button>
                                                            <span className={`text-[10px] px-1 rounded ${
                                                                isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'
                                                            }`}>
                                                                {widget.buttons?.length || 0} btn
                                                            </span>
                                                        </div>
                                                    </div>
                                                );
                                            });
                                        })()}
                                    </>
                                )}

                                {widgetHelperTab === 'mattoni' && (
                                    <>
                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const usedMattoniIds = usedIds.mattoni || [];
                                            const widgetIdsSet = new Set((availableMattoniWidgets || []).map(w => w.id));
                                            const usedWidgets = usedMattoniIds.filter(x => widgetIdsSet.has(x));
                                            if (usedWidgets.length === 0) return null;
                                            return (
                                                <div className="p-2 border-b border-gray-200 bg-amber-50">
                                                    <p className="text-xs font-bold text-gray-700 mb-1">Widget Mattoni in questa pagina</p>
                                                    {usedWidgets.map(wid => {
                                                        const w = availableMattoniWidgets.find(x => x.id === wid);
                                                        return (
                                                            <div key={wid} className="flex justify-between items-center gap-1 py-1">
                                                                <span className="text-xs truncate">{w?.title || `Widget #${wid}`}</span>
                                                                <div className="flex items-center gap-1 shrink-0">
                                                                    <button
                                                                        type="button"
                                                                        onClick={() => {
                                                                            setEditingMattoniWidget(w || { id: wid });
                                                                            setShowMattoniWidgetEditor(true);
                                                                        }}
                                                                        className="p-1 text-indigo-600 hover:bg-indigo-100 rounded"
                                                                        title="Modifica widget mattoni"
                                                                    >
                                                                        <Edit size={12} />
                                                                    </button>
                                                                    <span className="text-[10px] px-1 rounded bg-gray-100">ID:{wid}</span>
                                                                </div>
                                                            </div>
                                                        );
                                                    })}
                                                </div>
                                            );
                                        })()}

                                        <div className="p-2 border-b border-gray-200 bg-indigo-50">
                                            <button
                                                type="button"
                                                onClick={() => {
                                                    setEditingMattoniWidget(null);
                                                    setShowMattoniWidgetEditor(true);
                                                }}
                                                className="w-full bg-indigo-600 hover:bg-indigo-700 text-white px-3 py-2 rounded text-xs font-bold flex items-center justify-center gap-2 transition-colors"
                                            >
                                                <MousePointerClick size={14} />
                                                Crea / Configura Widget Mattoni
                                            </button>
                                        </div>

                                        {availableMattoniWidgets.length === 0 && (
                                            <p className="p-2 text-xs text-gray-500">Nessun widget mattoni disponibile</p>
                                        )}

                                        {(() => {
                                            const usedIds = getUsedWidgetIds();
                                            const sorted = sortByUsage(availableMattoniWidgets, usedIds.mattoni);
                                            return sorted.map(w => {
                                                const isUsed = usedIds.mattoni.includes(w.id);
                                                return (
                                                    <div
                                                        key={w.id}
                                                        className={`w-full text-left text-xs p-2 border-b hover:bg-blue-50 flex justify-between items-center group transition-colors ${
                                                            isUsed ? 'bg-green-50 border-l-4 border-green-500' : ''
                                                        }`}
                                                    >
                                                        <button
                                                            type="button"
                                                            onClick={() => insertWidget(`{{WIDGET_MATTONI:${getWidgetToken(w)}}}`)}
                                                            className="flex-1 flex items-center gap-2 truncate"
                                                        >
                                                            <span className={`font-bold group-hover:text-blue-800 truncate ${
                                                                isUsed ? 'text-green-700' : 'text-gray-700'
                                                            }`}>
                                                                {isUsed && <span className="text-green-600">✓ </span>}
                                                                {w.title || `Widget #${w.id}`}
                                                            </span>
                                                        </button>
                                                        <div className="flex items-center gap-1 shrink-0">
                                                            <button
                                                                type="button"
                                                                onClick={() => { setEditingMattoniWidget(w); setShowMattoniWidgetEditor(true); }}
                                                                className="p-1 text-indigo-600 hover:bg-indigo-100 rounded transition-colors"
                                                                title="Modifica widget"
                                                            >
                                                                <Edit size={12} />
                                                            </button>
                                                            <span className={`text-[10px] px-1 rounded ${
                                                                isUsed ? 'bg-green-200 text-green-800' : 'bg-gray-100 text-gray-500'
                                                            }`}>
                                                                ID:{w.id}
                                                            </span>
                                                        </div>
                                                    </div>
                                                );
                                            });
                                        })()}
                                    </>
                                )}
                            </div>
                        </div>
                    )}
                </div>
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

      {/* MODAL CARICAMENTO IMMAGINE */}
      {showUploadImage && (
        <div className="fixed inset-0 bg-black/90 z-60 flex items-center justify-center p-4">
          <div className="bg-white rounded-lg shadow-xl w-full max-w-2xl max-h-[90vh] flex flex-col">
            {/* Header */}
            <div className="p-4 border-b flex justify-between items-center bg-green-50 rounded-t-lg">
              <h3 className="font-bold text-lg text-gray-800 flex items-center gap-2">
                <Upload size={20} className="text-green-600" />
                Carica Nuova Immagine Wiki
              </h3>
              <button 
                onClick={() => {
                  setShowUploadImage(false);
                  setNewImageData({
                    titolo: '',
                    descrizione: '',
                    immagine: null,
                    larghezza_max: 800,
                    allineamento: 'center'
                  });
                  setNewImagePreview(null);
                }}
                className="text-gray-500 hover:text-red-600 font-bold text-xl px-2"
                disabled={uploadingImage}
              >
                <X size={20} />
              </button>
            </div>

            {/* Body */}
            <form onSubmit={handleUploadImage} className="p-4 overflow-y-auto flex-1 space-y-4">
              {/* Titolo */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Titolo <span className="text-red-500">*</span>
                </label>
                <input
                  type="text"
                  value={newImageData.titolo}
                  onChange={(e) => setNewImageData(prev => ({ ...prev, titolo: e.target.value }))}
                  className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                  placeholder="Es: Mappa della città"
                  required
                  disabled={uploadingImage}
                />
              </div>

              {/* Descrizione */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Descrizione (opzionale)
                </label>
                <textarea
                  value={newImageData.descrizione}
                  onChange={(e) => setNewImageData(prev => ({ ...prev, descrizione: e.target.value }))}
                  className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                  rows="3"
                  placeholder="Descrizione dell'immagine..."
                  disabled={uploadingImage}
                />
              </div>

              {/* File Upload */}
              <div>
                <label className="block text-xs font-bold text-gray-700 mb-1">
                  Immagine <span className="text-red-500">*</span>
                </label>
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleNewImageFileChange}
                  className="block w-full text-xs text-gray-500 file:mr-2 file:py-2 file:px-4 file:rounded file:border-0 file:bg-green-100 file:text-green-700 file:font-bold hover:file:bg-green-200"
                  required
                  disabled={uploadingImage}
                />
                {newImagePreview && (
                  <div className="mt-2 border border-gray-300 rounded p-2 bg-gray-50">
                    <img 
                      src={newImagePreview} 
                      alt="Anteprima" 
                      className="max-w-full h-auto max-h-48 mx-auto rounded"
                    />
                  </div>
                )}
              </div>

              {/* Larghezza Max e Allineamento */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">
                    Larghezza Max (px)
                  </label>
                  <input
                    type="number"
                    value={newImageData.larghezza_max}
                    onChange={(e) => setNewImageData(prev => ({ ...prev, larghezza_max: parseInt(e.target.value) || 0 }))}
                    className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                    min="0"
                    placeholder="0 = originale"
                    disabled={uploadingImage}
                  />
                </div>
                <div>
                  <label className="block text-xs font-bold text-gray-700 mb-1">
                    Allineamento
                  </label>
                  <select
                    value={newImageData.allineamento}
                    onChange={(e) => setNewImageData(prev => ({ ...prev, allineamento: e.target.value }))}
                    className="w-full border border-gray-300 p-2 rounded focus:ring-2 focus:ring-green-500 outline-none text-sm"
                    disabled={uploadingImage}
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
                    setShowUploadImage(false);
                    setNewImageData({
                      titolo: '',
                      descrizione: '',
                      immagine: null,
                      larghezza_max: 800,
                      allineamento: 'center'
                    });
                    setNewImagePreview(null);
                  }}
                  disabled={uploadingImage}
                  className="px-4 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded font-medium disabled:opacity-50"
                >
                  Annulla
                </button>
                <button
                  type="submit"
                  disabled={uploadingImage || !newImageData.immagine || !newImageData.titolo.trim()}
                  className="px-5 py-2 text-sm bg-green-600 text-white font-bold rounded hover:bg-green-700 shadow disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {uploadingImage && <div className="animate-spin h-3 w-3 border-2 border-white border-t-transparent rounded-full"></div>}
                  {uploadingImage ? 'Caricamento...' : 'Carica Immagine'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

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