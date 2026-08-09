/**
 * Smoke test (Node) per helper offline wiki / code azioni.
 * Esegui: node frontend/scripts/smoke_offline_helpers.mjs
 *
 * Non sostituisce una prova telefono+Edge; verifica regressioni pure JS.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = dirname(fileURLToPath(import.meta.url));
const root = join(__dirname, '..');

// filterWikiMenuBySearch è puro: import dinamico del modulo (usa IndexedDB solo nelle put/get).
const wikiDbUrl = pathToFileURL(join(root, 'src/lib/offlineWikiDb.js')).href;
const { filterWikiMenuBySearch } = await import(wikiDbUrl);

const flat = [
  { id: 1, titolo: 'Ambientazione', slug: 'ambientazione', public: true },
  { id: 2, titolo: 'Regolamento base', slug: 'regolamento', public: true },
  { id: 3, titolo: 'Bozza segreta', slug: 'bozza', public: false, visibile_solo_staff: true },
];

assert.equal(filterWikiMenuBySearch(flat, 'ambi').length, 1);
assert.equal(filterWikiMenuBySearch(flat, 'reg').length, 1);
assert.equal(
  filterWikiMenuBySearch(flat, 'bozza', { hideAdminContent: true, canEdit: true }).length,
  0
);
assert.equal(filterWikiMenuBySearch(flat, '').length, 0);

const sw = readFileSync(join(root, 'src/sw.js'), 'utf8');
assert.match(sw, /kor35-wiki-api/);
assert.match(sw, /NetworkFirst/);
assert.match(sw, /\/api\/plot\/api\/wiki\//);

const queueSrc = readFileSync(join(root, 'src/lib/offlineActionQueue.js'), 'utf8');
assert.match(queueSrc, /OFFLINE_ACTION_QR_SCAN/);
assert.match(queueSrc, /OFFLINE_ACTION_MESSAGE/);

const qrTab = readFileSync(join(root, 'src/components/QrTab.jsx'), 'utf8');
assert.match(qrTab, /enqueueOfflineAction/);
assert.match(qrTab, /flushQueuedScans/);

const msgTab = readFileSync(join(root, 'src/components/PlayerMessageTab.jsx'), 'utf8');
assert.match(msgTab, /OfflineConsultBanner/);
assert.match(msgTab, /!isOnline/);

console.log('OK smoke_offline_helpers: filter menu, SW wiki, coda QR, messaggi offline.');
