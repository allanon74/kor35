import React, { useMemo } from 'react';

const rotateMask = (mask, times) => {
  let conn = mask & 15;
  for (let t = 0; t < (times % 4); t += 1) {
    let next = 0;
    if (conn & 1) next |= 2;
    if (conn & 2) next |= 4;
    if (conn & 4) next |= 8;
    if (conn & 8) next |= 1;
    conn = next;
  }
  return conn;
};

const PipeCell = ({ conn, isStart, isEnd }) => {
  const has = (bit) => Boolean(conn & bit);
  const line = 'absolute bg-cyan-400';
  return (
    <div className="relative w-full h-full bg-gray-900/80">
      {has(1) && <div className={`${line} left-1/2 top-0 w-1 h-1/2 -translate-x-1/2`} />}
      {has(2) && <div className={`${line} right-0 top-1/2 h-1 w-1/2 -translate-y-1/2`} />}
      {has(4) && <div className={`${line} left-1/2 bottom-0 w-1 h-1/2 -translate-x-1/2`} />}
      {has(8) && <div className={`${line} left-0 top-1/2 h-1 w-1/2 -translate-y-1/2`} />}
      {isStart && (
        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-emerald-400">
          A
        </span>
      )}
      {isEnd && (
        <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-amber-400">
          B
        </span>
      )}
    </div>
  );
};

const PipeConnect = ({ size = 4, bases = [], rotations = [], start = 0, end = 15, onChange }) => {
  const conns = useMemo(
    () => (bases || []).map((b, i) => rotateMask(Number(b) || 0, Number(rotations?.[i]) || 0)),
    [bases, rotations]
  );

  const rotateAt = (idx) => {
    const next = [...(rotations || [])];
    while (next.length < size * size) next.push(0);
    next[idx] = ((Number(next[idx]) || 0) + 1) % 4;
    onChange({ rotations: next });
  };

  return (
    <div className="space-y-2">
      <p className="text-xs text-center text-gray-400">Ruota i tubi per collegare A → B</p>
      <div
        className="grid gap-1 w-full max-w-xs mx-auto aspect-square"
        style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: size * size }, (_, i) => (
          <button
            key={i}
            type="button"
            onClick={() => rotateAt(i)}
            className="aspect-square rounded border border-gray-600 overflow-hidden active:scale-95"
          >
            <PipeCell conn={conns[i] || 0} isStart={i === start} isEnd={i === end} />
          </button>
        ))}
      </div>
    </div>
  );
};

export default PipeConnect;
