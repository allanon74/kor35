/** Fallback invio se l'aura non ha una statistica di costo (allineato a COSTO_DEFAULT_INVIO_PROPOSTA). */
export const COSTO_INVIO_FALLBACK = 10;

const CAMPO_INVIO = {
  CER: 'stat_costo_invio_proposta_cerimoniale',
  INF: 'stat_costo_invio_proposta_infusione',
  TES: 'stat_costo_invio_proposta_tessitura',
};

/**
 * Valore di scheda della statistica agganciata all'aura.
 * Stessa precedenza del backend: punteggi del personaggio, poi valore di catalogo.
 */
export function valoreStatisticaScheda(char, meta) {
  if (!meta?.nome) return null;
  const base = Number(char?.punteggi_base?.[meta.nome] ?? 0);
  const chiave = meta.parametro || meta.sigla;
  const mods = (chiave && char?.modificatori_calcolati?.[chiave]) || null;
  const add = Number(mods?.add || 0);
  const mol = mods?.mol == null ? 1 : Number(mods.mol);
  const valore = Math.round((base + add) * mol);
  if (valore > 0) return valore;
  const catalogo = Number(meta.valore_base_predefinito || 0);
  return catalogo > 0 ? catalogo : null;
}

/** Costo invio = quantità × statistica indicata sull'aura (non una costante per mattone). */
export function costoInvioStimato({ tipo, aura, char, quantita }) {
  const campo = CAMPO_INVIO[tipo] || CAMPO_INVIO.TES;
  const meta = aura?.costi_stat_meta?.[campo];
  const unita = valoreStatisticaScheda(char, meta) ?? COSTO_INVIO_FALLBACK;
  return Math.max(0, Number(quantita) || 0) * unita;
}
