/** Core HTTP client KOR35 (fetchAuthenticated / public / campaign / maintenance). */
/**
 * Base URL del backend. Default: stringa vuota = percorsi relativi (stesso host del frontend).
 * Richiesto con reverse proxy (prod, mirror) che inoltra /api e /media a Django.
 * Solo se serve un host diverso (caso raro): imposta VITE_API_URL al build.
 */
const _viteApi = import.meta.env.VITE_API_URL;
export const API_BASE_URL =
  _viteApi != null && String(_viteApi).trim() !== ''
    ? String(_viteApi).replace(/\/$/, '')
    : '';

export const getActiveCampaignSlug = () => {
  const saved = String(localStorage.getItem('kor35_active_campaign') || '').trim().toLowerCase();
  return saved || 'kor35';
};

export const setActiveCampaignSlug = (slug) => {
  const normalized = String(slug || '').trim().toLowerCase() || 'kor35';
  localStorage.setItem('kor35_active_campaign', normalized);
  return normalized;
};

/** Confronto stabile slug campagna (DB vs localStorage / header). */
export const normCampaignSlug = (s) => String(s || '').trim().toLowerCase();

export const plotRisorseCacheKey = (campaignSlug = getActiveCampaignSlug()) =>
  `plot_risorse_cache_v3_${normCampaignSlug(campaignSlug || 'kor35')}`;

/** Invalida cache risorse Plot (es. dopo cambio ruolo membership campagna). */
export const invalidatePlotRisorseCache = (campaignSlug = null) => {
  try {
    if (campaignSlug) {
      sessionStorage.removeItem(plotRisorseCacheKey(campaignSlug));
      return;
    }
    Object.keys(sessionStorage).forEach((key) => {
      if (key.startsWith('plot_risorse_cache_v3_')) sessionStorage.removeItem(key);
    });
  } catch (_e) {
    /* storage non disponibile */
  }
};

/**
 * Stato globale maintenance: quando attivo, i client API evitano di chiamare
 * gli endpoint applicativi bloccati dal middleware (silenzioso, niente console.error).
 * Allowlist: pubblica config, healthz, login, console maintenance admin.
 *
 * Bootstrap SINCRONO da localStorage: alla seconda visita parte già con il flag
 * coerente, evitando una raffica di 503 prima che il config pubblico arrivi.
 */
let __kor35MaintenanceMode = false;
try {
  __kor35MaintenanceMode =
    String(localStorage.getItem('kor35_maintenance_mode') || '').toLowerCase() === 'true';
} catch (_e) {
  __kor35MaintenanceMode = false;
}

export const setApiMaintenanceMode = (v) => {
  const next = !!v;
  __kor35MaintenanceMode = next;
  try {
    localStorage.setItem('kor35_maintenance_mode', next ? 'true' : 'false');
  } catch (_e) {
    /* storage non disponibile: ignoriamo */
  }
};

export const isApiMaintenanceMode = () => __kor35MaintenanceMode;

export class MaintenanceSkipError extends Error {
  constructor(endpoint) {
    super('Sistema in manutenzione: chiamata sospesa lato client.');
    this.name = 'MaintenanceSkipError';
    this.endpoint = endpoint;
    this.maintenanceSkipped = true;
  }
}

const __MAINTENANCE_BLOCKED_PREFIXES = [
  '/api/personaggi/',
  '/api/social/',
  '/api/pilot/',
  '/api/plot/api/staff/',
  '/api/plot/api/eventi',
  '/api/plot/api/voci-portare',
  '/api/plot/api/giorni',
  '/api/plot/api/quests',
  '/api/plot/api/mostri-istanza',
  '/api/plot/api/viste-setup',
  '/api/plot/api/png-assegnati',
  '/api/plot/api/fasi',
  '/api/plot/api/tasks',
  '/api/plot/iscrizioni-evento/',
  '/api/auth/arcana/password-status/',
];

const __MAINTENANCE_ALLOW_PREFIXES = [
  '/api/healthz',
  '/api/version',
  '/api/plot/api/public/',
  '/api/plot/api/admin/maintenance-config/',
  '/api/auth/',
];

const isBlockedDuringMaintenance = (endpoint) => {
  if (!__kor35MaintenanceMode) return false;
  const path = String(endpoint || '');
  if (__MAINTENANCE_ALLOW_PREFIXES.some((p) => path.startsWith(p))) return false;
  return __MAINTENANCE_BLOCKED_PREFIXES.some((p) => path.startsWith(p));
};

/**
 * Helper generico per le chiamate API autenticate.
 * Gestisce l'header Authorization e il caso di token non valido.
 * @param {string} endpoint - L'endpoint API (es. /api/personaggi/api/personaggi/)
 * @param {object} options - Opzioni standard di fetch (method, body, etc.)
 * @param {function} onLogout - La funzione di logout da App.jsx
 */
export const fetchAuthenticated = async (endpoint, options = {}, onLogout) => {
  if (isBlockedDuringMaintenance(endpoint)) {
    return Promise.reject(new MaintenanceSkipError(endpoint));
  }

  const token = localStorage.getItem('kor35_token');
  
  if (!token) {
    console.error('Nessun token trovato, logout in corso.');
    if (onLogout) onLogout();
    // NOTA: Restituire una Promise reietta è corretto qui
    return Promise.reject(new Error('Nessun token di autenticazione.'));
  }

  const headers = {
    // 'Content-Type': 'application/json', // Rimosso: vedi nota sotto
    'Authorization': `Token ${token}`,
    'X-Campagna': getActiveCampaignSlug(),
    ...options.headers,
  };

  // Aggiungi Content-Type solo se il corpo non è FormData
  // (per gestire futuri upload di file)
  if (options.body && !(options.body instanceof FormData)) {
    headers['Content-Type'] = 'application/json';
  } else if (!options.body) {
    // Aggiungi solo se non c'è corpo (come nelle GET)
    headers['Content-Type'] = 'application/json';
  }

  try {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, { ...options, headers });

    // Solo 401 = sessione non valida. Il 403 è spesso «autenticato ma non autorizzato» (es. non staff): non fare logout.
    if (response.status === 401) {
      console.error('Token non valido o scaduto, logout in corso.');
      if (onLogout) onLogout();
      throw new Error('Autenticazione fallita.');
    }
    
    if (!response.ok) {
        // --- CORREZIONE: Gestione Errori "Body Stream" ---
        // Leggiamo la risposta come testo *una sola volta*.
        const errorText = await response.text();
        let errorMsg = errorText; // Default all'intero testo
        let errorData = null;
        
        try {
            // Proviamo a parsare il testo come JSON
            errorData = JSON.parse(errorText);
            // Se ci riusciamo, cerchiamo un messaggio di errore più pulito
            errorMsg = errorData.detail || errorData.error || errorData.message || JSON.stringify(errorData);
        } catch (e) {
            // Non era JSON, va bene. 'errorMsg' rimane l'HTML/testo
            // (es. la pagina 404 di Django)
        }
        
        // Ora lanciamo l'errore con status e data per gestione avanzata (es. 409 Conflict)
        const isMaintenance503 = response.status === 503 && (errorData?.maintenance_mode === true);
        if (!isMaintenance503) {
          console.error(`Errore API ${response.status} (${response.statusText}) per ${endpoint}:`, errorMsg);
        }
        const error = new Error(`Errore API (${response.status}): ${errorMsg}`);
        error.status = response.status;
        error.data = errorData;
        if (isMaintenance503) {
          error.maintenanceSkipped = true;
        }
        throw error;
    }

    if (response.status === 204) { // No Content
        return null;
    }

    return await response.json();
  
  } catch (error) {
    // Rimuoviamo il console.error qui perché lo gestiamo già sopra
    // in modo più pulito nel blocco !response.ok
    // console.error(`Errore durante il fetch a ${endpoint}:`, error);
    throw error;
  }
};

/**
 * Revisioni leggere per cache condizionale (max updated_at lato server).
 * @param {string[]} parts - es. ['punteggi_all', 'personaggi_list:0', 'personaggio:42']
 * @returns {Record<string, string|null>}
 */
export const fetchCacheRevision = async (parts, onLogout) => {
  if (!parts || parts.length === 0) return {};
  const q = parts.join(',');
  return fetchAuthenticated(
    `/api/personaggi/api/cache-revision/?q=${encodeURIComponent(q)}`,
    { method: 'GET' },
    onLogout
  );
};

export const getCampaigns = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/campagne/', { method: 'GET' }, onLogout);

export const validateActiveCampaign = (slug, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/campagne/active/',
    { method: 'POST', body: JSON.stringify({ slug }) },
    onLogout
  );

export const fetchPublic = async (endpoint, options = {}) => {
  if (isBlockedDuringMaintenance(endpoint)) {
    return Promise.reject(new MaintenanceSkipError(endpoint));
  }

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  try {
    // IMPORTANTE:
    // Le route "public" non devono ereditare la sessione Django (cookie admin)
    // altrimenti un utente apparentemente "non loggato" nella web app
    // potrebbe vedere contenuti staff/bozza.
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      ...options,
      headers,
      credentials: 'omit',
    });
    
    if (!response.ok) {
        const errorText = await response.text();
        const err = new Error(`Errore API Public (${response.status}): ${errorText}`);
        err.status = response.status;
        throw err;
    }
    return await response.json();
  } catch (error) {
    if (!error?.maintenanceSkipped) {
      console.error(`Errore fetch public ${endpoint}:`, error);
    }
    throw error;
  }
};

/** Stato Arcana SSO per la pagina login (nessun token richiesto). */
export const getArcanaSSOStatus = async () => {
  try {
    return await fetchPublic('/api/auth/arcana/status/');
  } catch {
    return { enabled: false, reachable: false };
  }
};

// --- SOCIAL (Fame-stagram) ---
