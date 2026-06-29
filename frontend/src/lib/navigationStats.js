/**
 * Sigle default statistiche navigazione (allineate a pilotaggio/navigation_stats.py).
 */
export const DEFAULT_NAVIGAZIONE_SIGLA = '0PI';
export const DEFAULT_INGEGNERIA_SIGLA = '0IN';
export const DEFAULT_STIVA_ACCESS_STAT_SIGLA = DEFAULT_INGEGNERIA_SIGLA;
export const DEFAULT_SABOTAGGIO_SIGLA = '0SA';
export const DEFAULT_RIPARAZIONE_SIGLA = '0RI';
export const DEFAULT_SCIENTIFICA_SIGLA = '0SC';
export const DEFAULT_COMUNICAZIONI_SIGLA = '0CO';

/** Campi runtime-config ↔ etichetta staff */
export const NAVIGATION_STAT_FIELDS = [
  {
    id: 'navigazione',
    label: 'Console Navigazione',
    siglaField: 'navigazione_stat_accesso_sigla',
    defaultSigla: DEFAULT_NAVIGAZIONE_SIGLA,
    requisito: '≥ 1',
    url: '/pilot/',
  },
  {
    id: 'ingegneria',
    label: 'Console Ingegneria',
    siglaField: 'compattatore_stat_accesso_sigla',
    defaultSigla: DEFAULT_INGEGNERIA_SIGLA,
    requisito: '> 0',
    url: '/pilot/?screen=compattatore',
  },
  {
    id: 'stiva_app',
    label: 'Tab Stiva (app giocatore)',
    siglaField: 'compattatore_stat_accesso_sigla',
    defaultSigla: DEFAULT_INGEGNERIA_SIGLA,
    requisito: '> 0',
    url: null,
    readOnlySigla: true,
    note: 'Usa la stessa sigla della Console Ingegneria.',
  },
  {
    id: 'scientifica',
    label: 'Console Scientifica',
    siglaField: 'scientifica_stat_accesso_sigla',
    defaultSigla: DEFAULT_SCIENTIFICA_SIGLA,
    requisito: '> 0',
    url: '/pilot/?screen=scientifica',
  },
  {
    id: 'sabotaggio',
    label: 'Sabotaggio sottosistemi (QR)',
    siglaField: 'sabotaggio_stat_sigla',
    defaultSigla: DEFAULT_SABOTAGGIO_SIGLA,
    requisito: '> 0',
    url: null,
  },
  {
    id: 'riparazione',
    label: 'Riparazione sottosistemi (QR)',
    siglaField: 'riparazione_stat_sigla',
    defaultSigla: DEFAULT_RIPARAZIONE_SIGLA,
    requisito: '> 0',
    url: null,
  },
  {
    id: 'comunicazioni',
    label: 'Console Comunicazioni (futuro)',
    siglaField: 'comunicazioni_stat_accesso_sigla',
    defaultSigla: DEFAULT_COMUNICAZIONI_SIGLA,
    requisito: '> 0',
    url: '/pilot/?screen=comunicazioni',
    future: true,
  },
];
