/**
 * Coda azioni offline best-effort (IndexedDB).
 * A3: scan QR in coda → replay GET quando online (no mutazioni furto/scambio).
 * A4: compose messaggi in coda (opzionale) — di default preferiamo blocco UI.
 */

const DB_NAME = 'kor35_offline_actions';
const DB_VERSION = 1;
const STORE = 'queue';
const LS_KEY = 'kor35_offline_action_queue';

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
        const s = db.createObjectStore(STORE, { keyPath: 'id' });
        s.createIndex('by_kind', 'kind', { unique: false });
        s.createIndex('by_created', 'created_at', { unique: false });
      }
    };
  });
}

function newId() {
  if (typeof crypto !== 'undefined' && crypto.randomUUID) return crypto.randomUUID();
  return `q_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function lsRead() {
  try {
    const raw = localStorage.getItem(LS_KEY);
    const arr = raw ? JSON.parse(raw) : [];
    return Array.isArray(arr) ? arr : [];
  } catch {
    return [];
  }
}

function lsWrite(items) {
  localStorage.setItem(LS_KEY, JSON.stringify(items.slice(-40)));
}

/**
 * @param {{ kind: string, payload: object, client_key?: string }} entry
 */
export async function enqueueOfflineAction(entry) {
  const row = {
    id: newId(),
    kind: String(entry.kind || ''),
    payload: entry.payload || {},
    client_key: entry.client_key || newId(),
    created_at: new Date().toISOString(),
    status: 'pending',
  };
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
      tx.objectStore(STORE).put(row);
    });
  } catch {
    const items = lsRead();
    items.push(row);
    lsWrite(items);
  }
  return row;
}

export async function listOfflineActions(kind = null) {
  try {
    const db = await openDb();
    const rows = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result || []);
      req.onerror = () => reject(req.error);
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
      };
    });
    const list = (rows || []).filter((r) => r.status === 'pending');
    return kind ? list.filter((r) => r.kind === kind) : list;
  } catch {
    const list = lsRead().filter((r) => r.status !== 'done');
    return kind ? list.filter((r) => r.kind === kind) : list;
  }
}

export async function removeOfflineAction(id) {
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
      tx.objectStore(STORE).delete(id);
    });
  } catch {
    lsWrite(lsRead().filter((r) => r.id !== id));
  }
}

/** Tipi azione ammessi in coda (no furto/scambio). */
export const OFFLINE_ACTION_QR_SCAN = 'qr_scan';
export const OFFLINE_ACTION_MESSAGE = 'message_compose';
