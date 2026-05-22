/**
 * Cache locale dello stato di gioco del personaggio (ultimo snapshot da API),
 * per la scheda Gioco quando non c'è rete o il dettaglio non è ancora caricato.
 * Usa IndexedDB con fallback su localStorage.
 */

const DB_NAME = 'kor35_offline_game_state';
const DB_VERSION = 1;
const STORE = 'snapshots';
const LS_PREFIX = 'kor35_offline_gs:';

function lsGet(personaggioId) {
  try {
    const raw = localStorage.getItem(LS_PREFIX + String(personaggioId));
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o !== 'object') return null;
    return { snapshot: o.snapshot, stored_at: o.stored_at || null };
  } catch {
    return null;
  }
}

function lsPut(personaggioId, snapshot) {
  const row = {
    snapshot,
    stored_at: new Date().toISOString(),
  };
  localStorage.setItem(LS_PREFIX + String(personaggioId), JSON.stringify(row));
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

/**
 * @param {string} personaggioId
 * @param {unknown} snapshot
 * @returns {Promise<void>}
 */
export async function putOfflineGameStateSnapshot(personaggioId, snapshot) {
  const id = String(personaggioId || '');
  if (!id) return;
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
      tx.onerror = () => reject(tx.error || new Error('IDB tx'));
      tx.onabort = () => reject(tx.error || new Error('IDB tx abort'));
      tx.objectStore(STORE).put({
        personaggio_id: id,
        snapshot,
        stored_at: new Date().toISOString(),
      });
    });
  } catch {
    lsPut(id, snapshot);
  }
}

/**
 * @param {string} personaggioId
 * @returns {Promise<{ snapshot: unknown, stored_at: string | null } | null>}
 */
export async function getOfflineGameStateSnapshot(personaggioId) {
  const id = String(personaggioId || '');
  if (!id) return null;
  try {
    const db = await openDb();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      tx.onerror = () => reject(tx.error || new Error('IDB read'));
      const req = tx.objectStore(STORE).get(id);
      req.onsuccess = () => resolve(req.result || null);
      req.onerror = () => reject(req.error || new Error('IDB get'));
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
      };
    });
    if (!row) return lsGet(id);
    return { snapshot: row.snapshot, stored_at: row.stored_at || null };
  } catch {
    return lsGet(id);
  }
}
