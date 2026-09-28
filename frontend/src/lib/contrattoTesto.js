/**
 * Sostituisce i segnaposto del testo contratto.
 * `segnapostoVuoto` vale in anteprima («…»); sul testo già stipulato resta vuoto.
 */
export function renderTestoContratto(modelloTesto, {
  proponente = '',
  cliente = 'il sottoscrittore',
  korp = '',
  scadenza = '',
  parametri = {},
  etichette = {},
  clausole = [],
  compensi = [],
  segnapostoVuoto = '',
} = {}) {
  const lineeParam = Object.entries(parametri)
    .map(([chiave, valore]) => `- ${etichette[chiave] || chiave}: ${valore == null ? '' : valore}`)
    .join('\n');
  const lineeClausole = clausole.length ? clausole.map((riga) => `- ${riga}`).join('\n') : '—';
  const lineeCompensi = compensi.length ? compensi.map((riga) => `- ${riga}`).join('\n') : '—';
  const tokenRe = /\{\{\s*([A-Za-z0-9_]+)(?:\s*:\s*([A-Za-z0-9_]+))?\s*\}\}/g;
  const mappa = {
    proponente: proponente || '',
    cliente: cliente || 'il sottoscrittore',
    korp: korp || '',
    scadenza: scadenza || '',
    parametri: lineeParam,
    clausole: lineeClausole,
    compensi: lineeCompensi,
  };
  return String(modelloTesto || '').replace(tokenRe, (intero, nome, chiave) => {
    if (nome === 'param' && chiave) {
      if (!Object.prototype.hasOwnProperty.call(parametri, chiave)) return intero;
      const valore = parametri[chiave];
      if (valore == null || valore === '') return segnapostoVuoto;
      return String(valore);
    }
    if (Object.prototype.hasOwnProperty.call(mappa, nome)) return String(mappa[nome]);
    return intero;
  });
}

export function anteprimaModello(modello, { nomeProponente = '', valoriProponente = {} } = {}) {
  if (!modello) return '';
  const parametri = {};
  const etichette = {};
  for (const parametro of modello.parametri || []) {
    if (!parametro?.chiave) continue;
    etichette[parametro.chiave] = parametro.etichetta || parametro.chiave;
    if (parametro.chi_compila === 'PROPONENTE') {
      const live = valoriProponente[parametro.chiave];
      parametri[parametro.chiave] = live == null || live === '' ? null : live;
    } else {
      parametri[parametro.chiave] = parametro.valore;
    }
  }
  const clausole = [];
  const compensi = [];
  for (const voce of modello.voci || []) {
    const etichetta = voce.testo ? `${voce.nome} — ${voce.testo}` : (voce.nome || '');
    if (voce.tipo === 'COMPENSO') compensi.push(etichetta);
    else clausole.push(etichetta);
  }
  let scadenza = '';
  if (modello.durata_modo === 'FINE_EVENTO') scadenza = 'fine evento';
  else if (modello.durata_giorni) scadenza = `tra ${modello.durata_giorni} giorni`;
  return renderTestoContratto(modello.testo, {
    proponente: nomeProponente || 'il proponente',
    cliente: 'il sottoscrittore',
    korp: modello.korp_nome || '',
    scadenza,
    parametri,
    etichette,
    clausole,
    compensi,
    segnapostoVuoto: '…',
  });
}
