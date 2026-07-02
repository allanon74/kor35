const pad2 = (n) => String(n).padStart(2, '0');

const NAIVE_DATE_RE = /^\d{4}-\d{2}-\d{2}$/;
const NAIVE_LOCAL_DATETIME_RE = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/;

/** Datetime «da form» senza offset (yyyy-mm-ddTHH:mm). */
export function isNaiveLocalDateTime(value) {
  if (!value || typeof value !== 'string') return false;
  return NAIVE_LOCAL_DATETIME_RE.test(value.trim());
}

/** Converte yyyy-mm-dd (o ISO datetime) in gg/mm/aaaa (fuso locale del browser). */
export function isoToItalianDate(iso) {
  if (!iso) return '';
  const raw = String(iso).trim();
  if (NAIVE_DATE_RE.test(raw)) {
    const [y, m, d] = raw.split('-');
    return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`;
  }
  if (isNaiveLocalDateTime(raw)) {
    return isoToItalianDate(raw.split('T')[0]);
  }
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}`;
}

/** Converte gg/mm/aaaa in yyyy-mm-dd; stringa vuota se assente, null se non valida. */
export function italianDateToIso(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return '';
  const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (!match) return null;
  const day = parseInt(match[1], 10);
  const month = parseInt(match[2], 10);
  const year = parseInt(match[3], 10);
  if (month < 1 || month > 12 || day < 1 || day > 31 || year < 1000) return null;
  const probe = new Date(year, month - 1, day);
  if (
    probe.getFullYear() !== year
    || probe.getMonth() !== month - 1
    || probe.getDate() !== day
  ) {
    return null;
  }
  return `${year}-${String(month).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
}

/** Converte ISO API / datetime-local in «gg/mm/aaaa, hh:mm» (ora locale utente). */
export function isoToItalianDateTime(iso) {
  if (!iso) return '';
  const raw = String(iso).trim();
  if (isNaiveLocalDateTime(raw)) {
    const [datePart, timePart] = raw.split('T');
    const [h, min] = (timePart || '').split(':');
    return `${isoToItalianDate(datePart)}, ${h.padStart(2, '0')}:${min.padStart(2, '0')}`;
  }
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  return `${pad2(d.getDate())}/${pad2(d.getMonth() + 1)}/${d.getFullYear()}, ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** Converte «gg/mm/aaaa, hh:mm» in yyyy-mm-ddTHH:mm locale; null se non valida. */
export function italianDateTimeToIso(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return '';
  const match = trimmed.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})\s*,\s*(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const dateIso = italianDateToIso(`${match[1]}/${match[2]}/${match[3]}`);
  if (!dateIso) return null;
  const hours = parseInt(match[4], 10);
  const minutes = parseInt(match[5], 10);
  if (hours > 23 || minutes > 59) return null;
  return `${dateIso}T${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

/** API ISO → yyyy-mm-ddTHH:mm nel fuso locale (per form / picker). */
export function apiIsoToLocalDateTimeValue(iso) {
  if (!iso) return '';
  const raw = String(iso).trim();
  if (isNaiveLocalDateTime(raw)) return raw;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/**
 * Interpreta l'orario inserito come locale (fuso del browser) e restituisce ISO UTC per Django.
 * Accetta yyyy-mm-ddTHH:mm oppure ISO già con offset/Z.
 */
export function localDateTimeToApiIso(localValue) {
  if (localValue === null || localValue === undefined || localValue === '') return null;
  const raw = String(localValue).trim();
  if (!raw) return null;
  const d = new Date(isNaiveLocalDateTime(raw) ? raw : raw);
  if (Number.isNaN(d.getTime())) return null;
  return d.toISOString();
}

/** yyyy-mm-dd (solo data) → ISO UTC mezzanotte locale. */
export function localDateToApiIso(localDate) {
  if (localDate === null || localDate === undefined || localDate === '') return null;
  const raw = String(localDate).trim();
  if (!raw) return null;
  if (NAIVE_DATE_RE.test(raw)) {
    const d = new Date(`${raw}T00:00:00`);
    if (Number.isNaN(d.getTime())) return null;
    return d.toISOString();
  }
  return localDateTimeToApiIso(raw);
}

/** Converte HH:mm[:ss] in hh:mm (24h). */
export function isoToItalianTime(time) {
  if (!time) return '';
  const [h, m] = String(time).split(':');
  if (h === undefined || m === undefined) return '';
  return `${h.padStart(2, '0')}:${m.padStart(2, '0')}`;
}

/** Converte hh:mm in HH:mm; null se non valida. */
export function italianTimeToIso(text) {
  const trimmed = String(text || '').trim();
  if (!trimmed) return '';
  const match = trimmed.match(/^(\d{1,2}):(\d{2})$/);
  if (!match) return null;
  const hours = parseInt(match[1], 10);
  const minutes = parseInt(match[2], 10);
  if (hours > 23 || minutes > 59) return null;
  return `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`;
}

/** Valore per input nativo type="date" (yyyy-mm-dd, locale). */
export function isoToNativeDateValue(iso) {
  if (!iso) return '';
  const raw = String(iso).trim();
  if (NAIVE_DATE_RE.test(raw)) return raw;
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Valore per input nativo type="datetime-local" (yyyy-mm-ddTHH:mm, locale). */
export function isoToNativeDateTimeLocalValue(iso) {
  return apiIsoToLocalDateTimeValue(iso);
}

/** Valore per input nativo type="time" (HH:mm). */
export function isoToNativeTimeValue(time) {
  if (!time) return '';
  const [h, m] = String(time).split(':');
  if (h === undefined || m === undefined) return '';
  return `${pad2(h)}:${pad2(m)}`;
}
