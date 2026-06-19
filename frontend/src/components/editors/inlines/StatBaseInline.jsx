import React, { useMemo, useState } from 'react';

const statMatchesFilter = (stat, query) => {
  const q = query.trim().toLowerCase();
  if (!q) return true;
  const haystack = [stat.nome, stat.parametro, stat.sigla]
    .filter(Boolean)
    .join(' ')
    .toLowerCase();
  return haystack.includes(q);
};

const parseNumeric = (value) => {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(value);
  return Number.isNaN(n) ? null : n;
};

const getDefaultValue = (stat) => parseNumeric(stat.valore_base_predefinito) ?? 0;

const valuesDiffer = (a, b) => {
  const na = parseNumeric(a);
  const nb = parseNumeric(b);
  if (na === null || nb === null) return String(a ?? '') !== String(b ?? '');
  return Math.abs(na - nb) > 1e-9;
};

const findExistingRecord = (items, statId) =>
  items.find((it) => (it.statistica?.id || it.statistica) === statId);

const isStatOverridden = (stat, items) => {
  const existingRecord = findExistingRecord(items, stat.id);
  if (!existingRecord) return false;
  const saved = parseNumeric(existingRecord.valore_base);
  if (saved === null) return false;
  return valuesDiffer(saved, getDefaultValue(stat));
};

const getDisplayValue = (stat, items) => {
  const existingRecord = findExistingRecord(items, stat.id);
  let displayValue = existingRecord?.valore_base;
  if (displayValue === null || displayValue === undefined || displayValue === '') {
    displayValue = stat.valore_base_predefinito;
  }
  return displayValue;
};

const sortByName = (a, b) => String(a.nome || '').localeCompare(String(b.nome || ''), 'it');

const StatBaseInline = ({ items, options, onChange }) => {
  const [filterText, setFilterText] = useState('');

  const { overridden, standard, overriddenTotal } = useMemo(() => {
    const filtered = options.filter((stat) => statMatchesFilter(stat, filterText));
    const custom = [];
    const rest = [];
    for (const stat of filtered) {
      if (isStatOverridden(stat, items)) custom.push(stat);
      else rest.push(stat);
    }
    custom.sort(sortByName);
    rest.sort(sortByName);
    const allCustom = options.filter((stat) => isStatOverridden(stat, items));
    return { overridden: custom, standard: rest, overriddenTotal: allCustom.length };
  }, [options, filterText, items]);

  const renderStatRow = (stat, isOverridden) => {
    const displayValue = getDisplayValue(stat, items);
    const defaultValue = getDefaultValue(stat);

    return (
      <div
        key={stat.id}
        className={`flex items-center gap-3 p-2 rounded transition-all border group ${
          isOverridden
            ? 'bg-amber-950/35 border-amber-600/50 hover:bg-amber-950/50 hover:border-amber-500/70 shadow-sm shadow-amber-950/20'
            : 'bg-gray-800/20 border-transparent hover:bg-gray-800/50 hover:border-gray-700/50'
        }`}
      >
        <div className="flex-1 min-w-0 flex flex-col gap-0.5">
          <div className="flex items-baseline gap-2 overflow-hidden">
            {isOverridden && (
              <span
                className="shrink-0 w-1.5 h-1.5 rounded-full bg-amber-400"
                title="Valore diverso dal default"
              />
            )}
            <span className={`text-[11px] font-bold truncate ${isOverridden ? 'text-amber-100' : 'text-gray-300'}`}>
              {stat.nome}
            </span>
            <span className={`text-[9px] font-mono shrink-0 ${isOverridden ? 'text-amber-600/80' : 'text-gray-600 group-hover:text-indigo-400'} transition-colors`}>
              ({stat.parametro})
            </span>
          </div>
          {isOverridden && (
            <span className="text-[9px] text-amber-700/90 pl-3.5">
              default: {defaultValue}
            </span>
          )}
        </div>

        <div className="w-20 shrink-0">
          <input
            type="number"
            step="any"
            className={`w-full bg-gray-950 p-1.5 rounded text-xs text-center outline-none font-bold ${
              isOverridden
                ? 'border border-amber-500/60 text-amber-300 focus:border-amber-400'
                : 'border border-gray-800 text-amber-500 focus:border-indigo-500'
            }`}
            value={displayValue ?? ''}
            onChange={(e) => {
              const newVal = e.target.value;
              const recordIndex = items.findIndex((it) => (it.statistica?.id || it.statistica) === stat.id);

              if (recordIndex !== -1) {
                onChange(recordIndex, 'valore_base', newVal);
              } else {
                onChange(-1, 'statistica', { statId: stat.id, value: newVal });
              }
            }}
          />
        </div>
      </div>
    );
  };

  const hasResults = overridden.length > 0 || standard.length > 0;

  return (
    <div className="bg-gray-900/50 p-4 rounded-lg border border-gray-700 w-full">
      <div className="mb-4 border-b border-gray-800 pb-2">
        <h3 className="text-sm font-bold uppercase tracking-widest text-indigo-400">Statistiche Base per l'abilità</h3>
        <p className="text-[9px] text-gray-500 italic uppercase font-medium">Parametri tecnici per la definizione dell'effetto</p>
      </div>

      <div className="mb-3 flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={filterText}
          onChange={(e) => setFilterText(e.target.value)}
          placeholder="Filtra per nome, parametro o sigla…"
          className="flex-1 min-w-[200px] bg-gray-950 p-2 rounded text-sm border border-gray-700 text-white placeholder:text-gray-600 focus:border-indigo-500 outline-none"
        />
        {filterText.trim() && (
          <button
            type="button"
            onClick={() => setFilterText('')}
            className="text-xs text-gray-500 hover:text-gray-300 px-2 py-1 rounded border border-gray-700 hover:border-gray-600 transition-colors"
          >
            Cancella
          </button>
        )}
        <span className="text-[10px] text-gray-500 tabular-nums">
          {overridden.length + standard.length} / {options.length}
        </span>
        {overriddenTotal > 0 && (
          <span className="text-[10px] font-bold text-amber-500/90 tabular-nums">
            {overriddenTotal} personalizzat{overriddenTotal === 1 ? 'a' : 'e'}
          </span>
        )}
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-x-8 gap-y-2 max-h-[500px] overflow-y-auto pr-2 custom-scrollbar">
        {!hasResults ? (
          <p className="col-span-full text-sm text-gray-500 italic py-4 text-center">
            Nessuna statistica corrisponde al filtro.
          </p>
        ) : (
          <>
            {overridden.length > 0 && (
              <>
                <div className="col-span-full flex items-center gap-2 pt-1 pb-1 sticky top-0 bg-gray-900/95 z-[1] backdrop-blur-sm">
                  <span className="text-[10px] font-black uppercase tracking-wider text-amber-400">
                    Valori personalizzati
                  </span>
                  <span className="text-[9px] text-amber-700/80">({overridden.length})</span>
                  <div className="flex-1 h-px bg-amber-900/50" />
                </div>
                {overridden.map((stat) => renderStatRow(stat, true))}
              </>
            )}
            {standard.length > 0 && (
              <>
                {overridden.length > 0 && (
                  <div className="col-span-full flex items-center gap-2 pt-3 pb-1 sticky top-0 bg-gray-900/95 z-[1] backdrop-blur-sm">
                    <span className="text-[10px] font-black uppercase tracking-wider text-gray-500">
                      Default catalogo
                    </span>
                    <div className="flex-1 h-px bg-gray-800" />
                  </div>
                )}
                {standard.map((stat) => renderStatRow(stat, false))}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default StatBaseInline;
