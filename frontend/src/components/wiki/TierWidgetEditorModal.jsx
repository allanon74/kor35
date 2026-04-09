import React, { useState, useEffect, useMemo } from 'react';
import { X, Plus, Trash2 } from 'lucide-react';
import { CHROMATIC_STYLES } from '../../utils/chromaticStyles';
import { getWikiTierList, getWikiTierWidget } from '../../api';

/** I 11 colori predefiniti per il gradiente (stessi temi degli stili cromatici) */
const GRADIENT_PRESET_COLORS = [
  { key: 'default', name: 'Default (grigio)', hex: '#374151' },
  { key: 'gray', name: 'Grigio', hex: '#b6cdd9' },
  { key: 'white', name: 'Bianco', hex: '#F0F0F0' },
  { key: 'red', name: 'Rosso', hex: '#FA0000' },
  { key: 'black', name: 'Nero', hex: '#111827' },
  { key: 'ochre', name: 'Ocra', hex: '#c79e0b' },
  { key: 'blue', name: 'Blu', hex: '#135cd1' },
  { key: 'yellow', name: 'Giallo', hex: '#faf610' },
  { key: 'purple', name: 'Viola', hex: '#efaaff' },
  { key: 'green', name: 'Verde', hex: '#92fa88' },
  { key: 'porpora', name: 'Porpora', hex: '#860050' },
];

const DEFAULT_GRADIENT_HEX = GRADIENT_PRESET_COLORS[0].hex;

/**
 * Modal per creare o modificare un Widget Tier (tier + opzioni di visualizzazione, gradiente colori).
 */
export default function TierWidgetEditorModal({ onClose, onSave, initialData = null }) {
  const [tiers, setTiers] = useState([]);
  const [tierId, setTierId] = useState(initialData?.tier ?? '');
  const [abilitiesCollapsible, setAbilitiesCollapsible] = useState(initialData?.abilities_collapsible ?? true);
  const [abilitiesCollapsedByDefault, setAbilitiesCollapsedByDefault] = useState(initialData?.abilities_collapsed_by_default ?? false);
  const [abilitiesSoloList, setAbilitiesSoloList] = useState(initialData?.abilities_solo_list ?? false);
  const [showDescription, setShowDescription] = useState(initialData?.show_description ?? true);
  const [colorStyle, setColorStyle] = useState(initialData?.color_style || 'default');
  const normalizeToPresetHex = (h) => {
    const hex = String(h).trim().startsWith('#') ? String(h).trim() : `#${String(h).trim()}`;
    const found = GRADIENT_PRESET_COLORS.find(p => p.hex.toLowerCase() === hex.toLowerCase());
    return found ? found.hex : DEFAULT_GRADIENT_HEX;
  };
  const [gradientColors, setGradientColors] = useState(
    Array.isArray(initialData?.gradient_colors) && initialData.gradient_colors.length > 0
      ? initialData.gradient_colors.map(normalizeToPresetHex)
      : [DEFAULT_GRADIENT_HEX]
  );
  const [tierSearch, setTierSearch] = useState('');
  const [saving, setSaving] = useState(false);

  const sortedTiers = useMemo(() => {
    const list = [...(tiers || [])].sort((a, b) => (a.nome || '').localeCompare(b.nome || ''));
    const q = (tierSearch || '').trim().toLowerCase();
    if (!q) return list;
    return list.filter(t => (t.nome || '').toLowerCase().includes(q));
  }, [tiers, tierSearch]);

  useEffect(() => {
    getWikiTierList()
      .then(data => setTiers(data || []))
      .catch(err => console.error('Errore caricamento tier:', err));
  }, []);

  // Carica dati widget quando si modifica per id (es. da "Widget Tier in questa pagina")
  useEffect(() => {
    if (initialData?.id && !initialData?.tier) {
      getWikiTierWidget(initialData.id)
        .then(w => {
          setTierId(w.tier);
          setAbilitiesCollapsible(w.abilities_collapsible ?? true);
          setAbilitiesCollapsedByDefault(w.abilities_collapsed_by_default ?? false);
          setAbilitiesSoloList(w.abilities_solo_list ?? false);
          setShowDescription(w.show_description ?? true);
          setColorStyle(w.color_style || 'default');
          if (Array.isArray(w.gradient_colors) && w.gradient_colors.length > 0) {
            setGradientColors(w.gradient_colors.map(normalizeToPresetHex));
          } else {
            setGradientColors([DEFAULT_GRADIENT_HEX]);
          }
        })
        .catch(err => console.error('Errore caricamento widget tier:', err));
    }
  }, [initialData?.id]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!tierId) {
      alert('Seleziona un Tier');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        tier: Number(tierId),
        abilities_collapsible: abilitiesCollapsible,
        abilities_collapsed_by_default: abilitiesCollapsedByDefault,
        abilities_solo_list: abilitiesSoloList,
        show_description: showDescription,
        color_style: colorStyle || 'default',
        gradient_colors: gradientColors.filter(c => c && String(c).trim()),
      };
      await onSave(payload, initialData?.id);
      onClose();
    } catch (err) {
      console.error('Errore salvataggio widget tier:', err);
      alert(err?.message || 'Errore durante il salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  const styleKeys = Object.keys(CHROMATIC_STYLES);

  return (
    <div className="fixed inset-0 bg-black/60 z-60 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-md">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-lg text-gray-800">
            {initialData?.id ? 'Modifica Widget Tier' : 'Nuovo Widget Tier'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-red-600 font-bold text-xl px-1">✕</button>
        </div>
        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Tier</label>
            <input
              type="text"
              placeholder="Cerca tier per nome..."
              value={tierSearch}
              onChange={e => setTierSearch(e.target.value)}
              className="w-full border border-gray-300 px-2 py-1.5 rounded text-sm mb-2 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
            />
            <select
              value={tierId}
              onChange={e => setTierId(e.target.value)}
              className="w-full border border-gray-300 p-2 rounded text-sm"
              required
            >
              <option value="">— Seleziona tier —</option>
              {sortedTiers.map(t => (
                <option key={t.id} value={t.id}>{t.nome}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Stile predefinito (se non usi gradiente)</label>
            <select
              value={colorStyle}
              onChange={e => setColorStyle(e.target.value)}
              className="w-full border border-gray-300 p-2 rounded text-sm"
            >
              {styleKeys.map(key => (
                <option key={key} value={key}>{CHROMATIC_STYLES[key].name}</option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Gradiente (uno o più colori)</label>
            <p className="text-[11px] text-gray-500 mb-2">Scegli uno o più colori tra i 10 predefiniti. Il widget userà un gradiente tra i colori selezionati.</p>
            <div className="space-y-2">
              {gradientColors.map((hex, i) => (
                <div key={i} className="flex items-center gap-2">
                  <div
                    className="h-9 w-10 rounded border border-gray-300 shrink-0"
                    style={{ background: hex.startsWith('#') ? hex : `#${hex}` }}
                    title={hex}
                  />
                  <select
                    value={hex.startsWith('#') ? hex : `#${hex}`}
                    onChange={e => {
                      const next = [...gradientColors];
                      next[i] = e.target.value;
                      setGradientColors(next);
                    }}
                    className="flex-1 border border-gray-300 px-2 py-1.5 rounded text-sm"
                  >
                    {GRADIENT_PRESET_COLORS.map(p => (
                      <option key={p.key} value={p.hex}>{p.name}</option>
                    ))}
                  </select>
                  <button
                    type="button"
                    onClick={() => setGradientColors(prev => prev.filter((_, j) => j !== i))}
                    disabled={gradientColors.length <= 1}
                    className="p-1.5 text-red-600 hover:bg-red-50 rounded disabled:opacity-40 disabled:cursor-not-allowed"
                    title="Rimuovi colore"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              ))}
              <button
                type="button"
                onClick={() => setGradientColors(prev => [...prev, DEFAULT_GRADIENT_HEX])}
                className="flex items-center gap-1.5 text-sm text-indigo-600 hover:bg-indigo-50 px-2 py-1.5 rounded"
              >
                <Plus size={14} />
                Aggiungi colore
              </button>
            </div>
            {gradientColors.length > 0 && (
              <div
                className="mt-2 h-8 rounded border border-gray-200"
                style={{
                  background: gradientColors.length === 1
                    ? gradientColors[0]
                    : `linear-gradient(135deg, ${gradientColors.join(', ')})`,
                }}
              />
            )}
          </div>
          <div className="flex flex-col gap-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={showDescription}
                onChange={e => setShowDescription(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">Mostra descrizione tier</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={abilitiesSoloList}
                onChange={e => setAbilitiesSoloList(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">Abilità in sola lista</span>
            </label>
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={abilitiesCollapsible}
                onChange={e => setAbilitiesCollapsible(e.target.checked)}
                className="rounded"
              />
              <span className="text-sm font-medium text-gray-700">Abilità comprimibili</span>
            </label>
            {abilitiesCollapsible && (
              <label className="flex items-center gap-2 cursor-pointer pl-5">
                <input
                  type="checkbox"
                  checked={abilitiesCollapsedByDefault}
                  onChange={e => setAbilitiesCollapsedByDefault(e.target.checked)}
                  className="rounded"
                />
                <span className="text-sm text-gray-600">Comprimi di default</span>
              </label>
            )}
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <button type="button" onClick={onClose} className="px-3 py-2 text-sm text-gray-600 hover:bg-gray-200 rounded">
              Annulla
            </button>
            <button type="submit" disabled={saving} className="px-4 py-2 text-sm bg-indigo-600 text-white font-bold rounded hover:bg-indigo-700 disabled:opacity-50">
              {saving ? 'Salvataggio...' : (initialData?.id ? 'Salva modifiche' : 'Crea widget')}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
