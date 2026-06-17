const UUID_RE = /[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}/i;
const SHORT_ID_RE = /^[A-Za-z0-9]{1,14}$/;

/**
 * Normalizza il payload letto da scanner QR.
 * Gli ID KOR35 sono stringhe alfanumeriche fino a 14 caratteri (non UUID).
 */
export function normalizeScannedQrId(raw) {
  const s = String(raw ?? '').trim();
  if (!s) return '';

  const queryMatch = s.match(/[?&]id=([A-Za-z0-9]{1,14})\b/);
  if (queryMatch) return queryMatch[1];

  const pathMatch = s.match(/\/qrcode[s]?\/([A-Za-z0-9]{1,14})(?:\/|\?|$)/i);
  if (pathMatch) return pathMatch[1];

  const uuidMatch = s.match(UUID_RE);
  if (uuidMatch) return uuidMatch[0];

  if (SHORT_ID_RE.test(s)) return s;

  const tokens = s.match(/[A-Za-z0-9]{8,14}/g);
  if (tokens?.length === 1) return tokens[0];

  return s;
}
