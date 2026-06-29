/** Audio campionati + sintesi vocale per alert console pilota. */

let voicesReadyPromise = null;
let activeAlarmBedStop = null;
let sharedCtx = null;

const ALARM_SAMPLE_IDS = ['giallo', 'rosso', 'nero', 'blu', 'crociera'];
const MIST_GLIDER_RE = /mist\s+g[li]d[e]?r/i;

const FEMALE_VOICE_HINTS = /female|femmin|elsa|alice|chiara|paola|silvia|elena|sara|zira|samantha|karen|victoria|fiona/i;
const MALE_VOICE_HINTS = /male|masch|diego|luca|cosimo|risto|marco|andrea|james|david|fred|daniel/i;

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

function alarmSampleUrl(allarmeId) {
  const id = String(allarmeId || '').toLowerCase();
  const base = import.meta.env.BASE_URL || '/pilot/';
  return `${base}sounds/allarmi/${id}.mp3`;
}

function createAlarmAudio(allarmeId) {
  const audio = new Audio(alarmSampleUrl(allarmeId));
  audio.preload = 'auto';
  return audio;
}

if (typeof window !== 'undefined') {
  ALARM_SAMPLE_IDS.forEach((id) => {
    const audio = createAlarmAudio(id);
    audio.load();
  });
}

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

/** Ferma sirena / lettore MP3 allarme in sottofondo. */
export function stopRedAlertSiren() {
  if (activeAlarmBedStop) {
    activeAlarmBedStop();
    activeAlarmBedStop = null;
  }
}

function stopAnnouncementPlayback() {
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  stopRedAlertSiren();
}

/**
 * Riproduce il campione MP3 una volta (antecedente alla voce).
 * @returns {Promise<void>}
 */
export function playAlarmSampleOnce(allarmeId, { volume = 1 } = {}) {
  if (typeof window === 'undefined') return Promise.resolve();

  const audio = createAlarmAudio(allarmeId);
  audio.loop = false;
  audio.volume = Math.max(0, Math.min(1, volume));

  return new Promise((resolve) => {
    const finish = () => {
      audio.onended = null;
      audio.onerror = null;
      audio.pause();
      resolve();
    };
    audio.onended = finish;
    audio.onerror = finish;
    audio.play().catch(finish);
  });
}

/**
 * Loop del campione MP3 in sottofondo (allarme rosso durante la voce).
 * @returns {() => void} stop
 */
export function startAlarmSampleBed(allarmeId, { volume = 0.52 } = {}) {
  if (typeof window === 'undefined') return () => {};

  stopRedAlertSiren();

  const audio = createAlarmAudio(allarmeId);
  audio.loop = true;
  audio.volume = Math.max(0, Math.min(1, volume));

  const stop = () => {
    try {
      audio.pause();
      audio.currentTime = 0;
      audio.loop = false;
    } catch (_) {
      // già fermato
    }
    if (activeAlarmBedStop === stop) {
      activeAlarmBedStop = null;
    }
  };

  audio.play().catch(() => {});
  activeAlarmBedStop = stop;
  return stop;
}

/** Compat: stinger MP3 prima della voce (non usato per rosso in loop). */
export function playAlarmStinger(allarmeId) {
  const id = String(allarmeId || '').toLowerCase();
  if (id === 'rosso') {
    const stop = startAlarmSampleBed('rosso');
    return delay(1200).then(() => stop());
  }
  return playAlarmSampleOnce(id);
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
    if (!text || typeof window === 'undefined' || !window.speechSynthesis) {
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
 * Campione MP3 dell'allarme + annuncio vocale femminile accodato.
 * @param {string} text
 * @param {{ allarme?: string, playSample?: boolean, pauseMs?: number }} [options]
 */
export async function speakItalianAnnouncement(text, options = {}) {
  if (typeof window === 'undefined' || !text) return;

  const {
    allarme = null,
    playSample = Boolean(allarme),
    pauseMs = allarme ? 480 : 360,
  } = options;
  const alarmId = String(allarme || '').toLowerCase();
  const isRedAlert = alarmId === 'rosso';

  stopAnnouncementPlayback();

  let stopBed = null;

  if (playSample && alarmId && ALARM_SAMPLE_IDS.includes(alarmId)) {
    if (isRedAlert) {
      stopBed = startAlarmSampleBed('rosso', { volume: 0.5 });
      await delay(280);
    } else {
      await playAlarmSampleOnce(alarmId);
      await delay(120);
    }
  }

  if (!window.speechSynthesis) {
    if (stopBed) stopBed();
    return;
  }

  const [italianVoice, englishVoice] = await Promise.all([
    pickItalianFemaleVoice(),
    pickEnglishFemaleVoice(),
  ]);

  const segments = splitAnnouncementSegments(text);
  const alarmRate = allarme && allarme !== 'crociera' ? 0.8 : 0.84;

  try {
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
  } finally {
    if (stopBed) {
      stopBed();
    }
  }
}

/** Annuncio allarme equipaggio: MP3 + voce. */
export function speakAllarmeEquipaggio(text, allarmeId) {
  return speakItalianAnnouncement(text, { allarme: allarmeId, playSample: true });
}

export async function announceDefconChange(level) {
  if (typeof window === 'undefined' || !window.speechSynthesis) return;
  const n = Number(level);
  if (!Number.isFinite(n)) return;
  stopAnnouncementPlayback();
  const voice = await pickItalianFemaleVoice();
  await speakSegment(`Passaggio a DEFCON ${n}`, {
    lang: 'it-IT',
    rate: 0.86,
    pitch: 1.08,
    voice,
  });
}
