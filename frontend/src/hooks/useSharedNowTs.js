import { useEffect, useState } from 'react';

/**
 * Un unico setInterval(1s) condiviso tra tab HUD (Game, Inventario, Abilità, …).
 * Evita N timer indipendenti che forzavano re-render paralleli su Edge Wi‑Fi.
 */
let sharedNowTs = Date.now();
let intervalId = null;
const subscribers = new Set();

function ensureTicking() {
  if (intervalId != null) return;
  intervalId = window.setInterval(() => {
    sharedNowTs = Date.now();
    subscribers.forEach((notify) => {
      try {
        notify(sharedNowTs);
      } catch {
        /* noop */
      }
    });
  }, 1000);
}

function stopIfIdle() {
  if (subscribers.size > 0 || intervalId == null) return;
  window.clearInterval(intervalId);
  intervalId = null;
}

export function useSharedNowTs() {
  const [nowTs, setNowTs] = useState(sharedNowTs);

  useEffect(() => {
    const notify = (ts) => setNowTs(ts);
    subscribers.add(notify);
    ensureTicking();
    setNowTs(sharedNowTs);
    return () => {
      subscribers.delete(notify);
      stopIfIdle();
    };
  }, []);

  return nowTs;
}
