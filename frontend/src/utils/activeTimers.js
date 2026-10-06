/** Chiave stabile nell'overlay: l'id istanza, altrimenti il nome (timer legacy). */
export function timerStateKey(row) {
  if (row?.id != null && String(row.id) !== '') return String(row.id);
  return String(row?.nome || row?.label || 'timer');
}

export function normalizeTimerRow(row) {
  if (!row || typeof row !== 'object') return null;
  let endTime = typeof row.endTime === 'number' ? row.endTime : null;
  const rawFine = row.data_fine || row.endsAt;
  if (rawFine) {
    const parsed = new Date(rawFine).getTime();
    if (!Number.isNaN(parsed)) endTime = parsed;
  }
  if (endTime == null || Number.isNaN(endTime)) {
    const duration = parseInt(row.duration || 0, 10) || 0;
    endTime = Date.now() + duration * 1000;
  }
  const id = row.id != null && String(row.id) !== '' ? String(row.id) : undefined;
  return {
    id,
    nome: row.nome || row.label || 'Operazione',
    endTime,
    alert_suono: row.alert_suono !== false,
    notifica_push: !!row.notifica_push,
    messaggio_in_app: row.messaggio_in_app !== false,
    segnale_luminoso: row.segnale_luminoso !== false,
    scaduto: !!row.scaduto,
    source: row.source || (id && id.startsWith('innesco:') ? 'innesco_timer' : undefined),
    variant: row.variant || undefined,
    richiede_ack: !!row.richiede_ack || !!(id && id.startsWith('innesco:')),
  };
}

/**
 * Unisce la lista letta dal server.
 * I timer innesco assenti dalla risposta (ack o non più destinatario) escono dallo stato.
 * Gli altri timer (tipologia, trappola) restano finché non scadono in locale.
 */
export function mergeActiveTimers(prev, rows) {
  const next = { ...(prev || {}) };
  const incoming = new Set();
  (Array.isArray(rows) ? rows : []).forEach((row) => {
    const normalized = normalizeTimerRow(row);
    if (!normalized) return;
    const key = timerStateKey(normalized);
    incoming.add(key);
    next[key] = {
      ...normalized,
      variant: normalized.variant || next[key]?.variant,
    };
  });
  Object.keys(next).forEach((key) => {
    if (String(key).startsWith('innesco:') && !incoming.has(key)) {
      delete next[key];
    }
  });
  return next;
}

export const TIMER_CORNERS = ['tr', 'br', 'bl', 'tl'];

export function nextTimerCorner(current) {
  const idx = TIMER_CORNERS.indexOf(current);
  const start = idx < 0 ? 0 : idx;
  return TIMER_CORNERS[(start + 1) % TIMER_CORNERS.length];
}
