/**
 * Normalizzazione coordinate evento (lat/lng canonici) — mirror logica backend.
 */

const COORD_DECIMAL_PLACES = 6;

const PAIR_PATTERN = /^\s*(-?\d+(?:[.,]\d+)?)\s*[,;\s]\s*(-?\d+(?:[.,]\d+)?)\s*$/;
const GOOGLE_AT_PATTERN = /@(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)/i;
const GOOGLE_Q_PATTERN = /[?&]q=(-?\d+(?:\.\d+)?),\s*(-?\d+(?:\.\d+)?)/i;

function toNumber(value) {
  if (value === null || value === undefined || value === '') return null;
  const n = Number(String(value).trim().replace(',', '.'));
  return Number.isFinite(n) ? n : NaN;
}

function roundCoord(n) {
  const factor = 10 ** COORD_DECIMAL_PLACES;
  return Math.round(n * factor) / factor;
}

function validateRange(lat, lng) {
  if (lat < -90 || lat > 90) throw new Error('Latitudine fuori range (-90 … 90).');
  if (lng < -180 || lng > 180) throw new Error('Longitudine fuori range (-180 … 180).');
}

export function parseCoordinatesFromText(text) {
  const raw = String(text || '').trim();
  if (!raw) throw new Error('Testo coordinate vuoto.');

  const pair = raw.match(PAIR_PATTERN);
  if (pair) {
    const lat = toNumber(pair[1]);
    const lng = toNumber(pair[2]);
    if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
      throw new Error('Coppia coordinate non valida.');
    }
    validateRange(lat, lng);
    return { latitudine: roundCoord(lat), longitudine: roundCoord(lng) };
  }

  for (const pattern of [GOOGLE_AT_PATTERN, GOOGLE_Q_PATTERN]) {
    const found = raw.match(pattern);
    if (found) {
      const lat = toNumber(found[1]);
      const lng = toNumber(found[2]);
      if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
        throw new Error('URL mappe senza coordinate valide.');
      }
      validateRange(lat, lng);
      return { latitudine: roundCoord(lat), longitudine: roundCoord(lng) };
    }
  }

  throw new Error('Formato non riconosciuto. Usa «lat, lng» o un link Google Maps.');
}

export function normalizeCoordinatesForSave(latRaw, lngRaw) {
  const latEmpty = latRaw === null || latRaw === undefined || latRaw === '';
  const lngEmpty = lngRaw === null || lngRaw === undefined || lngRaw === '';
  if (latEmpty && lngEmpty) {
    return { latitudine: null, longitudine: null };
  }
  const lat = toNumber(latRaw);
  const lng = toNumber(lngRaw);
  if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
    throw new Error('Latitudine e longitudine vanno indicate entrambe o lasciate vuote.');
  }
  validateRange(lat, lng);
  return { latitudine: roundCoord(lat), longitudine: roundCoord(lng) };
}

export function buildNavigatoreLinks(lat, lng) {
  const latS = String(lat);
  const lngS = String(lng);
  return {
    geo: `geo:${latS},${lngS}`,
    google_maps: `https://www.google.com/maps?q=${latS},${lngS}`,
    apple_maps: `https://maps.apple.com/?ll=${latS},${lngS}`,
    waze: `https://waze.com/ul?ll=${latS},${lngS}&navigate=yes`,
  };
}

export function hasValidCoordinates(latRaw, lngRaw) {
  try {
    const { latitudine, longitudine } = normalizeCoordinatesForSave(latRaw, lngRaw);
    return latitudine !== null && longitudine !== null;
  } catch {
    return false;
  }
}
