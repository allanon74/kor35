import React from 'react';

/**
 * Campi condivisi: frazione trasferimento + fattore valore deposito.
 */
export default function EconomiaDepositoParamsFields({
  frazione,
  setFrazione,
  fattore,
  setFattore,
  compact = false,
}) {
  const labelCls = compact ? 'block text-xs text-gray-500 mb-1' : 'block text-sm text-gray-400 mb-1';
  const hintCls = compact ? 'text-[11px] text-gray-500 mt-1' : 'text-xs text-gray-500 mt-1';
  const inputCls = compact
    ? 'w-full bg-gray-800 border border-gray-700 rounded px-3 py-1.5 text-sm'
    : 'w-full bg-gray-800 border border-gray-700 rounded px-3 py-2';

  const esempioPrezzo = (() => {
    const f = Number(fattore) || 0.9;
    if (f <= 0) return '—';
    return (100 / f).toFixed(2);
  })();

  return (
    <div className={compact ? 'grid gap-3 sm:grid-cols-2' : 'grid gap-4'}>
      <div>
        <label className={labelCls}>
          Frazione stipendio trasferibile (deposito → corrente)
        </label>
        <input
          type="number"
          step="0.01"
          min="0"
          className={inputCls}
          value={frazione}
          onChange={(e) => setFrazione(e.target.value)}
        />
        <p className={hintCls}>
          {compact
            ? 'Tetto = frazione × stipendio evento (es. 1.50 = fino al 150%).'
            : 'Tetto = frazione × stipendio evento (es. 1.50 = fino a 150% dello stipendio).'}
        </p>
      </div>
      <div>
        <label className={labelCls}>Fattore valore deposito (0.01–1.00)</label>
        <input
          type="number"
          step="0.01"
          min="0.01"
          max="1"
          className={inputCls}
          value={fattore}
          onChange={(e) => setFattore(e.target.value)}
        />
        <p className={hintCls}>
          {compact
            ? `Bene da 100 CR in corrente costa ${esempioPrezzo} CR dal deposito.`
            : `Bene da 100 CR sul corrente costa ${esempioPrezzo} CR dal deposito (prezzo / fattore).`}
        </p>
      </div>
    </div>
  );
}
