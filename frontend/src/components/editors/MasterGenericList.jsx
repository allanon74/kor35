import React, { useState, useMemo, useCallback, useEffect, memo } from 'react';
import { useDebounce } from '../../hooks/useDebounce';
import { Search, Pencil, Trash2, Plus, FilterX, QrCode, Puzzle } from 'lucide-react';
import { applyColumnFilters, applyMultiSort, columnKey, hasActiveColumnFilters } from '../../staff/staffTableModel';
import { useStaffTableControls } from '../../staff/useStaffTableControls';
import { StaffTableControls } from '../../staff/StaffTableControls';
import StaffDataTable from '../../staff/StaffDataTable';
import SearchableSelect from './SearchableSelect';

/** Sopra questa soglia, senza `ui` esplicito, si usa un select invece delle chip. */
const DEFAULT_SELECT_THRESHOLD = 8;

const MasterGenericList = ({
  items = [],
  title,
  onAdd,
  onEdit,
  onDelete,
  onScanQr,
  onMinigioco,
  extraRowActions,
  onRowClick,
  addLabel = 'Nuovo',
  loading = false,
  /** Testo usato per la ricerca libera (default: nome/titolo/…). */
  getSearchText = null,
  /** Etichetta modale eliminazione (default: nome/titolo/…). */
  getItemLabel: getItemLabelProp = null,
  searchPlaceholder = 'Cerca per nome...',
  filterConfig = [],
  columns = [],
  sortLogic,
  emptyMessage = 'Seleziona dei filtri o cerca per visualizzare i dati.',
  /** Se true, ricerca e filtri non riducono `items` in locale: il parent deve ricaricare dal server (es. lista abilità paginata). */
  serverDrivenFiltering = false,
  /** Chiamato quando cambiano termine di ricerca (debounced) o filtri attivi. */
  onServerQueryChange = null,
  persistKey = null,
  /** false = altezza contenuta (liste annidate). Default true per i tool full-page. */
  fill = true,
  showSearch = true,
  toolbarExtra = null,
}) => {
  const normalizedKey = (persistKey || title || '').toString().trim().toLowerCase().replace(/\s+/g, '-');
  const {
    searchTerm,
    setSearchTerm,
    activeFilters,
    toggleFilter,
    setFilterValues,
    resetChipFilters,
    sorts,
    cycleSort,
    resetSorts,
    hiddenColumnKeys,
    toggleColumn,
    resetColumns,
    columnFilters,
    setColumnFilter,
    resetColumnFilters,
    showColumnFilters,
    setShowColumnFilters,
  } = useStaffTableControls({ persistKey: normalizedKey, columns });

  const resolveFilterUi = useCallback((conf) => {
    if (conf.ui === 'select' || conf.ui === 'chips' || conf.ui === 'icon') return conf.ui;
    if (conf.type === 'icon') return 'icon';
    const threshold = conf.selectThreshold ?? DEFAULT_SELECT_THRESHOLD;
    if ((conf.options?.length || 0) > threshold) return 'select';
    return 'chips';
  }, []);

  const [pendingDeleteItem, setPendingDeleteItem] = useState(null);
  const [isDeleting, setIsDeleting] = useState(false);

  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  useEffect(() => {
    if (!serverDrivenFiltering || !onServerQueryChange) return;
    onServerQueryChange({ search: debouncedSearchTerm, activeFilters });
  }, [serverDrivenFiltering, onServerQueryChange, debouncedSearchTerm, activeFilters]);

  const resetFilters = useCallback(() => {
    resetChipFilters();
    resetColumnFilters();
  }, [resetChipFilters, resetColumnFilters]);

  const resolveSearchText = useCallback((item) => {
    if (getSearchText) return String(getSearchText(item) || '');
    return item.nome || item.titolo || item.dichiarazione || item.label || '';
  }, [getSearchText]);

  const getItemLabel = useCallback((item) => {
    if (!item) return '';
    if (getItemLabelProp) return getItemLabelProp(item);
    return item.nome || item.titolo || item.dichiarazione || item.label || `ID ${item.id}`;
  }, [getItemLabelProp]);

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
    let filtered = items;

    if (!serverDrivenFiltering) {
      filtered = items.filter((item) => {
        const searchText = resolveSearchText(item).toLowerCase();
        const matchSearch = searchText.includes(debouncedSearchTerm.toLowerCase());
        if (debouncedSearchTerm && !matchSearch) return false;

        return Object.entries(activeFilters).every(([key, values]) => {
          if (!values?.length) return true;
          const conf = filterConfig.find((c) => c.key === key);
          if (conf?.match) return conf.match(item, values);
          const itemVal = item[key]?.id !== undefined ? item[key].id : item[key];
          return values.includes(itemVal);
        });
      });
    }

    filtered = applyColumnFilters(filtered, columnFilters, columns);

    if (sorts.length) {
      return applyMultiSort(filtered, sorts, columns);
    }
    return sortLogic ? [...filtered].sort(sortLogic) : filtered;
  }, [
    items,
    debouncedSearchTerm,
    activeFilters,
    sortLogic,
    filterConfig,
    serverDrivenFiltering,
    resolveSearchText,
    columnFilters,
    columns,
    sorts,
  ]);

  const ROW_BATCH = 40;
  const [visibleRowCount, setVisibleRowCount] = useState(ROW_BATCH);
  const filteredKey = useMemo(
    () => filteredItems.map((i) => i?.id).join(','),
    [filteredItems],
  );
  useEffect(() => {
    setVisibleRowCount(ROW_BATCH);
  }, [filteredKey]);
  const visibleItems = useMemo(
    () => filteredItems.slice(0, visibleRowCount),
    [filteredItems, visibleRowCount],
  );

  const hasActions = Boolean(onEdit || onDelete || onScanQr || onMinigioco || extraRowActions);
  const chipsActive = Object.values(activeFilters).some((a) => a?.length > 0);
  const columnFiltersActive = hasActiveColumnFilters(columnFilters);

  const renderActions = useCallback((item) => (
    <>
      {extraRowActions ? extraRowActions(item) : null}
      {onScanQr && (
        <button
          type="button"
          onClick={() => onScanQr(item.id)}
          className="p-2 bg-blue-600/20 text-blue-500 hover:bg-blue-600 hover:text-white rounded-lg transition-all"
          title="Associa QR"
        >
          <QrCode size={14} />
        </button>
      )}
      {onMinigioco && (
        <button
          type="button"
          onClick={() => onMinigioco(item)}
          disabled={!item.qrcode_id}
          className="p-2 bg-indigo-600/20 text-indigo-400 hover:bg-indigo-600 hover:text-white rounded-lg transition-all disabled:opacity-30 disabled:cursor-not-allowed"
          title={item.qrcode_id ? 'Configura minigioco QR' : 'Associa prima un QR'}
        >
          <Puzzle size={14} />
        </button>
      )}
      {onEdit && (
        <button
          type="button"
          onClick={() => onEdit(item)}
          className="p-2 bg-amber-600/20 text-amber-500 hover:bg-amber-600 hover:text-white rounded-lg transition-all"
          title="Modifica"
        >
          <Pencil size={14} />
        </button>
      )}
      {onDelete && (
        <button
          type="button"
          onClick={() => setPendingDeleteItem(item)}
          className="p-2 bg-red-600/20 text-red-500 hover:bg-red-600 hover:text-white rounded-lg transition-all"
          title="Elimina"
        >
          <Trash2 size={14} />
        </button>
      )}
    </>
  ), [extraRowActions, onScanQr, onMinigioco, onEdit, onDelete]);

  return (
    <div className={`flex flex-col space-y-4 ${fill ? 'h-full' : 'min-h-[360px] max-h-[75vh]'}`}>
      <div className="flex-none bg-gray-800 p-4 rounded-xl border border-gray-700 shadow-lg space-y-4">
        <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <h2 className="text-xl font-bold text-white uppercase tracking-tighter">{title}</h2>

          <div className="flex flex-wrap items-center gap-2 w-full md:w-auto justify-end">
            {toolbarExtra}
            {(chipsActive || columnFiltersActive) && (
              <button
                type="button"
                onClick={resetFilters}
                className="text-gray-500 hover:text-white flex items-center gap-1 text-[10px] uppercase font-bold transition-colors"
              >
                <FilterX size={14} /> Reset
              </button>
            )}
            <StaffTableControls
              sorts={sorts}
              onResetSorts={resetSorts}
              columns={columns}
              hiddenColumnKeys={hiddenColumnKeys}
              onToggleColumn={toggleColumn}
              onResetColumns={resetColumns}
              showColumnFilters={showColumnFilters}
              onToggleColumnFilters={() => setShowColumnFilters((v) => !v)}
              columnFilters={columnFilters}
              onResetColumnFilters={resetColumnFilters}
            />
            {onAdd && (
              <button
                type="button"
                onClick={onAdd}
                className="bg-cyan-600 hover:bg-cyan-500 px-4 py-2 rounded-lg font-black text-xs transition-all flex items-center gap-2 uppercase text-white shadow-lg active:scale-95 whitespace-nowrap"
              >
                <Plus size={16} /> {addLabel}
              </button>
            )}
          </div>
        </div>

        {sorts.length > 0 && (
          <p className="text-[10px] uppercase tracking-wide text-gray-500">
            Ordinamento:{' '}
            {sorts.map((spec, i) => {
              const col = columns.find((c, idx) => columnKey(c, idx) === spec.key);
              const label = col?.header || spec.key;
              return (
                <span key={spec.key} className="mr-2 text-cyan-300/90">
                  {i + 1}. {label} {spec.dir === 'desc' ? '↓' : '↑'}
                </span>
              );
            })}
          </p>
        )}

        {showSearch && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
            <input
              type="text"
              placeholder={searchPlaceholder}
              className="w-full bg-gray-950 border border-gray-700 rounded-lg pl-10 pr-4 py-2 text-sm focus:border-cyan-500 outline-none text-white transition-all placeholder:text-gray-700"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
            />
          </div>
        )}

        {filterConfig.length > 0 && (
          <div className="flex flex-wrap items-end gap-x-4 gap-y-2 pt-2 border-t border-gray-700/50">
            {filterConfig.map((conf) => {
              const ui = resolveFilterUi(conf);
              const activeVals = activeFilters[conf.key] || [];
              const selectValue = activeVals[0] ?? null;

              if (ui === 'select') {
                const selectOptions = conf.options.map((opt) => ({
                  id: opt.id,
                  nome: opt.label || opt.nome,
                }));
                return (
                  <div key={conf.key} className="flex flex-col gap-1 min-w-[160px] max-w-xs flex-1 sm:flex-none">
                    <span className="text-[10px] font-black text-gray-500 uppercase tracking-wide">
                      {conf.label}
                    </span>
                    <SearchableSelect
                      options={selectOptions}
                      value={selectValue}
                      onChange={(id) => setFilterValues(conf.key, id == null ? [] : [id])}
                      placeholder={conf.placeholder || `Tutti · ${conf.label}`}
                      labelKey="nome"
                      valueKey="id"
                    />
                  </div>
                );
              }

              return (
                <div key={conf.key} className="flex flex-col gap-1">
                  <span className="text-[10px] font-black text-gray-500 uppercase tracking-wide">
                    {conf.label}
                  </span>
                  <div className="flex flex-wrap gap-1.5">
                    {conf.options.map((opt) => {
                      const isActive = activeVals.includes(opt.id);
                      return (
                        <button
                          key={String(opt.id)}
                          type="button"
                          onClick={() => toggleFilter(conf.key, opt.id)}
                          title={opt.label || opt.nome}
                          className={`transition-all duration-200 ${
                            ui === 'icon' || conf.type === 'icon'
                              ? 'p-1 rounded-full border'
                              : 'px-2.5 py-1 rounded text-xs font-bold border'
                          } ${
                            isActive
                              ? 'bg-cyan-600 border-cyan-400 text-white shadow-lg'
                              : 'bg-gray-900 border-gray-700 text-gray-500 hover:border-gray-500'
                          }`}
                          style={
                            (ui === 'icon' || conf.type === 'icon') && isActive
                              ? { backgroundColor: opt.colore || opt.color }
                              : {}
                          }
                        >
                          {conf.renderOption
                            ? conf.renderOption(opt, isActive)
                            : opt.label || opt.nome}
                        </button>
                      );
                    })}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="flex-1 bg-gray-800 rounded-xl border border-gray-700 shadow-xl overflow-hidden flex flex-col min-h-0">
        <StaffDataTable
          columns={columns}
          items={visibleItems}
          hiddenColumnKeys={hiddenColumnKeys}
          sorts={sorts}
          onCycleSort={cycleSort}
          showColumnFilters={showColumnFilters}
          columnFilters={columnFilters}
          onColumnFilterChange={setColumnFilter}
          renderActions={hasActions ? renderActions : undefined}
          onRowClick={onRowClick}
          loading={loading}
        />

        {!loading && visibleRowCount < filteredItems.length && (
          <div className="p-3 border-t border-gray-700/50">
            <button
              type="button"
              onClick={() => setVisibleRowCount((n) => Math.min(n + ROW_BATCH, filteredItems.length))}
              className="w-full py-2.5 text-xs font-bold uppercase tracking-wide text-gray-400 bg-gray-900/60 hover:bg-gray-700 border border-dashed border-gray-600 rounded-lg"
            >
              Carica altri ({filteredItems.length - visibleRowCount} rimanenti)
            </button>
          </div>
        )}

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
                type="button"
                onClick={() => setPendingDeleteItem(null)}
                disabled={isDeleting}
                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-bold text-white disabled:opacity-60"
              >
                Annulla
              </button>
              <button
                type="button"
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
