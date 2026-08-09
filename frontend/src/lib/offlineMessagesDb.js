/**
 * Cache lettura messaggi inbox (A4) — IndexedDB + fallback localStorage.
 */

const DB_NAME = 'kor35_offline_messages';
const DB_VERSION = 1;
const STORE = 'inbox';
const LS_PREFIX = 'kor35_offline_msgs:';

function lsGet(personaggioId) {
  try {
    const raw = localStorage.getItem(LS_PREFIX + String(personaggioId));
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o !== 'object') return null;
    return { messages: o.messages || [], stored_at: o.stored_at || null };
  } catch {
    return null;
  }
}

function lsPut(personaggioId, messages) {
  localStorage.setItem(
    LS_PREFIX + String(personaggioId),
    JSON.stringify({ messages, stored_at: new Date().toISOString() })
  );
}

function openDb() {
  return new Promise((resolve, reject) => {
    if (typeof indexedDB === 'undefined') {
      reject(new Error('indexedDB unavailable'));
      return;
    }
    const req = indexedDB.open(DB_NAME, DB_VERSION);
    req.onerror = () => reject(req.error || new Error('IDB open failed'));
    req.onsuccess = () => resolve(req.result);
    req.onupgradeneeded = (ev) => {
      const db = ev.target.result;
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'personaggio_id' });
      }
    };
  });
}

export async function putOfflineMessages(personaggioId, messages) {
  const id = String(personaggioId || '');
  if (!id) return;
  const payload = Array.isArray(messages) ? messages : [];
  try {
    const db = await openDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
        resolve();
      };
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE).put({
        personaggio_id: id,
        messages: payload,
        stored_at: new Date().toISOString(),
      });
    });
  } catch {
    lsPut(id, payload);
  }
}

export async function getOfflineMessages(personaggioId) {
  const id = String(personaggioId || '');
  if (!id) return null;
  try {
    const db = await openDb();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error);
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
      };
    });
    if (!row) return null;
    return { messages: row.messages || [], stored_at: row.stored_at || null };
  } catch {
    return lsGet(id);
  }
}
