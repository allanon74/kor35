const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;

/**
 * Normalizza il payload letto da scanner QR (UUID puro, URL con ?id=, path con UUID).
 */
export function normalizeScannedQrId(raw) {
  const s = String(raw ?? '').trim();
  if (!s) return '';

  const queryMatch = s.match(/[?&]id=([0-9a-f-]{36})/i);
  if (queryMatch) return queryMatch[1];

  const pathMatch = s.match(UUID_RE);
  if (pathMatch) return pathMatch[0];

  return s;
}
