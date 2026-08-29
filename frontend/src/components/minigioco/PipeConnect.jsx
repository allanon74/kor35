import React, { useMemo } from 'react';
import { pipeReachableFrom, rotatePipeMask } from './pipeHelpers';

const PipeCell = ({ conn, isStart, isEnd, reachable, solved }) => {
  const has = (bit) => Boolean(conn & bit);
  const lineColor = solved ? 'bg-emerald-400' : reachable ? 'bg-cyan-300' : 'bg-cyan-600/70';
  const line = `absolute ${lineColor}`;
  return (
    <div
      className={`relative w-full h-full ${
        solved
          ? 'bg-emerald-900/50'
          : reachable
            ? 'bg-cyan-950/90'
            : 'bg-gray-900/80'
      }`}
    >
      {has(1) && <div className={`${line} left-1/2 top-0 w-1.5 h-1/2 -translate-x-1/2`} />}
      {has(2) && <div className={`${line} right-0 top-1/2 h-1.5 w-1/2 -translate-y-1/2`} />}
      {has(4) && <div className={`${line} left-1/2 bottom-0 w-1.5 h-1/2 -translate-x-1/2`} />}
      {has(8) && <div className={`${line} left-0 top-1/2 h-1.5 w-1/2 -translate-y-1/2`} />}
      {isStart && (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-emerald-300 drop-shadow">
          A
        </span>
      )}
      {isEnd && (
        <span className="absolute inset-0 flex items-center justify-center text-xs font-bold text-amber-300 drop-shadow">
          B
        </span>
      )}
    </div>
  );
};

const PipeConnect = ({ size = 4, bases = [], rotations = [], start = 0, end = 15, onChange }) => {
  const conns = useMemo(
    () => (bases || []).map((b, i) => rotatePipeMask(Number(b) || 0, Number(rotations?.[i]) || 0)),
    [bases, rotations]
  );

  const reachable = useMemo(
    () => pipeReachableFrom(size, bases, rotations, start),
    [size, bases, rotations, start]
  );
  const solved = reachable.has(end);

  const rotateAt = (idx) => {
    const next = [...(rotations || [])];
    while (next.length < size * size) next.push(0);
    next[idx] = ((Number(next[idx]) || 0) + 1) % 4;
    onChange({ rotations: next });
  };

  const gapClass = size >= 5 ? 'gap-1.5' : 'gap-1';

  return (
    <div className="space-y-2">
      <p className="text-xs text-center text-gray-400">
        Ruota i tubi per collegare <span className="text-emerald-400 font-semibold">A</span>
        {' → '}
        <span className="text-amber-400 font-semibold">B</span>
        {solved ? ' — collegato!' : ''}
      </p>
      <div
        className={`grid ${gapClass} w-full max-w-xs mx-auto aspect-square`}
        style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: size * size }, (_, i) => {
          const isReach = reachable.has(i);
          return (
            <button
              key={i}
              type="button"
              onClick={() => rotateAt(i)}
              className={`aspect-square min-h-[28px] rounded border overflow-hidden active:scale-95 ${
                solved && isReach
                  ? 'border-emerald-400'
                  : isReach
                    ? 'border-cyan-500/80'
                    : 'border-gray-600'
              }`}
            >
              <PipeCell
                conn={conns[i] || 0}
                isStart={i === start}
                isEnd={i === end}
                reachable={isReach}
                solved={solved && isReach}
              />
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default PipeConnect;
