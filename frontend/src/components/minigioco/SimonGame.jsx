import React, { useEffect, useState, useRef } from 'react';

const COLORS = [
  'bg-red-600 border-red-400',
  'bg-blue-600 border-blue-400',
  'bg-amber-500 border-amber-300',
  'bg-emerald-600 border-emerald-400',
  'bg-violet-600 border-violet-400',
  'bg-pink-600 border-pink-400',
];

const softVibrate = (ms = 30) => {
  try {
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(ms);
  } catch {
    /* ignore */
  }
};

const SimonGame = ({
  numButtons = 4,
  sequence = [],
  playerInput = [],
  onChange,
  onPhaseChange,
}) => {
  const [lit, setLit] = useState(-1);
  const [phase, setPhase] = useState('demo');
  const [demoKey, setDemoKey] = useState(0);
  const [errorFlash, setErrorFlash] = useState(false);
  const cancelRef = useRef(null);

  useEffect(() => {
    onPhaseChange?.(phase);
  }, [phase, onPhaseChange]);

  useEffect(() => {
    if (!sequence?.length) return undefined;
    let cancelled = false;
    cancelRef.current = () => {
      cancelled = true;
    };

    const run = async () => {
      setPhase('demo');
      setErrorFlash(false);
      onChange?.({ player_input: [] });
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
    // eslint-disable-next-line react-hooks/exhaustive-deps -- replay via demoKey
  }, [sequence, demoKey]);

  const handleTap = (idx) => {
    if (phase !== 'input') return;
    softVibrate(25);
    const next = [...(playerInput || []), idx];
    onChange({ player_input: next });
    setLit(idx);
    setTimeout(() => setLit(-1), 200);
    if (next.length < sequence.length && sequence[next.length - 1] !== idx) {
      setErrorFlash(true);
      softVibrate([40, 40, 40]);
      setTimeout(() => {
        onChange({ player_input: [] });
        setErrorFlash(false);
      }, 350);
    }
  };

  const replayDemo = () => {
    if (phase === 'demo') return;
    cancelRef.current?.();
    setDemoKey((k) => k + 1);
  };

  const cols = numButtons <= 4 ? 2 : 3;

  return (
    <div className="space-y-3">
      <p className={`text-xs text-center ${errorFlash ? 'text-red-400 font-semibold' : 'text-gray-400'}`}>
        {errorFlash
          ? 'Errore — riprova'
          : phase === 'demo'
            ? 'Memorizza la sequenza…'
            : `Ripeti (${(playerInput || []).length}/${sequence.length})`}
      </p>
      <div
        className={`grid gap-2 max-w-xs mx-auto ${errorFlash ? 'animate-pulse' : ''}`}
        style={{ gridTemplateColumns: `repeat(${cols}, minmax(0, 1fr))` }}
      >
        {Array.from({ length: numButtons }, (_, i) => (
          <button
            key={i}
            type="button"
            disabled={phase !== 'input'}
            onClick={() => handleTap(i)}
            className={`aspect-square min-h-[44px] rounded-xl border-2 transition-all ${
              COLORS[i % COLORS.length]
            } ${lit === i ? 'scale-110 brightness-125 shadow-lg' : 'opacity-80'}`}
          />
        ))}
      </div>
      {phase === 'input' && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={replayDemo}
            className="text-xs px-3 py-1.5 rounded bg-gray-800 border border-gray-600 text-indigo-300"
          >
            Rivedi sequenza
          </button>
        </div>
      )}
    </div>
  );
};

export default SimonGame;
