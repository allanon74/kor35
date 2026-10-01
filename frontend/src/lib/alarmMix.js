/**
 * Mix tra campione di allarme e parlato.
 * Il file parte subito; la voce entra dopo 1,5 s, in sovrapposizione.
 * Se il campione finisce prima, resta solo la frase.
 * Se la frase finisce prima, il campione resta 2 s e poi sfuma in 2 s.
 */

export const ALARM_SPEECH_LEAD_MS = 1500;
export const ALARM_TAIL_HOLD_MS = 2000;
export const ALARM_FADE_MS = 2000;

/**
 * Attesa interrompibile: se `cancelled()` diventa vero, si risolve subito.
 * @param {number} ms
 * @param {() => boolean} [cancelled]
 */
export function delayUnlessCancelled(ms, cancelled = () => false) {
  return new Promise((resolve) => {
    if (cancelled()) {
      resolve();
      return;
    }
    let settled = false;
    const finish = () => {
      if (settled) return;
      settled = true;
      clearTimeout(timer);
      clearInterval(poll);
      resolve();
    };
    const timer = setTimeout(finish, ms);
    const poll = setInterval(() => {
      if (cancelled()) finish();
    }, 40);
  });
}

/**
 * Dissolvenza lineare del volume HTMLAudioElement, poi pausa.
 * Se il file è già fermo, non fa nulla.
 * @param {HTMLAudioElement} audio
 * @param {number} durationMs
 */
export function fadeHtmlAudio(audio, durationMs) {
  const ms = Math.max(0, Number(durationMs) || 0);
  if (!audio || audio.paused || audio.ended || ms === 0) {
    try {
      audio?.pause();
    } catch (_) {
      /* già fermo */
    }
    return Promise.resolve();
  }
  const startVol = audio.volume;
  const nowFn = () => (typeof performance !== 'undefined' ? performance.now() : Date.now());
  const frame = (cb) => {
    if (typeof requestAnimationFrame === 'function') return requestAnimationFrame(cb);
    return setTimeout(() => cb(nowFn()), 16);
  };
  const t0 = nowFn();
  return new Promise((resolve) => {
    const tick = (now) => {
      if (audio.paused || audio.ended) {
        resolve();
        return;
      }
      const p = Math.min(1, (now - t0) / ms);
      audio.volume = Math.max(0, startVol * (1 - p));
      if (p >= 1) {
        try {
          audio.pause();
        } catch (_) {
          /* ignore */
        }
        resolve();
        return;
      }
      frame(tick);
    };
    frame(tick);
  });
}

/**
 * Apre un campione e lo fa partire subito (una volta, senza loop).
 * @param {string} url
 * @param {{ volume?: number, onRegisterStop?: (stop: (() => void) | null) => void }} [options]
 */
export function bindHtmlAlarmSample(url, { volume = 1, onRegisterStop } = {}) {
  let ended = false;
  let settle = () => {};
  const endedPromise = new Promise((resolve) => {
    settle = resolve;
  });
  const markEnded = () => {
    if (ended) return;
    ended = true;
    settle();
  };

  const empty = {
    ended: Promise.resolve(),
    isEnded: () => true,
    fadeOut: async () => {},
    stop: () => {},
  };

  if (!url || typeof window === 'undefined' || typeof window.Audio !== 'function') {
    markEnded();
    return empty;
  }

  const audio = new window.Audio(url);
  audio.preload = 'auto';
  audio.loop = false;
  audio.volume = Math.max(0, Math.min(1, volume));
  audio.onended = markEnded;
  audio.onerror = markEnded;
  const played = audio.play();
  if (played && typeof played.catch === 'function') {
    played.catch(() => markEnded());
  }

  const stop = () => {
    try {
      audio.pause();
      audio.currentTime = 0;
    } catch (_) {
      /* già fermo */
    }
    markEnded();
  };
  if (onRegisterStop) onRegisterStop(stop);

  return {
    ended: endedPromise,
    isEnded: () => ended || Boolean(audio.ended),
    stop,
    fadeOut: (ms) => fadeHtmlAudio(audio, ms),
  };
}

/**
 * @param {{
 *   startSample: () => {
 *     ended: Promise<void>,
 *     isEnded: () => boolean,
 *     fadeOut: (ms: number) => Promise<void>,
 *     stop: () => void,
 *   },
 *   speak: () => Promise<void>,
 *   delay: (ms: number) => Promise<void>,
 *   cancelled?: () => boolean,
 * }} session
 */
export async function mixAlarmWithSpeech({
  startSample,
  speak,
  delay,
  cancelled = () => false,
}) {
  const sample = startSample();
  try {
    await delay(ALARM_SPEECH_LEAD_MS);
    if (cancelled()) return;
    await speak();
    if (cancelled() || sample.isEnded()) return;
    let sampleFinishedDuringHold = false;
    await Promise.race([
      delay(ALARM_TAIL_HOLD_MS),
      sample.ended.then(() => {
        sampleFinishedDuringHold = true;
      }),
    ]);
    if (cancelled() || sample.isEnded() || sampleFinishedDuringHold) return;
    await sample.fadeOut(ALARM_FADE_MS);
  } finally {
    sample.stop();
  }
}
