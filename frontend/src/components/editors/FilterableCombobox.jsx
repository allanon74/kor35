import React, { useEffect, useId, useMemo, useRef, useState } from 'react';

/**
 * Combobox con filtro testuale e lista suggerimenti.
 * options: { value, label, searchText? }[]
 */
const FilterableCombobox = ({
  options = [],
  value,
  onChange,
  placeholder = 'Cerca…',
  className = '',
  disabled = false,
  allowCustom = false,
  normalizeCustom = (v) => v,
  emptyHint = 'Nessun risultato',
  maxItems = 40,
}) => {
  const listId = useId();
  const wrapRef = useRef(null);
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');

  const selected = useMemo(
    () => options.find((o) => String(o.value) === String(value ?? '')),
    [options, value],
  );

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return options.slice(0, maxItems);
    return options
      .filter((o) => {
        const hay = `${o.searchText ?? o.label ?? ''} ${o.value ?? ''}`.toLowerCase();
        return hay.includes(q);
      })
      .slice(0, maxItems);
  }, [options, query, maxItems]);

  useEffect(() => {
    const onDoc = (e) => {
      if (wrapRef.current && !wrapRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', onDoc);
    return () => document.removeEventListener('mousedown', onDoc);
  }, []);

  const commitCustom = () => {
    if (!allowCustom) return;
    const raw = query.trim();
    if (!raw) return;
    onChange(normalizeCustom(raw));
    setQuery('');
    setOpen(false);
  };

  const handleBlur = () => {
    window.setTimeout(() => {
      if (allowCustom && query.trim()) {
        commitCustom();
      } else {
        setOpen(false);
        setQuery('');
      }
    }, 150);
  };

  const displayValue = open ? query : (selected?.label ?? (allowCustom && value ? String(value) : ''));

  return (
    <div ref={wrapRef} className={`relative min-w-[120px] flex-1 ${className}`}>
      <input
        type="text"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        disabled={disabled}
        autoComplete="off"
        placeholder={placeholder}
        className="w-full bg-gray-800 border border-gray-600 rounded px-1.5 py-0.5 text-xs"
        value={displayValue}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
        }}
        onFocus={() => {
          setQuery(selected?.label ?? (value ? String(value) : ''));
          setOpen(true);
        }}
        onBlur={handleBlur}
        onKeyDown={(e) => {
          if (e.key === 'Enter') {
            e.preventDefault();
            if (filtered.length === 1) {
              onChange(filtered[0].value);
              setQuery('');
              setOpen(false);
            } else if (allowCustom && query.trim()) {
              commitCustom();
            }
          } else if (e.key === 'Escape') {
            setOpen(false);
            setQuery('');
          }
        }}
      />
      {open && !disabled && (
        <ul
          id={listId}
          role="listbox"
          className="absolute z-50 left-0 right-0 mt-0.5 max-h-44 overflow-y-auto bg-gray-900 border border-gray-600 rounded shadow-lg text-xs"
        >
          {filtered.length === 0 ? (
            <li className="px-2 py-1.5 text-gray-500 italic">
              {emptyHint}
              {allowCustom && query.trim() ? ' — Invio per usare il testo' : ''}
            </li>
          ) : (
            filtered.map((o) => (
              <li key={String(o.value)}>
                <button
                  type="button"
                  role="option"
                  aria-selected={String(o.value) === String(value ?? '')}
                  className={`w-full text-left px-2 py-1.5 hover:bg-indigo-900/60 truncate ${
                    String(o.value) === String(value ?? '') ? 'bg-indigo-950/80 text-indigo-200' : 'text-gray-200'
                  }`}
                  onMouseDown={(e) => e.preventDefault()}
                  onClick={() => {
                    onChange(o.value);
                    setQuery('');
                    setOpen(false);
                  }}
                >
                  {o.label}
                </button>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  );
};

export default FilterableCombobox;
