import React from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown } from 'lucide-react';
import {
  columnKey,
  isColumnFilterable,
  isColumnSortable,
  visibleColumns,
} from './staffTableModel';

function SortGlyph({ spec, index }) {
  if (!spec) {
    return <ArrowUpDown size={11} className="text-gray-600 opacity-0 group-hover:opacity-100" />;
  }
  const Icon = spec.dir === 'desc' ? ArrowDown : ArrowUp;
  return (
    <span className="inline-flex items-center gap-0.5 text-cyan-300">
      <Icon size={12} />
      <span className="min-w-[0.75rem] text-[9px] font-black leading-none">{index + 1}</span>
    </span>
  );
}

function visibleColumnEntries(columns, hiddenColumnKeys) {
  const hidden = new Set(hiddenColumnKeys || []);
  return (columns || [])
    .map((col, idx) => ({ col, idx, key: columnKey(col, idx) }))
    .filter((entry) => !hidden.has(entry.key));
}

/**
 * Tabella staff con intestazioni cliccabili (sort multiplo), filtri per colonna e CRUD in colonna Azioni.
 */
export default function StaffDataTable({
  columns = [],
  items = [],
  hiddenColumnKeys = [],
  sorts = [],
  onCycleSort,
  showColumnFilters = false,
  columnFilters = {},
  onColumnFilterChange,
  renderActions,
  onRowClick,
  loading = false,
  minWidth = 600,
}) {
  const entries = visibleColumnEntries(columns, hiddenColumnKeys);
  const sortIndexByKey = new Map(sorts.map((s, i) => [s.key, i]));
  const hasActions = typeof renderActions === 'function';

  return (
    <div className="overflow-auto flex-1 min-h-0">
      <table className="w-full text-left border-collapse" style={{ minWidth }}>
        <thead className="sticky top-0 z-20">
          <tr className="bg-gray-900 text-gray-400 text-[10px] uppercase font-black tracking-widest border-b border-gray-700 shadow-md">
            {entries.map(({ col, key }) => {
              const sortable = isColumnSortable(col) && typeof onCycleSort === 'function';
              const specIdx = sortIndexByKey.get(key);
              const spec = specIdx == null ? null : sorts[specIdx];
              const align =
                col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : 'text-left';
              return (
                <th
                  key={key}
                  className={`px-2 py-2 whitespace-nowrap bg-gray-900 ${align}`}
                  style={{ width: col.width }}
                >
                  {sortable ? (
                    <button
                      type="button"
                      onClick={() => onCycleSort(key)}
                      className={`group inline-flex max-w-full items-center gap-1 ${align === 'text-right' ? 'ml-auto' : align === 'text-center' ? 'mx-auto' : ''} rounded px-1 py-0.5 hover:bg-gray-800 hover:text-white`}
                      title={
                        spec
                          ? spec.dir === 'asc'
                            ? 'Clicca per ordine decrescente'
                            : 'Clicca per togliere questo ordinamento'
                          : 'Clicca per ordinare (crescente)'
                      }
                    >
                      <span className="truncate">{col.header}</span>
                      <SortGlyph spec={spec} index={specIdx ?? 0} />
                    </button>
                  ) : (
                    <span>{col.header}</span>
                  )}
                </th>
              );
            })}
            {hasActions && (
              <th className="px-4 py-3 text-right w-24 bg-gray-900 sticky right-0 z-30 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.5)]">
                Azioni
              </th>
            )}
          </tr>
          {showColumnFilters && (
            <tr className="bg-gray-950 border-b border-gray-800">
              {entries.map(({ col, key }) => (
                <th key={`f-${key}`} className="px-2 py-1.5 font-normal">
                  {isColumnFilterable(col) ? (
                    <input
                      type="search"
                      value={columnFilters[key] || ''}
                      onChange={(e) => onColumnFilterChange?.(key, e.target.value)}
                      placeholder="Filtra…"
                      className="w-full min-w-[4rem] rounded border border-gray-700 bg-gray-900 px-2 py-1 text-[11px] font-normal normal-case tracking-normal text-gray-200 placeholder:text-gray-600 focus:border-cyan-600 outline-none"
                    />
                  ) : (
                    <span className="block h-7" />
                  )}
                </th>
              ))}
              {hasActions && <th className="sticky right-0 bg-gray-950" />}
            </tr>
          )}
        </thead>
        <tbody className="divide-y divide-gray-700/50 text-sm">
          {!loading &&
            items.map((item) => (
              <tr
                key={item.id ?? item.pk ?? item.sync_id}
                onClick={onRowClick ? () => onRowClick(item) : undefined}
                className={`hover:bg-gray-700/30 transition-colors border-b border-gray-800/50 text-white group ${
                  onRowClick ? 'cursor-pointer' : ''
                }`}
              >
                {entries.map(({ col, key }) => {
                  const align =
                    col.align === 'center' ? 'text-center' : col.align === 'right' ? 'text-right' : '';
                  return (
                    <td key={key} className={`px-4 py-3 whitespace-nowrap ${align}`}>
                      {col.render ? col.render(item) : null}
                    </td>
                  );
                })}
                {hasActions && (
                  <td className="px-4 py-3 text-right whitespace-nowrap sticky right-0 bg-gray-800 group-hover:bg-gray-700/30 transition-colors z-10 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.3)]">
                    <div
                      className="flex justify-end gap-1 opacity-100 md:opacity-60 md:group-hover:opacity-100 transition-opacity"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {renderActions(item)}
                    </div>
                  </td>
                )}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
