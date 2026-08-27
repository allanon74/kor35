import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  cycleColumnSort,
  defaultVisibleColumnKeys,
  hasActiveColumnFilters,
} from './staffTableModel';

function readPersisted(storageKey) {
  if (!storageKey) {
    return {
      searchTerm: '',
      activeFilters: {},
      sorts: [],
      hiddenColumnKeys: [],
      columnFilters: {},
      showColumnFilters: false,
    };
  }
  try {
    const raw = localStorage.getItem(storageKey);
    if (!raw) {
      return {
        searchTerm: '',
        activeFilters: {},
        sorts: [],
        hiddenColumnKeys: [],
        columnFilters: {},
        showColumnFilters: false,
      };
    }
    const parsed = JSON.parse(raw);
    return {
      searchTerm: typeof parsed?.searchTerm === 'string' ? parsed.searchTerm : '',
      activeFilters:
        parsed?.activeFilters && typeof parsed.activeFilters === 'object' ? parsed.activeFilters : {},
      sorts: Array.isArray(parsed?.sorts)
        ? parsed.sorts.filter((s) => s && s.key && (s.dir === 'asc' || s.dir === 'desc'))
        : [],
      hiddenColumnKeys: Array.isArray(parsed?.hiddenColumnKeys)
        ? parsed.hiddenColumnKeys.filter((k) => typeof k === 'string')
        : [],
      columnFilters:
        parsed?.columnFilters && typeof parsed.columnFilters === 'object' ? parsed.columnFilters : {},
      showColumnFilters: Boolean(parsed?.showColumnFilters),
    };
  } catch {
    return {
      searchTerm: '',
      activeFilters: {},
      sorts: [],
      hiddenColumnKeys: [],
      columnFilters: {},
      showColumnFilters: false,
    };
  }
}

/**
 * Stato persistente per tabelle staff: search, chip-filtri, sort multiplo, colonne, filtri colonna.
 */
export function useStaffTableControls({ persistKey, columns = [] } = {}) {
  const normalizedKey = (persistKey || '').toString().trim().toLowerCase().replace(/\s+/g, '-');
  const storageKey = normalizedKey ? `staff_master_list_filters:${normalizedKey}` : null;
  const persisted = useMemo(() => readPersisted(storageKey), [storageKey]);

  const [searchTerm, setSearchTerm] = useState(persisted.searchTerm);
  const [activeFilters, setActiveFilters] = useState(persisted.activeFilters);
  const [sorts, setSorts] = useState(persisted.sorts);
  const [hiddenColumnKeys, setHiddenColumnKeys] = useState(persisted.hiddenColumnKeys);
  const [columnFilters, setColumnFilters] = useState(persisted.columnFilters);
  const [showColumnFilters, setShowColumnFilters] = useState(
    persisted.showColumnFilters || hasActiveColumnFilters(persisted.columnFilters),
  );

  useEffect(() => {
    if (!storageKey) return;
    try {
      localStorage.setItem(
        storageKey,
        JSON.stringify({
          searchTerm,
          activeFilters,
          sorts,
          hiddenColumnKeys,
          columnFilters,
          showColumnFilters,
        }),
      );
    } catch {
      // ignore localStorage quota/availability
    }
  }, [storageKey, searchTerm, activeFilters, sorts, hiddenColumnKeys, columnFilters, showColumnFilters]);

  const knownKeys = useMemo(
    () => new Set(defaultVisibleColumnKeys(columns)),
    [columns],
  );

  const sanitizedSorts = useMemo(
    () => sorts.filter((s) => knownKeys.has(s.key)),
    [sorts, knownKeys],
  );

  const sanitizedHiddenKeys = useMemo(
    () => hiddenColumnKeys.filter((k) => knownKeys.has(k)),
    [hiddenColumnKeys, knownKeys],
  );

  const sanitizedColumnFilters = useMemo(() => {
    const next = {};
    Object.entries(columnFilters || {}).forEach(([key, value]) => {
      if (knownKeys.has(key) && String(value || '').trim() !== '') {
        next[key] = value;
      }
    });
    return next;
  }, [columnFilters, knownKeys]);

  const cycleSort = useCallback((key) => {
    setSorts((prev) => cycleColumnSort(prev, key));
  }, []);

  const resetSorts = useCallback(() => setSorts([]), []);

  const toggleColumn = useCallback((key) => {
    setHiddenColumnKeys((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else {
        const visibleCount = [...knownKeys].filter((k) => !next.has(k)).length;
        if (visibleCount <= 1) return prev;
        next.add(key);
      }
      return [...next];
    });
  }, [knownKeys]);

  const resetColumns = useCallback(() => setHiddenColumnKeys([]), []);

  const setColumnFilter = useCallback((key, value) => {
    setColumnFilters((prev) => {
      const next = { ...prev, [key]: value };
      if (!String(value || '').trim()) delete next[key];
      return next;
    });
  }, []);

  const resetColumnFilters = useCallback(() => setColumnFilters({}), []);

  const toggleFilter = useCallback((key, val) => {
    setActiveFilters((prev) => {
      const current = prev[key] || [];
      const updated = current.includes(val) ? current.filter((v) => v !== val) : [...current, val];
      return { ...prev, [key]: updated };
    });
  }, []);

  const resetChipFilters = useCallback(() => {
    setActiveFilters({});
    setSearchTerm('');
  }, []);

  const resetAll = useCallback(() => {
    setActiveFilters({});
    setSearchTerm('');
    setSorts([]);
    setColumnFilters({});
    setHiddenColumnKeys([]);
  }, []);

  return {
    searchTerm,
    setSearchTerm,
    activeFilters,
    toggleFilter,
    resetChipFilters,
    sorts: sanitizedSorts,
    cycleSort,
    resetSorts,
    hiddenColumnKeys: sanitizedHiddenKeys,
    toggleColumn,
    resetColumns,
    columnFilters: sanitizedColumnFilters,
    setColumnFilter,
    resetColumnFilters,
    showColumnFilters,
    setShowColumnFilters,
    resetAll,
  };
}
