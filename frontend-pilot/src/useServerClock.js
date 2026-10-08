import { useEffect, useRef, useState } from 'react';
import { anchoredRemainingSeconds, clockOffsetMs } from './serverClock.js';

export function useTickingNow(intervalMs = 250) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), intervalMs);
    return () => clearInterval(id);
  }, [intervalMs]);
  return now;
}

/** Ora di gioco: orologio del nodo + tempo trascorso sul device dal campione. */
export function useGameNow(serverTimeIso, clientNow) {
  const sampleRef = useRef({ iso: '', offset: 0 });
  if (!serverTimeIso) {
    sampleRef.current = { iso: '', offset: 0 };
  } else if (sampleRef.current.iso !== serverTimeIso) {
    sampleRef.current = {
      iso: serverTimeIso,
      offset: clockOffsetMs(serverTimeIso, clientNow),
    };
  }
  return clientNow + sampleRef.current.offset;
}

/**
 * Parte da `baseSeconds` (calcolati sul server) e scala solo i millisecondi
 * locali passati da quando quel campione è arrivato.
 */
export function useAnchoredSeconds(baseSeconds, sampleKey, clientNow) {
  const anchorRef = useRef(null);
  const base = Number(baseSeconds);
  const usable = baseSeconds != null && baseSeconds !== '' && Number.isFinite(base);
  const key = usable ? `${sampleKey ?? ''}|${base}` : '';
  if (!key) {
    anchorRef.current = null;
  } else if (!anchorRef.current || anchorRef.current.key !== key) {
    anchorRef.current = { key, at: clientNow, base };
  }
  if (!anchorRef.current) return null;
  return anchoredRemainingSeconds(anchorRef.current.base, anchorRef.current.at, clientNow);
}
