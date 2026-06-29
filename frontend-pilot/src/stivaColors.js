/** Mappa sigle colore componente nave (0C0–0C9) → hex da seed catalogo. */
export const COMPONENTE_COLORI_HEX = {
  '0C0': '#111111',
  '0C1': '#f5f5f5',
  '0C2': '#c62828',
  '0C3': '#2e7d32',
  '0C4': '#1565c0',
  '0C5': '#f9a825',
  '0C6': '#6a1b9a',
  '0C7': '#ef6c00',
  '0C8': '#00838f',
  '0C9': '#ad1457',
};

const NOME_FALLBACK = {
  nero: '#111111',
  bianco: '#f5f5f5',
  rosso: '#c62828',
  verde: '#2e7d32',
  blu: '#1565c0',
  giallo: '#f9a825',
  viola: '#6a1b9a',
  arancio: '#ef6c00',
  ciano: '#00838f',
  magenta: '#ad1457',
};

export function hexPerColoreComponente(sigla, nome) {
  const s = (sigla || '').trim().toUpperCase();
  if (COMPONENTE_COLORI_HEX[s]) return COMPONENTE_COLORI_HEX[s];
  const n = (nome || '').trim().toLowerCase();
  return NOME_FALLBACK[n] || '#3a4a5c';
}

function luminanza(hex) {
  const h = hex.replace('#', '');
  const r = parseInt(h.slice(0, 2), 16) / 255;
  const g = parseInt(h.slice(2, 4), 16) / 255;
  const b = parseInt(h.slice(4, 6), 16) / 255;
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

export function testoSuSfondo(hex) {
  return luminanza(hex) > 0.62 ? '#0b0d12' : '#f5f8ff';
}
