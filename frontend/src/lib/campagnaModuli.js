/**
 * Accesso moduli campagna (allineato a backend/personaggi/campagna_moduli.py).
 * OFF = nascosto; TEST = solo staff/master (e PnG); OPEN = tutti.
 */

export const MODULO_ACCESSO_OFF = 'OFF';
export const MODULO_ACCESSO_TEST = 'TEST';
export const MODULO_ACCESSO_OPEN = 'OPEN';
/** Valore di scrittura: rimuove l'override e torna al default del registry. */
export const MODULO_ACCESSO_DEFAULT = 'DEFAULT';

export const MODULO_ACCESSO_OPTIONS = [
  { value: MODULO_ACCESSO_OFF, label: 'Disattivo' },
  { value: MODULO_ACCESSO_TEST, label: 'Testing (staff/master)' },
  { value: MODULO_ACCESSO_OPEN, label: 'Aperto (tutti)' },
];

/** Fallback registry se l'API non lo fornisce. */
export const CAMPAGNA_MODULI_REGISTRY = [
  { key: 'tasks', label: 'Tasks (missioni)', descrizione: 'Missioni evento con premi Crediti/Prestigio.', default: 'OFF' },
  { key: 'pilotaggio', label: 'Pilotaggio', descrizione: 'Console nave, stiva, QR sottosistemi.', default: 'OPEN' },
  { key: 'carte', label: 'Carte collezionabili', descrizione: 'Tab Carte e tool staff.', default: 'OFF' },
  { key: 'scommesse', label: 'Scommesse', descrizione: 'Allibratore e tab scommesse.', default: 'OPEN' },
  { key: 'social', label: 'Social (InstaFame)', descrizione: 'Feed social e report eventi.', default: 'OPEN' },
  { key: 'negozi', label: 'Negozi mercante', descrizione: 'Tab negozi e listini staff.', default: 'OPEN' },
  { key: 'creazione_guidata', label: 'Creazione guidata PG', descrizione: 'Wizard creazione personaggio (staff).', default: 'OPEN' },
];

export const STAFF_TOOL_TO_MODULO = {
  tasks: 'tasks',
  pilotaggio: 'pilotaggio',
  'carte-collezionabili': 'carte',
  scommesse: 'scommesse',
  'negozi-mercante': 'negozi',
  'creazione-guidata': 'creazione_guidata',
  'social-report': 'social',
};

export const PLAYER_TAB_TO_MODULO = {
  scommesse: 'scommesse',
  carte: 'carte',
  negozi: 'negozi',
  social: 'social',
  // Tasks non ha una tab di primo livello: pannello in Personaggi (MissioniPersonaggioPanel).
};

export function getModuloAccesso(moduliMap, key, registry = CAMPAGNA_MODULI_REGISTRY) {
  const map = moduliMap && typeof moduliMap === 'object' ? moduliMap : {};
  if (map[key] === MODULO_ACCESSO_OFF || map[key] === MODULO_ACCESSO_TEST || map[key] === MODULO_ACCESSO_OPEN) {
    return map[key];
  }
  const row = registry.find((r) => r.key === key);
  return row?.default || MODULO_ACCESSO_OFF;
}

/**
 * @param {string} modo
 * @param {{ isCampaignStaffer?: boolean, isDjangoStaff?: boolean, isGlobalSuperuser?: boolean, isPngStaff?: boolean }} flags
 */
export function canAccessModuloMode(modo, flags = {}) {
  if (modo === MODULO_ACCESSO_OPEN) return true;
  if (modo === MODULO_ACCESSO_OFF) return false;
  // TEST
  return !!(
    flags.isCampaignStaffer ||
    flags.isDjangoStaff ||
    flags.isGlobalSuperuser ||
    flags.isPngStaff
  );
}

/** True se la campagna ha un valore esplicito per il modulo (non il default registry). */
export function isModuloOverride(moduliRawMap, key) {
  const raw = moduliRawMap && typeof moduliRawMap === 'object' ? moduliRawMap : {};
  return (
    raw[key] === MODULO_ACCESSO_OFF ||
    raw[key] === MODULO_ACCESSO_TEST ||
    raw[key] === MODULO_ACCESSO_OPEN
  );
}

export function moduloDefault(key, registry = CAMPAGNA_MODULI_REGISTRY) {
  return registry.find((r) => r.key === key)?.default || MODULO_ACCESSO_OFF;
}

/** Tab giocatore e tool staff impattati da un modulo (per la UI staff). */
export function moduloImpatti(key) {
  const staffTools = Object.entries(STAFF_TOOL_TO_MODULO)
    .filter(([, k]) => k === key)
    .map(([toolId]) => toolId);
  const playerTabs = Object.entries(PLAYER_TAB_TO_MODULO)
    .filter(([, k]) => k === key)
    .map(([tabId]) => tabId);
  return { staffTools, playerTabs };
}

export function staffToolModuloEnabled(moduliMap, toolId) {
  const key = STAFF_TOOL_TO_MODULO[toolId];
  if (!key) return true;
  return getModuloAccesso(moduliMap, key) !== MODULO_ACCESSO_OFF;
}
