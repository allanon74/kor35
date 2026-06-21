/** Audio e sintesi vocale per alert console pilota (Web Audio + speechSynthesis). */

let sharedCtx = null;

export function getPilotAudioContext() {
  if (typeof window === 'undefined') return null;
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return null;
  if (!sharedCtx) sharedCtx = new AudioCtx();
  if (sharedCtx.state === 'suspended') {
    sharedCtx.resume().catch(() => {});
  }
  return sharedCtx;
}

export function playTone({
  frequency = 440,
  duration = 0.12,
  type = 'sine',
  gain = 0.04,
  when = 0,
} = {}) {
  const ctx = getPilotAudioContext();
  if (!ctx) return;
  const t0 = ctx.currentTime + when;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = type;
  osc.frequency.value = frequency;
  g.gain.setValueAtTime(gain, t0);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + duration);
  osc.connect(g);
  g.connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

/** Avviso soft quando compare un evento non critico. */
export function playMinorEventAlert() {
  playTone({ frequency: 587, duration: 0.09, type: 'sine', gain: 0.028 });
  playTone({ frequency: 740, duration: 0.11, type: 'sine', gain: 0.022, when: 0.1 });
}

/** Burst iniziale evento critico (loop continuo gestito dal componente). */
export function playCriticalEventBurst() {
  playTone({ frequency: 280, duration: 0.18, type: 'square', gain: 0.038 });
  playTone({ frequency: 220, duration: 0.22, type: 'square', gain: 0.042, when: 0.14 });
  playTone({ frequency: 280, duration: 0.18, type: 'square', gain: 0.038, when: 0.32 });
}

/** Un colpo del loop allarme evento critico. */
export function playCriticalEventAlarmTick(alternate = false) {
  playTone({
    frequency: alternate ? 880 : 520,
    duration: 0.14,
    type: 'square',
    gain: 0.032,
  });
  playTone({
    frequency: alternate ? 660 : 390,
    duration: 0.16,
    type: 'square',
    gain: 0.028,
    when: 0.12,
  });
}

export function announceDefconChange(level) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  const n = Number(level);
  if (!Number.isFinite(n)) return;
  window.speechSynthesis.cancel();
  const utter = new SpeechSynthesisUtterance(`Passaggio a DEFCON ${n}`);
  utter.lang = 'it-IT';
  utter.rate = 0.92;
  utter.pitch = 0.85;
  utter.volume = 1;
  window.speechSynthesis.speak(utter);
}
