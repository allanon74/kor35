import React, { useState } from 'react';

const softVibrate = (ms = 25) => {
  try {
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(ms);
  } catch {
    /* ignore */
  }
};

/**
 * Tocca le celle nell'ordine indicato (numeri/glifi).
 */
const TapOrder = ({ cells = [], order = [], playerInput = [], onChange }) => {
  const [errorFlash, setErrorFlash] = useState(false);
  const done = new Set(playerInput || []);
  const nextExpected = order[playerInput.length];
  const cols = Math.ceil(Math.sqrt(cells.length || 1));

  const onTap = (cellId) => {
    if (done.has(cellId)) return;
    const expected = order[playerInput.length];
    if (cellId !== expected) {
      setErrorFlash(true);
      softVibrate([40, 40, 40]);
      setTimeout(() => {
        onChange({ player_input: [] });
        setErrorFlash(false);
      }, 350);
      return;
    }
    softVibrate(25);
    onChange({ player_input: [...playerInput, cellId] });
  };

  return (
    <div className="space-y-3">
      <p className={`text-xs text-center ${errorFlash ? 'text-red-400 font-semibold' : 'text-gray-400'}`}>
        {errorFlash
          ? 'Ordine errato — riprova'
          : `Tocca in ordine (${(playerInput || []).length}/${order.length})`}
      </p>
      <div
        className="grid gap-2 max-w-xs mx-auto"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {cells.map((cell) => {
          const id = cell.id;
          const isDone = done.has(id);
          const isNext = id === nextExpected && !errorFlash;
          return (
            <button
              key={id}
              type="button"
              disabled={isDone}
              onClick={() => onTap(id)}
              className={`aspect-square min-h-[44px] rounded-xl border-2 text-lg font-bold transition-all ${
                isDone
                  ? 'bg-emerald-900/60 border-emerald-500 text-emerald-200 opacity-70'
                  : isNext
                    ? 'bg-indigo-800 border-indigo-400 text-white scale-[1.02]'
                    : 'bg-gray-800 border-gray-600 text-gray-200'
              }`}
            >
              {cell.label}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default TapOrder;
