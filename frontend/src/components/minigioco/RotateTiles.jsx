import React from 'react';

/**
 * Ogni cella ha rotazione 0–3 (×90°). Tap per ruotare.
 */
const RotateTiles = ({ size, rotations, imageUrl, onChange }) => {
  const total = size * size;
  const pct = 100 / size;

  const rotateAt = (idx) => {
    const next = [...(rotations || Array(total).fill(0))];
    next[idx] = ((Number(next[idx]) || 0) + 1) % 4;
    onChange({ rotations: next });
  };

  return (
    <div
      className="relative w-full max-w-sm mx-auto aspect-square bg-gray-950 rounded-lg overflow-hidden border border-cyan-500/50"
      style={{ touchAction: 'manipulation' }}
    >
      {Array.from({ length: total }, (_, idx) => {
        const rot = Number((rotations || [])[idx]) || 0;
        const pr = Math.floor(idx / size);
        const pc = idx % size;
        return (
          <button
            key={idx}
            type="button"
            className="absolute box-border border border-white/10 overflow-hidden active:brightness-110"
            style={{
              width: `${pct}%`,
              height: `${pct}%`,
              left: `${(idx % size) * pct}%`,
              top: `${Math.floor(idx / size) * pct}%`,
            }}
            onClick={() => rotateAt(idx)}
            aria-label={`Ruota cella ${idx + 1}`}
          >
            <div
              className="w-full h-full"
              style={{
                transform: `rotate(${rot * 90}deg)`,
                transformOrigin: 'center center',
                backgroundImage: imageUrl ? `url(${imageUrl})` : undefined,
                backgroundSize: `${size * 100}%`,
                backgroundPosition: `${pc * (100 / (size - 1))}% ${pr * (100 / (size - 1))}%`,
                backgroundColor: imageUrl ? undefined : '#134e4a',
              }}
            />
          </button>
        );
      })}
    </div>
  );
};

export default RotateTiles;
