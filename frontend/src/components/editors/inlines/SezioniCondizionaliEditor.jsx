import React from 'react';
import { Plus, Trash2, ChevronUp, ChevronDown } from 'lucide-react';
import RichTextEditor from '../../RichTextEditor';
import SearchableSelect from '../SearchableSelect';
import { RequisitiGruppoEditor } from '../RequisitiAccessoEditor';
import { useRequisitiAccessoLookup } from '../../../hooks/useRequisitiAccessoLookup';

const emptyCondizioni = () => ({
  operator: 'AND',
  requisiti: [{ tipo: 'punteggio', nome: '', min: 2, op: 'gt' }],
});

const emptySezione = (ordine = 0) => ({
  ordine,
  testo: '',
  condizioni: emptyCondizioni(),
  statistiche_base: [],
  modificatori: [],
});

const emptyBaseRow = () => ({ statistica: null, valore_base: 0 });
const emptyModRow = () => ({
  statistica: null,
  valore: 0,
  tipo_modificatore: 'ADD',
  solo_oggetto_ospitante: false,
});

const SezioniCondizionaliEditor = ({
  items = [],
  statsOptions = [],
  onChange,
  onLogout,
}) => {
  const { lookup, loading: lookupLoading } = useRequisitiAccessoLookup(onLogout);
  const list = Array.isArray(items) ? items : [];

  const commit = (next) => onChange(next.map((s, idx) => ({ ...s, ordine: idx })));

  const updateAt = (idx, patch) => {
    commit(list.map((s, i) => (i === idx ? { ...s, ...patch } : s)));
  };

  const move = (idx, dir) => {
    const dest = idx + dir;
    if (dest < 0 || dest >= list.length) return;
    const next = [...list];
    const [row] = next.splice(idx, 1);
    next.splice(dest, 0, row);
    commit(next);
  };

  const updateNested = (idx, key, nestedIdx, field, value) => {
    const nested = [...(list[idx][key] || [])];
    nested[nestedIdx] = { ...nested[nestedIdx], [field]: value };
    updateAt(idx, { [key]: nested });
  };

  return (
    <div className="bg-indigo-950/20 p-4 rounded-lg border border-indigo-500/30 space-y-4">
      <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-3">
        <div className="min-w-0">
          <h3 className="text-sm font-bold text-indigo-300 uppercase tracking-widest">
            Sezioni condizionali
          </h3>
          <p className="text-[11px] text-gray-400 mt-1">
            Testo extra, statistiche base e modificatori visibili/attivi solo se il personaggio
            soddisfa la condizione (es. Aura Magica &gt; 2).
          </p>
        </div>
        <button
          type="button"
          onClick={() => commit([...list, emptySezione(list.length)])}
          className="text-xs bg-indigo-600 hover:bg-indigo-500 px-3 py-2 rounded font-bold shrink-0 min-h-11"
        >
          + Sezione
        </button>
      </div>

      {list.length === 0 && (
        <p className="text-xs text-gray-500 italic">Nessuna sezione condizionale.</p>
      )}

      <div className="space-y-4">
        {list.map((sezione, idx) => (
          <div key={sezione.id || idx} className="bg-gray-900/80 border border-indigo-500/20 rounded-xl p-4 space-y-4">
            <div className="flex items-center justify-between gap-2">
              <span className="text-[10px] font-black uppercase tracking-widest text-indigo-400">
                Sezione {idx + 1}
              </span>
              <div className="flex items-center gap-1">
                <button type="button" className="text-gray-400 p-1" onClick={() => move(idx, -1)} aria-label="Su">
                  <ChevronUp size={14} />
                </button>
                <button type="button" className="text-gray-400 p-1" onClick={() => move(idx, 1)} aria-label="Giù">
                  <ChevronDown size={14} />
                </button>
                <button
                  type="button"
                  className="text-red-400 p-1"
                  onClick={() => commit(list.filter((_, i) => i !== idx))}
                  aria-label="Rimuovi sezione"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>

            <RequisitiGruppoEditor
              value={sezione.condizioni || emptyCondizioni()}
              onChange={(condizioni) => updateAt(idx, { condizioni })}
              lookup={lookup}
              lookupLoading={lookupLoading}
              label="Attiva se"
            />

            <RichTextEditor
              label="Testo addizionale (visibile solo se la condizione è vera)"
              value={sezione.testo || ''}
              onChange={(testo) => updateAt(idx, { testo })}
            />

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="text-[10px] font-black uppercase tracking-widest text-amber-400">
                  Statistiche base di questa sezione
                </h4>
                <button
                  type="button"
                  className="text-[10px] text-amber-300 flex items-center gap-1"
                  onClick={() => updateAt(idx, {
                    statistiche_base: [...(sezione.statistiche_base || []), emptyBaseRow()],
                  })}
                >
                  <Plus size={12} /> Aggiungi
                </button>
              </div>
              {(sezione.statistiche_base || []).map((row, rIdx) => (
                <div key={rIdx} className="flex gap-2 items-center">
                  <div className="flex-1">
                    <SearchableSelect
                      options={statsOptions}
                      value={row.statistica?.id || row.statistica || ''}
                      onChange={(val) => updateNested(idx, 'statistiche_base', rIdx, 'statistica', val ? parseInt(val, 10) : null)}
                      placeholder="Statistica"
                    />
                  </div>
                  <input
                    type="number"
                    className="w-20 bg-gray-950 border border-gray-700 rounded p-2 text-sm text-center"
                    value={row.valore_base ?? 0}
                    onChange={(e) => updateNested(idx, 'statistiche_base', rIdx, 'valore_base', Number(e.target.value))}
                  />
                  <button
                    type="button"
                    className="text-red-400 p-1"
                    onClick={() => updateAt(idx, {
                      statistiche_base: (sezione.statistiche_base || []).filter((_, i) => i !== rIdx),
                    })}
                  >
                    ✕
                  </button>
                </div>
              ))}
            </div>

            <div className="space-y-2">
              <div className="flex justify-between items-center">
                <h4 className="text-[10px] font-black uppercase tracking-widest text-emerald-400">
                  Modificatori generali di questa sezione
                </h4>
                <button
                  type="button"
                  className="text-[10px] text-emerald-300 flex items-center gap-1"
                  onClick={() => updateAt(idx, {
                    modificatori: [...(sezione.modificatori || []), emptyModRow()],
                  })}
                >
                  <Plus size={12} /> Aggiungi
                </button>
              </div>
              {(sezione.modificatori || []).map((row, rIdx) => (
                <div key={rIdx} className="bg-gray-800/60 border border-gray-700 rounded p-2 space-y-2">
                  <div className="flex flex-wrap gap-2 items-center">
                    <div className="flex-1 min-w-[160px]">
                      <SearchableSelect
                        options={statsOptions}
                        value={row.statistica?.id || row.statistica || ''}
                        onChange={(val) => updateNested(idx, 'modificatori', rIdx, 'statistica', val ? parseInt(val, 10) : null)}
                        placeholder="Statistica"
                      />
                    </div>
                    <select
                      className="bg-gray-950 border border-gray-700 rounded p-2 text-sm"
                      value={row.tipo_modificatore || 'ADD'}
                      onChange={(e) => updateNested(idx, 'modificatori', rIdx, 'tipo_modificatore', e.target.value)}
                    >
                      <option value="ADD">Additivo (+)</option>
                      <option value="MOL">Moltiplicatore (x)</option>
                    </select>
                    <input
                      type="number"
                      step="any"
                      className="w-20 bg-gray-950 border border-gray-700 rounded p-2 text-sm text-center"
                      value={row.valore ?? 0}
                      onChange={(e) => updateNested(idx, 'modificatori', rIdx, 'valore', e.target.value)}
                    />
                    <button
                      type="button"
                      className="text-red-400 p-1"
                      onClick={() => updateAt(idx, {
                        modificatori: (sezione.modificatori || []).filter((_, i) => i !== rIdx),
                      })}
                    >
                      ✕
                    </button>
                  </div>
                  <label className="flex items-center gap-2 text-[10px] text-cyan-300 cursor-pointer">
                    <input
                      type="checkbox"
                      className="accent-cyan-500"
                      checked={!!row.solo_oggetto_ospitante}
                      onChange={(e) => updateNested(idx, 'modificatori', rIdx, 'solo_oggetto_ospitante', e.target.checked)}
                    />
                    Solo formule dell&apos;oggetto (non modifica il personaggio)
                  </label>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default SezioniCondizionaliEditor;
export { emptySezione, emptyCondizioni };
