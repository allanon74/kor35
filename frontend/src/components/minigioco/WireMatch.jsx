import React, { useState } from 'react';

const WIRE_COLORS = [
  { bg: 'bg-red-500', ring: 'ring-red-300' },
  { bg: 'bg-blue-500', ring: 'ring-blue-300' },
  { bg: 'bg-amber-400', ring: 'ring-amber-200' },
  { bg: 'bg-emerald-500', ring: 'ring-emerald-300' },
  { bg: 'bg-violet-500', ring: 'ring-violet-300' },
  { bg: 'bg-pink-500', ring: 'ring-pink-300' },
];

/**
 * Collega i fili: tap sinistra → destra sullo stesso id/colore.
 */
const WireMatch = ({
  pairs = [],
  leftOrder,
  rightOrder,
  matchedPairs = [],
  onChange,
}) => {
  const [selectedLeft, setSelectedLeft] = useState(null);
  const [flashError, setFlashError] = useState(false);
  const matched = new Set(matchedPairs || []);
  const n = pairs.length;
  const left = leftOrder?.length === n ? leftOrder : pairs.map((p) => p.id);
  const right = rightOrder?.length === n ? rightOrder : [...left].reverse();

  const tryMatch = (leftId, rightId) => {
    if (matched.has(leftId)) return;
    if (leftId === rightId) {
      onChange({ matched_pairs: [...matchedPairs, leftId] });
      setSelectedLeft(null);
      setFlashError(false);
      return;
    }
    setFlashError(true);
    setTimeout(() => {
      setFlashError(false);
      setSelectedLeft(null);
    }, 350);
  };

  const onLeft = (id) => {
    if (matched.has(id)) return;
    setSelectedLeft(id);
    setFlashError(false);
  };

  const onRight = (id) => {
    if (matched.has(id) || selectedLeft == null) return;
    tryMatch(selectedLeft, id);
  };

  const colorFor = (id) => WIRE_COLORS[id % WIRE_COLORS.length];

  return (
    <div className="space-y-3">
      <p className={`text-xs text-center ${flashError ? 'text-red-400 font-semibold' : 'text-gray-400'}`}>
        {flashError
          ? 'Colore sbagliato — riprova'
          : selectedLeft != null
            ? 'Tocca il filo destro dello stesso colore'
            : 'Tocca un filo a sinistra, poi il corrispondente a destra'}
      </p>
      <div className="flex justify-between gap-4 max-w-xs mx-auto">
        <div className="flex flex-col gap-2 flex-1">
          {left.map((id) => {
            const c = colorFor(id);
            const done = matched.has(id);
            return (
              <button
                key={`L-${id}`}
                type="button"
                disabled={done}
                onClick={() => onLeft(id)}
                className={`h-11 min-h-[44px] rounded-lg border-2 ${c.bg} ${
                  selectedLeft === id ? `ring-2 ${c.ring} scale-[1.02]` : 'border-white/20'
                } ${done ? 'opacity-40' : ''}`}
                aria-label={`Filo sinistro ${id + 1}`}
              />
            );
          })}
        </div>
        <div className="flex flex-col gap-2 flex-1">
          {right.map((id) => {
            const c = colorFor(id);
            const done = matched.has(id);
            return (
              <button
                key={`R-${id}`}
                type="button"
                disabled={done}
                onClick={() => onRight(id)}
                className={`h-11 min-h-[44px] rounded-lg border-2 ${c.bg} border-white/20 ${
                  done ? 'opacity-40' : ''
                }`}
                aria-label={`Filo destro ${id + 1}`}
              />
            );
          })}
        </div>
      </div>
      <p className="text-[10px] text-center text-gray-500">
        {matched.size}/{n} collegati
      </p>
    </div>
  );
};

export default WireMatch;
