/** Etichette e helper condivisi fra listino giocatore e anteprima staff. */

export const TIPO_VOCE_LABEL = {
  OGB: 'Oggetto',
  OGG: 'Oggetto unico',
  ABL: 'Abilità',
  INF: 'Infusione',
  TES: 'Tessitura',
  CER: 'Cerimoniale',
  CON: 'Consumabile',
  SER: 'Pezzo da collezione',
  BND: 'Pacchetto',
};

export const fmtCr = (n) => {
  const v = Number(n);
  if (Number.isNaN(v)) return '0.00';
  return v.toFixed(2);
};

/** Etichetta tipo da mostrare come badge sulla voce. */
export const labelTipoVoce = (voce) => {
  if (!voce) return '';
  if (voce.tipo === 'bundle') return TIPO_VOCE_LABEL.BND;
  return TIPO_VOCE_LABEL[voce.tipo_voce] || '';
};

/** HTML descrittivo della voce (testo formattato dal backend o descrizione grezza). */
export const descrizioneVoce = (voce) =>
  (voce?.testo_formattato || voce?.descrizione || '').trim();
