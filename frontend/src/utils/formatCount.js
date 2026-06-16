/** Conteggi interi con separatori migliaia (locale it-IT: 1.234.567). */
export function formatCount(value) {
  const n = Number(value);
  if (!Number.isFinite(n)) return '0';
  return n.toLocaleString('it-IT', { maximumFractionDigits: 0 });
}
