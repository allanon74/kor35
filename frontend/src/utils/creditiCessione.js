/**
 * Cessioni P2P: due tipologie di crediti (corrente / deposito).
 */

export function numCredito(value) {
  const n = Number(value);
  return Number.isFinite(n) ? n : 0;
}

export function importiDaProposta(proposta) {
  if (!proposta) {
    return { corrente: 0, deposito: 0, ricevereCorrente: 0, ricevereDeposito: 0 };
  }
  const corr = numCredito(proposta.crediti_corrente_da_dare);
  const dep = numCredito(proposta.crediti_deposito_da_dare);
  const ricCorr = numCredito(proposta.crediti_corrente_da_ricevere);
  const ricDep = numCredito(proposta.crediti_deposito_da_ricevere);
  if (corr > 0 || dep > 0 || ricCorr > 0 || ricDep > 0) {
    return {
      corrente: corr,
      deposito: dep,
      ricevereCorrente: ricCorr,
      ricevereDeposito: ricDep,
    };
  }
  const amt = numCredito(proposta.crediti_da_dare);
  const amtR = numCredito(proposta.crediti_da_ricevere);
  const isDep = proposta.conto_crediti === 'DEPOSITO';
  return {
    corrente: isDep ? 0 : amt,
    deposito: isDep ? amt : 0,
    ricevereCorrente: isDep ? 0 : amtR,
    ricevereDeposito: isDep ? amtR : 0,
  };
}

export function formatImportiCessione(corrente, deposito, { duale = true } = {}) {
  const c = numCredito(corrente);
  const d = numCredito(deposito);
  if (!duale) {
    return `${(c + d).toFixed(2)} CR`;
  }
  const parts = [];
  if (c > 0) parts.push(`${c.toFixed(2)} CR correnti`);
  if (d > 0) parts.push(`${d.toFixed(2)} CR deposito`);
  return parts.join(' + ') || '0 CR';
}

export function importiDaMessaggio(msg) {
  if (!msg) return { corrente: 0, deposito: 0 };
  const corr = numCredito(msg.crediti_corrente_allegati);
  const dep = numCredito(msg.crediti_deposito_allegati);
  if (corr > 0 || dep > 0) return { corrente: corr, deposito: dep };
  const amt = numCredito(msg.crediti_allegati);
  if (amt <= 0) return { corrente: 0, deposito: 0 };
  if (msg.conto_crediti_allegati === 'DEPOSITO') return { corrente: 0, deposito: amt };
  return { corrente: amt, deposito: 0 };
}
