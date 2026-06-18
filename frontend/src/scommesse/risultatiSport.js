/**
 * Tipi risultato scommesse (allineati a backend/personaggi/scommesse_risultati.py).
 */
export const TIPI_RISULTATO = [
  { id: 'calcio', label: 'Calcio', pareggio: true, unita: 'gol' },
  { id: 'rugby', label: 'Rugby', pareggio: true, unita: 'pt' },
  { id: 'basket', label: 'Basket', pareggio: false, unita: 'pt' },
  { id: 'football_usa', label: 'Football americano', pareggio: false, unita: 'pt' },
  { id: 'baseball', label: 'Baseball', pareggio: false, unita: 'run' },
  { id: 'tennis', label: 'Tennis', pareggio: false, unita: 'set' },
  { id: 'volley', label: 'Pallavolo', pareggio: false, unita: 'set' },
  { id: 'hockey', label: 'Hockey su ghiaccio', pareggio: false, unita: 'gol' },
];

const META_BY_ID = Object.fromEntries(TIPI_RISULTATO.map((t) => [t.id, t]));

export function metaTipoRisultato(tipo) {
  return META_BY_ID[tipo] || META_BY_ID.calcio;
}

export function pareggioConsentito(tipo) {
  return metaTipoRisultato(tipo).pareggio;
}

export function formattaRisultato(tipo, casa, trasferta) {
  const meta = metaTipoRisultato(tipo);
  return `${casa}-${trasferta} ${meta.unita}`;
}

export function esitiScommessa(pareggioOk) {
  const base = [
    { id: '1', label: '1' },
    { id: '2', label: '2' },
  ];
  if (pareggioOk) {
    return [{ id: '1', label: '1' }, { id: 'X', label: 'X' }, { id: '2', label: '2' }];
  }
  return base;
}

export function labelTipoRisultato(tipo) {
  return metaTipoRisultato(tipo).label;
}
