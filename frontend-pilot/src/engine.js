/**
 * Mini-motore locale per il fallback offline.
 *
 * Quando il backend non e' raggiungibile, accumuliamo gli input del pilota
 * con il loro timestamp e calcoliamo un'evoluzione *speculativa* del DEFCON
 * basata sulle stesse regole del backend (best-effort, last-write-wins).
 *
 * Al ritorno online, l'app sincronizza chiamando in sequenza
 * `api.command(codice)` per ogni input pendente, applicando il vero
 * verdetto autoritativo del backend.
 *
 * Nota: il fallback NON e' una replica completa del motore, e' una bridge
 * UX per non lasciare la console muta in caso di rete instabile.
 */

const QUEUE_KEY = 'kor35_pilot_offline_queue';
const STATE_KEY = 'kor35_pilot_offline_state';

export function loadOfflineQueue() {
  try { return JSON.parse(localStorage.getItem(QUEUE_KEY) || '[]'); }
  catch (_) { return []; }
}
export function saveOfflineQueue(queue) {
  localStorage.setItem(QUEUE_KEY, JSON.stringify(queue));
}
export function pushOfflineCommand(codice) {
  const q = loadOfflineQueue();
  q.push({ codice, ts: Date.now() });
  saveOfflineQueue(q);
}
export function clearOfflineQueue() {
  localStorage.removeItem(QUEUE_KEY);
}

export function loadCachedState() {
  try { return JSON.parse(localStorage.getItem(STATE_KEY) || 'null'); }
  catch (_) { return null; }
}
export function saveCachedState(state) {
  if (!state) return;
  localStorage.setItem(STATE_KEY, JSON.stringify(state));
}
export function clearCachedState() {
  localStorage.removeItem(STATE_KEY);
}

/**
 * Sincronizza la coda offline col backend.
 * Ritorna { applicati, errori }.
 */
export async function flushOfflineQueue(apiClient) {
  const queue = loadOfflineQueue();
  if (!queue.length) return { applicati: 0, errori: 0 };
  let applicati = 0;
  let errori = 0;
  for (const item of queue) {
    try {
      await apiClient.command(item.codice);
      applicati += 1;
    } catch (_) {
      errori += 1;
    }
  }
  clearOfflineQueue();
  return { applicati, errori };
}
