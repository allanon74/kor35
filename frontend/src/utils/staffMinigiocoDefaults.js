import { staffSaveMinigiocoQrConfig, staffGetMinigiocoSezioneDefault, staffSaveMinigiocoSezioneDefault } from '../api';

/** Fallback locale (deprecato): solo se API non disponibile. */
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

/** Carica default sezione da DB; fallback localStorage se API fallisce o row assente. */
export async function loadPageMinigiocoSettingsAsync(pageKey, onLogout) {
  try {
    const data = await staffGetMinigiocoSezioneDefault(pageKey, onLogout);
    if (data?.config) {
      return {
        applyToNew: Boolean(data.apply_to_new),
        config: data.config,
        fromDb: true,
        rowId: data.row?.id || null,
      };
    }
    if (data && data.apply_to_new != null && !data.config) {
      const legacy = loadPageMinigiocoSettings(pageKey);
      return {
        applyToNew: Boolean(data.apply_to_new),
        config: legacy.config,
        fromDb: false,
        rowId: data.row?.id || null,
      };
    }
  } catch {
    /* fallback sotto */
  }
  const legacy = loadPageMinigiocoSettings(pageKey);
  return { ...legacy, fromDb: false, rowId: null };
}

/** Salva default sezione in DB (+ cache localStorage). */
export async function savePageMinigiocoSettingsAsync(pageKey, { applyToNew, config }, onLogout) {
  const payload = {
    page_key: pageKey,
    apply_to_new: Boolean(applyToNew),
    sezione_attiva: Boolean(config?.sezione_attiva),
    attivo: Boolean(config?.attivo),
    tipi_abilitati: config?.tipi_abilitati || [],
    difficolta: Number(config?.difficolta) || 4,
    requisiti_attivazione: config?.requisiti_attivazione || [],
    messaggio_accesso_negato: config?.messaggio_accesso_negato || '',
    esclusioni_minigioco: config?.esclusioni_minigioco || [],
    regole_difficolta: config?.regole_difficolta || [],
    messaggio_pre: config?.messaggio_pre || '',
    messaggio_vittoria: config?.messaggio_vittoria || '',
    timer_secondi:
      config?.timer_secondi === '' || config?.timer_secondi == null
        ? null
        : Number(config.timer_secondi),
    timer_scadenza_azione: config?.timer_scadenza_azione || 'reset_minigioco',
    usa_biblioteca_se_vuota: config?.usa_biblioteca_se_vuota !== false,
    modalita_sblocco: config?.modalita_sblocco || 'permanente',
    sblocco_secondi:
      config?.modalita_sblocco === 'temporaneo' && config?.sblocco_secondi
        ? Number(config.sblocco_secondi)
        : null,
    pattern: config?.pattern_id || null,
  };
  const saved = await staffSaveMinigiocoSezioneDefault(payload, onLogout);
  savePageMinigiocoSettings(pageKey, { applyToNew, config });
  return saved;
}

export async function setPageMinigiocoApplyToNewAsync(pageKey, applyToNew, onLogout) {
  const current = await loadPageMinigiocoSettingsAsync(pageKey, onLogout);
  if (!current.config && !current.rowId) {
    // Evita di creare un template vuoto in DB: cache solo locale fino al salvataggio editor.
    setPageMinigiocoApplyToNew(pageKey, applyToNew);
    return;
  }
  await savePageMinigiocoSettingsAsync(
    pageKey,
    { applyToNew: Boolean(applyToNew), config: current.config || {} },
    onLogout,
  );
}

/** Converte config JSON (senza immagine file) in FormData per staffSaveMinigiocoQrConfig. */
export function minigiocoConfigToFormData(config, { usaDefaultPagina = null } = {}) {
  const fd = new FormData();
  if (usaDefaultPagina !== null) {
    fd.append('usa_default_pagina', usaDefaultPagina ? 'true' : 'false');
  }
  if (!config || typeof config !== 'object') return fd;
  fd.append('sezione_attiva', config.sezione_attiva ? 'true' : 'false');
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
  fd.append('messaggio_accesso_negato', config.messaggio_accesso_negato || '');
  fd.append('esclusioni_minigioco', JSON.stringify(config.esclusioni_minigioco || []));
  fd.append('regole_difficolta', JSON.stringify(config.regole_difficolta || []));
  if (config.timer_secondi !== '' && config.timer_secondi != null) {
    fd.append('timer_secondi', String(config.timer_secondi));
  } else {
    fd.append('timer_secondi', '');
  }
  if (config.pattern_id) {
    fd.append('pattern_id', String(config.pattern_id));
  } else {
    fd.append('pattern_id', '');
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
  const { applyToNew, config } = await loadPageMinigiocoSettingsAsync(pageKey, onLogout);
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
