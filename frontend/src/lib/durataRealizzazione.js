/** Durata forgiatura leggibile (es. 90 → "1 min 30 s"). */
export function formatDurataRealizzazione(secondi) {
  const totale = Math.max(0, Math.floor(Number(secondi) || 0));
  if (totale === 0) return '0 s';
  const ore = Math.floor(totale / 3600);
  const minuti = Math.floor((totale % 3600) / 60);
  const restanti = totale % 60;
  const parti = [];
  if (ore > 0) parti.push(`${ore} h`);
  if (minuti > 0) parti.push(`${minuti} min`);
  if (restanti > 0) parti.push(`${restanti} s`);
  return parti.join(' ');
}
