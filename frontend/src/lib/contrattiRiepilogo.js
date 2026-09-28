/** Stati in cui il personaggio ha davvero sottoscritto come cliente. */
export const STATI_COME_CLIENTE = ['STIPULATO', 'SCADUTO', 'RISOLTO'];

const ORDINE_CLIENTE = { STIPULATO: 0, SCADUTO: 1, RISOLTO: 2 };

export function contaAttivi(contratti, ruolo) {
  return (contratti || []).filter((c) => c?.ruolo === ruolo && c?.stato === 'STIPULATO').length;
}

export function contrattiComeCliente(contratti) {
  return (contratti || [])
    .filter((c) => c?.ruolo === 'CLIENTE' && STATI_COME_CLIENTE.includes(c?.stato))
    .slice()
    .sort((a, b) => (ORDINE_CLIENTE[a.stato] ?? 9) - (ORDINE_CLIENTE[b.stato] ?? 9));
}

export function numeriContratti(scheda) {
  const riepilogo = scheda?.riepilogo;
  if (riepilogo && Number.isFinite(Number(riepilogo.attivi_cliente)) && Number.isFinite(Number(riepilogo.attivi_offerente))) {
    return {
      attiviCliente: Number(riepilogo.attivi_cliente),
      attiviOfferente: Number(riepilogo.attivi_offerente),
    };
  }
  return {
    attiviCliente: contaAttivi(scheda?.contratti, 'CLIENTE'),
    attiviOfferente: contaAttivi(scheda?.contratti, 'PROPONENTE'),
  };
}
