/**
 * Cache JSON pagine wiki visitate (A2 client-side, complementa Workbox).
 */

const DB_NAME = 'kor35_offline_wiki';
const DB_VERSION = 1;
const STORE = 'pages';
const LS_PREFIX = 'kor35_offline_wiki:';

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
        db.createObjectStore(STORE, { keyPath: 'slug' });
      }
    };
  });
}

export async function putOfflineWikiPage(slug, pageData) {
  const key = String(slug || '').trim();
  if (!key || !pageData) return;
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
        slug: key,
        page: pageData,
        stored_at: new Date().toISOString(),
      });
    });
  } catch {
    try {
      localStorage.setItem(
        LS_PREFIX + key,
        JSON.stringify({ page: pageData, stored_at: new Date().toISOString() })
      );
    } catch {
      /* quota */
    }
  }
}

export async function getOfflineWikiPage(slug) {
  const key = String(slug || '').trim();
  if (!key) return null;
  try {
    const db = await openDb();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE, 'readonly');
      const req = tx.objectStore(STORE).get(key);
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
    return { page: row.page, stored_at: row.stored_at || null };
  } catch {
    try {
      const raw = localStorage.getItem(LS_PREFIX + key);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
}
