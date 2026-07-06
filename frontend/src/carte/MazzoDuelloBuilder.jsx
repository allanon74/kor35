import React, { useMemo } from 'react';
import { Plus, Star, Trash2, X } from 'lucide-react';
import CardFrame from './CardFrame';
import { groupCollezioneStacks } from './collezioneUtils';
import { MAZZO_DUELLO_SIZE } from './carteConstants';

export const MAZZI_DUELLO_MAX = 5;

export default function MazzoDuelloBuilder({
  carte = [],
  carteById,
  mazzi = [],
  activeMazzoId,
  mazzoIds,
  mazzoNome,
  mazzoIsDefault,
  leaderId,
  regoleMazzo = [],
  onLeaderChange,
  onMazzoIdsChange,
  onActiveMazzoChange,
  onMazzoNomeChange,
  onMazzoIsDefaultChange,
  onNewMazzo,
  onSave,
  onDelete,
  saving = false,
  temaEnergie,
  keywords = [],
  tagsGlossary = [],
}) {
  const stacks = useMemo(() => groupCollezioneStacks(carte), [carte]);
  const inMazzoSet = useMemo(() => new Set(mazzoIds), [mazzoIds]);
  const leaderStacks = useMemo(
    () => stacks.filter((s) => s.carta?.tipo === 'PG'),
    [stacks],
  );
  const leaderItem = leaderId ? carteById.get(leaderId) : null;

  const countCopiesInMazzoForCarta = (cartaId) => mazzoIds.filter((cpId) => {
    const item = carteById.get(cpId);
    return item?.carta?.id === cartaId;
  }).length;

  const removeAt = (index) => {
    onMazzoIdsChange(mazzoIds.filter((_, i) => i !== index));
  };

  const addCopyFromStack = (stack) => {
    if (mazzoIds.length >= MAZZO_DUELLO_SIZE) return;
    const cartaId = stack.carta.id;
    const already = countCopiesInMazzoForCarta(cartaId);
    const maxCopies = stack.carta.duplicabile ? 2 : 1;
    if (already >= maxCopies) return;
    const pick = stack.copies.find((c) => !inMazzoSet.has(c.id));
    if (!pick) return;
    onMazzoIdsChange([...mazzoIds, pick.id]);
  };

  const slotIndices = Array.from({ length: MAZZO_DUELLO_SIZE }, (_, i) => i);
  const mazziSlots = Array.from({ length: MAZZI_DUELLO_MAX }, (_, i) => mazzi[i] || null);

  return (
    <div className="space-y-3">
      <p className="text-xs text-indigo-200/80">
        Tocca una carta nella collezione per aggiungerla (max {MAZZO_DUELLO_SIZE}).
        Tocca una carta nel mazzo (con la X) per rimuoverla.
      </p>

      {regoleMazzo.length > 0 && (
        <details className="rounded border border-indigo-900/60 bg-indigo-950/30 px-2 py-1.5 text-xs text-indigo-100/90">
          <summary className="cursor-pointer font-bold text-indigo-200">Regole mazzo (Sette Elegie)</summary>
          <ul className="mt-1.5 list-disc space-y-0.5 pl-4">
            {regoleMazzo.map((regola) => (
              <li key={regola}>{regola}</li>
            ))}
          </ul>
        </details>
      )}

      <div className="flex flex-wrap gap-1">
        {mazziSlots.map((m, idx) => {
          const isNewSlot = !m && idx === mazzi.length && mazzi.length < MAZZI_DUELLO_MAX;
          const isActive = m
            ? m.id === activeMazzoId
            : isNewSlot && !activeMazzoId;
          if (!m && idx > mazzi.length) return null;
          return (
            <button
              key={m?.id || `new-${idx}`}
              type="button"
              onClick={() => {
                if (m) onActiveMazzoChange(m);
                else if (isNewSlot) onNewMazzo();
              }}
              className={`flex items-center gap-1 rounded border px-2 py-1 text-xs font-bold ${
                isActive ? 'border-indigo-400 bg-indigo-900 text-white' : 'border-gray-600 bg-gray-900 text-gray-400'
              }`}
            >
              {m?.is_default && <Star size={12} className="text-amber-300" fill="currentColor" />}
              {m ? (m.nome || `Mazzo ${idx + 1}`) : <><Plus size={12} /> Nuovo</>}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <label className="flex flex-col text-xs text-gray-400">
          Nome mazzo
          <input
            type="text"
            value={mazzoNome}
            onChange={(e) => onMazzoNomeChange(e.target.value)}
            className="mt-0.5 rounded border border-gray-600 bg-gray-950 px-2 py-1 text-sm text-white"
            maxLength={80}
          />
        </label>
        <label className="flex items-center gap-1 pt-4 text-xs text-gray-400">
          <input
            type="checkbox"
            checked={mazzoIsDefault}
            onChange={(e) => onMazzoIsDefaultChange(e.target.checked)}
            className="rounded"
          />
          Predefinito per i duelli
        </label>
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-bold text-amber-200">
          <span>Leader (comandante)</span>
          <span className={leaderId ? 'text-emerald-300' : 'text-amber-300'}>
            {leaderId ? 'Selezionato' : 'Obbligatorio'}
          </span>
        </div>
        {leaderItem ? (
          <button
            type="button"
            onClick={() => onLeaderChange(null)}
            className="relative rounded-lg border-2 border-amber-500 bg-amber-950/30 p-1"
            title="Rimuovi Leader"
          >
            <CardFrame
              item={leaderItem}
              compact
              temaEnergie={temaEnergie}
              keywords={keywords}
              tagsGlossary={tagsGlossary}
              showRules={false}
            />
            <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-800 text-white">
              <X size={10} />
            </span>
          </button>
        ) : (
          <p className="text-[10px] text-gray-500">Scegli un Personaggio dalla lista sotto (non nel mazzo).</p>
        )}
        {!leaderId && (
          <div className="mt-2 flex flex-wrap justify-center gap-2">
            {leaderStacks.map((stack) => {
              const inDeck = countCopiesInMazzoForCarta(stack.carta.id);
              const pick = stack.copies.find((c) => !inMazzoSet.has(c.id));
              const canPick = pick && inDeck === 0;
              return (
                <button
                  key={`leader-${stack.key}`}
                  type="button"
                  disabled={!canPick}
                  onClick={() => canPick && onLeaderChange(pick.id)}
                  className={`relative rounded-lg ${canPick ? 'opacity-100' : 'opacity-30'}`}
                  title={canPick ? 'Scegli come Leader' : 'Già nel mazzo o non disponibile'}
                >
                  <CardFrame
                    item={stack.representative}
                    compact
                    temaEnergie={temaEnergie}
                    keywords={keywords}
              tagsGlossary={tagsGlossary}
                    showRules={false}
                  />
                </button>
              );
            })}
          </div>
        )}
      </div>

      <div>
        <div className="mb-1 flex items-center justify-between text-xs font-bold text-indigo-200">
          <span>Composizione mazzo</span>
          <span className={mazzoIds.length === MAZZO_DUELLO_SIZE ? 'text-emerald-300' : 'text-amber-300'}>
            {mazzoIds.length}/{MAZZO_DUELLO_SIZE} carte
          </span>
        </div>
        <div className="grid grid-cols-5 gap-1.5">
          {slotIndices.map((i) => {
            const cpId = mazzoIds[i];
            const item = cpId ? carteById.get(cpId) : null;
            return (
              <button
                key={`slot-${i}`}
                type="button"
                title={item ? 'Rimuovi dal mazzo' : 'Slot vuoto'}
                onClick={() => item && removeAt(i)}
                className={`flex min-h-[88px] items-center justify-center rounded-lg border-2 border-dashed p-0.5 transition-colors ${
                  item
                    ? 'border-indigo-500 bg-indigo-950/40 hover:border-red-500'
                    : 'border-gray-700 bg-gray-900/40'
                }`}
              >
                {item ? (
                  <div className="relative w-full">
                    <CardFrame item={item} compact size="sm" temaEnergie={temaEnergie} keywords={keywords} showRules={false} />
                    <span className="absolute -right-0.5 -top-0.5 flex h-4 w-4 items-center justify-center rounded-full bg-red-800 text-white">
                      <X size={10} />
                    </span>
                  </div>
                ) : (
                  <span className="text-[10px] text-gray-600">{i + 1}</span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <h4 className="mb-2 text-xs font-bold text-gray-400">Aggiungi dalla collezione</h4>
        <div className="flex flex-wrap justify-center gap-2">
          {stacks.map((stack) => {
            const inDeck = countCopiesInMazzoForCarta(stack.carta.id);
            const maxCopies = stack.carta.duplicabile ? 2 : 1;
            const canAdd = mazzoIds.length < MAZZO_DUELLO_SIZE && inDeck < maxCopies
              && stack.copies.some((c) => !inMazzoSet.has(c.id));
            return (
              <button
                key={stack.key}
                type="button"
                disabled={!canAdd}
                onClick={() => addCopyFromStack(stack)}
                className={`relative rounded-lg transition-opacity ${canAdd ? 'opacity-100' : 'opacity-40'}`}
                title={canAdd ? 'Aggiungi al mazzo' : 'Non aggiungibile'}
              >
                <CardFrame
                  item={stack.representative}
                  compact
                  temaEnergie={temaEnergie}
                  keywords={keywords}
              tagsGlossary={tagsGlossary}
                  showRules={false}
                />
                {stack.count > 1 && (
                  <span className="pointer-events-none absolute -right-1 -top-1 rounded-full bg-violet-700 px-1 text-[9px] font-bold text-white">
                    ×{stack.count}
                  </span>
                )}
                {inDeck > 0 && (
                  <span className="pointer-events-none absolute bottom-0 left-0 right-0 rounded-b-lg bg-indigo-900/90 py-0.5 text-center text-[8px] font-bold text-indigo-200">
                    Nel mazzo: {inDeck}/{maxCopies}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="flex flex-wrap gap-2">
        <button
          type="button"
          disabled={saving || mazzoIds.length !== MAZZO_DUELLO_SIZE || !leaderId}
          onClick={onSave}
          className="rounded bg-emerald-800 px-3 py-1.5 text-xs font-bold disabled:opacity-50"
        >
          {saving ? 'Salvataggio…' : 'Salva mazzo'}
        </button>
        {activeMazzoId && (
          <button
            type="button"
            disabled={saving}
            onClick={onDelete}
            className="flex items-center gap-1 rounded bg-red-950 px-3 py-1.5 text-xs font-bold text-red-200 disabled:opacity-50"
          >
            <Trash2 size={12} /> Elimina
          </button>
        )}
        <button
          type="button"
          onClick={() => onMazzoIdsChange([])}
          className="rounded border border-gray-600 px-3 py-1.5 text-xs text-gray-400"
        >
          Svuota bozza
        </button>
      </div>
    </div>
  );
}
