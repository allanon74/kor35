/** Audio e sintesi vocale per alert console pilota (Web Audio + speechSynthesis). */

let sharedCtx = null;
let voicesReadyPromise = null;

const MIST_GLIDER_RE = /mist\s+g[li]d[e]?r/i;

const FEMALE_VOICE_HINTS = /female|femmin|elsa|alice|chiara|paola|silvia|elena|sara|zira|samantha|karen|victoria|fiona/i;
const MALE_VOICE_HINTS = /male|masch|diego|luca|cosimo|risto|marco|andrea|james|david|fred|daniel/i;

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

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function ensureVoices() {
  if (typeof window === 'undefined' || !window.speechSynthesis) {
    return Promise.resolve([]);
  }
  if (voicesReadyPromise) return voicesReadyPromise;
  voicesReadyPromise = new Promise((resolve) => {
    const pick = () => {
      const voices = window.speechSynthesis.getVoices();
      if (voices.length) {
        resolve(voices);
        return true;
      }
      return false;
    };
    if (pick()) return;
    const onChange = () => {
      if (pick()) {
        window.speechSynthesis.removeEventListener('voiceschanged', onChange);
      }
    };
    window.speechSynthesis.addEventListener('voiceschanged', onChange);
    window.setTimeout(() => resolve(window.speechSynthesis.getVoices()), 400);
  });
  return voicesReadyPromise;
}

function pickVoice(voices, langPrefix, { female = true } = {}) {
  const pool = voices.filter((v) => String(v.lang || '').toLowerCase().startsWith(langPrefix));
  if (!pool.length) return null;

  if (female) {
    const hinted = pool.find((v) => FEMALE_VOICE_HINTS.test(v.name));
    if (hinted) return hinted;
    const notMale = pool.find((v) => !MALE_VOICE_HINTS.test(v.name));
    if (notMale) return notMale;
  }

  return pool[0];
}

async function pickItalianFemaleVoice() {
  const voices = await ensureVoices();
  return pickVoice(voices, 'it', { female: true });
}

async function pickEnglishFemaleVoice() {
  const voices = await ensureVoices();
  return pickVoice(voices, 'en', { female: true });
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

function playToneSweep({ fromHz, toHz, duration = 0.4, type = 'sine', gain = 0.035, when = 0 } = {}) {
  const ctx = getPilotAudioContext();
  if (!ctx) return;
  const t0 = ctx.currentTime + when;
  const osc = ctx.createOscillator();
  const g = ctx.createGain();
  osc.type = type;
  osc.frequency.setValueAtTime(fromHz, t0);
  osc.frequency.linearRampToValueAtTime(toHz, t0 + duration);
  g.gain.setValueAtTime(gain, t0);
  g.gain.exponentialRampToValueAtTime(0.001, t0 + duration);
  osc.connect(g);
  g.connect(ctx.destination);
  osc.start(t0);
  osc.stop(t0 + duration + 0.02);
}

/** Suono identificativo stile ponte nave (prima dell'annuncio vocale). */
export function playAlarmStinger(allarmeId) {
  const id = String(allarmeId || '').toLowerCase();
  getPilotAudioContext();

  switch (id) {
    case 'giallo':
      // Allerta gialla: coppie di toni alternati
      for (let i = 0; i < 4; i += 1) {
        const w = i * 0.42;
        playTone({ frequency: 784, duration: 0.16, type: 'triangle', gain: 0.038, when: w });
        playTone({ frequency: 587, duration: 0.16, type: 'triangle', gain: 0.034, when: w + 0.18 });
      }
      return delay(1850);

    case 'rosso':
      // Allarme rosso: klaxon rapido
      for (let i = 0; i < 5; i += 1) {
        const w = i * 0.34;
        playTone({ frequency: 440, duration: 0.14, type: 'square', gain: 0.036, when: w });
        playTone({ frequency: 330, duration: 0.14, type: 'square', gain: 0.032, when: w + 0.15 });
      }
      return delay(2100);

    case 'nero':
      // Allarme nero: risonanza profonda + tremolo acuto
      playTone({ frequency: 72, duration: 1.6, type: 'sine', gain: 0.05, when: 0 });
      for (let i = 0; i < 8; i += 1) {
        playTone({
          frequency: 1180,
          duration: 0.08,
          type: 'sine',
          gain: 0.018,
          when: 0.12 + i * 0.18,
        });
      }
      return delay(2200);

    case 'blu':
      // Allarme blu: sweep ascendente + tono di tenuta
      playToneSweep({ fromHz: 420, toHz: 988, duration: 0.55, type: 'sine', gain: 0.034, when: 0 });
      playTone({ frequency: 880, duration: 0.7, type: 'sine', gain: 0.028, when: 0.58 });
      playTone({ frequency: 660, duration: 0.5, type: 'sine', gain: 0.022, when: 1.05 });
      return delay(1750);

    case 'crociera':
      // Ripristino crociera: campanello di conferma
      playTone({ frequency: 523, duration: 0.22, type: 'sine', gain: 0.03, when: 0 });
      playTone({ frequency: 659, duration: 0.22, type: 'sine', gain: 0.028, when: 0.2 });
      playTone({ frequency: 784, duration: 0.35, type: 'sine', gain: 0.026, when: 0.42 });
      return delay(1100);

    default:
      return Promise.resolve();
  }
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

function splitAnnouncementSegments(text) {
  const raw = String(text || '').trim();
  if (!raw) return [];

  const sentences = raw.split(/(?<=\.)\s+/).filter(Boolean);
  const segments = [];

  for (const sentence of sentences) {
    if (MIST_GLIDER_RE.test(sentence)) {
      const parts = sentence.split(/(mist\s+g[li]d[e]?r)/i);
      for (const part of parts) {
        const chunk = part.trim();
        if (!chunk) continue;
        segments.push({
          text: MIST_GLIDER_RE.test(chunk) ? 'Mist Glider' : chunk,
          lang: MIST_GLIDER_RE.test(chunk) ? 'en-US' : 'it-IT',
        });
      }
    } else {
      segments.push({ text: sentence, lang: 'it-IT' });
    }
  }

  return segments;
}

function speakSegment(text, { lang = 'it-IT', rate = 0.84, pitch = 1.08, voice = null } = {}) {
  return new Promise((resolve) => {
    if (!text) {
      resolve();
      return;
    }
    const utter = new SpeechSynthesisUtterance(text);
    utter.lang = lang;
    utter.rate = rate;
    utter.pitch = pitch;
    utter.volume = 1;
    if (voice) utter.voice = voice;
    utter.onend = () => resolve();
    utter.onerror = () => resolve();
    window.speechSynthesis.speak(utter);
  });
}

/**
 * Annuncio vocale con voce femminile, pause tra le frasi e suono identificativo opzionale.
 * @param {string} text
 * @param {{ allarme?: string, playStinger?: boolean, pauseMs?: number }} [options]
 */
export async function speakItalianAnnouncement(text, options = {}) {
  if (typeof window === 'undefined' || !window.speechSynthesis || !text) return;

  const { allarme = null, playStinger = Boolean(allarme), pauseMs = allarme ? 520 : 380 } = options;

  window.speechSynthesis.cancel();

  if (playStinger && allarme) {
    await playAlarmStinger(allarme);
    await delay(180);
  }

  const [italianVoice, englishVoice] = await Promise.all([
    pickItalianFemaleVoice(),
    pickEnglishFemaleVoice(),
  ]);

  const segments = splitAnnouncementSegments(text);
  const alarmRate = allarme && allarme !== 'crociera' ? 0.8 : 0.84;

  for (let i = 0; i < segments.length; i += 1) {
    const seg = segments[i];
    const isEnglish = seg.lang === 'en-US';
    await speakSegment(seg.text, {
      lang: seg.lang,
      rate: isEnglish ? 0.88 : alarmRate,
      pitch: isEnglish ? 1.02 : 1.1,
      voice: isEnglish ? englishVoice : italianVoice,
    });
    if (i < segments.length - 1) {
      await delay(pauseMs);
    }
  }
}

/** Annuncio allarme equipaggio: stinger + voce per il tipo scelto. */
export function speakAllarmeEquipaggio(text, allarmeId) {
  return speakItalianAnnouncement(text, { allarme: allarmeId, playStinger: true });
}

export async function announceDefconChange(level) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  const n = Number(level);
  if (!Number.isFinite(n)) return;
  window.speechSynthesis.cancel();
  const voice = await pickItalianFemaleVoice();
  await speakSegment(`Passaggio a DEFCON ${n}`, {
    lang: 'it-IT',
    rate: 0.86,
    pitch: 1.08,
    voice,
  });
}
