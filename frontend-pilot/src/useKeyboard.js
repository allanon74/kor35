import { useEffect, useRef, useState } from 'react';

/**
 * Hook tastiera esclusiva.
 *
 * - In viaggio (`enabled=true`) ascolta solo: A-Z, 0-9 (input codici),
 *   Backspace (clear ultimo char), Enter (invio codice).
 * - Riempie un buffer di esattamente 3 caratteri (i primi 2 alfanumerici,
 *   il 3o numerico). Quando raggiunge 3 char invoca `onSubmit` automatico.
 * - Tutti gli altri tasti vengono ignorati e il default e' prevenuto.
 */
export function useExclusiveKeyboard({ enabled, onSubmit }) {
  const [buffer, setBuffer] = useState('');
  const onSubmitRef = useRef(onSubmit);
  onSubmitRef.current = onSubmit;

  useEffect(() => {
    if (!enabled) return;
    const handler = (ev) => {
      const k = ev.key;
      if (k === 'Backspace') {
        ev.preventDefault();
        setBuffer((b) => b.slice(0, -1));
        return;
      }
      if (k === 'Enter') {
        ev.preventDefault();
        setBuffer((b) => {
          if (b.length === 3 && onSubmitRef.current) {
            onSubmitRef.current(b);
            return '';
          }
          return b;
        });
        return;
      }
      if (/^[a-zA-Z0-9]$/.test(k)) {
        ev.preventDefault();
        setBuffer((b) => {
          if (b.length >= 3) return b;
          const ch = k.toUpperCase();
          const idx = b.length;
          if (idx < 2 && /[A-Z0-9]/.test(ch)) {
            const next = b + ch;
            if (next.length === 3) {
              setTimeout(() => {
                if (onSubmitRef.current) onSubmitRef.current(next);
              }, 0);
              return '';
            }
            return next;
          }
          if (idx === 2 && /[0-9]/.test(ch)) {
            const next = b + ch;
            setTimeout(() => {
              if (onSubmitRef.current) onSubmitRef.current(next);
            }, 0);
            return '';
          }
          return b;
        });
        return;
      }
      ev.preventDefault();
    };
    window.addEventListener('keydown', handler, { capture: true });
    return () => window.removeEventListener('keydown', handler, { capture: true });
  }, [enabled]);

  return { buffer, reset: () => setBuffer('') };
}
