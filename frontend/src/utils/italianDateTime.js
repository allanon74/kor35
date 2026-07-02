/** Converte yyyy-mm-dd (o ISO datetime) in gg/mm/aaaa. */
export function isoToItalianDate(iso) {
  if (!iso) return '';
  const datePart = String(iso).split('T')[0];
  const [y, m, d] = datePart.split('-');
  if (!y || !m || !d) return '';
  return `${d.padStart(2, '0')}/${m.padStart(2, '0')}/${y}`;
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

/** Converte ISO / datetime-local in «gg/mm/aaaa, hh:mm» (24h, locale). */
export function isoToItalianDateTime(iso) {
  if (!iso) return '';
  const raw = String(iso);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(raw)) {
    const [datePart, timePart] = raw.slice(0, 16).split('T');
    const [h, min] = (timePart || '').split(':');
    if (datePart && h !== undefined && min !== undefined) {
      return `${isoToItalianDate(datePart)}, ${h.padStart(2, '0')}:${min.padStart(2, '0')}`;
    }
  }
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  const day = String(d.getDate()).padStart(2, '0');
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const year = d.getFullYear();
  const hours = String(d.getHours()).padStart(2, '0');
  const minutes = String(d.getMinutes()).padStart(2, '0');
  return `${day}/${month}/${year}, ${hours}:${minutes}`;
}

/** Converte «gg/mm/aaaa, hh:mm» in yyyy-mm-ddTHH:mm; null se non valida. */
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

const pad2 = (n) => String(n).padStart(2, '0');

/** Valore per input nativo type="date" (yyyy-mm-dd). */
export function isoToNativeDateValue(iso) {
  if (!iso) return '';
  const datePart = String(iso).split('T')[0];
  if (/^\d{4}-\d{2}-\d{2}$/.test(datePart)) return datePart;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}`;
}

/** Valore per input nativo type="datetime-local" (yyyy-mm-ddTHH:mm, locale). */
export function isoToNativeDateTimeLocalValue(iso) {
  if (!iso) return '';
  const raw = String(iso);
  if (/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}$/.test(raw.slice(0, 16))) return raw.slice(0, 16);
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return '';
  return `${d.getFullYear()}-${pad2(d.getMonth() + 1)}-${pad2(d.getDate())}T${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

/** Valore per input nativo type="time" (HH:mm). */
export function isoToNativeTimeValue(time) {
  if (!time) return '';
  const [h, m] = String(time).split(':');
  if (h === undefined || m === undefined) return '';
  return `${pad2(h)}:${pad2(m)}`;
}
