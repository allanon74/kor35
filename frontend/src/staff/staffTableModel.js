/**
 * Modello tabelle dashboard staff: ordinamento multiplo, filtri colonna, visibilità.
 * L'ordine degli sort è l'ordine di attivazione (click). Ciclo: asc → desc → togli.
 */
import React from 'react';

export function slugifyColumnHeader(header, idx) {
  const base = String(header || '')
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '');
  return base || `col-${idx}`;
}

export function columnKey(col, idx = 0) {
  if (!col) return `col-${idx}`;
  return col.key || col.sortKey || slugifyColumnHeader(col.header, idx);
}

export function extractRenderableText(node) {
  if (node == null || node === false || node === true) return '';
  if (typeof node === 'string' || typeof node === 'number') return String(node);
  if (typeof node === 'bigint') return String(node);
  if (Array.isArray(node)) {
    return node.map(extractRenderableText).filter(Boolean).join(' ');
  }
  if (React.isValidElement(node)) {
    const { children, title, alt } = node.props || {};
    const fromChildren = extractRenderableText(children);
    if (fromChildren) return fromChildren;
    if (title) return String(title);
    if (alt) return String(alt);
    return '';
  }
  if (typeof node === 'object') {
    if (node.nome) return String(node.nome);
    if (node.label) return String(node.label);
    if (node.id != null) return String(node.id);
  }
  return '';
}

function unwrapField(value) {
  if (value == null) return '';
  if (typeof value === 'object') {
    if (value.nome) return value.nome;
    if (value.label) return value.label;
    if (value.id != null) return value.id;
  }
  return value;
}

export function getColumnSortValue(col, item) {
  if (!col || !item) return '';
  if (typeof col.getSortValue === 'function') {
    return col.getSortValue(item);
  }
  const key = col.sortKey || col.key;
  if (key && Object.prototype.hasOwnProperty.call(item, key)) {
    return unwrapField(item[key]);
  }
  if (typeof col.render === 'function') {
    try {
      return extractRenderableText(col.render(item));
    } catch {
      return '';
    }
  }
  return '';
}

export function getColumnFilterValue(col, item) {
  if (!col || !item) return '';
  if (typeof col.getFilterValue === 'function') {
    return col.getFilterValue(item);
  }
  return getColumnSortValue(col, item);
}

function parseComparableNumber(value) {
  if (typeof value === 'number' && Number.isFinite(value)) return value;
  if (typeof value === 'boolean') return value ? 1 : 0;
  if (value instanceof Date) {
    const t = value.getTime();
    return Number.isNaN(t) ? null : t;
  }
  const raw = String(value ?? '').trim();
  if (!raw) return null;
  const iso = Date.parse(raw);
  if (!Number.isNaN(iso) && /^\d{4}-\d{2}-\d{2}/.test(raw)) return iso;
  const normalized = raw.replace(/\s/g, '').replace(',', '.');
  if (!/^-?\d+(\.\d+)?$/.test(normalized)) return null;
  const n = Number(normalized);
  return Number.isFinite(n) ? n : null;
}

export function compareSortValues(a, b) {
  const aEmpty = a == null || a === '';
  const bEmpty = b == null || b === '';
  if (aEmpty && bEmpty) return 0;
  if (aEmpty) return 1;
  if (bEmpty) return -1;

  const na = parseComparableNumber(a);
  const nb = parseComparableNumber(b);
  if (na != null && nb != null && na !== nb) return na - nb;

  return String(a).localeCompare(String(b), 'it', { numeric: true, sensitivity: 'base' });
}

/**
 * Ciclo click intestazione: 1° asc, 2° desc, 3° rimuove.
 * I nuovi sort si accodano (ordine di applicazione = ordine dei click).
 */
export function cycleColumnSort(sorts, key) {
  const list = Array.isArray(sorts) ? sorts : [];
  const idx = list.findIndex((s) => s.key === key);
  if (idx === -1) {
    return [...list, { key, dir: 'asc' }];
  }
  if (list[idx].dir === 'asc') {
    return list.map((s, i) => (i === idx ? { ...s, dir: 'desc' } : s));
  }
  return list.filter((_, i) => i !== idx);
}

export function applyMultiSort(items, sorts, columns) {
  if (!Array.isArray(items) || items.length < 2) return items || [];
  if (!sorts?.length) return items;
  const colByKey = new Map((columns || []).map((col, idx) => [columnKey(col, idx), col]));
  const copy = [...items];
  copy.sort((a, b) => {
    for (const spec of sorts) {
      const col = colByKey.get(spec.key);
      const av = getColumnSortValue(col, a);
      const bv = getColumnSortValue(col, b);
      const cmp = compareSortValues(av, bv);
      if (cmp !== 0) return spec.dir === 'desc' ? -cmp : cmp;
    }
    return 0;
  });
  return copy;
}

export function applyColumnFilters(items, columnFilters, columns) {
  if (!items?.length) return items || [];
  const entries = Object.entries(columnFilters || {}).filter(([, v]) => String(v || '').trim() !== '');
  if (!entries.length) return items;
  const colByKey = new Map((columns || []).map((col, idx) => [columnKey(col, idx), col]));
  return items.filter((item) =>
    entries.every(([key, raw]) => {
      const needle = String(raw).trim().toLowerCase();
      if (!needle) return true;
      const col = colByKey.get(key);
      const hay = String(getColumnFilterValue(col, item) ?? '').toLowerCase();
      return hay.includes(needle);
    }),
  );
}

export function isColumnSortable(col) {
  return col?.sortable !== false;
}

export function isColumnFilterable(col) {
  return col?.filterable !== false;
}

export function isColumnHideable(col) {
  return col?.hideable !== false;
}

export function defaultVisibleColumnKeys(columns) {
  return (columns || []).map((col, idx) => columnKey(col, idx));
}

export function visibleColumns(columns, hiddenKeys) {
  const hidden = new Set(hiddenKeys || []);
  return (columns || []).filter((col, idx) => !hidden.has(columnKey(col, idx)));
}

export function hasActiveColumnFilters(columnFilters) {
  return Object.values(columnFilters || {}).some((v) => String(v || '').trim() !== '');
}
