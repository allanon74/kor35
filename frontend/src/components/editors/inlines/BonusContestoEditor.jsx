import React from 'react';
import SearchableSelect from '../SearchableSelect';

const EMPTY_BONUS = {
  caratteristica: null,
  valore: 1,
  vale_tessiture: false,
  vale_infusioni: false,
  vale_cerimoniali: false,
  aure: [],
};

function toggleId(list, id) {
  const key = String(id);
  const current = (list || []).map((item) => String(item));
  if (current.includes(key)) return (list || []).filter((item) => String(item) !== key);
  return [...(list || []), id];
}

export function BonusContestoEditor({ rows = [], onChange, caratteristiche = [], aure = [] }) {
  const update = (index, patch) => {
    const next = rows.map((row, idx) => (idx === index ? { ...row, ...patch } : row));
    onChange(next);
  };

  return (
    <div className="bg-gray-900/40 p-4 rounded-xl border border-amber-800/40 space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xs font-black uppercase text-amber-300">Bonus caratteristica contestuale</h3>
          <p className="text-[11px] text-gray-400 mt-1 leading-snug">
            Vale solo per creazione e formule dell&apos;ambito scelto. Non aumenta punti vita, chakra o gli altri derivati.
            Nessuna aura selezionata = tutte le aure di quell&apos;ambito.
          </p>
        </div>
        <button
          type="button"
          className="min-h-11 shrink-0 bg-amber-700 hover:bg-amber-600 text-white text-xs font-bold px-3 py-2 rounded"
          onClick={() => onChange([...(rows || []), { ...EMPTY_BONUS }])}
        >
          + Aggiungi bonus
        </button>
      </div>
      {(rows || []).length === 0 && (
        <p className="text-xs text-gray-500">Nessun bonus contestuale.</p>
      )}
      {(rows || []).map((row, idx) => (
        <div key={idx} className="grid grid-cols-1 md:grid-cols-12 gap-3 bg-gray-950/70 p-3 rounded border border-gray-800">
          <div className="md:col-span-4">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Caratteristica</label>
            <SearchableSelect
              options={caratteristiche}
              value={row.caratteristica || ''}
              onChange={(value) => update(idx, { caratteristica: value })}
              placeholder="Caratteristica"
            />
          </div>
          <div className="md:col-span-2">
            <label className="text-[10px] text-gray-500 uppercase font-black block mb-1">Valore</label>
            <input
              type="number"
              min={1}
              className="w-full min-h-11 bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
              value={row.valore ?? 1}
              onChange={(e) => update(idx, { valore: Math.max(1, parseInt(e.target.value, 10) || 1) })}
            />
          </div>
          <div className="md:col-span-5 flex flex-wrap items-end gap-3">
            {[
              ['vale_tessiture', 'Tessiture'],
              ['vale_infusioni', 'Infusioni'],
              ['vale_cerimoniali', 'Cerimoniali'],
            ].map(([key, label]) => (
              <label key={key} className="min-h-11 flex items-center gap-2 text-xs font-bold cursor-pointer">
                <input
                  type="checkbox"
                  className="w-4 h-4 accent-amber-500"
                  checked={!!row[key]}
                  onChange={(e) => update(idx, { [key]: e.target.checked })}
                />
                {label}
              </label>
            ))}
          </div>
          <div className="md:col-span-1 flex items-end">
            <button
              type="button"
              className="min-h-11 w-full text-xs font-bold text-red-300 border border-red-900/60 rounded px-2"
              onClick={() => onChange(rows.filter((_, i) => i !== idx))}
            >
              Rimuovi
            </button>
          </div>
          <div className="md:col-span-12">
            <p className="text-[10px] text-gray-500 uppercase font-black mb-1">Aure (vuoto = tutte)</p>
            <div className="flex flex-wrap gap-2">
              {(aure || []).map((aura) => {
                const active = (row.aure || []).some((id) => String(id) === String(aura.id));
                return (
                  <button
                    key={aura.id}
                    type="button"
                    className={`min-h-11 px-3 py-2 rounded text-xs font-bold border ${active ? 'bg-amber-800/70 border-amber-400 text-amber-100' : 'bg-gray-900 border-gray-700 text-gray-300'}`}
                    onClick={() => update(idx, { aure: toggleId(row.aure, aura.id) })}
                  >
                    {aura.nome}
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

export function AbilitaConferiteEditor({ rows = [], onChange, abilitaOptions = [] }) {
  return (
    <div className="bg-gray-900/40 p-4 rounded-xl border border-sky-800/40 space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h3 className="text-xs font-black uppercase text-sky-300">Abilità conferite</h3>
          <p className="text-[11px] text-gray-400 mt-1 leading-snug">
            Attive solo mentre l&apos;oggetto è attivo. Non contano come possesso per acquisti e prerequisiti.
            Se l&apos;abilità assegna punteggi globali, quelli valgono finché l&apos;oggetto è attivo.
          </p>
        </div>
        <button
          type="button"
          className="min-h-11 shrink-0 bg-sky-700 hover:bg-sky-600 text-white text-xs font-bold px-3 py-2 rounded"
          onClick={() => onChange([...(rows || []), { abilita: null }])}
        >
          + Aggiungi abilità
        </button>
      </div>
      {(rows || []).length === 0 && (
        <p className="text-xs text-gray-500">Nessuna abilità conferita.</p>
      )}
      {(rows || []).map((row, idx) => (
        <div key={idx} className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
          <div className="sm:col-span-10">
            <SearchableSelect
              options={abilitaOptions}
              value={row.abilita || ''}
              onChange={(value) => {
                const next = rows.map((item, i) => (i === idx ? { ...item, abilita: value } : item));
                onChange(next);
              }}
              placeholder="Abilità"
            />
          </div>
          <button
            type="button"
            className="sm:col-span-2 min-h-11 text-xs font-bold text-red-300 border border-red-900/60 rounded px-2"
            onClick={() => onChange(rows.filter((_, i) => i !== idx))}
          >
            Rimuovi
          </button>
        </div>
      ))}
    </div>
  );
}
