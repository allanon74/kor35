import React from 'react';
import { Plus, Trash2 } from 'lucide-react';

/**
 * Costi risorsa all'attivazione (PV, PA, CHA, pool, …).
 * options: lista Statistica da getStatisticheList (preferire is_risorsa_pool).
 */
const ActivationCostInline = ({ items = [], options = [], onChange, onAdd, onRemove }) => {
  const poolOptions = (options || []).filter((s) => s.is_risorsa_pool);
  const selectOptions = poolOptions.length ? poolOptions : (options || []);

  const getStatId = (row) => row.statistica?.id || row.statistica;

  return (
    <div className="bg-gray-900/50 p-4 rounded-lg border border-amber-500/20 w-full">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2 border-b border-gray-800 pb-2">
        <div>
          <h3 className="text-sm font-bold uppercase tracking-widest text-amber-400">Costi attivazione risorsa</h3>
          <p className="text-[9px] text-gray-500 italic uppercase font-medium">
            Consumati all&apos;uso (oggetto: oltre alla carica; tessitura: all&apos;attivazione runtime)
          </p>
        </div>
        <button
          type="button"
          onClick={onAdd}
          className="flex items-center gap-1 px-2 py-1 rounded bg-amber-900/40 hover:bg-amber-800/50 text-[10px] font-bold uppercase text-amber-200"
        >
          <Plus size={12} /> Aggiungi costo
        </button>
      </div>

      {(items || []).length === 0 && (
        <p className="text-xs text-gray-500 italic">Nessun costo aggiuntivo configurato.</p>
      )}

      <div className="space-y-2">
        {(items || []).map((row, idx) => {
          const statId = getStatId(row);
          const usedElsewhere = new Set(
            (items || [])
              .map((r, i) => (i === idx ? null : getStatId(r)))
              .filter(Boolean)
              .map(String)
          );
          return (
            <div
              key={`cost-${idx}-${statId || 'new'}`}
              className="flex flex-wrap items-center gap-2 bg-gray-800/30 p-2 rounded border border-gray-700/50"
            >
              <select
                className="flex-1 min-w-[180px] bg-gray-950 p-2 rounded text-xs border border-gray-700 text-white"
                value={statId || ''}
                onChange={(e) => onChange(idx, 'statistica', e.target.value ? parseInt(e.target.value, 10) : null)}
              >
                <option value="">— Statistica —</option>
                {selectOptions.map((s) => (
                  <option key={s.id} value={s.id} disabled={usedElsewhere.has(String(s.id))}>
                    {s.nome} ({s.sigla}){s.is_risorsa_pool ? '' : ' · legacy'}
                  </option>
                ))}
              </select>
              <input
                type="number"
                min="1"
                className="w-20 bg-gray-950 p-2 rounded text-xs text-center border border-gray-700 text-amber-400 font-bold"
                value={row.costo ?? 1}
                onChange={(e) => onChange(idx, 'costo', parseInt(e.target.value || '1', 10) || 1)}
              />
              <button
                type="button"
                onClick={() => onRemove(idx)}
                className="p-2 text-red-400 hover:text-red-300"
                title="Rimuovi"
              >
                <Trash2 size={14} />
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default ActivationCostInline;
