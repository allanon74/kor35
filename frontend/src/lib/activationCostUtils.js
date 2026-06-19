import { getTacticalPoolCurrent } from './gamePoolUtils';

/** Allinea sigle backend (CHK→CHA, PG→PS). */
export function normalizeActivationSigla(sigla) {
  const s = String(sigla || '').toUpperCase();
  if (s === 'CHK') return 'CHA';
  if (s === 'PG') return 'PS';
  return s;
}

/** Valore corrente risorsa (pool tattici, pool FRT, legacy temp). */
export function getResourceCurrent(char, sigla) {
  if (!char) return 0;
  const s = normalizeActivationSigla(sigla);
  const pools = char.risorse_pool_ui || [];
  const row = pools.find((p) => normalizeActivationSigla(p?.sigla) === s);
  if (row != null && row.valore_corrente != null) {
    return Number(row.valore_corrente);
  }
  const rc = char.risorse_consumabili || {};
  if (rc[s] !== undefined && rc[s] !== null) {
    return Number(rc[s]);
  }
  const prim = (char.statistiche_primarie || []).find(
    (x) => normalizeActivationSigla(x?.sigla) === s
  );
  const maxFallback = prim?.valore_max ?? 0;
  return getTacticalPoolCurrent(char, s, `${s}_CUR`, maxFallback);
}

/** Aggiorna contatori risorsa nel cache personaggio (react-query). */
export function setResourceCurrent(char, sigla, newValue) {
  if (!char) return char;
  const s = normalizeActivationSigla(sigla);
  const val = Math.max(0, Number(newValue) || 0);
  const next = { ...char };

  const poolUi = [...(next.risorse_pool_ui || [])];
  const pIdx = poolUi.findIndex((p) => normalizeActivationSigla(p?.sigla) === s);
  if (pIdx >= 0) {
    poolUi[pIdx] = { ...poolUi[pIdx], valore_corrente: val };
  }
  next.risorse_pool_ui = poolUi;

  next.risorse_consumabili = { ...(next.risorse_consumabili || {}), [s]: val };

  if (Array.isArray(next.statistiche_primarie)) {
    next.statistiche_primarie = next.statistiche_primarie.map((st) =>
      normalizeActivationSigla(st?.sigla) === s ? { ...st, valore_corrente: val } : st
    );
  }

  const temp = { ...(next.statistiche_temporanee || {}) };
  delete temp[`${s}_CUR`];
  if (s === 'CHA') delete temp.CHK_CUR;
  next.statistiche_temporanee = temp;

  return next;
}

/** Applica costi attivazione al payload personaggio (optimistic). */
export function applyActivationCostsOptimistic(char, costi) {
  let next = char;
  for (const row of costi || []) {
    const sigla = row.statistica?.sigla || row.stat_sigla;
    const costo = Number(row.costo || 0);
    if (!sigla || costo <= 0) continue;
    const cur = getResourceCurrent(next, sigla);
    next = setResourceCurrent(next, sigla, cur - costo);
  }
  return next;
}

/** Verifica disponibilità costi e prepara etichette UI. */
export function evaluateActivationCosts(char, costi) {
  const rows = (costi || [])
    .map((row) => {
      const sigla = normalizeActivationSigla(row.statistica?.sigla || row.stat_sigla);
      const nome = row.statistica?.nome || sigla;
      const costo = Number(row.costo || 0);
      const current = getResourceCurrent(char, sigla);
      return { sigla, nome, costo, current, ok: current >= costo };
    })
    .filter((r) => r.costo > 0);

  return {
    rows,
    affordable: rows.length === 0 || rows.every((r) => r.ok),
    label: rows.map((r) => `-${r.costo} ${r.sigla}`).join(', '),
  };
}

/** Merge risposta API personaggio nel cache Game (oggetti/tessiture preservati se assenti). */
export function mergePersonaggioGameCache(oldData, personaggio, { oggettoPatch } = {}) {
  if (!personaggio) return oldData;
  const next = { ...oldData, ...personaggio };
  if (oggettoPatch?.id && Array.isArray(next.oggetti)) {
    next.oggetti = next.oggetti.map((o) =>
      String(o.id) === String(oggettoPatch.id) ? { ...o, ...oggettoPatch } : o
    );
  }
  return next;
}
