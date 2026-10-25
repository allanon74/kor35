/** Fallback invio se l'aura non ha una statistica di costo (allineato a COSTO_DEFAULT_INVIO_PROPOSTA). */
export const COSTO_INVIO_FALLBACK = 10;

const CAMPO_INVIO = {
  CER: 'stat_costo_invio_proposta_cerimoniale',
  INF: 'stat_costo_invio_proposta_infusione',
  TES: 'stat_costo_invio_proposta_tessitura',
};

function numero(valore) {
  const n = Number(valore);
  return Number.isFinite(n) ? n : 0;
}

/**
 * Base di scheda della statistica agganciata all'aura.
 * `punteggi_base` è indicizzato per nome; `statistiche_base_dict` per parametro/sigla.
 */
function baseScheda(char, meta) {
  const nome = (meta?.nome || '').trim();
  if (nome && char?.punteggi_base && Object.prototype.hasOwnProperty.call(char.punteggi_base, nome)) {
    return numero(char.punteggi_base[nome]);
  }
  const chiave = meta?.parametro || meta?.sigla;
  const dict = char?.statistiche_base_dict;
  if (chiave && dict && Object.prototype.hasOwnProperty.call(dict, chiave)) {
    return numero(dict[chiave]);
  }
  return null;
}

/**
 * Valore di scheda della statistica agganciata all'aura.
 * Stessa precedenza del backend: punteggi del personaggio, poi valore di catalogo.
 */
export function valoreStatisticaScheda(char, meta) {
  if (!meta?.nome) return null;
  const baseNota = baseScheda(char, meta);
  const base = baseNota == null ? 0 : baseNota;
  const chiave = meta.parametro || meta.sigla;
  const mods = (chiave && char?.modificatori_calcolati?.[chiave]) || null;
  const add = numero(mods?.add);
  const mol = mods?.mol == null ? 1 : numero(mods.mol);
  const valore = Math.round((base + add) * mol);
  if (valore > 0) return valore;
  const catalogo = numero(meta.valore_base_predefinito);
  return catalogo > 0 ? catalogo : null;
}

/**
 * Anteprima invio: quantità × statistica indicata sull'aura.
 * `daAddebitare` è la differenza rispetto a quanto già versato (un rinvio non riscala il totale).
 */
export function dettaglioCostoInvio({ tipo, aura, char, quantita, giaPagato = 0 }) {
  const campo = CAMPO_INVIO[tipo] || CAMPO_INVIO.TES;
  const meta = aura?.costi_stat_meta?.[campo] || null;
  const unita = valoreStatisticaScheda(char, meta) ?? COSTO_INVIO_FALLBACK;
  const q = Math.max(0, numero(quantita));
  const totale = q * unita;
  const pagato = Math.max(0, numero(giaPagato));
  return {
    unita,
    quantita: q,
    totale,
    giaPagato: pagato,
    daAddebitare: totale - pagato,
    daStatistica: Boolean(meta?.nome),
  };
}

/** Costo invio lordo = quantità × statistica indicata sull'aura (non una costante per mattone). */
export function costoInvioStimato(args) {
  return dettaglioCostoInvio(args).totale;
}

/** Riga breve sul delta rispetto a quanto già versato. */
export function etichettaDeltaInvio(daAddebitare) {
  const delta = numero(daAddebitare);
  if (delta < 0) return `rimborso ${-delta} CR`;
  if (delta === 0) return 'nessun altro addebito';
  return `all'invio ${delta} CR`;
}

export function messaggioConfermaInvio(dettaglio) {
  const movimento = etichettaDeltaInvio(dettaglio?.daAddebitare);
  const gia = numero(dettaglio?.giaPagato);
  const versati = gia > 0 ? ` Già versati ${gia} CR.` : '';
  return `Confermi l'invio in valutazione? Costo invio ${numero(dettaglio?.totale)} CR: ${movimento}.${versati} Lo staff può approvarla oppure rimandarla in bozza con delle note.`;
}
