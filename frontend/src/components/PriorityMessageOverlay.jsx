import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { getSorteggioAckPending, postSorteggioAckConferma } from '../api';
import RichTextDisplay from './RichTextDisplay';
import { isNativeApp } from '../lib/nativePlatform';

function devicePayload() {
  const nav = typeof navigator !== 'undefined' ? navigator : {};
  const screenObj = typeof window !== 'undefined' ? window.screen : null;
  return {
    platform: nav.platform || nav.userAgentData?.platform || '',
    language: nav.language || '',
    screen: screenObj ? `${screenObj.width}x${screenObj.height}` : '',
    native: isNativeApp(),
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone || '',
  };
}

/**
 * Overlay a schermo intero per messaggi staff prioritari.
 * Non si chiude finché il giocatore non conferma.
 */
export default function PriorityMessageOverlay({ personaggioId, onLogout, extraItem = null }) {
  const [coda, setCoda] = useState([]);
  const [sending, setSending] = useState(false);
  const audioRef = useRef(null);
  const loopRef = useRef(null);

  const current = extraItem || coda[0] || null;

  const loadPending = useCallback(async () => {
    if (!personaggioId) return;
    try {
      const data = await getSorteggioAckPending(personaggioId, onLogout);
      setCoda(Array.isArray(data) ? data : []);
    } catch {
      /* silenzioso: overlay non deve rompere la app */
    }
  }, [onLogout, personaggioId]);

  useEffect(() => {
    loadPending();
    const id = window.setInterval(loadPending, 12000);
    return () => window.clearInterval(id);
  }, [loadPending]);

  useEffect(() => {
    const onPrio = (ev) => {
      const item = ev.detail;
      if (!item) return;
      setCoda((prev) => {
        if (prev.some((p) => p.esito_id === item.esito_id)) return prev;
        return [...prev, item];
      });
    };
    window.addEventListener('kor35:msg-prioritario', onPrio);
    return () => window.removeEventListener('kor35:msg-prioritario', onPrio);
  }, []);

  const stopAlarm = useCallback(() => {
    if (loopRef.current) {
      window.clearInterval(loopRef.current);
      loopRef.current = null;
    }
    if (audioRef.current) {
      try {
        audioRef.current.pause();
        audioRef.current.currentTime = 0;
      } catch {
        /* ignore */
      }
    }
  }, []);

  useEffect(() => {
    if (!current) {
      stopAlarm();
      return undefined;
    }
    const play = () => {
      try {
        if (!audioRef.current) {
          audioRef.current = new Audio('/sounds/alert.mp3');
          audioRef.current.loop = false;
        }
        audioRef.current.currentTime = 0;
        audioRef.current.play().catch(() => {});
      } catch {
        /* ignore */
      }
    };
    play();
    loopRef.current = window.setInterval(play, 2500);
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      stopAlarm();
      document.body.style.overflow = prevOverflow;
    };
  }, [current, stopAlarm]);

  const conferma = async () => {
    if (!current?.esito_id || !personaggioId) return;
    setSending(true);
    try {
      await postSorteggioAckConferma(
        current.esito_id,
        { personaggio_id: personaggioId, dispositivo: devicePayload() },
        onLogout,
      );
      setCoda((prev) => prev.filter((p) => p.esito_id !== current.esito_id));
    } catch (e) {
      window.alert(e.message || 'Conferma non riuscita, riprova.');
    } finally {
      setSending(false);
    }
  };

  if (!current || typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[400] flex flex-col bg-black text-white"
      style={{ height: '100dvh' }}
      role="alertdialog"
      aria-modal="true"
      aria-labelledby="prio-msg-title"
    >
      <div className="flex-1 min-h-0 overflow-y-auto px-4 py-6 pt-[max(1.5rem,var(--kor-safe-top))]">
        <p className="text-[11px] font-black uppercase tracking-[0.25em] text-red-400 mb-3">
          Messaggio prioritario staff
        </p>
        <h1 id="prio-msg-title" className="text-2xl font-black break-words mb-4">
          {current.titolo || 'Messaggio staff'}
        </h1>
        <div className="prose prose-invert max-w-none text-base leading-relaxed">
          <RichTextDisplay content={current.testo || ''} />
        </div>
      </div>
      <div className="shrink-0 border-t border-red-900 bg-red-950/80 p-4 pb-[max(1rem,var(--kor-safe-bottom))]">
        <button
          type="button"
          disabled={sending}
          onClick={conferma}
          className="w-full min-h-14 rounded-xl bg-red-600 hover:bg-red-500 font-black text-lg uppercase tracking-wide disabled:opacity-60"
        >
          {sending ? 'Invio conferma…' : 'Ho letto e compreso.'}
        </button>
      </div>
    </div>,
    document.body,
  );
}
