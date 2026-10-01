/**
 * Anteprima allarme staff: stesso schema della plancia (campione + voce TTS).
 * Logica allineata a frontend-pilot/src/pilotAlerts.js (speakAllarmeEquipaggio).
 */

const ALARM_SAMPLE_IDS = ['giallo', 'rosso', 'nero', 'blu', 'crociera'];
const MIST_GLIDER_RE = /mist\s+g[li]d[e]?r/i;
const FEMALE_VOICE_HINTS = /female|femmin|elsa|alice|chiara|paola|silvia|elena|sara|zira|samantha|karen|victoria|fiona/i;
const MALE_VOICE_HINTS = /male|masch|diego|luca|cosimo|risto|marco|andrea|james|david|fred|daniel/i;

let voicesReadyPromise = null;
let activeBedStop = null;
let previewGeneration = 0;

function delay(ms) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, ms);
  });
}

/** URL campione: remoto staff, oppure statico storico per i cinque colori. */
export function resolveStaffAlarmSampleUrl(allarmeId, remoteUrl = '') {
  const remote = String(remoteUrl || '').trim();
  if (remote) return remote;
  const id = String(allarmeId || '').toLowerCase();
  if (!ALARM_SAMPLE_IDS.includes(id)) return '';
  return `/pilot/sounds/allarmi/${id}.mp3`;
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
    if (pick()) return undefined;
    const onChange = () => {
      if (pick()) {
        window.speechSynthesis.removeEventListener('voiceschanged', onChange);
      }
    };
    window.speechSynthesis.addEventListener('voiceschanged', onChange);
    window.setTimeout(() => resolve(window.speechSynthesis.getVoices()), 400);
    return undefined;
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

function stopBed() {
  if (activeBedStop) {
    activeBedStop();
    activeBedStop = null;
  }
}

/** Ferma anteprima in corso (voce + campione). */
export function stopAlarmPreview() {
  previewGeneration += 1;
  if (typeof window !== 'undefined' && window.speechSynthesis) {
    window.speechSynthesis.cancel();
  }
  stopBed();
}

function playSampleOnce(url, volume = 1) {
  if (!url || typeof window === 'undefined') return Promise.resolve();
  const audio = new Audio(url);
  audio.preload = 'auto';
  audio.loop = false;
  audio.volume = Math.max(0, Math.min(1, volume));
  return new Promise((resolve) => {
    const finish = () => {
      audio.onended = null;
      audio.onerror = null;
      try {
        audio.pause();
      } catch (_) {
        /* ignore */
      }
      resolve();
    };
    audio.onended = finish;
    audio.onerror = finish;
    audio.play().catch(finish);
  });
}

function startSampleBed(url, volume = 0.5) {
  if (!url || typeof window === 'undefined') return () => {};
  stopBed();
  const audio = new Audio(url);
  audio.preload = 'auto';
  audio.loop = true;
  audio.volume = Math.max(0, Math.min(1, volume));
  const stop = () => {
    try {
      audio.pause();
      audio.currentTime = 0;
      audio.loop = false;
    } catch (_) {
      /* ignore */
    }
    if (activeBedStop === stop) activeBedStop = null;
  };
  audio.play().catch(() => {});
  activeBedStop = stop;
  return stop;
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
 * Anteprima: campione (se c'è) poi voce, come sulla plancia.
 * @param {{ allarmeId: string, testo: string, campioneUrl?: string }} opts
 */
export async function previewAlarmAnnouncement({
  allarmeId,
  testo,
  campioneUrl = '',
} = {}) {
  if (typeof window === 'undefined') return;
  const text = String(testo || '').trim();
  if (!text) return;

  const gen = ++previewGeneration;
  stopBed();
  if (window.speechSynthesis) window.speechSynthesis.cancel();

  const alarmId = String(allarmeId || '').toLowerCase();
  const isRed = alarmId === 'rosso';
  const sampleUrl = resolveStaffAlarmSampleUrl(alarmId, campioneUrl);

  let stopLocalBed = null;
  try {
    if (sampleUrl) {
      if (isRed) {
        stopLocalBed = startSampleBed(sampleUrl, 0.5);
        await delay(280);
      } else {
        await playSampleOnce(sampleUrl);
        await delay(120);
      }
    }
    if (gen !== previewGeneration) return;
    if (!window.speechSynthesis) return;

    const voices = await ensureVoices();
    if (gen !== previewGeneration) return;
    const italianVoice = pickVoice(voices, 'it', { female: true });
    const englishVoice = pickVoice(voices, 'en', { female: true });
    const segments = splitAnnouncementSegments(text);
    const alarmRate = alarmId && alarmId !== 'crociera' ? 0.8 : 0.84;
    const pauseMs = alarmId ? 480 : 360;

    for (let i = 0; i < segments.length; i += 1) {
      if (gen !== previewGeneration) return;
      const seg = segments[i];
      const isEnglish = seg.lang === 'en-US';
      await speakSegment(seg.text, {
        lang: seg.lang,
        rate: isEnglish ? 0.88 : alarmRate,
        pitch: isEnglish ? 1.02 : 1.1,
        voice: isEnglish ? englishVoice : italianVoice,
      });
      if (i < segments.length - 1) await delay(pauseMs);
    }
  } finally {
    if (stopLocalBed) stopLocalBed();
  }
}
