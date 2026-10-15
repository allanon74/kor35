/** Scelta del plot aperto di default in Gestione plot. */

export function ordinaPlot(eventi) {
  return [...(eventi || [])].sort((a, b) => {
    const da = new Date(a?.data_inizio || 0).getTime();
    const db = new Date(b?.data_inizio || 0).getTime();
    if (da !== db) return da - db;
    return String(a?.id || '').localeCompare(String(b?.id || ''));
  });
}

export function plotArchiviato(ev) {
  return Boolean(ev?.archiviato_at);
}

/**
 * Un plot è concluso se lo staff l'ha terminato, oppure se la data di fine
 * è passata e non è stato avviato (e non ha la data ancora da definire).
 * Un evento ufficialmente in corso resta non concluso.
 */
export function plotConcluso(ev, now = new Date()) {
  if (!ev || plotArchiviato(ev)) return false;
  if (ev.ended_at) return true;
  if (ev.started_at) return false;
  if (ev.data_da_definire) return false;
  if (!ev.data_fine) return false;
  const fine = new Date(ev.data_fine).getTime();
  return Number.isFinite(fine) && fine < now.getTime();
}

/** Primo plot attivo, in ordine di data, che non è concluso. */
export function primoPlotNonConcluso(eventi, now = new Date()) {
  return ordinaPlot(eventi).find((ev) => !plotArchiviato(ev) && !plotConcluso(ev, now)) || null;
}

/**
 * Apertura predefinita: il primo plot non concluso.
 * Se tutti i plot attivi sono conclusi, il più vecchio ancora in elenco.
 */
export function plotPredefinito(eventi, now = new Date()) {
  return (
    primoPlotNonConcluso(eventi, now)
    || ordinaPlot(eventi).find((ev) => !plotArchiviato(ev))
    || null
  );
}
