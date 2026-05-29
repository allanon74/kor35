import React from 'react';

const DEFAULTS = {
  pct_vendita_min: 20,
  pct_vendita_max: 80,
  pct_rivendita_min: 120,
  pct_rivendita_max: 200,
  cr_per_livello_oggetto: 200,
};

const NegozioConfigEconomiaEditor = ({ value, onChange }) => {
  const cfg = { ...DEFAULTS, ...(value && typeof value === 'object' ? value : {}) };

  const set = (key, v) => onChange({ ...cfg, [key]: Number(v) || 0 });

  return (
    <div className="space-y-2 text-sm border border-gray-700 rounded-lg p-3 bg-gray-900/40">
      <div className="text-xs font-semibold text-gray-400 uppercase">Economia usato</div>
      <div className="grid grid-cols-2 gap-2">
        <label className="text-xs text-gray-500">
          % acquisto PG (min)
          <input
            type="number"
            className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded p-1"
            value={cfg.pct_vendita_min}
            onChange={(e) => set('pct_vendita_min', e.target.value)}
          />
        </label>
        <label className="text-xs text-gray-500">
          % acquisto PG (max)
          <input
            type="number"
            className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded p-1"
            value={cfg.pct_vendita_max}
            onChange={(e) => set('pct_vendita_max', e.target.value)}
          />
        </label>
        <label className="text-xs text-gray-500">
          % rivendita (min)
          <input
            type="number"
            className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded p-1"
            value={cfg.pct_rivendita_min}
            onChange={(e) => set('pct_rivendita_min', e.target.value)}
          />
        </label>
        <label className="text-xs text-gray-500">
          % rivendita (max)
          <input
            type="number"
            className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded p-1"
            value={cfg.pct_rivendita_max}
            onChange={(e) => set('pct_rivendita_max', e.target.value)}
          />
        </label>
        <label className="text-xs text-gray-500 col-span-2">
          CR per livello oggetto (valore riferimento)
          <input
            type="number"
            className="w-full mt-0.5 bg-gray-900 border border-gray-600 rounded p-1"
            value={cfg.cr_per_livello_oggetto}
            onChange={(e) => set('cr_per_livello_oggetto', e.target.value)}
          />
        </label>
      </div>
    </div>
  );
};

export default NegozioConfigEconomiaEditor;
