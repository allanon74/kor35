import React, { useMemo } from 'react';

/**
 * Sliding puzzle (15-puzzle): tiles è l'ordine dei pezzi in ogni cella.
 * Il pezzo "buco" ha valore size*size - 1.
 */
const SlidingPuzzle = ({ size, tiles, imageUrl, onChange }) => {
  const total = size * size;
  const emptyVal = total - 1;

  const emptyIdx = useMemo(() => {
    const list = tiles || [];
    const i = list.indexOf(emptyVal);
    return i >= 0 ? i : total - 1;
  }, [tiles, emptyVal, total]);

  const neighbors = (idx) => {
    const r = Math.floor(idx / size);
    const c = idx % size;
    const out = [];
    if (r > 0) out.push((r - 1) * size + c);
    if (r < size - 1) out.push((r + 1) * size + c);
    if (c > 0) out.push(r * size + (c - 1));
    if (c < size - 1) out.push(r * size + (c + 1));
    return out;
  };

  const tryMove = (idx) => {
    if (!neighbors(idx).includes(emptyIdx)) return;
    const next = [...(tiles || [])];
    next[emptyIdx] = next[idx];
    next[idx] = emptyVal;
    onChange({ tiles: next });
  };

  const pct = 100 / size;

  return (
    <div
      className="relative w-full max-w-sm mx-auto aspect-square bg-gray-950 rounded-lg overflow-hidden border border-indigo-500/50"
      style={{ touchAction: 'manipulation' }}
    >
      {(tiles || []).map((piece, idx) => {
        if (piece === emptyVal) {
          return (
            <div
              key={idx}
              className="absolute bg-gray-900/80 border border-gray-800 box-border"
              style={{
                width: `${pct}%`,
                height: `${pct}%`,
                left: `${(idx % size) * pct}%`,
                top: `${Math.floor(idx / size) * pct}%`,
              }}
            />
          );
        }
        const pr = Math.floor(piece / size);
        const pc = piece % size;
        return (
          <button
            key={idx}
            type="button"
            className="absolute box-border border border-white/10 active:brightness-110"
            style={{
              width: `${pct}%`,
              height: `${pct}%`,
              left: `${(idx % size) * pct}%`,
              top: `${Math.floor(idx / size) * pct}%`,
              backgroundImage: imageUrl ? `url(${imageUrl})` : undefined,
              backgroundSize: `${size * 100}%`,
              backgroundPosition: `${pc * (100 / (size - 1))}% ${pr * (100 / (size - 1))}%`,
              backgroundColor: imageUrl ? undefined : '#312e81',
            }}
            onClick={() => tryMove(idx)}
            aria-label={`Pezzo ${piece + 1}`}
          />
        );
      })}
    </div>
  );
};

export default SlidingPuzzle;
