import React, { useState } from 'react';
import { ArrowDown, ArrowUp, ArrowUpDown, ChevronDown, ChevronRight } from 'lucide-react';
import {
  columnKey,
  columnMobileRole,
  isColumnFilterable,
  isColumnSortable,
} from './staffTableModel';

function SortGlyph({ spec, index, alwaysVisible = false }) {
  if (!spec) {
    return (
      <ArrowUpDown
        size={11}
        className={`text-gray-600 ${alwaysVisible ? 'opacity-70' : 'opacity-0 group-hover:opacity-100'}`}
      />
    );
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

function partitionMobileEntries(entries) {
  const badges = [];
  const subtitles = [];
  const meta = [];
  const details = [];
  let title = null;
  entries.forEach((entry) => {
    const role = columnMobileRole(entry.col, { titleAssigned: Boolean(title) });
    if (role === 'hidden') return;
    if (role === 'badge') {
      badges.push(entry);
      return;
    }
    if (role === 'subtitle') {
      subtitles.push(entry);
      return;
    }
    if (role === 'meta') {
      meta.push(entry);
      return;
    }
    if (role === 'title' && !title) {
      title = entry;
      return;
    }
    details.push(entry);
  });
  return { badges, title, subtitles, meta, details };
}

function mobileHeader(col) {
  return col.mobileHeader || col.header;
}

function renderCell(col, item) {
  return col.render ? col.render(item) : null;
}

function StaffMobileCards({
  entries,
  items,
  sorts,
  onCycleSort,
  showColumnFilters,
  columnFilters,
  onColumnFilterChange,
  renderActions,
  onRowClick,
  loading,
}) {
  const hasActions = typeof renderActions === 'function';
  const sortIndexByKey = new Map(sorts.map((s, i) => [s.key, i]));
  const { badges, title, subtitles, meta, details } = partitionMobileEntries(entries);
  const [sortOpen, setSortOpen] = useState(false);
  const canSort = typeof onCycleSort === 'function' && entries.some(({ col }) => isColumnSortable(col));
  const sortSummary = sorts
    .map((spec) => {
      const entry = entries.find((e) => e.key === spec.key);
      const label = entry ? mobileHeader(entry.col) : spec.key;
      return `${label} ${spec.dir === 'desc' ? '↓' : '↑'}`;
    })
    .join(', ');

  return (
    <div className="min-w-0" data-testid="staff-mobile-cards">
      {canSort && (
        <div className="sticky top-0 z-10 border-b border-gray-700 bg-gray-900">
          <button
            type="button"
            data-testid="staff-mobile-sort-toggle"
            aria-expanded={sortOpen}
            onClick={() => setSortOpen((open) => !open)}
            className={`flex w-full min-h-11 items-center gap-2 px-3 text-left text-xs font-bold ${
              sorts.length ? 'text-cyan-100' : 'text-gray-300'
            }`}
          >
            <span className="min-w-0 flex-1 truncate">
              Ordina{sortSummary ? ` · ${sortSummary}` : ''}
            </span>
            <ChevronDown size={16} className={`shrink-0 transition-transform ${sortOpen ? 'rotate-180' : ''}`} />
          </button>
          {sortOpen && (
            <div data-testid="staff-mobile-sort-chips" className="flex gap-1 overflow-x-auto px-2 pb-2">
              {entries.map(({ col, key }) => {
                const sortable = isColumnSortable(col);
                const specIdx = sortIndexByKey.get(key);
                const spec = specIdx == null ? null : sorts[specIdx];
                if (!sortable) return null;
                return (
                  <button
                    key={key}
                    type="button"
                    onClick={() => onCycleSort(key)}
                    className={`inline-flex shrink-0 items-center gap-1 rounded-full border px-3 py-2 min-h-11 text-[10px] font-bold uppercase tracking-wide ${
                      spec
                        ? 'border-cyan-500 bg-cyan-900/40 text-cyan-100'
                        : 'border-gray-700 bg-gray-950 text-gray-400'
                    }`}
                  >
                    {mobileHeader(col)}
                    <SortGlyph spec={spec} index={specIdx ?? 0} alwaysVisible />
                  </button>
                );
              })}
            </div>
          )}
        </div>
      )}

      {showColumnFilters && (
        <div className="grid grid-cols-2 gap-2 border-b border-gray-800 bg-gray-950 px-3 py-2">
          {entries.map(({ col, key }) => (
            isColumnFilterable(col) ? (
              <label key={`f-${key}`} className="flex min-w-0 flex-col gap-0.5">
                <span className="text-[9px] font-black uppercase tracking-wide text-gray-500">
                  {mobileHeader(col)}
                </span>
                <input
                  type="search"
                  value={columnFilters[key] || ''}
                  onChange={(e) => onColumnFilterChange?.(key, e.target.value)}
                  placeholder="Filtra…"
                  className="w-full min-h-11 rounded border border-gray-700 bg-gray-900 px-2 py-1.5 text-xs text-gray-200 placeholder:text-gray-600 focus:border-cyan-600 outline-none"
                />
              </label>
            ) : null
          ))}
        </div>
      )}

      <ul className="divide-y divide-gray-800">
        {!loading &&
          items.map((item) => {
            const clickable = typeof onRowClick === 'function';
            return (
              <li key={item.id ?? item.pk ?? item.sync_id} data-testid="staff-mobile-card">
                <div
                  onClick={clickable ? () => onRowClick(item) : undefined}
                  className={`px-3 py-2.5 text-white min-h-11 ${
                    clickable ? 'cursor-pointer active:bg-gray-700/40' : ''
                  }`}
                >
                  <div className="flex items-start gap-2">
                    {badges.length > 0 && (
                      <div className="flex shrink-0 flex-wrap items-center gap-1 pt-0.5">
                        {badges.map(({ col, key }) => (
                          <div key={key} className="flex items-center justify-center">
                            {renderCell(col, item)}
                          </div>
                        ))}
                      </div>
                    )}
                    <div className="min-w-0 flex-1">
                      {title ? (
                        <div className="break-words text-base font-bold leading-snug text-cyan-50 [overflow:visible] [&_.truncate]:whitespace-normal [&_.truncate]:overflow-visible [&_[class*='max-w-']]:max-w-none">
                          {renderCell(title.col, item)}
                        </div>
                      ) : null}
                      {subtitles.length > 0 && (
                        <p data-testid="staff-mobile-subtitle" className="mt-0.5 break-words text-xs leading-snug text-gray-400">
                          {subtitles.map((entry, index) => (
                            <span key={entry.key}>
                              {index > 0 ? <span className="text-gray-600"> · </span> : null}
                              <span className="[&>*]:inline">{renderCell(entry.col, item)}</span>
                            </span>
                          ))}
                        </p>
                      )}
                      {meta.length > 0 && (
                        <div data-testid="staff-mobile-meta" className="mt-1.5 flex flex-wrap gap-1.5">
                          {meta.map(({ col, key }) => (
                            <span
                              key={key}
                              className="inline-flex max-w-full items-baseline gap-1 rounded-md bg-gray-950/80 px-2 py-1 text-[11px] leading-snug text-gray-300"
                            >
                              <span className="shrink-0 text-[9px] font-black uppercase tracking-wide text-gray-500">
                                {mobileHeader(col)}
                              </span>
                              <span className="min-w-0 break-words [&>*]:inline">{renderCell(col, item)}</span>
                            </span>
                          ))}
                        </div>
                      )}
                      {details.map(({ col, key }) => (
                        <div key={key} data-testid="staff-mobile-detail" className="mt-1 min-w-0 text-xs leading-snug">
                          <span className="mr-1 text-[9px] font-black uppercase tracking-wide text-gray-500">
                            {mobileHeader(col)}
                          </span>
                          <span className="break-words text-gray-300 [&>*]:inline [overflow:visible] [&_.truncate]:whitespace-normal [&_.truncate]:overflow-visible [&_[class*='max-w-']]:max-w-none">
                            {renderCell(col, item)}
                          </span>
                        </div>
                      ))}
                    </div>
                    {clickable && !hasActions ? (
                      <ChevronRight size={18} className="mt-0.5 shrink-0 text-gray-500" aria-hidden />
                    ) : null}
                  </div>
                  {hasActions && (
                    <div
                      className="mt-2 flex flex-wrap justify-end gap-1.5 [&_button]:min-h-11 [&_button]:min-w-11"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {renderActions(item)}
                    </div>
                  )}
                </div>
              </li>
            );
          })}
      </ul>
    </div>
  );
}

/**
 * Tabella staff con intestazioni cliccabili (sort multiplo), filtri per colonna e CRUD in colonna Azioni.
 * Sotto `lg` usa card compatte (titolo, sottotitolo, chip). L'ordinamento è dietro il pulsante Ordina,
 * così l'elenco resta leggibile su telefono.
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
  mobileOnRowClick,
  loading = false,
  minWidth = 600,
}) {
  const entries = visibleColumnEntries(columns, hiddenColumnKeys);
  const sortIndexByKey = new Map(sorts.map((s, i) => [s.key, i]));
  const hasActions = typeof renderActions === 'function';
  const cardRowClick = mobileOnRowClick || onRowClick;

  return (
    <>
      <div className="lg:hidden min-w-0">
        <StaffMobileCards
          entries={entries}
          items={items}
          sorts={sorts}
          onCycleSort={onCycleSort}
          showColumnFilters={showColumnFilters}
          columnFilters={columnFilters}
          onColumnFilterChange={onColumnFilterChange}
          renderActions={renderActions}
          onRowClick={cardRowClick}
          loading={loading}
        />
      </div>

      <div className="hidden lg:block overflow-auto flex-1 min-h-0 min-w-0">
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
                <th className="px-4 py-3 text-right min-w-[10.5rem] bg-gray-900 sticky right-0 z-30 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.5)]">
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
                      <td
                        key={key}
                        className={`px-4 py-3 ${col.wrap ? 'whitespace-normal' : 'whitespace-nowrap'} ${align}`}
                      >
                        {col.render ? col.render(item) : null}
                      </td>
                    );
                  })}
                  {hasActions && (
                    <td className="px-4 py-3 text-right whitespace-nowrap sticky right-0 bg-gray-800 group-hover:bg-gray-700/30 transition-colors z-10 shadow-[-5px_0px_5px_-2px_rgba(0,0,0,0.3)]">
                      <div
                        className="flex justify-end items-center gap-1.5 opacity-100"
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
    </>
  );
}
