/**
 * Oggetti allegabili a un messaggio tra personaggi.
 * Si invia tutto ciò che è nello zaino, tranne innesti/mutazioni/aumenti
 * corporei e ciò che è già montato su un altro oggetto.
 * Un oggetto modificato si invia intero: le materie e le mod restano montate.
 */

const TIPI_NON_CEDIBILI = new Set(['INN', 'MUT', 'AUM']);

export function oggettoCedibileViaMessaggio(item) {
  if (!item || item.id == null || item.id === '') return false;
  if (item.is_equipaggiato) return false;
  if (item.slot_corpo) return false;
  if (item.ospitato_su) return false;
  if (TIPI_NON_CEDIBILI.has(item.tipo_oggetto)) return false;
  return true;
}

export function etichettaOggettoCedibile(item) {
  const base = item?.nome || `Oggetto ${item?.id}`;
  const mods = (item?.potenziamenti_installati || [])
    .map((mod) => mod?.nome)
    .filter(Boolean);
  if (!mods.length) return base;
  return `${base} (${mods.join(', ')})`;
}

export function filtraOggettiCedibili(oggetti = []) {
  return (oggetti || []).filter(oggettoCedibileViaMessaggio);
}
