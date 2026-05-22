import React, { useMemo } from 'react';
import { X } from 'lucide-react';
import SearchableSelect from './SearchableSelect';

export function formatAbilitaPickerLabel(ab) {
  if (!ab?.nome) return '';
  const parts = [ab.nome];
  if (ab.costo_pc > 0) parts.push(`${ab.costo_pc} PC`);
  if (Number(ab.costo_crediti) > 0) parts.push(`${ab.costo_crediti} CR`);
  if (ab.nascondi_in_scheda_abilita) parts.push('nascosta scheda');
  if (ab.is_tratto_aura) parts.push('tratto aura');
  return parts.join(' · ');
}

export function abilitaToSyncId(ab) {
  if (!ab) return '';
  return String(ab.sync_id || ab.id || '').trim();
}

/**
 * Selezione multipla abilità per wizard (payload abilita_sync_ids).
 * @param {object[]} options - righe da staffGetAbilitaListAll
 * @param {string[]} selectedSyncIds
 */
export default function AbilitaMultiPicker({
  options = [],
  selectedSyncIds = [],
  onChange,
  disabled = false,
}) {
  const bySyncId = useMemo(() => {
    const map = new Map();
    for (const ab of options) {
      const sid = abilitaToSyncId(ab);
      if (sid) map.set(sid, ab);
    }
    return map;
  }, [options]);

  const availableToAdd = useMemo(() => {
    const sel = new Set(selectedSyncIds.map(String));
    return options
      .filter((ab) => {
        const sid = abilitaToSyncId(ab);
        return sid && !sel.has(sid);
      })
      .map((ab) => ({
        ...ab,
        id: abilitaToSyncId(ab),
        nome: formatAbilitaPickerLabel(ab),
      }));
  }, [options, selectedSyncIds]);

  const addAbilita = (syncId) => {
    if (!syncId || disabled) return;
    const sid = String(syncId);
    if (selectedSyncIds.includes(sid)) return;
    onChange([...selectedSyncIds, sid]);
  };

  const removeAbilita = (syncId) => {
    if (disabled) return;
    onChange(selectedSyncIds.filter((s) => String(s) !== String(syncId)));
  };

  return (
    <div className="space-y-2">
      <label className="text-[10px] uppercase font-bold text-gray-500 tracking-wide">
        Abilità suggerite
      </label>
      {selectedSyncIds.length > 0 ? (
        <ul className="flex flex-wrap gap-1.5">
          {selectedSyncIds.map((sid) => {
            const ab = bySyncId.get(String(sid));
            return (
              <li
                key={sid}
                className="inline-flex items-center gap-1 max-w-full px-2 py-1 rounded-md bg-violet-900/50 border border-violet-600/60 text-xs text-violet-100"
              >
                <span className="truncate" title={ab ? formatAbilitaPickerLabel(ab) : sid}>
                  {ab?.nome || `ID ${sid}`}
                </span>
                {!disabled ? (
                  <button
                    type="button"
                    onClick={() => removeAbilita(sid)}
                    className="shrink-0 p-0.5 rounded hover:bg-violet-800 text-violet-300"
                    aria-label="Rimuovi"
                  >
                    <X size={12} />
                  </button>
                ) : null}
              </li>
            );
          })}
        </ul>
      ) : (
        <p className="text-xs text-gray-500 italic">Nessuna abilità selezionata.</p>
      )}
      <SearchableSelect
        options={availableToAdd}
        value={null}
        onChange={(v) => addAbilita(v)}
        placeholder="Aggiungi abilità..."
        labelKey="nome"
        valueKey="id"
        disabled={disabled || availableToAdd.length === 0}
        minOptionsForSearch={8}
      />
    </div>
  );
}
