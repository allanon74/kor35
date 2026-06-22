/** Query @mention attiva subito prima del cursore (dopo inizio testo o spazio). */
const ACTIVE_MENTION_REGEX = /(^|[\s])@([A-Za-z0-9_]{0,30})$/;

/**
 * Trova un @mention in corso di digitazione alla posizione del cursore.
 * @returns {{ query: string, atIndex: number, endIndex: number } | null}
 */
export function findActiveMention(text, cursorPos) {
  const len = String(text || '').length;
  const pos = Math.max(0, Math.min(cursorPos ?? len, len));
  const before = String(text || '').slice(0, pos);
  const match = before.match(ACTIVE_MENTION_REGEX);
  if (!match) return null;
  const atIndex = before.lastIndexOf('@');
  if (atIndex < 0) return null;
  return { query: match[2], atIndex, endIndex: pos };
}

/**
 * Sostituisce il @mention parziale al cursore con il testo finale (es. `@123 `).
 */
export function replaceActiveMention(text, cursorPos, replacement) {
  const active = findActiveMention(text, cursorPos);
  if (!active) {
    const next = `${text || ''}${replacement}`;
    return { text: next, cursorPos: next.length };
  }
  const nextText =
    String(text || '').slice(0, active.atIndex) + replacement + String(text || '').slice(active.endIndex);
  return { text: nextText, cursorPos: active.atIndex + replacement.length };
}
