import React, { useState, useEffect } from 'react';
import { X, Plus, Trash2, GripVertical, ExternalLink, AppWindow, ChevronDown } from 'lucide-react';
import * as LucideIcons from 'lucide-react';
import { COLOR_PRESETS, SIZE_PRESETS, BUTTON_STYLES } from '../wg/WidgetButtons';
import { getWikiMenu } from '../../api';

/**
 * Modal per configurare il Widget Buttons
 * Permette di creare/modificare pulsanti configurabili
 */

// Lista delle icone più comuni di Lucide
const COMMON_ICONS = [
  'Sparkles', 'LogIn', 'Scroll', 'BookOpen', 'Users', 'Calendar', 'Share2',
  'Home', 'Settings', 'Mail', 'Phone', 'MapPin', 'Globe', 'Shield',
  'Star', 'Heart', 'Zap', 'Award', 'Bookmark', 'Bell', 'Camera',
  'Gift', 'Music', 'Video', 'Image', 'File', 'Folder', 'Search',
  'Edit', 'Trash', 'Download', 'Upload', 'Save', 'Send', 'Lock',
  'Unlock', 'Key', 'Eye', 'EyeOff', 'Flag', 'Tag', 'Target',
  'TrendingUp', 'Activity', 'BarChart', 'PieChart', 'Coffee', 'Pizza',
  'Briefcase', 'ShoppingCart', 'CreditCard', 'DollarSign', 'Percent'
];

export default function ButtonWidgetEditorModal({ onClose, onSave, initialData = null }) {
  const [widgetTitle, setWidgetTitle] = useState(initialData?.title || '');
  const [buttons, setButtons] = useState(initialData?.buttons || []);
  const [editingIndex, setEditingIndex] = useState(null);
  
  // Lista degli slug wiki disponibili
  const [wikiSlugs, setWikiSlugs] = useState([]);
  const [filteredSlugs, setFilteredSlugs] = useState([]);
  const [showSlugSuggestions, setShowSlugSuggestions] = useState(false);

  // Form per singolo pulsante
  const [buttonForm, setButtonForm] = useState({
    title: '',
    description: '',
    subtext: '',
    icon: '',
    color_preset: 'indigo_purple',
    size: 'medium',
    style: 'gradient',
    link_type: 'wiki', // 'wiki' o 'app'
    wiki_slug: '',
    app_route: ''
  });

  // Carica gli slug wiki all'apertura
  useEffect(() => {
    const fetchWikiSlugs = async () => {
      try {
        const menuData = await getWikiMenu();
        const slugs = menuData.map(page => page.slug).filter(Boolean);
        setWikiSlugs(slugs);
      } catch (error) {
        console.error('Errore caricamento slugs:', error);
      }
    };
    fetchWikiSlugs();
  }, []);

  // Filtra gli slug in base al testo inserito
  useEffect(() => {
    if (buttonForm.wiki_slug && wikiSlugs.length > 0) {
      const filtered = wikiSlugs.filter(slug => 
        slug.toLowerCase().includes(buttonForm.wiki_slug.toLowerCase())
      ).slice(0, 10); // Max 10 suggerimenti
      setFilteredSlugs(filtered);
    } else {
      setFilteredSlugs([]);
    }
  }, [buttonForm.wiki_slug, wikiSlugs]);

  // Apri form per modificare un pulsante esistente
  const handleEditButton = (index) => {
    setEditingIndex(index);
    setButtonForm(buttons[index]);
  };

  // Aggiungi o aggiorna pulsante
  const handleSaveButton = () => {
    if (!buttonForm.title.trim()) {
      alert('Il titolo è obbligatorio');
      return;
    }

    if (buttonForm.link_type === 'wiki' && !buttonForm.wiki_slug.trim()) {
      alert('Lo slug della pagina wiki è obbligatorio');
      return;
    }

    if (buttonForm.link_type === 'app' && !buttonForm.app_route.trim()) {
      alert('Il percorso dell\'app è obbligatorio');
      return;
    }

    const newButtons = [...buttons];
    
    if (editingIndex !== null) {
      // Modifica esistente
      newButtons[editingIndex] = { ...buttonForm };
    } else {
      // Nuovo pulsante
      newButtons.push({ ...buttonForm });
    }

    setButtons(newButtons);
    
    // Reset form
    setButtonForm({
      title: '',
      description: '',
      subtext: '',
      icon: '',
      color_preset: 'indigo_purple',
      size: 'medium',
      style: 'gradient',
      link_type: 'wiki',
      wiki_slug: '',
      app_route: ''
    });
    setEditingIndex(null);
  };

  // Cancella form
  const handleCancelEdit = () => {
    setButtonForm({
      title: '',
      description: '',
      subtext: '',
      icon: '',
      color_preset: 'indigo_purple',
      size: 'medium',
      style: 'gradient',
      link_type: 'wiki',
      wiki_slug: '',
      app_route: ''
    });
    setEditingIndex(null);
  };

  // Elimina pulsante
  const handleDeleteButton = (index) => {
    if (confirm('Sei sicuro di voler eliminare questo pulsante?')) {
      setButtons(buttons.filter((_, i) => i !== index));
      if (editingIndex === index) {
        handleCancelEdit();
      }
    }
  };

  // Sposta pulsante
  const moveButton = (index, direction) => {
    const newButtons = [...buttons];
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    
    if (targetIndex >= 0 && targetIndex < buttons.length) {
      [newButtons[index], newButtons[targetIndex]] = [newButtons[targetIndex], newButtons[index]];
      setButtons(newButtons);
    }
  };

  // Salva widget completo
  const handleSaveWidget = () => {
    if (buttons.length === 0) {
      alert('Aggiungi almeno un pulsante');
      return;
    }

    onSave({
      title: widgetTitle,
      buttons: buttons
    });
  };

  // Render icona preview
  const IconPreview = ({ iconName, size = 20 }) => {
    const Icon = LucideIcons[iconName];
    return Icon ? <Icon size={size} /> : <div className="w-5 h-5 bg-gray-300 rounded"></div>;
  };

  return (
    <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4 overflow-y-auto">
      <div className="bg-white rounded-xl shadow-2xl max-w-6xl w-full max-h-[90vh] overflow-hidden flex flex-col my-8">
        
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-gray-200 bg-linear-to-r from-indigo-50 to-purple-50">
          <div>
            <h2 className="text-2xl font-bold text-gray-900">Widget Pulsanti</h2>
            <p className="text-sm text-gray-600 mt-1">Configura i pulsanti di navigazione</p>
          </div>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 p-2 hover:bg-white/50 rounded-lg transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        <div className="flex-1 overflow-y-auto p-6">
          <div className="grid md:grid-cols-2 gap-6">
            
            {/* COLONNA SINISTRA: Lista Pulsanti */}
            <div>
              <h3 className="text-lg font-bold text-gray-900 mb-4 flex items-center gap-2">
                <span>Pulsanti Configurati</span>
                <span className="text-sm font-normal text-gray-500">({buttons.length})</span>
              </h3>

              {buttons.length === 0 ? (
                <div className="bg-gray-50 border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
                  <p className="text-gray-500 text-sm">Nessun pulsante configurato</p>
                  <p className="text-gray-400 text-xs mt-1">Usa il form a destra per aggiungerne uno</p>
                </div>
              ) : (
                <div className="space-y-2">
                  {buttons.map((btn, index) => (
                    <div
                      key={index}
                      className={`
                        border-2 rounded-lg p-3 transition-all
                        ${editingIndex === index 
                          ? 'border-indigo-500 bg-indigo-50' 
                          : 'border-gray-200 bg-white hover:border-gray-300'
                        }
                      `}
                    >
                      <div className="flex items-start gap-3">
                        {/* Icona drag (decorativa) */}
                        <div className="text-gray-400 mt-1">
                          <GripVertical size={16} />
                        </div>

                        {/* Icona pulsante */}
                        <div className={`${COLOR_PRESETS[btn.color_preset]?.icon || 'bg-gray-500'} text-white p-2 rounded shrink-0`}>
                          <IconPreview iconName={btn.icon} />
                        </div>

                        {/* Info */}
                        <div className="flex-1 min-w-0">
                          <div className="font-bold text-sm text-gray-900 truncate">{btn.title}</div>
                          <div className="text-xs text-gray-500 flex items-center gap-2 mt-1">
                            <span className="capitalize">{SIZE_PRESETS[btn.size]?.name}</span>
                            <span>•</span>
                            <span className="capitalize">{btn.style === 'gradient' ? 'Gradiente' : 'Chiaro'}</span>
                            <span>•</span>
                            {btn.link_type === 'wiki' ? (
                              <span className="flex items-center gap-1">
                                <ExternalLink size={10} /> Wiki
                              </span>
                            ) : (
                              <span className="flex items-center gap-1">
                                <AppWindow size={10} /> App
                              </span>
                            )}
                          </div>
                        </div>

                        {/* Azioni */}
                        <div className="flex gap-1 shrink-0">
                          <button
                            onClick={() => moveButton(index, 'up')}
                            disabled={index === 0}
                            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                            title="Sposta su"
                          >
                            ▲
                          </button>
                          <button
                            onClick={() => moveButton(index, 'down')}
                            disabled={index === buttons.length - 1}
                            className="p-1 text-gray-400 hover:text-gray-600 disabled:opacity-30"
                            title="Sposta giù"
                          >
                            ▼
                          </button>
                          <button
                            onClick={() => handleEditButton(index)}
                            className="p-1.5 text-indigo-600 hover:bg-indigo-100 rounded transition-colors"
                            title="Modifica"
                          >
                            ✏️
                          </button>
                          <button
                            onClick={() => handleDeleteButton(index)}
                            className="p-1.5 text-red-600 hover:bg-red-100 rounded transition-colors"
                            title="Elimina"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* COLONNA DESTRA: Form Pulsante */}
            <div className="border-l border-gray-200 pl-6">
              <h3 className="text-lg font-bold text-gray-900 mb-4">
                {editingIndex !== null ? 'Modifica Pulsante' : 'Nuovo Pulsante'}
              </h3>

              <div className="space-y-4">
                
                {/* Titolo */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">
                    Titolo * <span className="text-xs font-normal text-gray-500">(breve)</span>
                  </label>
                  <input
                    type="text"
                    value={buttonForm.title}
                    onChange={(e) => setButtonForm({ ...buttonForm, title: e.target.value })}
                    placeholder="Es: Ambientazione"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                {/* Descrizione */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">
                    Descrizione <span className="text-xs font-normal text-gray-500">(opzionale)</span>
                  </label>
                  <input
                    type="text"
                    value={buttonForm.description}
                    onChange={(e) => setButtonForm({ ...buttonForm, description: e.target.value })}
                    placeholder="Es: Scopri il mondo di KOR35"
                    className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                  />
                </div>

                {/* Sottotesto (solo per style gradient) */}
                {buttonForm.style === 'gradient' && (
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Sottotesto <span className="text-xs font-normal text-gray-500">(opzionale, solo gradiente)</span>
                    </label>
                    <input
                      type="text"
                      value={buttonForm.subtext}
                      onChange={(e) => setButtonForm({ ...buttonForm, subtext: e.target.value })}
                      placeholder="Es: Inizia da qui →"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                    />
                  </div>
                )}

                {/* Icona con Preview */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">
                    Icona <span className="text-xs font-normal text-gray-500">(opzionale)</span>
                  </label>
                  <div className="relative">
                    <select
                      value={buttonForm.icon}
                      onChange={(e) => setButtonForm({ ...buttonForm, icon: e.target.value })}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent appearance-none pr-10"
                    >
                      <option value="">Nessuna icona</option>
                      {COMMON_ICONS.map(iconName => (
                        <option key={iconName} value={iconName}>{iconName}</option>
                      ))}
                    </select>
                    
                    {/* Preview Icona Selezionata */}
                    {buttonForm.icon && (
                      <div className="absolute right-10 top-1/2 -translate-y-1/2 pointer-events-none">
                        <IconPreview iconName={buttonForm.icon} size={20} />
                      </div>
                    )}
                    
                    <div className="absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none">
                      <ChevronDown size={16} className="text-gray-400" />
                    </div>
                  </div>
                  
                  {/* Preview Grande sotto */}
                  {buttonForm.icon && (
                    <div className="mt-2 p-3 bg-gray-50 rounded-lg border border-gray-200 flex items-center gap-3">
                      <div className="bg-indigo-500 text-white p-2 rounded">
                        <IconPreview iconName={buttonForm.icon} size={24} />
                      </div>
                      <span className="text-sm text-gray-700 font-medium">{buttonForm.icon}</span>
                    </div>
                  )}
                </div>

                {/* Stile */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">Stile *</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setButtonForm({ ...buttonForm, style: 'gradient' })}
                      className={`p-3 border-2 rounded-lg text-sm font-medium transition-all ${
                        buttonForm.style === 'gradient'
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Gradiente (grande)
                    </button>
                    <button
                      type="button"
                      onClick={() => setButtonForm({ ...buttonForm, style: 'light' })}
                      className={`p-3 border-2 rounded-lg text-sm font-medium transition-all ${
                        buttonForm.style === 'light'
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      Chiaro (compatto)
                    </button>
                  </div>
                </div>

                {/* Dimensione */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">Dimensione *</label>
                  <div className="grid grid-cols-3 gap-2">
                    {Object.entries(SIZE_PRESETS).map(([key, preset]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setButtonForm({ ...buttonForm, size: key })}
                        className={`p-2 border-2 rounded-lg text-xs font-medium transition-all ${
                          buttonForm.size === key
                            ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                            : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                        }`}
                      >
                        {preset.name}
                      </button>
                    ))}
                  </div>
                </div>

                {/* Colore */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">Schema Colori *</label>
                  <div className="grid grid-cols-2 gap-2 max-h-48 overflow-y-auto p-1">
                    {Object.entries(COLOR_PRESETS).map(([key, preset]) => (
                      <button
                        key={key}
                        type="button"
                        onClick={() => setButtonForm({ ...buttonForm, color_preset: key })}
                        className={`p-2 border-2 rounded-lg text-xs font-medium transition-all flex items-center gap-2 ${
                          buttonForm.color_preset === key
                            ? 'border-indigo-500 bg-indigo-50'
                            : 'border-gray-300 bg-white hover:border-gray-400'
                        }`}
                      >
                        <div className={`w-6 h-6 rounded bg-linear-to-br ${preset.gradient}`}></div>
                        <span className="truncate">{preset.name}</span>
                      </button>
                    ))}
                  </div>
                </div>

                {/* Tipo Link */}
                <div>
                  <label className="block text-sm font-bold text-gray-700 mb-1">Destinazione *</label>
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      type="button"
                      onClick={() => setButtonForm({ ...buttonForm, link_type: 'wiki' })}
                      className={`p-3 border-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                        buttonForm.link_type === 'wiki'
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      <ExternalLink size={16} /> Pagina Wiki
                    </button>
                    <button
                      type="button"
                      onClick={() => setButtonForm({ ...buttonForm, link_type: 'app' })}
                      className={`p-3 border-2 rounded-lg text-sm font-medium transition-all flex items-center justify-center gap-2 ${
                        buttonForm.link_type === 'app'
                          ? 'border-indigo-500 bg-indigo-50 text-indigo-700'
                          : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                      }`}
                    >
                      <AppWindow size={16} /> Sezione App
                    </button>
                  </div>
                </div>

                {/* Campo Wiki Slug con Autocomplete */}
                {buttonForm.link_type === 'wiki' && (
                  <div className="relative">
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Slug Pagina Wiki * <span className="text-xs font-normal text-gray-500">(es: ambientazione)</span>
                    </label>
                    <input
                      type="text"
                      value={buttonForm.wiki_slug}
                      onChange={(e) => {
                        setButtonForm({ ...buttonForm, wiki_slug: e.target.value });
                        setShowSlugSuggestions(true);
                      }}
                      onFocus={() => setShowSlugSuggestions(true)}
                      onBlur={() => setTimeout(() => setShowSlugSuggestions(false), 200)}
                      placeholder="ambientazione"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                      autoComplete="off"
                    />
                    
                    {/* Suggerimenti Autocomplete */}
                    {showSlugSuggestions && filteredSlugs.length > 0 && (
                      <div className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-48 overflow-y-auto">
                        {filteredSlugs.map((slug, idx) => (
                          <button
                            key={idx}
                            type="button"
                            onClick={() => {
                              setButtonForm({ ...buttonForm, wiki_slug: slug });
                              setShowSlugSuggestions(false);
                            }}
                            className="w-full text-left px-3 py-2 hover:bg-indigo-50 text-sm font-mono text-gray-700 hover:text-indigo-700 transition-colors border-b border-gray-100 last:border-b-0"
                          >
                            {slug}
                          </button>
                        ))}
                      </div>
                    )}
                    
                    <p className="text-xs text-gray-500 mt-1">
                      💡 Inizia a digitare per vedere i suggerimenti. Puoi anche inserire slug nuovi.
                    </p>
                  </div>
                )}

                {/* Campo App Route */}
                {buttonForm.link_type === 'app' && (
                  <div>
                    <label className="block text-sm font-bold text-gray-700 mb-1">
                      Percorso App * <span className="text-xs font-normal text-gray-500">(es: /app)</span>
                    </label>
                    <input
                      type="text"
                      value={buttonForm.app_route}
                      onChange={(e) => setButtonForm({ ...buttonForm, app_route: e.target.value })}
                      placeholder="/app"
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent font-mono text-sm"
                    />
                  </div>
                )}

                {/* Azioni form pulsante */}
                <div className="flex gap-2 pt-4 border-t border-gray-200">
                  {editingIndex !== null && (
                    <button
                      type="button"
                      onClick={handleCancelEdit}
                      className="flex-1 px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 font-medium transition-colors"
                    >
                      Annulla
                    </button>
                  )}
                  <button
                    type="button"
                    onClick={handleSaveButton}
                    className="flex-1 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium transition-colors flex items-center justify-center gap-2"
                  >
                    <Plus size={18} />
                    {editingIndex !== null ? 'Aggiorna' : 'Aggiungi'}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 p-6 bg-gray-50 flex items-center justify-between">
          <button
            onClick={onClose}
            className="px-6 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-white font-medium transition-colors"
          >
            Annulla
          </button>
          <button
            onClick={handleSaveWidget}
            disabled={buttons.length === 0}
            className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-bold transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            Salva Widget
          </button>
        </div>
      </div>
    </div>
  );
}
