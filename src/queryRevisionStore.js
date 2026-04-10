/**
 * Ultima revisione server (ISO string) per chiavi cache-revision.
 * In-memory: si azzera al reload; allineato alla cache React Query in RAM.
 */
const revisionByKey = new Map();

export function getRevision(key) {
  return revisionByKey.get(key);
}

export function setRevision(key, iso) {
  if (key && iso) revisionByKey.set(key, iso);
}

export function clearRevision(key) {
  if (key) revisionByKey.delete(key);
}

export function clearAllRevisions() {
  revisionByKey.clear();
}
