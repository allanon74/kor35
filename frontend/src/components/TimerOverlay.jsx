import React, { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useSharedNowTs } from '../hooks/useSharedNowTs';
import { ackInnescoTimerScaduto } from '../api';
import { installTimerAlarmUnlock, playTimerAlarm } from '../lib/timerAlarm';
import { nextTimerCorner, TIMER_CORNERS } from '../utils/activeTimers';

const CORNER_STORAGE_KEY = 'kor35-timer-corner';

const CORNER_CLASS = {
  tr: 'top-[calc(var(--kor-safe-top,0px)+4.5rem)] right-3 items-end',
  br: 'bottom-[calc(env(safe-area-inset-bottom,0px)+5.5rem)] right-3 items-end',
  bl: 'bottom-[calc(env(safe-area-inset-bottom,0px)+5.5rem)] left-3 items-start',
  tl: 'top-[calc(var(--kor-safe-top,0px)+4.5rem)] left-3 items-start',
};

function readCorner() {
  try {
    const saved = localStorage.getItem(CORNER_STORAGE_KEY);
    if (TIMER_CORNERS.includes(saved)) return saved;
  } catch {
    /* storage non disponibile */
  }
  return 'tr';
}

const formatLeft = (seconds) => {
  const s = Math.max(0, seconds);
  const mins = Math.floor(s / 60);
  const secs = s % 60;
  return `${mins}:${secs.toString().padStart(2, '0')}`;
};

const expiryKey = (timer) => `${timer.key}|${timer.endTime}`;

const SingleTimer = ({ timer, onMove }) => {
  const nowTs = useSharedNowTs();
  const timeLeft = Math.max(0, Math.floor((timer.endTime - nowTs) / 1000));
  const isDanger = timer.variant === 'danger';
  const glow = timer.segnale_luminoso !== false;

  return (
    <button
      type="button"
      onClick={onMove}
      className={`pointer-events-auto mb-2 min-h-11 w-[min(92vw,280px)] rounded-2xl border-2 px-4 py-3 text-left text-white shadow-2xl backdrop-blur-sm ${
        isDanger
          ? 'border-red-400 bg-red-950/95 shadow-[0_0_24px_rgba(239,68,68,0.45)]'
          : 'border-amber-400 bg-gray-950/95 shadow-[0_0_22px_rgba(251,191,36,0.35)]'
      } ${glow ? 'animate-pulse' : ''}`}
      title="Tocca per spostare il timer in un altro angolo"
      aria-label={`Timer ${timer.nome}${timer.istanza ? `, ${timer.istanza}` : ''}, ${formatLeft(timeLeft)} rimanenti. Tocca per spostarlo.`}
    >
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className={`text-[10px] font-black uppercase tracking-[0.18em] ${isDanger ? 'text-red-300' : 'text-amber-300'}`}>
            {isDanger ? 'Trappola' : 'Timer'}
          </div>
          <div className="break-words text-base font-black uppercase leading-tight line-clamp-2">{timer.nome}</div>
          {timer.istanza ? (
            <div className="mt-0.5 break-words text-xs font-semibold leading-snug text-white/90 line-clamp-2">
              {timer.istanza}
            </div>
          ) : null}
        </div>
        <div className={`font-mono text-3xl font-black tabular-nums ${isDanger ? 'text-red-200' : 'text-amber-300'}`}>
          {formatLeft(timeLeft)}
        </div>
      </div>
    </button>
  );
};

export const TimerOverlay = ({ activeTimers, onRemove, personaggioId, onLogout }) => {
  const nowTs = useSharedNowTs();
  const [corner, setCorner] = useState(readCorner);
  const [modal, setModal] = useState(null);
  const dismissed = useRef(new Set());
  const alarmed = useRef(new Set());

  useEffect(() => {
    installTimerAlarmUnlock();
  }, []);

  const moveCorner = useCallback(() => {
    setCorner((prev) => {
      const next = nextTimerCorner(prev);
      try {
        localStorage.setItem(CORNER_STORAGE_KEY, next);
      } catch {
        /* ignora */
      }
      return next;
    });
  }, []);

  const running = Object.entries(activeTimers || {})
    .map(([key, timer]) => ({ key, ...timer }))
    .filter((timer) => timer.endTime > nowTs && !timer.scaduto);

  useEffect(() => {
    if (modal) return undefined;
    const due = Object.entries(activeTimers || {})
      .map(([key, timer]) => ({ key, ...timer }))
      .filter((timer) => timer.scaduto || (timer.endTime && nowTs >= timer.endTime))
      .filter((timer) => !dismissed.current.has(expiryKey(timer)));
    if (!due.length) return undefined;
    const first = due[0];
    if (first.messaggio_in_app === false) {
      dismissed.current.add(expiryKey(first));
      onRemove?.(first.key);
      return undefined;
    }
    const mark = expiryKey(first);
    if (!alarmed.current.has(mark) && first.alert_suono !== false) {
      alarmed.current.add(mark);
      playTimerAlarm();
    }
    setModal(first);
    return undefined;
  }, [activeTimers, nowTs, modal, onRemove]);

  const confirmExpired = async () => {
    if (!modal) return;
    const current = modal;
    dismissed.current.add(expiryKey(current));
    setModal(null);
    const rawId = String(current.id || current.key || '');
    if (rawId.startsWith('innesco:') && personaggioId) {
      try {
        await ackInnescoTimerScaduto(
          {
            personaggio_id: personaggioId,
            innesco_id: rawId.slice('innesco:'.length),
            id: rawId,
            data_fine: new Date(current.endTime).toISOString(),
          },
          onLogout,
        );
      } catch (err) {
        console.warn('Ack timer non registrato', err);
      }
    }
    onRemove?.(current.key);
  };

  const chip = running.length > 0 && typeof document !== 'undefined'
    ? createPortal(
      <div className={`fixed z-[180] flex max-w-[min(92vw,280px)] flex-col pointer-events-none ${CORNER_CLASS[corner] || CORNER_CLASS.tr}`}>
        {running.map((timer) => (
          <SingleTimer key={timer.key} timer={timer} onMove={moveCorner} />
        ))}
      </div>,
      document.body,
    )
    : null;

  const expiredScreen = modal && typeof document !== 'undefined'
    ? createPortal(
      <div
        className="fixed inset-0 z-[220] flex flex-col items-center justify-center bg-black/95 px-5 py-8 text-center"
        role="alertdialog"
        aria-modal="true"
        aria-labelledby="timer-scaduto-titolo"
      >
        <h1
          id="timer-scaduto-titolo"
          className="max-w-[18ch] break-words text-4xl font-black uppercase leading-tight text-red-600 sm:text-6xl"
        >
          <span className="block">Timer {modal.nome} scaduto!</span>
          {modal.istanza ? (
            <span className="mt-3 block text-3xl normal-case text-red-400 sm:text-5xl">{modal.istanza}</span>
          ) : null}
        </h1>
        <button
          type="button"
          onClick={confirmExpired}
          className="mt-10 min-h-12 min-w-36 rounded-xl bg-red-700 px-8 py-3 text-lg font-black text-white"
        >
          Ok
        </button>
      </div>,
      document.body,
    )
    : null;

  return (
    <>
      {chip}
      {expiredScreen}
    </>
  );
};

export default TimerOverlay;
