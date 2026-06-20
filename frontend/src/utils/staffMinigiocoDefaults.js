import { staffSaveMinigiocoQrConfig } from '../api';

/** Impostazioni minigioco di default per pagina staff (localStorage, per browser). */
const STORAGE_KEY = 'kor35_staff_minigioco_page_defaults';

export const MINIGIOCO_PAGE_KEYS = {
  manifesti: 'manifesti',
  nodi: 'nodi',
  innescoTimer: 'innesco-timer',
  pilotSottosistemi: 'pilot-sottosistemi',
  pilotEventi: 'pilot-eventi',
};

export function loadPageMinigiocoSettings(pageKey) {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    const row = all[pageKey];
    if (!row || typeof row !== 'object') {
      return { applyToNew: false, config: null };
    }
    return {
      applyToNew: Boolean(row.applyToNew),
      config: row.config && typeof row.config === 'object' ? row.config : null,
    };
  } catch {
    return { applyToNew: false, config: null };
  }
}

export function savePageMinigiocoSettings(pageKey, { applyToNew, config }) {
  try {
    const all = JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
    all[pageKey] = {
      applyToNew: Boolean(applyToNew),
      config: config || null,
      updatedAt: new Date().toISOString(),
    };
    localStorage.setItem(STORAGE_KEY, JSON.stringify(all));
    return true;
  } catch {
    return false;
  }
}

export function setPageMinigiocoApplyToNew(pageKey, applyToNew) {
  const current = loadPageMinigiocoSettings(pageKey);
  savePageMinigiocoSettings(pageKey, { ...current, applyToNew: Boolean(applyToNew) });
}

/** Converte config JSON (senza immagine file) in FormData per staffSaveMinigiocoQrConfig. */
export function minigiocoConfigToFormData(config, { usaDefaultPagina = null } = {}) {
  const fd = new FormData();
  if (usaDefaultPagina !== null) {
    fd.append('usa_default_pagina', usaDefaultPagina ? 'true' : 'false');
  }
  if (!config || typeof config !== 'object') return fd;
  fd.append('attivo', config.attivo ? 'true' : 'false');
  fd.append('usa_biblioteca_se_vuota', config.usa_biblioteca_se_vuota !== false ? 'true' : 'false');
  fd.append('tipi_abilitati', JSON.stringify(config.tipi_abilitati || []));
  fd.append('difficolta', String(Number(config.difficolta) || 4));
  fd.append('messaggio_pre', config.messaggio_pre || '');
  fd.append('messaggio_vittoria', config.messaggio_vittoria || '');
  fd.append('timer_scadenza_azione', config.timer_scadenza_azione || 'reset_minigioco');
  fd.append('modalita_sblocco', config.modalita_sblocco || 'permanente');
  if (config.modalita_sblocco === 'temporaneo' && config.sblocco_secondi) {
    fd.append('sblocco_secondi', String(config.sblocco_secondi));
  } else {
    fd.append('sblocco_secondi', '');
  }
  fd.append('requisiti_attivazione', JSON.stringify(config.requisiti_attivazione || []));
  fd.append('esclusioni_minigioco', JSON.stringify(config.esclusioni_minigioco || []));
  fd.append('regole_difficolta', JSON.stringify(config.regole_difficolta || []));
  if (config.timer_secondi !== '' && config.timer_secondi != null) {
    fd.append('timer_secondi', String(config.timer_secondi));
  } else {
    fd.append('timer_secondi', '');
  }
  if (usaDefaultPagina === null && config.usa_default_pagina != null) {
    fd.append('usa_default_pagina', config.usa_default_pagina ? 'true' : 'false');
  }
  return fd;
}

export async function staffSetMinigiocoUsaDefault(qrId, usaDefault, onLogout) {
  const fd = new FormData();
  fd.append('usa_default_pagina', usaDefault ? 'true' : 'false');
  return staffSaveMinigiocoQrConfig(qrId, fd, onLogout);
}

/**
 * Copia il template pagina sul QR. Con forceApply salta il check applyToNew (toggle manuale).
 */
export async function applyDefaultMinigiocoToQr(
  pageKey,
  qrId,
  onLogout,
  _legacySaveArg = null,
  { forceApply = false, usaDefaultPagina = true } = {},
) {
  if (!qrId || !pageKey) return false;
  const { applyToNew, config } = loadPageMinigiocoSettings(pageKey);
  if (!forceApply && (!applyToNew || !config)) return false;
  if (config) {
    const fd = minigiocoConfigToFormData(config, { usaDefaultPagina });
    await staffSaveMinigiocoQrConfig(qrId, fd, onLogout);
    return true;
  }
  if (usaDefaultPagina) {
    await staffSetMinigiocoUsaDefault(qrId, true, onLogout);
    return true;
  }
  return false;
}

export function unwrapStaffList(data) {
  if (Array.isArray(data)) return data;
  if (data && Array.isArray(data.results)) return data.results;
  return [];
}

export function patchStaffListMinigiocoDefault(setItems, itemId, usaDefault) {
  setItems((prev) =>
    prev.map((row) =>
      row.id === itemId ? { ...row, minigioco_usa_default: Boolean(usaDefault) } : row,
    ),
  );
}
