/**
 * Cache wiki offline (A2 + menu indice):
 * - pages: JSON pagine visitate
 * - menu: flat list indice sidebar
 */

const DB_NAME = 'kor35_offline_wiki';
const DB_VERSION = 2;
const STORE_PAGES = 'pages';
const STORE_MENU = 'menu';
const MENU_KEY = 'flat';
const LS_PREFIX = 'kor35_offline_wiki:';
const LS_MENU = 'kor35_offline_wiki_menu';

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
      if (!db.objectStoreNames.contains(STORE_PAGES)) {
        db.createObjectStore(STORE_PAGES, { keyPath: 'slug' });
      }
      if (!db.objectStoreNames.contains(STORE_MENU)) {
        db.createObjectStore(STORE_MENU, { keyPath: 'id' });
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
      const tx = db.transaction(STORE_PAGES, 'readwrite');
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
        resolve();
      };
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE_PAGES).put({
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
      const tx = db.transaction(STORE_PAGES, 'readonly');
      const req = tx.objectStore(STORE_PAGES).get(key);
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

export async function putOfflineWikiMenu(flatList) {
  const items = Array.isArray(flatList) ? flatList : [];
  try {
    const db = await openDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MENU, 'readwrite');
      tx.oncomplete = () => {
        try {
          db.close();
        } catch {
          /* ignore */
        }
        resolve();
      };
      tx.onerror = () => reject(tx.error);
      tx.objectStore(STORE_MENU).put({
        id: MENU_KEY,
        items,
        stored_at: new Date().toISOString(),
      });
    });
  } catch {
    try {
      localStorage.setItem(
        LS_MENU,
        JSON.stringify({ items, stored_at: new Date().toISOString() })
      );
    } catch {
      /* quota */
    }
  }
}

export async function getOfflineWikiMenu() {
  try {
    const db = await openDb();
    const row = await new Promise((resolve, reject) => {
      const tx = db.transaction(STORE_MENU, 'readonly');
      const req = tx.objectStore(STORE_MENU).get(MENU_KEY);
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
    return { items: row.items || [], stored_at: row.stored_at || null };
  } catch {
    try {
      const raw = localStorage.getItem(LS_MENU);
      if (!raw) return null;
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }
}

/** Filtra flat menu per ricerca locale (offline / cache hit). */
export function filterWikiMenuBySearch(flatList, term, { hideAdminContent = false, canEdit = false } = {}) {
  const q = String(term || '').trim().toLowerCase();
  if (!q) return [];
  const list = Array.isArray(flatList) ? flatList : [];
  return list.filter((i) => {
    if (!String(i?.titolo || '').toLowerCase().includes(q)) return false;
    if (hideAdminContent && canEdit) {
      if (i.public === false || i.visibile_solo_staff === true) return false;
    }
    return true;
  });
}
