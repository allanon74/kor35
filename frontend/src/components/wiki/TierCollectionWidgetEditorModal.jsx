import React, { useEffect, useMemo, useState } from 'react';
import { getWikiTierCollectionWidget, getWikiTierWidgetList, getWikiPunteggi } from '../../api';

function normalizeIds(v) {
  if (!Array.isArray(v)) return [];
  return v.map((x) => (typeof x === 'object' ? x?.id : x)).filter(Boolean).map(Number);
}

export default function TierCollectionWidgetEditorModal({ onClose, onSave, initialData = null }) {
  const [saving, setSaving] = useState(false);
  const [tierWidgets, setTierWidgets] = useState([]);
  const [caratteristiche, setCaratteristiche] = useState([]);
  const [title, setTitle] = useState(initialData?.title || '');
  const [sourceMode, setSourceMode] = useState(initialData?.source_mode || 'all');
  const [tierTypeFilter, setTierTypeFilter] = useState(initialData?.tier_type_filter || 'all');
  const [sortBy, setSortBy] = useState(initialData?.sort_by || 'tier_name');
  const [sortDir, setSortDir] = useState(initialData?.sort_dir || 'asc');
  const [showRuntimeFilters, setShowRuntimeFilters] = useState(initialData?.show_runtime_filters ?? true);
  const [showSearchControl, setShowSearchControl] = useState(initialData?.show_search_control ?? true);
  const [showTierTypeControl, setShowTierTypeControl] = useState(initialData?.show_tier_type_control ?? true);
  const [showCharacteristicsControl, setShowCharacteristicsControl] = useState(initialData?.show_characteristics_control ?? true);
  const [showSortControls, setShowSortControls] = useState(initialData?.show_sort_controls ?? true);
  const [badgeMode, setBadgeMode] = useState(initialData?.badge_mode || 'compact');
  const [caratteristicheFilterMode, setCaratteristicheFilterMode] = useState(initialData?.caratteristiche_filter_mode || 'any');
  const [selectedCaratteristicheIds, setSelectedCaratteristicheIds] = useState(normalizeIds(initialData?.caratteristiche));
  const [selectedWidgetIds, setSelectedWidgetIds] = useState(normalizeIds(initialData?.widgets));

  useEffect(() => {
    getWikiTierWidgetList()
      .then((data) => setTierWidgets(data || []))
      .catch((err) => console.error('Errore caricamento widget tier:', err));
    getWikiPunteggi('CA')
      .then((data) => setCaratteristiche(data || []))
      .catch((err) => console.error('Errore caricamento caratteristiche:', err));
  }, []);

  useEffect(() => {
    if (initialData?.id && !initialData?.widgets) {
      getWikiTierCollectionWidget(initialData.id)
        .then((w) => {
          setTitle(w.title || '');
          setSourceMode(w.source_mode || 'all');
          setTierTypeFilter(w.tier_type_filter || 'all');
          setSortBy(w.sort_by || 'tier_name');
          setSortDir(w.sort_dir || 'asc');
          setShowRuntimeFilters(w.show_runtime_filters ?? true);
          setShowSearchControl(w.show_search_control ?? true);
          setShowTierTypeControl(w.show_tier_type_control ?? true);
          setShowCharacteristicsControl(w.show_characteristics_control ?? true);
          setShowSortControls(w.show_sort_controls ?? true);
          setBadgeMode(w.badge_mode || 'compact');
          setCaratteristicheFilterMode(w.caratteristiche_filter_mode || 'any');
          setSelectedCaratteristicheIds(normalizeIds(w.caratteristiche));
          setSelectedWidgetIds(normalizeIds(w.widgets));
        })
        .catch((err) => console.error('Errore caricamento widget collezione tier:', err));
    }
  }, [initialData?.id]);

  const sortedTierWidgets = useMemo(() => {
    return [...tierWidgets].sort((a, b) => String(a?.tier_nome || '').localeCompare(String(b?.tier_nome || '')));
  }, [tierWidgets]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        title: title || '',
        source_mode: sourceMode,
        tier_type_filter: tierTypeFilter,
        sort_by: sortBy,
        sort_dir: sortDir,
        badge_mode: badgeMode,
        caratteristiche_filter_mode: caratteristicheFilterMode,
        show_runtime_filters: !!showRuntimeFilters,
        show_search_control: !!showSearchControl,
        show_tier_type_control: !!showTierTypeControl,
        show_characteristics_control: !!showCharacteristicsControl,
        show_sort_controls: !!showSortControls,
        caratteristiche_ids: selectedCaratteristicheIds,
        widget_ids: sourceMode === 'selected' ? selectedWidgetIds : [],
      };
      await onSave(payload, initialData?.id);
      onClose();
    } catch (err) {
      console.error('Errore salvataggio widget collezione tier:', err);
      alert(err?.message || 'Errore durante il salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/60 z-60 flex items-center justify-center p-4">
      <div className="bg-white rounded-lg shadow-xl w-full max-w-xl">
        <div className="p-4 border-b flex justify-between items-center">
          <h3 className="font-bold text-lg text-gray-800">
            {initialData?.id ? 'Modifica Collezione Tier' : 'Nuova Collezione Tier'}
          </h3>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-red-600 font-bold text-xl px-1">✕</button>
        </div>

        <form onSubmit={handleSubmit} className="p-4 space-y-4">
          <div>
            <label className="block text-xs font-bold text-gray-700 mb-1">Titolo (opzionale)</label>
            <input
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full border border-gray-300 px-2 py-1.5 rounded text-sm"
              placeholder="Es. Elenco Professioni"
            />
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Origine elementi</label>
              <select value={sourceMode} onChange={(e) => setSourceMode(e.target.value)} className="w-full border border-gray-300 p-2 rounded text-sm">
                <option value="all">Tutti i widget tier</option>
                <option value="selected">Solo widget selezionati</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Filtro tipo Tier</label>
              <select value={tierTypeFilter} onChange={(e) => setTierTypeFilter(e.target.value)} className="w-full border border-gray-300 p-2 rounded text-sm">
                <option value="all">Tutti</option>
                <option value="G0">Tabelle Generali</option>
                <option value="T1">Tier 1</option>
                <option value="T2">Tier 2</option>
                <option value="T3">Tier 3</option>
                <option value="T4">Tier 4</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Ordina per</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="w-full border border-gray-300 p-2 rounded text-sm">
                <option value="tier_name">Nome tier</option>
                <option value="widget_created">Creazione widget</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Direzione</label>
              <select value={sortDir} onChange={(e) => setSortDir(e.target.value)} className="w-full border border-gray-300 p-2 rounded text-sm">
                <option value="asc">Crescente</option>
                <option value="desc">Decrescente</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Badge caratteristiche</label>
              <select value={badgeMode} onChange={(e) => setBadgeMode(e.target.value)} className="w-full border border-gray-300 p-2 rounded text-sm">
                <option value="compact">Compatto (sigla)</option>
                <option value="extended">Esteso (nome)</option>
              </select>
            </div>
          </div>

          <label className="flex items-center gap-2 cursor-pointer">
            <input type="checkbox" checked={showRuntimeFilters} onChange={(e) => setShowRuntimeFilters(e.target.checked)} className="rounded" />
            <span className="text-sm font-medium text-gray-700">Mostra filtri e ordinamento nel widget</span>
          </label>

          {showRuntimeFilters && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 p-3 rounded border border-gray-200 bg-gray-50">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={showSearchControl} onChange={(e) => setShowSearchControl(e.target.checked)} className="rounded" />
                <span className="text-sm text-gray-700">Mostra ricerca testuale</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={showTierTypeControl} onChange={(e) => setShowTierTypeControl(e.target.checked)} className="rounded" />
                <span className="text-sm text-gray-700">Mostra filtro tipo Tier</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={showCharacteristicsControl} onChange={(e) => setShowCharacteristicsControl(e.target.checked)} className="rounded" />
                <span className="text-sm text-gray-700">Mostra filtro caratteristiche</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={showSortControls} onChange={(e) => setShowSortControls(e.target.checked)} className="rounded" />
                <span className="text-sm text-gray-700">Mostra ordinamento</span>
              </label>
            </div>
          )}

          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Filtro caratteristiche (matching)</label>
              <select
                value={caratteristicheFilterMode}
                onChange={(e) => setCaratteristicheFilterMode(e.target.value)}
                className="w-full border border-gray-300 p-2 rounded text-sm"
              >
                <option value="any">Qualsiasi caratteristica selezionata</option>
                <option value="all">Tutte le caratteristiche selezionate</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Caratteristiche da includere</label>
              <select
                multiple
                value={selectedCaratteristicheIds.map(String)}
                onChange={(e) => setSelectedCaratteristicheIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
                className="w-full border border-gray-300 p-2 rounded text-sm h-28"
              >
                {caratteristiche
                  .slice()
                  .sort((a, b) => String(a?.nome || '').localeCompare(String(b?.nome || '')))
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nome}
                    </option>
                  ))}
              </select>
            </div>
          </div>

          {sourceMode === 'selected' && (
            <div>
              <label className="block text-xs font-bold text-gray-700 mb-1">Widget Tier inclusi</label>
              <select
                multiple
                value={selectedWidgetIds.map(String)}
                onChange={(e) => setSelectedWidgetIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))}
                className="w-full border border-gray-300 p-2 rounded text-sm h-48"
              >
                {sortedTierWidgets.map((w) => (
                  <option key={w.id} value={w.id}>
                    {w.tier_nome || `Widget #${w.id}`}
                  </option>
                ))}
              </select>
            </div>
          )}

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
