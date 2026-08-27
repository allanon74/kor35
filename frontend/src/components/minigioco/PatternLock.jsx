import React, { useEffect, useState, useRef, useCallback } from 'react';

const softVibrate = (ms = 30) => {
  try {
    if (typeof navigator !== 'undefined' && navigator.vibrate) navigator.vibrate(ms);
  } catch {
    /* ignore */
  }
};

const PatternLock = ({ pattern = [], playerInput = [], onChange, onPhaseChange }) => {
  const [phase, setPhase] = useState('demo');
  const [litPath, setLitPath] = useState([]);
  const [dragPath, setDragPath] = useState([]);
  const [demoKey, setDemoKey] = useState(0);
  const [errorFlash, setErrorFlash] = useState(false);
  const dragging = useRef(false);
  const dragPathRef = useRef([]);
  const gridRef = useRef(null);

  useEffect(() => {
    onPhaseChange?.(phase);
  }, [phase, onPhaseChange]);

  useEffect(() => {
    if (!pattern?.length) return undefined;
    let cancelled = false;
    const run = async () => {
      setPhase('demo');
      setLitPath([]);
      setDragPath([]);
      setErrorFlash(false);
      onChange?.({ player_input: [] });
      await new Promise((r) => setTimeout(r, 300));
      for (let i = 0; i < pattern.length; i += 1) {
        if (cancelled) return;
        setLitPath(pattern.slice(0, i + 1));
        await new Promise((r) => setTimeout(r, 350));
      }
      await new Promise((r) => setTimeout(r, 500));
      if (!cancelled) {
        setLitPath([]);
        setPhase('input');
      }
    };
    run();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- replay via demoKey
  }, [pattern, demoKey]);

  const nodeAt = useCallback((clientX, clientY) => {
    const grid = gridRef.current;
    if (!grid) return null;
    const cells = grid.querySelectorAll('[data-node]');
    for (const el of cells) {
      const rect = el.getBoundingClientRect();
      const pad = 8;
      if (
        clientX >= rect.left - pad &&
        clientX <= rect.right + pad &&
        clientY >= rect.top - pad &&
        clientY <= rect.bottom + pad
      ) {
        return Number(el.dataset.node);
      }
    }
    return null;
  }, []);

  const neighbors = (idx) => {
    const r = Math.floor(idx / 3);
    const c = idx % 3;
    const out = [];
    for (let dr = -1; dr <= 1; dr += 1) {
      for (let dc = -1; dc <= 1; dc += 1) {
        if (dr === 0 && dc === 0) continue;
        const nr = r + dr;
        const nc = c + dc;
        if (nr >= 0 && nr < 3 && nc >= 0 && nc < 3) out.push(nr * 3 + nc);
      }
    }
    return out;
  };

  const appendNode = (idx) => {
    if (idx == null || phase !== 'input') return;
    setDragPath((prev) => {
      if (prev.includes(idx)) return prev;
      if (prev.length && !neighbors(prev[prev.length - 1]).includes(idx)) return prev;
      const next = [...prev, idx];
      dragPathRef.current = next;
      onChange({ player_input: next });
      softVibrate(20);
      return next;
    });
  };

  const onPointerDown = (e) => {
    if (phase !== 'input') return;
    dragging.current = true;
    setErrorFlash(false);
    dragPathRef.current = [];
    setDragPath([]);
    onChange({ player_input: [] });
    appendNode(nodeAt(e.clientX, e.clientY));
  };

  const onPointerMove = (e) => {
    if (!dragging.current || phase !== 'input') return;
    appendNode(nodeAt(e.clientX, e.clientY));
  };

  const onPointerUp = () => {
    if (!dragging.current) return;
    dragging.current = false;
    const path = dragPathRef.current || [];
    if (!path.length || phase !== 'input') return;
    const ok =
      path.length === pattern.length &&
      path.every((n, i) => n === pattern[i]);
    if (!ok) {
      setErrorFlash(true);
      softVibrate([40, 40, 40]);
      setTimeout(() => {
        dragPathRef.current = [];
        setDragPath([]);
        onChange({ player_input: [] });
        setErrorFlash(false);
      }, 450);
    }
  };

  const replayDemo = () => {
    if (phase === 'demo') return;
    setDemoKey((k) => k + 1);
  };

  const active = phase === 'demo' ? litPath : dragPath.length ? dragPath : playerInput || [];

  const linePoints = (path) => {
    if (!path?.length) return '';
    return path
      .map((idx) => {
        const r = Math.floor(idx / 3);
        const c = idx % 3;
        return `${12 + c * 38}%,${12 + r * 38}%`;
      })
      .join(' ');
  };

  return (
    <div className={`space-y-2 select-none touch-none ${errorFlash ? 'animate-pulse' : ''}`}>
      <p className={`text-xs text-center ${errorFlash ? 'text-red-400 font-semibold' : 'text-gray-400'}`}>
        {errorFlash
          ? 'Errore — riprova'
          : phase === 'demo'
            ? 'Memorizza il pattern…'
            : 'Disegna lo stesso percorso'}
      </p>
      <div
        ref={gridRef}
        className="relative w-full max-w-[280px] mx-auto aspect-square"
        onPointerDown={onPointerDown}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onPointerLeave={onPointerUp}
        onPointerCancel={onPointerUp}
      >
        <svg className="absolute inset-0 w-full h-full pointer-events-none" viewBox="0 0 100 100">
          <polyline
            points={linePoints(active)}
            fill="none"
            stroke="currentColor"
            strokeWidth="3"
            className={errorFlash ? 'text-red-400' : 'text-indigo-400'}
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
        <div className="grid grid-cols-3 grid-rows-3 gap-3 w-full h-full p-2">
          {Array.from({ length: 9 }, (_, i) => (
            <div
              key={i}
              data-node={i}
              className={`rounded-full border-2 min-h-[44px] min-w-[44px] flex items-center justify-center ${
                active.includes(i)
                  ? errorFlash
                    ? 'bg-red-500 border-red-300 scale-110'
                    : 'bg-indigo-500 border-indigo-300 scale-110'
                  : 'bg-gray-800 border-gray-600'
              }`}
            />
          ))}
        </div>
      </div>
      {phase === 'input' && (
        <div className="flex justify-center">
          <button
            type="button"
            onClick={replayDemo}
            className="text-xs px-3 py-1.5 rounded bg-gray-800 border border-gray-600 text-indigo-300"
          >
            Rivedi pattern
          </button>
        </div>
      )}
    </div>
  );
};

export default PatternLock;
