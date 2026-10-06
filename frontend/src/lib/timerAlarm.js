/**
 * Allarme scadenza timer.
 * L'AudioContext si sblocca al primo tocco (i browser bloccano l'audio senza gesto).
 * Alla scadenza si suona in locale: non serve un sync di rete ogni secondo.
 */

let audioCtx = null;
let unlockInstalled = false;

function getAudioContext() {
  const Ctx = window.AudioContext || window.webkitAudioContext;
  if (!Ctx) return null;
  if (!audioCtx) audioCtx = new Ctx();
  return audioCtx;
}

export function installTimerAlarmUnlock() {
  if (unlockInstalled || typeof window === 'undefined') return;
  unlockInstalled = true;
  const unlock = () => {
    try {
      const ctx = getAudioContext();
      if (ctx && ctx.state === 'suspended') ctx.resume();
    } catch {
      /* il gesto arriverà più tardi */
    }
  };
  window.addEventListener('pointerdown', unlock, { passive: true });
  window.addEventListener('keydown', unlock);
}

export function playTimerAlarm() {
  try {
    if (typeof navigator !== 'undefined' && typeof navigator.vibrate === 'function') {
      navigator.vibrate([180, 80, 180, 80, 360]);
    }
  } catch {
    /* vibrate opzionale */
  }

  try {
    const ctx = getAudioContext();
    if (!ctx) throw new Error('no-audio');
    if (ctx.state === 'suspended') ctx.resume();
    const start = ctx.currentTime + 0.02;
    [0, 0.42, 0.84].forEach((offset) => {
      const osc = ctx.createOscillator();
      const gain = ctx.createGain();
      osc.type = 'square';
      osc.frequency.setValueAtTime(880, start + offset);
      gain.gain.setValueAtTime(0.0001, start + offset);
      gain.gain.exponentialRampToValueAtTime(0.22, start + offset + 0.03);
      gain.gain.exponentialRampToValueAtTime(0.0001, start + offset + 0.32);
      osc.connect(gain);
      gain.connect(ctx.destination);
      osc.start(start + offset);
      osc.stop(start + offset + 0.34);
    });
    return;
  } catch {
    /* fallback file, se presente nel build */
  }

  try {
    const audio = new Audio('/sounds/alert.mp3');
    audio.play().catch(() => {});
  } catch {
    /* niente audio disponibile */
  }
}
