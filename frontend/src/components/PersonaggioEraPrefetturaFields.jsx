import React, { useMemo } from 'react';

export default function PersonaggioEraPrefetturaFields({
  ere = [],
  era = '',
  prefettura = '',
  prefetturaEsterna = false,
  canEditEra = true,
  showPrefetturaEsterna = true,
  onChange,
  selectClassName = 'mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2',
  labelClassName = 'text-xs text-gray-400 uppercase',
  eraReadonlyClassName = 'mt-1 w-full bg-gray-900 border border-gray-700 rounded p-2 text-sm text-gray-200',
}) {
  const hasMultipleEre = ere.length > 1;
  const selectedEra = useMemo(
    () => ere.find((item) => String(item.id) === String(era)),
    [ere, era]
  );
  const allPrefetture = useMemo(
    () => ere.flatMap((item) => (item.prefetture || []).map((p) => ({ ...p, era_ref: item }))),
    [ere]
  );
  const prefettureDisponibili = useMemo(() => {
    if (prefetturaEsterna) return allPrefetture;
    return selectedEra?.prefetture || [];
  }, [prefetturaEsterna, allPrefetture, selectedEra]);

  const disabled = !canEditEra;

  return (
    <>
      <div className="grid md:grid-cols-2 gap-3">
        <div>
          <label className={labelClassName}>Era</label>
          {hasMultipleEre ? (
            <select
              className={selectClassName}
              value={era || ''}
              onChange={(e) => onChange?.({ era: e.target.value || '', prefettura: '' })}
              disabled={disabled}
            >
              <option value="">Seleziona era</option>
              {ere.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.nome}
                </option>
              ))}
            </select>
          ) : (
            <div className={eraReadonlyClassName}>{ere[0]?.nome || 'Campagna base'}</div>
          )}
        </div>
        <div>
          <label className={labelClassName}>Prefettura</label>
          <select
            className={selectClassName}
            value={prefettura || ''}
            onChange={(e) => onChange?.({ prefettura: e.target.value || '' })}
            disabled={disabled}
          >
            <option value="">Seleziona prefettura</option>
            {prefettureDisponibili.map((p) => (
              <option key={p.id} value={p.id}>
                {p.regione_sigla ? `${p.regione_sigla} ${p.nome}` : p.nome}
              </option>
            ))}
          </select>
        </div>
      </div>
      {showPrefetturaEsterna ? (
        <label className="inline-flex items-center gap-2 text-sm text-gray-300">
          <input
            type="checkbox"
            checked={!!prefetturaEsterna}
            onChange={(e) => onChange?.({ prefettura_esterna: e.target.checked, prefettura: '' })}
            disabled={disabled}
          />
          Prefettura esterna
        </label>
      ) : null}
    </>
  );
}
