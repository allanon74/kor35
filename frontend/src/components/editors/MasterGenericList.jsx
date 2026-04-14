import React, { useState, useMemo, useCallback, useEffect, memo } from 'react';
import { useDebounce } from '../../hooks/useDebounce';
import { Search, Pencil, Trash2, Plus, FilterX, QrCode } from 'lucide-react';

const MasterGenericList = ({ 
  items = [], 
  title, 
  onAdd, 
  onEdit, 
  onDelete, 
  onScanQr,
  addLabel = "Nuovo",
  loading = false,
  filterConfig = [], 
  columns = [],
  sortLogic,
  emptyMessage = "Seleziona dei filtri o cerca per visualizzare i dati.",
  /** Se true, ricerca e filtri non riducono `items` in locale: il parent deve ricaricare dal server (es. lista abilità paginata). */
  serverDrivenFiltering = false,
  /** Chiamato quando cambiano termine di ricerca (debounced) o filtri attivi. */
  onServerQueryChange = null,
  persistKey = null,
}) => {
  const normalizedKey = (persistKey || title || '').toString().trim().toLowerCase().replace(/\s+/g, '-');
  const storageKey = normalizedKey ? `staff_master_list_filters:${normalizedKey}` : null;
  const readPersisted = () => {
    if (!storageKey) return { searchTerm: '', activeFilters: {} };
    try {
      const raw = localStorage.getItem(storageKey);
      if (!raw) return { searchTerm: '', activeFilters: {} };
      const parsed = JSON.parse(raw);
      return {
        searchTerm: typeof parsed?.searchTerm === 'string' ? parsed.searchTerm : '',
        activeFilters: parsed?.activeFilters && typeof parsed.activeFilters === 'object' ? parsed.activeFilters : {},
      };
    } catch {
      return { searchTerm: '', activeFilters: {} };
    }
  };
  const persisted = readPersisted();
  const [searchTerm, setSearchTerm] = useState(persisted.searchTerm);
  const [activeFilters, setActiveFilters] = useState(persisted.activeFilters);
  const [pendingDeleteItem, setPendingDeleteItem] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);
  
  // Debounce del search term per migliorare le performance
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  useEffect(() => {
    if (!serverDrivenFiltering || !onServerQueryChange) return;
    onServerQueryChange({ search: debouncedSearchTerm, activeFilters });
  }, [serverDrivenFiltering, onServerQueryChange, debouncedSearchTerm, activeFilters]);

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(storageKey, JSON.stringify({ searchTerm, activeFilters }));
    } catch {
      // ignore localStorage quota/availability issues
    }
  }, [storageKey, searchTerm, activeFilters]);

  const toggleFilter = useCallback((key, val) => {
    setActiveFilters(prev => {
      const current = prev[key] || [];
      const updated = current.includes(val) ? current.filter(v => v !== val) : [...current, val];
      return { ...prev, [key]: updated };
    });
  }, []);

  const resetFilters = useCallback(() => {
    setActiveFilters({});
    setSearchTerm('');
  }, []);

  const getItemLabel = useCallback((item) => {
    if (!item) return '';
    return item.nome || item.titolo || item.dichiarazione || item.label || `ID ${item.id}`;
  }, []);

  const handleConfirmDelete = useCallback(async () => {
    if (!pendingDeleteItem || !onDelete) return;
    try {
      setIsDeleting(true);
      await onDelete(pendingDeleteItem.id);
      setPendingDeleteItem(null);
    } finally {
      setIsDeleting(false);
    }
  }, [pendingDeleteItem, onDelete]);

  const filteredItems = useMemo(() => {
    if (serverDrivenFiltering) {
      return sortLogic ? [...items].sort(sortLogic) : items;
    }

    const hasActiveFilters = Object.values(activeFilters).some(arr => arr.length > 0);
    // Rimossa la logica che nasconde i dati quando ci sono filtri configurati
    // I dati vengono sempre mostrati, i filtri sono opzionali

    let filtered = items.filter(item => {
      // Cerca in 'nome' o 'titolo' (per supportare sia oggetti che immagini)
      const searchText = (item.nome || item.titolo || "").toLowerCase();
      const matchSearch = searchText.includes(debouncedSearchTerm.toLowerCase());
      if (debouncedSearchTerm && !matchSearch) return false;
      
      return Object.entries(activeFilters).every(([key, values]) => {
        if (values.length === 0) return true;
        const conf = filterConfig.find(c => c.key === key);
        if (conf?.match) return conf.match(item, values);
        const itemVal = item[key]?.id !== undefined ? item[key].id : item[key];
        return values.includes(itemVal);
      });
    });

    return sortLogic ? [...filtered].sort(sortLogic) : filtered;
  }, [items, debouncedSearchTerm, activeFilters, sortLogic, filterConfig, serverDrivenFiltering]);

  return (
    // H-FULL e FLEX-COL sono cruciali per bloccare l'altezza e scrollare dentro
    <div className="flex flex-col h-full space-y-4">
      
      {/* HEADER FISSO */}
      <div className="flex-none bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <h2 className="text-xl font-bold text-white uppercase tracking-tighter">{title}</h2>
          
          <div className="flex items-center gap-3 w-full md:w-auto justify-end">
            {Object.values(activeFilters).some(a => a.length > 0) && (
                <button 
                  onClick={resetFilters} 
                  className="text-gray-500 hover:text-white flex items-center gap-1 text-[10px] uppercase font-bold transition-colors"
                >
                    <FilterX size={14} /> Reset
                </button>
            )}
            <button 
              onClick={onAdd} 
              className="bg-cyan-600 hover:bg-cyan-500 px-4 py-2 rounded-lg font-black text-xs transition-all flex items-center gap-2 uppercase text-white shadow-lg active:scale-95 whitespace-nowrap"
            >
              <Plus size={16} /> {addLabel}
            </button>
          </div>
        </div>

        <div className="relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
          <input 
            type="text" 
            placeholder="Cerca per nome..." 
            className="w-full bg-gray-950 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:border-cyan-500 outline-none text-white transition-all placeholder:text-gray-700"
            value={searchTerm} 
            onChange={e => setSearchTerm(e.target.value)}
          />
        </div>

        {filterConfig.length > 0 && (
          <div className="space-y-3 pt-2 border-t border-gray-700/50">
            {filterConfig.map(conf => (
              <div key={conf.key} className="flex flex-col md:flex-row items-start md:items-center gap-2">
                <span className="text-[10px] font-black text-gray-500 uppercase w-full md:w-auto min-w-[70px] mb-1 md:mb-0">
                  {conf.label}:
                </span>
                <div className="flex flex-wrap gap-2">
                    {conf.options.map(opt => {
                      const isActive = (activeFilters[conf.key] || []).includes(opt.id);
                      return (
                        <button 
                          key={opt.id}
                          onClick={() => toggleFilter(conf.key, opt.id)}
                          title={opt.label || opt.nome}
                          className={`transition-all duration-200 ${conf.type === 'icon' ? 'p-1 rounded-full border' : 'px-3 py-1 rounded text-xs font-bold border'} ${
                            isActive
                            ? 'bg-cyan-600 border-cyan-400 text-white shadow-lg scale-105' 
                            : 'bg-gray-900 border-gray-700 text-gray-500 hover:border-gray-500'
                          }`}
                          style={conf.type === 'icon' && isActive ? { backgroundColor: opt.colore || opt.color } : {}}
                        >
                          {conf.renderOption ? conf.renderOption(opt, isActive) : (opt.label || opt.nome)}
                        </button>
                      );
                    })}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* BODY SCROLLABILE - Questa è la parte magica per mobile */}
      <div className="flex-1 bg-gray-800 rounded-xl border border-gray-700 shadow-xl overflow-hidden flex flex-col min-h-0">
        <div className="overflow-auto flex-1"> {/* Overflow-auto qui gestisce X e Y */}
          <table className="w-full text-left border-collapse min-w-[600px]">
            <thead className="sticky top-0 z-20"> {/* Sticky Header */}
              <tr className="bg-gray-900 text-gray-400 text-[10px] uppercase font-black tracking-widest border-b border-gray-700 shadow-md">
                {columns.map((col, idx) => (
                  <th 
                    key={idx} 
                    className={`px-4 py-3 whitespace-nowrap bg-gray-900 ${col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : ''}`} 
                    style={{ width: col.width }}
                  >
                    {col.header}
                  </th>
                ))}
                <th className="px-4 py-3 text-right w-24 bg-gray-900 sticky right-0 z-30 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.5)]">Azioni</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-700/50 text-sm">
              {filteredItems.map(item => (
                <tr key={item.id} className="hover:bg-gray-700/30 transition-colors border-b border-gray-800/50 text-white group">
                  {columns.map((col, idx) => (
                    <td 
                      key={idx} 
                      className={`px-4 py-3 whitespace-nowrap ${col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : ''}`}
                    >
                      {col.render(item)}
                    </td>
                  ))}
                  <td className="px-4 py-3 text-right whitespace-nowrap sticky right-0 bg-gray-800 group-hover:bg-gray-700/30 transition-colors z-10 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.3)]">
                      <div className="flex justify-end gap-1 opacity-100 md:opacity-60 md:group-hover:opacity-100 transition-opacity">
                        {onScanQr && (
                          <button 
                            onClick={() => onScanQr(item.id)} 
                            className="p-2 bg-blue-600/20 text-blue-500 hover:bg-blue-600 hover:text-white rounded-lg transition-all"
                            title="Associa QR"
                          >
                            <QrCode size={14} />
                          </button>
                        )}
                        <button 
                          onClick={() => onEdit(item)} 
                          className="p-2 bg-amber-600/20 text-amber-500 hover:bg-amber-600 hover:text-white rounded-lg transition-all"
                        >
                          <Pencil size={14} />
                        </button>
                        <button 
                          onClick={() => setPendingDeleteItem(item)} 
                          className="p-2 bg-red-600/20 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all"
                        >
                          <Trash2 size={14} />
                        </button>
                      </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        
          {loading && (
              <div className="p-12 text-center text-cyan-500 animate-pulse font-black uppercase tracking-widest">
                  Caricamento dati in corso...
              </div>
          )}
          
          {!loading && filteredItems.length === 0 && (
              <div className="p-12 text-center space-y-3">
                  <div className="text-gray-700 flex justify-center"><FilterX size={48} /></div>
                  <p className="text-gray-500 italic text-sm max-w-xs mx-auto">
                      {emptyMessage}
                  </p>
              </div>
          )}
        </div>
      </div>

      {pendingDeleteItem && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="w-full max-w-md bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
            <div className="p-4 border-b border-gray-700">
              <h3 className="text-white font-bold text-lg">Conferma eliminazione</h3>
              <p className="text-sm text-gray-400 mt-1">
                Stai per eliminare: <span className="text-gray-200 font-semibold">{getItemLabel(pendingDeleteItem)}</span>
              </p>
            </div>
            <div className="p-4 flex justify-end gap-2">
              <button
                onClick={() => setPendingDeleteItem(null)}
                disabled={isDeleting}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-bold text-white disabled:opacity-60"
              >
                Annulla
              </button>
              <button
                onClick={handleConfirmDelete}
                disabled={isDeleting}
                className="px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-bold text-white disabled:opacity-60"
              >
                {isDeleting ? 'Eliminazione...' : 'Elimina'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(MasterGenericList);