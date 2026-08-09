/**
 * Cache locale offline (IndexedDB + fallback localStorage):
 * - snapshots: stato gioco (Game tab)
 * - details: dettaglio personaggio (Scheda / HomeTab)
 */

const DB_NAME = 'kor35_offline_game_state';
const DB_VERSION = 2;
const STORE_SNAP = 'snapshots';
const STORE_DETAIL = 'details';
const LS_PREFIX_GS = 'kor35_offline_gs:';
const LS_PREFIX_DETAIL = 'kor35_offline_detail:';

function lsGet(prefix, personaggioId) {
  try {
    const raw = localStorage.getItem(prefix + String(personaggioId));
    if (!raw) return null;
    const o = JSON.parse(raw);
    if (!o || typeof o !== 'object') return null;
    return { snapshot: o.snapshot ?? o.detail, stored_at: o.stored_at || null };
  } catch {
    return null;
  }
}

function lsPut(prefix, personaggioId, payload) {
  const row = {
    snapshot: payload,
    detail: payload,
    stored_at: new Date().toISOString(),
  };
  localStorage.setItem(prefix + String(personaggioId), JSON.stringify(row));
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
      if (!db.objectStoreNames.contains(STORE_SNAP)) {
        db.createObjectStore(STORE_SNAP, { keyPath: 'personaggio_id' });
      }
      if (!db.objectStoreNames.contains(STORE_DETAIL)) {
        db.createObjectStore(STORE_DETAIL, { keyPath: 'personaggio_id' });
      }
    };
  });
}

async function idbPut(storeName, personaggioId, payload) {
  const id = String(personaggioId || '');
  if (!id) return;
  const db = await openDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readwrite');
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
    tx.objectStore(storeName).put({
      personaggio_id: id,
      snapshot: payload,
      detail: payload,
      stored_at: new Date().toISOString(),
    });
  });
}

async function idbGet(storeName, personaggioId) {
  const id = String(personaggioId || '');
  if (!id) return null;
  const db = await openDb();
  const row = await new Promise((resolve, reject) => {
    const tx = db.transaction(storeName, 'readonly');
    tx.onerror = () => reject(tx.error || new Error('IDB read'));
    const req = tx.objectStore(storeName).get(id);
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
  if (!row) return null;
  return {
    snapshot: row.snapshot ?? row.detail,
    stored_at: row.stored_at || null,
  };
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
    await idbPut(STORE_SNAP, id, snapshot);
  } catch {
    lsPut(LS_PREFIX_GS, id, snapshot);
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
    const row = await idbGet(STORE_SNAP, id);
    if (row) return row;
    return lsGet(LS_PREFIX_GS, id);
  } catch {
    return lsGet(LS_PREFIX_GS, id);
  }
}

/**
 * Cache dettaglio personaggio (Scheda).
 * @param {string} personaggioId
 * @param {unknown} detail
 */
export async function putOfflineCharacterDetail(personaggioId, detail) {
  const id = String(personaggioId || '');
  if (!id || !detail) return;
  try {
    await idbPut(STORE_DETAIL, id, detail);
  } catch {
    lsPut(LS_PREFIX_DETAIL, id, detail);
  }
}

/**
 * @param {string} personaggioId
 * @returns {Promise<{ snapshot: unknown, stored_at: string | null } | null>}
 */
export async function getOfflineCharacterDetail(personaggioId) {
  const id = String(personaggioId || '');
  if (!id) return null;
  try {
    const row = await idbGet(STORE_DETAIL, id);
    if (row) return row;
    return lsGet(LS_PREFIX_DETAIL, id);
  } catch {
    return lsGet(LS_PREFIX_DETAIL, id);
  }
}
