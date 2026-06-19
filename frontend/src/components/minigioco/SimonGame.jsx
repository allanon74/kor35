import React, { useEffect, useState, useRef } from 'react';

const COLORS = [
  'bg-red-600 border-red-400',
  'bg-blue-600 border-blue-400',
  'bg-amber-500 border-amber-300',
  'bg-emerald-600 border-emerald-400',
  'bg-violet-600 border-violet-400',
  'bg-pink-600 border-pink-400',
];

const SimonGame = ({ numButtons = 4, sequence = [], playerInput = [], onChange }) => {
  const [lit, setLit] = useState(-1);
  const [phase, setPhase] = useState('demo');
  const playedRef = useRef(false);

  useEffect(() => {
    if (!sequence?.length || playedRef.current) return undefined;
    playedRef.current = true;
    let cancelled = false;

    const run = async () => {
      setPhase('demo');
      await new Promise((r) => setTimeout(r, 400));
      for (let i = 0; i < sequence.length; i += 1) {
        if (cancelled) return;
        setLit(sequence[i]);
        await new Promise((r) => setTimeout(r, 450));
        setLit(-1);
        await new Promise((r) => setTimeout(r, 180));
      }
      if (!cancelled) setPhase('input');
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [sequence]);

  const handleTap = (idx) => {
    if (phase !== 'input') return;
    const next = [...(playerInput || []), idx];
    onChange({ player_input: next });
    setLit(idx);
    setTimeout(() => setLit(-1), 200);
    if (next.length < sequence.length && sequence[next.length - 1] !== idx) {
      setTimeout(() => onChange({ player_input: [] }), 350);
    }
  };

  const cols = numButtons <= 4 ? 2 : 3;

  return (
    <div className="space-y-3">
      <p className="text-xs text-center text-gray-400">
        {phase === 'demo' ? 'Memorizza la sequenza…' : `Ripeti (${(playerInput || []).length}/${sequence.length})`}
      </p>
      <div
        className="grid gap-2 max-w-xs mx-auto"
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: numButtons }, (_, i) => (
          <button
            key={i}
            type="button"
            disabled={phase !== 'input'}
            onClick={() => handleTap(i)}
            className={`aspect-square rounded-xl border-2 transition-all ${
              COLORS[i % COLORS.length]
            } ${lit === i ? 'scale-110 brightness-125 shadow-lg' : 'opacity-80'}`}
          />
        ))}
      </div>
    </div>
  );
};

export default SimonGame;
