import React, { useEffect, useMemo, useState } from 'react';
import { Plus, Trash2 } from 'lucide-react';
import {
  buildBonusEquip,
  DUEL_STAT_OPTIONS,
  DUEL_STAT_ROWS,
  parseBonusEquip,
  REL_SIGLE_OPTIONS,
} from '../../carte/bonusEquipEditor';

const emptyExtraRow = () => ({ stat: 'forza', valore: '', se_leader: false });

export default function BonusEquipEditor({ value, onChange, tipo }) {
  const parsed = useMemo(() => parseBonusEquip(value), [value]);
  const [relSigla, setRelSigla] = useState(parsed.relSigla);
  const [relValore, setRelValore] = useState(parsed.relValore);
  const [flat, setFlat] = useState(parsed.flat);
  const [extraDuello, setExtraDuello] = useState(parsed.extraDuello);
  const [showAdvanced, setShowAdvanced] = useState(parsed.extraDuello.length > 0);

  useEffect(() => {
    setRelSigla(parsed.relSigla);
    setRelValore(parsed.relValore);
    setFlat(parsed.flat);
    setExtraDuello(parsed.extraDuello);
    if (parsed.extraDuello.length > 0) setShowAdvanced(true);
  }, [parsed]);

  const emit = (patch) => {
    const next = {
      relSigla: patch.relSigla ?? relSigla,
      relValore: patch.relValore ?? relValore,
      flat: patch.flat ?? flat,
      extraDuello: patch.extraDuello ?? extraDuello,
    };
    onChange(buildBonusEquip(next));
  };

  const updateFlat = (key, raw) => {
    const nextFlat = { ...flat, [key]: raw === '' ? '' : Number(raw) };
    setFlat(nextFlat);
    emit({ flat: nextFlat });
  };

  const isOggetto = tipo === 'OGG';

  return (
    <div className="rounded border border-amber-900/50 bg-amber-950/20 p-2">
      <h4 className="mb-1 text-xs font-bold text-amber-300">Bonus equip</h4>
      <p className="mb-2 text-[10px] text-gray-500">
        {isOggetto
          ? 'Equip in duello (su eroe) e bonus passivo nello slot reliquiario del personaggio.'
          : 'Opzionale: utile se la carta può essere equipaggiata o messa in reliquiario.'}
      </p>

      <div className="mb-3 rounded border border-gray-700/80 bg-gray-900/40 p-2">
        <p className="mb-1 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
          Reliquiario (legacy)
        </p>
        <div className="grid grid-cols-2 gap-2">
          <label className="block text-xs text-gray-400">
            Statistica
            <select
              className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              value={relSigla}
              onChange={(e) => {
                const v = e.target.value;
                setRelSigla(v);
                emit({ relSigla: v });
              }}
            >
              {REL_SIGLE_OPTIONS.map((o) => (
                <option key={o.value || 'none'} value={o.value}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="block text-xs text-gray-400">
            Valore
            <input
              type="number"
              className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              value={relValore}
              disabled={!relSigla}
              onChange={(e) => {
                const v = e.target.value === '' ? '' : Number(e.target.value);
                setRelValore(v);
                emit({ relValore: v });
              }}
            />
          </label>
        </div>
      </div>

      <div className="mb-2 rounded border border-gray-700/80 bg-gray-900/40 p-2">
        <p className="mb-2 text-[10px] font-semibold uppercase tracking-wide text-gray-400">
          Duello — bonus su eroe equipaggiato
        </p>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[280px] text-xs">
            <thead>
              <tr className="text-left text-gray-500">
                <th className="pb-1 pr-2 font-normal">Stat</th>
                <th className="pb-1 pr-2 font-normal">Sempre</th>
                <th className="pb-1 font-normal">Solo Leader</th>
              </tr>
            </thead>
            <tbody>
              {DUEL_STAT_ROWS.map(({ key, label }) => (
                <tr key={key}>
                  <td className="py-0.5 pr-2 text-gray-300">{label}</td>
                  <td className="py-0.5 pr-2">
                    <input
                      type="number"
                      className="w-16 rounded border border-gray-600 bg-gray-900 px-1 py-0.5 text-sm"
                      value={flat[key]}
                      onChange={(e) => updateFlat(key, e.target.value)}
                    />
                  </td>
                  <td className="py-0.5">
                    <input
                      type="number"
                      className="w-16 rounded border border-gray-600 bg-gray-900 px-1 py-0.5 text-sm"
                      value={flat[`${key}_se_leader`]}
                      onChange={(e) => updateFlat(`${key}_se_leader`, e.target.value)}
                    />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <button
        type="button"
        className="mb-2 text-[10px] text-amber-400/90 underline"
        onClick={() => setShowAdvanced((v) => !v)}
      >
        {showAdvanced ? 'Nascondi lista avanzata' : 'Lista avanzata (duello[])'}
      </button>

      {showAdvanced && (
        <div className="space-y-2 rounded border border-dashed border-gray-600 p-2">
          <p className="text-[10px] text-gray-500">
            Righe extra serializzate in <code className="text-gray-400">bonus_equip.duello</code>.
            Usa per combinazioni non coperte dalla tabella sopra.
          </p>
          {extraDuello.map((row, idx) => (
            <div key={idx} className="flex flex-wrap items-end gap-2">
              <label className="text-xs text-gray-400">
                Stat
                <select
                  className="ml-1 rounded border border-gray-600 bg-gray-900 px-1 py-0.5 text-sm"
                  value={row.stat}
                  onChange={(e) => {
                    const next = extraDuello.map((r, i) => (i === idx ? { ...r, stat: e.target.value } : r));
                    setExtraDuello(next);
                    emit({ extraDuello: next });
                  }}
                >
                  {DUEL_STAT_OPTIONS.map((o) => (
                    <option key={o.value} value={o.value}>{o.label}</option>
                  ))}
                </select>
              </label>
              <label className="text-xs text-gray-400">
                Valore
                <input
                  type="number"
                  className="ml-1 w-14 rounded border border-gray-600 bg-gray-900 px-1 py-0.5 text-sm"
                  value={row.valore}
                  onChange={(e) => {
                    const v = e.target.value === '' ? '' : Number(e.target.value);
                    const next = extraDuello.map((r, i) => (i === idx ? { ...r, valore: v } : r));
                    setExtraDuello(next);
                    emit({ extraDuello: next });
                  }}
                />
              </label>
              <label className="flex items-center gap-1 text-xs text-gray-400">
                <input
                  type="checkbox"
                  checked={row.se_leader}
                  onChange={(e) => {
                    const next = extraDuello.map((r, i) => (
                      i === idx ? { ...r, se_leader: e.target.checked } : r
                    ));
                    setExtraDuello(next);
                    emit({ extraDuello: next });
                  }}
                />
                Solo Leader
              </label>
              <button
                type="button"
                className="rounded p-1 text-red-400 hover:bg-red-950/50"
                title="Rimuovi riga"
                onClick={() => {
                  const next = extraDuello.filter((_, i) => i !== idx);
                  setExtraDuello(next);
                  emit({ extraDuello: next });
                }}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          <button
            type="button"
            className="flex items-center gap-1 rounded border border-gray-600 px-2 py-0.5 text-xs text-gray-300 hover:bg-gray-800"
            onClick={() => {
              const next = [...extraDuello, emptyExtraRow()];
              setExtraDuello(next);
              emit({ extraDuello: next });
            }}
          >
            <Plus size={12} /> Aggiungi riga
          </button>
        </div>
      )}
    </div>
  );
}
