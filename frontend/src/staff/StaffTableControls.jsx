import React, { useEffect, useRef, useState } from 'react';
import { Columns3, Filter, FilterX, RotateCcw } from 'lucide-react';
import { columnKey, hasActiveColumnFilters, isColumnHideable } from './staffTableModel';

export function StaffTableControls({
  sorts = [],
  onResetSorts,
  columns = [],
  hiddenColumnKeys = [],
  onToggleColumn,
  onResetColumns,
  showColumnFilters = false,
  onToggleColumnFilters,
  columnFilters = {},
  onResetColumnFilters,
  compact = false,
}) {
  const [openCols, setOpenCols] = useState(false);
  const colRef = useRef(null);

  useEffect(() => {
    if (!openCols) return undefined;
    const onDoc = (e) => {
      if (colRef.current && !colRef.current.contains(e.target)) setOpenCols(false);
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, [openCols]);

  const hiddenSet = new Set(hiddenColumnKeys);
  const filtersOn = hasActiveColumnFilters(columnFilters);
  const btn = compact
    ? 'inline-flex items-center gap-1 rounded border border-gray-700 bg-gray-900 px-2 py-1 text-[10px] font-bold uppercase tracking-wide text-gray-300 hover:border-gray-500 hover:text-white'
    : 'inline-flex items-center gap-1 rounded-lg border border-gray-700 bg-gray-900 px-2.5 py-1.5 text-[10px] font-bold uppercase tracking-wide text-gray-300 hover:border-gray-500 hover:text-white';

  return (
    <div className="flex flex-wrap items-center gap-2">
      {sorts.length > 0 && onResetSorts && (
        <button type="button" onClick={onResetSorts} className={btn} title="Rimuovi tutti gli ordinamenti">
          <RotateCcw size={12} /> Reset ordinamenti
          <span className="rounded bg-cyan-900/80 px-1 text-cyan-200">{sorts.length}</span>
        </button>
      )}
      {onToggleColumnFilters && (
        <button
          type="button"
          onClick={onToggleColumnFilters}
          className={`${btn} ${showColumnFilters || filtersOn ? 'border-cyan-600 text-cyan-200' : ''}`}
        >
          <Filter size={12} /> Filtri
        </button>
      )}
      {filtersOn && onResetColumnFilters && (
        <button type="button" onClick={onResetColumnFilters} className={btn}>
          <FilterX size={12} /> Reset filtri
        </button>
      )}
      <div className="relative" ref={colRef}>
        <button
          type="button"
          onClick={() => setOpenCols((v) => !v)}
          className={`${btn} ${hiddenColumnKeys.length ? 'border-amber-600 text-amber-200' : ''}`}
        >
          <Columns3 size={12} /> Colonne
        </button>
        {openCols && (
          <div className="absolute right-0 z-40 mt-1 w-56 rounded-lg border border-gray-600 bg-gray-900 p-2 shadow-xl">
            <p className="mb-2 px-1 text-[10px] font-bold uppercase tracking-wide text-gray-500">
              Colonne visibili
            </p>
            <ul className="max-h-64 space-y-1 overflow-y-auto">
              {columns.map((col, idx) => {
                const key = columnKey(col, idx);
                const hideable = isColumnHideable(col);
                const checked = !hiddenSet.has(key);
                return (
                  <li key={key}>
                    <label className={`flex items-center gap-2 rounded px-1 py-0.5 text-xs ${hideable ? 'text-gray-200 cursor-pointer hover:bg-gray-800' : 'text-gray-500'}`}>
                      <input
                        type="checkbox"
                        className="accent-cyan-500"
                        checked={checked}
                        disabled={!hideable}
                        onChange={() => hideable && onToggleColumn(key)}
                      />
                      {col.header}
                    </label>
                  </li>
                );
              })}
            </ul>
            {hiddenColumnKeys.length > 0 && onResetColumns && (
              <button
                type="button"
                onClick={() => {
                  onResetColumns();
                  setOpenCols(false);
                }}
                className="mt-2 w-full rounded bg-gray-800 px-2 py-1 text-[10px] font-bold uppercase text-gray-300 hover:bg-gray-700"
              >
                Ripristina default
              </button>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
