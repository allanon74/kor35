/**
 * Base URL del backend. Default: stringa vuota = percorsi relativi (stesso host del frontend).
 * Richiesto con reverse proxy (prod, mirror) che inoltra /api e /media a Django.
 * Solo se serve un host diverso (caso raro): imposta VITE_API_URL al build.
 */
import { normalizeScannedQrId } from './utils/qrScan';
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
export const socialGetPosts = (personaggioId, onLogout, page = 1, pageSize = 30, options = {}) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  if (options?.hashtag) params.set('hashtag', String(options.hashtag).replace(/^#/, ''));
  return fetchAuthenticated(`/api/social/posts/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreatePost = (formData, personaggioId, onLogout) => {
  const endpoint = `/api/social/posts/${personaggioId ? `?personaggio_id=${personaggioId}` : ''}`;
  return fetchAuthenticated(endpoint, { method: 'POST', body: formData }, onLogout);
};

export const socialToggleLike = (postId, personaggioId, onLogout) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  const qs = params.toString();
  return fetchAuthenticated(
    `/api/social/posts/${postId}/like/${qs ? `?${qs}` : ''}`,
    {
      method: 'POST',
      body: personaggioId != null && personaggioId !== '' ? JSON.stringify({ personaggio_id: personaggioId }) : undefined,
    },
    onLogout
  );
};

export const socialToggleCommentLike = (postId, commentId, personaggioId, onLogout) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  const qs = params.toString();
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/like/${qs ? `?${qs}` : ''}`,
    {
      method: 'POST',
      body: personaggioId != null && personaggioId !== '' ? JSON.stringify({ personaggio_id: personaggioId }) : undefined,
    },
    onLogout
  );
};

export const socialGetComments = (postId, personaggioId, onLogout, page = 1, pageSize = 10) => {
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/posts/${postId}/comments/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateComment = (postId, testo, personaggioId, onLogout) => {
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${personaggioId ? `?personaggio_id=${personaggioId}` : ''}`,
    { method: 'POST', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialUpdateComment = (postId, commentId, testo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/${qp}`,
    { method: 'PATCH', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialDeleteComment = (postId, commentId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/posts/${postId}/comments/${commentId}/${qp}`,
    { method: 'DELETE' },
    onLogout
  );
};

export const socialGetMyProfile = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/profile/me/${qp}`, { method: 'GET' }, onLogout);
};

function formDataHasUpload(fd) {
  for (const value of fd.values()) {
    if (value instanceof Blob) return true;
  }
  return false;
}

function formDataToPlainObject(fd) {
  const out = {};
  for (const [key, value] of fd.entries()) {
    if (value instanceof Blob) continue;
    out[key] = String(value);
  }
  return out;
}

/**
 * Aggiorna profilo InstaFame.
 * - Oggetto plain o FormData senza file → JSON PATCH (UTF-8, emoji nel nickname/descrizione).
 * - FormData con file → multipart PATCH (solo upload foto).
 */
export const socialUpdateMyProfile = (payload, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  const endpoint = `/api/social/profile/me/${qp}`;

  if (payload instanceof FormData) {
    if (formDataHasUpload(payload)) {
      return fetchAuthenticated(endpoint, { method: 'PATCH', body: payload }, onLogout);
    }
    return fetchAuthenticated(
      endpoint,
      { method: 'PATCH', body: JSON.stringify(formDataToPlainObject(payload)) },
      onLogout
    );
  }

  return fetchAuthenticated(
    endpoint,
    { method: 'PATCH', body: JSON.stringify(payload || {}) },
    onLogout
  );
};

export const socialGetKorpList = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/korp/', { method: 'GET' }, onLogout);
};

export const socialGetProfileByCharacter = (personaggioId, onLogout) => {
  return fetchAuthenticated(`/api/social/profiles/${personaggioId}/`, { method: 'GET' }, onLogout);
};

export const socialGetPublicPostBySlug = (slug) => {
  return fetchPublic(`/api/social/public/posts/${slug}/`);
};

export const socialUpdatePost = (postId, formData, onLogout) => {
  return fetchAuthenticated(`/api/social/posts/${postId}/`, { method: 'PATCH', body: formData }, onLogout);
};

export const socialDeletePost = (postId, onLogout) => {
  return fetchAuthenticated(`/api/social/posts/${postId}/`, { method: 'DELETE' }, onLogout);
};

export const socialGetStaffEventReport = (eventoId, onLogout) => {
  const qp = eventoId ? `?evento_id=${eventoId}` : '';
  return fetchAuthenticated(`/api/social/staff/event-report/${qp}`, { method: 'GET' }, onLogout);
};

export const socialGetNotifications = (personaggioId, onLogout, options = {}) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  if (options.limit) params.set('limit', String(options.limit));
  if (options.since) params.set('since', String(options.since));
  const qs = params.toString();
  return fetchAuthenticated(`/api/social/notifications/${qs ? `?${qs}` : ''}`, { method: 'GET' }, onLogout);
};

export const socialGetGroups = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${qp}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroup = (payload, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${qp}`, { method: 'POST', body: JSON.stringify(payload) }, onLogout);
};

export const socialRequestJoinGroup = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/request_join/${qp}`, { method: 'POST' }, onLogout);
};

export const socialGetGroupPosts = (groupId, personaggioId, onLogout, page = 1, pageSize = 10) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroupPost = (groupId, formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${qp}`, { method: 'POST', body: formData }, onLogout);
};

export const socialUpdateGroupPost = (groupId, postId, formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${postId}/${qp}`, { method: 'PATCH', body: formData }, onLogout);
};

export const socialDeleteGroupPost = (groupId, postId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/posts/${postId}/${qp}`, { method: 'DELETE' }, onLogout);
};

export const socialGetGroupMessages = (groupId, personaggioId, onLogout, page = 1, pageSize = 20) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/groups/${groupId}/messages/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateGroupMessage = (groupId, testo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/messages/${qp}`,
    { method: 'POST', body: JSON.stringify({ testo }) },
    onLogout
  );
};

export const socialDeleteGroupMessage = (groupId, messageId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/messages/${messageId}/${qp}`, { method: 'DELETE' }, onLogout);
};

export const socialGetGroupMembers = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/members/${qp}`, { method: 'GET' }, onLogout);
};

export const socialInviteGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/invite/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialApproveGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/approve_member/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialRejectGroupMember = (groupId, personaggioTargetId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/reject_member/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId }) },
    onLogout
  );
};

export const socialSetGroupMemberRole = (groupId, personaggioTargetId, ruolo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/groups/${groupId}/set_member_role/${qp}`,
    { method: 'POST', body: JSON.stringify({ personaggio_target_id: personaggioTargetId, ruolo }) },
    onLogout
  );
};

export const socialAcceptGroupInvite = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/accept_invite/${qp}`, { method: 'POST' }, onLogout);
};

export const socialDeclineGroupInvite = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/decline_invite/${qp}`, { method: 'POST' }, onLogout);
};

export const socialLeaveGroup = (groupId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/groups/${groupId}/leave/${qp}`, { method: 'POST' }, onLogout);
};

// --- SOCIAL STORIES ---
export const socialGetStories = (personaggioId, onLogout, page = 1, pageSize = 50) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('page', String(page));
  params.set('page_size', String(pageSize));
  return fetchAuthenticated(`/api/social/stories/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialCreateStory = (formData, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${qp}`, { method: 'POST', body: formData }, onLogout);
};

export const socialMarkStoryViewed = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/viewed/${qp}`, { method: 'POST' }, onLogout);
};

export const socialReactStory = (storyId, emoji, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/${storyId}/react/${qp}`,
    { method: 'POST', body: JSON.stringify({ emoji }) },
    onLogout
  );
};

export const socialGetStoryReplies = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/replies/${qp}`, { method: 'GET' }, onLogout);
};

export const socialReplyStory = (storyId, testo, sendDm = true, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/${storyId}/replies/${qp}`,
    { method: 'POST', body: JSON.stringify({ testo, send_dm: !!sendDm }) },
    onLogout
  );
};

export const socialGetHighlights = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/highlights/${qp}`, { method: 'GET' }, onLogout);
};

export const socialCreateHighlight = (titolo, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/create_highlight/${qp}`,
    { method: 'POST', body: JSON.stringify({ titolo }) },
    onLogout
  );
};

export const socialAddStoryToHighlight = (highlightId, storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(
    `/api/social/stories/highlights/${highlightId}/add/${qp}`,
    { method: 'POST', body: JSON.stringify({ story_id: storyId }) },
    onLogout
  );
};

export const socialGetMyStoryActivity = (personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/my_activity/${qp}`, { method: 'GET' }, onLogout);
};

export const socialGetMyStoryHistory = (personaggioId, onLogout, includeExpired = true) => {
  const params = new URLSearchParams();
  if (personaggioId) params.set('personaggio_id', String(personaggioId));
  params.set('include_expired', includeExpired ? 'true' : 'false');
  return fetchAuthenticated(`/api/social/stories/my_history/?${params.toString()}`, { method: 'GET' }, onLogout);
};

export const socialConvertStoryToPost = (storyId, personaggioId, onLogout) => {
  const qp = personaggioId ? `?personaggio_id=${personaggioId}` : '';
  return fetchAuthenticated(`/api/social/stories/${storyId}/convert_to_post/${qp}`, { method: 'POST' }, onLogout);
};

// --- Funzioni API specifiche ---

/**
 * Recupera la configurazione degli slot corporei (costanti).
 * Utile se vuoi popolarli dinamicamente, altrimenti usiamo costanti nel frontend.
 */
export const getBodySlots = () => {
  // Possiamo hardcodarlo nel frontend per semplicità o fare una chiamata
  return [
      { code: 'HD1', name: 'Testa 1 (Cervello/Occhi)' },
      { code: 'HD2', name: 'Testa 2 (Volto/Orecchie)' },
      { code: 'TR1', name: 'Tronco 1 (Cuore/Polmoni)' },
      { code: 'TR2', name: 'Tronco 2 (Spina Dorsale/Pelle)' },
      { code: 'RA', name: 'Braccio Destro' },
      { code: 'LA', name: 'Braccio Sinistro' },
      { code: 'RL', name: 'Gamba Destra' },
      { code: 'LL', name: 'Gamba Sinistra' },
  ];
};

/**
 * Recupera la lista dei personaggi associati all'utente.
 */
export const getPersonaggiList = (onLogout, viewAll = false) => {
  const queryParam = viewAll ? '?view_all=true' : '';
  return fetchAuthenticated(`/api/personaggi/api/personaggi/${queryParam}`, { method: 'GET' }, onLogout);
};

/**
 * Recupera i dettagli di un personaggio specifico.
 */
export const getPersonaggioDetail = (id, onLogout) => {
  const cleanId = String(id ?? '').trim();
  if (!cleanId) {
    return Promise.reject(new Error('ID personaggio mancante.'));
  }
  return fetchAuthenticated(`/api/personaggi/api/personaggi/${cleanId}/`, { method: 'GET' }, onLogout);
};

/**
 * Snapshot compatto per modalità offline (stesso permesso del dettaglio personaggio).
 */
export const getPersonaggioGameState = (id, onLogout) => {
  const cleanId = String(id ?? '').trim();
  if (!cleanId) {
    return Promise.reject(new Error('ID personaggio mancante.'));
  }
  return fetchAuthenticated(`/api/personaggi/api/personaggi/${cleanId}/game_state/`, { method: 'GET' }, onLogout);
};

export const getQrCodeData = (qrId, onLogout, personaggioId = null, minigiocoSessionId = null) => {
  const cleanId = normalizeScannedQrId(qrId);
  const params = new URLSearchParams();
  if (personaggioId != null && personaggioId !== '') {
    params.set('personaggio_id', String(personaggioId));
  }
  if (minigiocoSessionId) {
    params.set('minigioco_session_id', String(minigiocoSessionId));
  }
  const q = params.toString() ? `?${params.toString()}` : '';
  return fetchAuthenticated(`/api/personaggi/api/qrcode/${cleanId}/${q}`, { method: 'GET' }, onLogout);
};

export const minigiocoComplete = (sessionId, personaggioId, stato, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/minigioco/${sessionId}/complete/`,
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: personaggioId, stato }),
    },
    onLogout
  );

export const minigiocoExpire = (sessionId, personaggioId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/minigioco/${sessionId}/expire/`,
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: personaggioId }),
    },
    onLogout
  );

export const staffGetMinigiocoQrConfig = (qrId, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/minigioco-qr/${qrId}/`, { method: 'GET' }, onLogout);

export const staffSaveMinigiocoQrConfig = (qrId, formData, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/minigioco-qr/${qrId}/`,
    { method: 'PUT', body: formData },
    onLogout
  );

export const staffGetMinigiocoBiblioteca = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/minigioco-biblioteca/', { method: 'GET' }, onLogout);

export const staffAggiornaMinigiocoBiblioteca = (target = 100, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/minigioco-biblioteca/aggiorna/',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ target }),
    },
    onLogout
  );

export const OPENVERSE_REGISTER_URL = 'https://api.openverse.org/v1/auth_tokens/register/';

/** Registrazione Openverse dal browser (bypass Cloudflare VPS). */
export async function openverseRegisterFromBrowser({ name, description, email }) {
  const resp = await fetch(OPENVERSE_REGISTER_URL, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      name: (name || '').trim(),
      description: (description || '').trim(),
      email: (email || '').trim(),
    }),
  });
  const text = await resp.text();
  let data = null;
  try {
    data = JSON.parse(text);
  } catch {
    data = null;
  }
  if (!resp.ok) {
    const cloudflare = /just a moment/i.test(text) || (/cloudflare/i.test(text) && /<!doctype html/i.test(text));
    const err = new Error(
      cloudflare
        ? 'Openverse bloccato da Cloudflare anche dal browser. Incolla le credenziali manualmente o riprova da un\'altra rete.'
        : `Openverse HTTP ${resp.status}: ${text.slice(0, 200)}`
    );
    err.cloudflare = cloudflare;
    throw err;
  }
  if (!data?.client_id || !data?.client_secret) {
    throw new Error('Risposta Openverse incompleta (mancano client_id o client_secret).');
  }
  return data;
}

export const staffSalvaOpenverseMinigioco = (payload, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/minigioco-biblioteca/openverse/salva/',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    onLogout
  );

export const staffRegistraOpenverseMinigioco = (payload, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/minigioco-biblioteca/openverse/registra/',
    {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    },
    onLogout
  );

export const staffVerificaOpenverseMinigioco = (onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/minigioco-biblioteca/openverse/verifica/',
    { method: 'POST' },
    onLogout
  );

export const staffInspectQrCode = (qrId, onLogout) => {
  return fetchAuthenticated(`/api/personaggi/api/staff/qr-inspect/${qrId}/`, { method: 'GET' }, onLogout);
};

export const staffQrInventarioScan = (payload, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/staff/qr-inventario-scan/',
    { method: 'POST', body: JSON.stringify(payload) },
    onLogout
  );
};

/**
 * Richiede un oggetto da un inventario (azione "Prendi") - Sistema legacy
 */
export const richiediTransazione = (oggettoId, mittenteInventarioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/transazioni/richiedi/', 
    {
      method: 'POST',
      body: JSON.stringify({
        oggetto_id: oggettoId,
        mittente_id: mittenteInventarioId,
      })
    },
    onLogout
  );
};

/**
 * Crea una nuova transazione avanzata con proposta iniziale
 */
export const createTransazioneAvanzata = (destinatarioId, proposta, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/transazioni/avanzata/',
    {
      method: 'POST',
      body: JSON.stringify({
        destinatario_id: destinatarioId,
        proposta: proposta
      })
    },
    onLogout
  );
};

/**
 * Recupera il dettaglio di una transazione con tutte le proposte
 */
export const getTransazioneDetail = (transazioneId, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/transazioni/${transazioneId}/`,
    { method: 'GET' },
    onLogout
  );
};

/**
 * Aggiunge una proposta (controproposta o rilancio) a una transazione
 */
export const addPropostaTransazione = (transazioneId, proposta, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/transazioni/${transazioneId}/proposta/`,
    {
      method: 'POST',
      body: JSON.stringify(proposta)
    },
    onLogout
  );
};

/**
 * Accetta o rifiuta una transazione
 */
export const confermaTransazione = (transazioneId, azione, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/transazioni/${transazioneId}/conferma/`,
    {
      method: 'POST',
      body: JSON.stringify({ azione: azione }) // 'accetta' o 'rifiuta'
    },
    onLogout
  );
};

/**
 * Tenta di rubare un oggetto da un personaggio (azione "Ruba").
 */
export const rubaOggetto = (oggettoId, targetPersonaggioId, onLogout, personaggioId = null) => {
  const body = {
    oggetto_id: oggettoId,
    target_personaggio_id: targetPersonaggioId,
  };
  if (personaggioId != null && personaggioId !== '') body.personaggio_id = personaggioId;
  return fetchAuthenticated(
    '/api/personaggi/api/transazioni/ruba/', 
    {
      method: 'POST',
      body: JSON.stringify(body)
    },
    onLogout
  );
};

/**
 * Acquisisce un oggetto/attivata da un QR code.
 */
export const acquisisciItem = (qrCodeId, onLogout, personaggioId = null) => {
  const body = { qrcode_id: qrCodeId };
  if (personaggioId != null && personaggioId !== '') body.personaggio_id = personaggioId;
  return fetchAuthenticated(
    '/api/personaggi/api/transazioni/acquisisci/', 
    {
      method: 'POST',
      body: JSON.stringify(body)
    },
    onLogout
  );
};

/**
 * Recupera la lista master di tutte le abilità.
 * @deprecated Non più usata, sostituita da getAcquirableSkills e dati da getPersonaggioDetail
 */
export const getAbilitaMasterList = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/abilita/master_list/', { method: 'GET' }, onLogout);
};

/**
 * Tenta di acquisire un'abilità per il personaggio loggato.
 */
export const acquireAbilita = (abilitaId, characterId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/acquisisci_abilita/', 
    {
      method: 'POST',
      body: JSON.stringify({
        abilita_id: abilitaId,
        personaggio_id: characterId, // <-- NUOVO: Passa l'ID al backend
      })
    },
    onLogout
  );
};

/**
 * Revoca l'acquisto di un'abilità.
 */
export const revokeAbilita = (abilitaId, characterId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/revoca_abilita/',
    {
      method: 'POST',
      body: JSON.stringify({
        abilita_id: abilitaId,
        personaggio_id: characterId,
      }),
    },
    onLogout
  );
};

/**
 * Recupera la lista di tutti i punteggi (Caratteristiche, Statistiche, ecc).
 */
export const getPunteggiList = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/punteggi/all/', { method: 'GET' }, onLogout);
};

/**
 * Recupera la lista dei contenitori statistiche (configurazione scheda).
 * GET /api/personaggi/api/statistiche/containers/
 */
export const getStatisticaContainers = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/statistiche/containers/', { method: 'GET' }, onLogout);
};


// --- MODIFICA CHIAVE ---
// Questa è la versione corretta della funzione che usa il tuo
// helper 'fetchAuthenticated' e l'URL corretto.
// Sostituisce la versione errata che ti avevo dato.

/**
 * Recupera la lista *filtrata* di abilità acquistabili per il personaggio.
 * GET /api/personaggi/api/personaggio/me/abilita_acquistabili/
 */
export const getAcquirableSkills = (onLogout, selectedCharacterId) => {
  // Aggiunge l'ID del personaggio come query parameter. Il backend dovrà leggere 'char_id'.
  const queryParam = selectedCharacterId ? `?char_id=${selectedCharacterId}` : '';
  
  return fetchAuthenticated(
    `/api/personaggi/api/personaggio/me/abilita_acquistabili/${queryParam}`, // <--- AGGIUNTO queryParam
    { method: 'GET' }, 
    onLogout
  );
};

/**
 * GET /api/personaggi/api/messaggi/ - Ottiene la lista dei messaggi per il PG loggato.
 */
export const getMessages = (personaggioId, onLogout) => {
  if (!personaggioId) {
    return Promise.resolve([]); // Ritorna un array vuoto se l'ID non è fornito
  }
  const url = `/api/personaggi/api/messaggi/?personaggio_id=${personaggioId}`;

  return fetchAuthenticated(url, { method: 'GET' }, onLogout);
};

export const getMessageUnreadCounts = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/messaggi/unread_counts/', { method: 'GET' }, onLogout);
};

/**
 * POST /api/personaggi/api/messaggi/broadcast/send/ - Invia un messaggio Broadcast.
 */
export const postBroadcastMessage = (messageData, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/messaggi/broadcast/send/',
    {
      method: 'POST',
      body: JSON.stringify(messageData)
    },
    onLogout
  );
};

/**
 * GET /api/personaggi/api/messaggi/admin/sent/ - Ottiene i messaggi inviati dall'admin.
 */
export const getAdminSentMessages = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/messaggi/admin/sent/', { method: 'GET' }, onLogout);
};

export const saveWebPushSubscription = async (subscription, onLogout) => {
    const token = localStorage.getItem('kor35_token'); // O il nome chiave che usi tu
    
    if (!token) return;

    const response = await fetch(`${API_BASE_URL}/api/personaggi/api/webpush/subscribe/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Token ${token}` // FONDAMENTALE: Invia l'identità dell'utente
        },
        body: JSON.stringify(subscription)
    });

    if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Errore server (${response.status}): ${errorText}`);
    }

    return await response.json();
};

// --- NUOVE FUNZIONI PER INFUSIONI E TESSITURE ---

/**
 * Recupera la lista delle infusioni acquistabili.
 */
export const getAcquirableInfusioni = (characterId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/personaggio/me/infusioni_acquistabili/?char_id=${characterId}`, 
    { method: 'GET' }
  );
};

/**
 * Acquisisce un'infusione.
 */
export const acquireInfusione = (infusioneId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/acquisisci_infusione/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        infusione_id: infusioneId, 
        personaggio_id: personaggioId 
      }),
    }, 
    onLogout
  );
};

/**
 * Revoca l'acquisto di un'infusione.
 */
export const revokeInfusione = (infusioneId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/revoca_infusione/',
    {
      method: 'POST',
      body: JSON.stringify({
        infusione_id: infusioneId,
        personaggio_id: personaggioId,
      }),
    },
    onLogout
  );
};

/**
 * Recupera la lista delle tessiture acquistabili.
 */
export const getAcquirableTessiture = (characterId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/personaggio/me/tessiture_acquistabili/?char_id=${characterId}`, 
    { method: 'GET' }
  );
};

/**
 * Acquisisce una tessitura.
 */
export const acquireTessitura = (tessituraId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/acquisisci_tessitura/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        tessitura_id: tessituraId, 
        personaggio_id: personaggioId 
      }),
    }, 
    onLogout
  );
};

/**
 * Revoca l'acquisto di una tessitura.
 */
export const revokeTessitura = (tessituraId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/revoca_tessitura/',
    {
      method: 'POST',
      body: JSON.stringify({
        tessitura_id: tessituraId,
        personaggio_id: personaggioId,
      }),
    },
    onLogout
  );
};

/**
 * Revoca l'acquisto di un cerimoniale.
 */
export const revokeCerimoniale = (cerimonialeId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/revoca_cerimoniale/',
    {
      method: 'POST',
      body: JSON.stringify({
        cerimoniale_id: cerimonialeId,
        personaggio_id: personaggioId,
      }),
    },
    onLogout
  );
};

/**
 * Toggle favorite status di una tessitura.
 */
export const consumaConsumabile = (consumabileId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/consuma_consumabile/',
    {
      method: 'POST',
      body: JSON.stringify({
        consumabile_id: consumabileId,
        personaggio_id: personaggioId,
      }),
    },
    onLogout
  );
};

export const toggleTessituraFavorite = (tessituraId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/toggle_tessitura_favorite/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        tessitura_id: tessituraId, 
        personaggio_id: personaggioId 
      }),
    }, 
    onLogout
  );
};

/**
 * Avvia la creazione di un consumabile da tessitura (Alchimia). Costo e tempo dipendono dall'aura della tessitura.
 */
export const avviaCreazioneConsumabile = (tessituraId, personaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/avvia_creazione_consumabile/',
    {
      method: 'POST',
      body: JSON.stringify({ tessitura_id: tessituraId, personaggio_id: personaggioId }),
    },
    onLogout
  );
};

/**
 * Completa una creazione consumabile scaduta e aggiunge il consumabile all'inventario.
 * fetchAuthenticated restituisce già il body parsato, non la Response.
 */
export const completaCreazioneConsumabile = (personaggioId, creazioneId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/completa_creazione_consumabile/',
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: personaggioId, creazione_id: creazioneId ?? null }),
    },
    onLogout
  );
};

export const getModelliAura = (auraId) => {
  return fetchAuthenticated(`/api/personaggi/api/punteggio/${auraId}/modelli/`, { method: 'GET' });
};

export const selezionaModelloAura = (personaggioId, modelloId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggio/me/seleziona_modello_aura/', 
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: personaggioId, modello_id: modelloId })
    }, 
    onLogout
  );
};

export const getProposte = async (charId) => {
    // fetchAuthenticated restituisce già i dati, non la response raw.
    // L'errore viene gestito internamente a fetchAuthenticated.
    return await fetchAuthenticated(`/api/personaggi/api/proposte/?char_id=${charId}`, {
        method: 'GET'
    });
};

export const createProposta = async (data) => {
    return await fetchAuthenticated(`/api/personaggi/api/proposte/`, {
        method: 'POST',
        body: JSON.stringify(data)
    });
};

export const updateProposta = async (id, data) => {
    return await fetchAuthenticated(`/api/personaggi/api/proposte/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    });
};

export const deleteProposta = async (id) => {
    // Qui fetchAuthenticated potrebbe tornare null (204 No Content), va bene così.
    await fetchAuthenticated(`/api/personaggi/api/proposte/${id}/`, {
        method: 'DELETE'
    });
    return true;
};

export const sendProposta = async (id) => {
    return await fetchAuthenticated(`/api/personaggi/api/proposte/${id}/invia_proposta/`, {
        method: 'POST'
    });
};

// --- UTILITIES PUNTEGGI ---

export const getAllPunteggi = async () => {
    // Assicurati che l'URL finisca con /all/ come definito in urls.py
    return await fetchAuthenticated(`/api/personaggi/api/punteggi/all/`, {
        method: 'GET'
    });
};

/**
 * Mattoni per aura; con personaggioId filtra i proibiti in base al modello di aura scelto dal PG.
 * Risposta normalizzata: { mattoni, obbligatorie_caratteristica_ids }.
 */
export const getMattoniAura = async (auraId, personaggioId = null) => {
    const q = personaggioId ? `?personaggio_id=${encodeURIComponent(personaggioId)}` : '';
    const raw = await fetchAuthenticated(`/api/personaggi/api/punteggio/${auraId}/mattoni/${q}`, {
        method: 'GET'
    });
    if (Array.isArray(raw)) {
        return { mattoni: raw, obbligatorie_caratteristica_ids: [] };
    }
    return {
        mattoni: raw?.mattoni ?? [],
        obbligatorie_caratteristica_ids: raw?.obbligatorie_caratteristica_ids ?? [],
    };
};

export const getAdminPendingProposalsCount = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/admin/pending_proposals_count/', { method: 'GET' }, onLogout);
};

export const markMessageAsRead = (messageId, characterId, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/messaggi/${messageId}/leggi/`,
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: characterId })
    },
    onLogout
  );
};

/**
 * Cancella un messaggio (soft delete per l'utente).
 * POST /api/personaggi/api/messaggi/<id>/cancella/
 */
export const deleteMessage = (messageId, characterId, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/messaggi/${messageId}/cancella/`,
    {
      method: 'POST',
      body: JSON.stringify({ personaggio_id: characterId })
    },
    onLogout
  );
};

/**
 * Recupera i log paginati.
 * @param {number} page - Numero di pagina (default 1)
 */
export const getPersonaggioLogs = (page = 1) => {
  return fetchAuthenticated(`/api/personaggi/api/personaggio/me/logs/?page=${page}`, { method: 'GET' });
};

/**
 * Recupera le transazioni paginate.
 * @param {number} page - Numero di pagina
 * @param {string} tipo - 'entrata' o 'uscita'
 * @param {string} charId - ID del personaggio (opzionale)
 */
export const getPersonaggioTransazioni = (page = 1, tipo = 'entrata', charId = null) => {
  let url = `/api/personaggi/api/personaggio/me/transazioni/?page=${page}&tipo=${tipo}`;
  if (charId) {
    url += `&char_id=${charId}`;
  }
  return fetchAuthenticated(url, { method: 'GET' });
}
/**
 * Cerca personaggi per nome (Autocomplete)
 * Opzionalmente filtra per compatibilità con un'infusione (Innesto).
 */
export const searchPersonaggi = (query, currentCharacterId, infusioneId = null) => {
  let url = `/api/personaggi/api/personaggi/search/?q=${encodeURIComponent(query)}&current_char_id=${currentCharacterId}`;
  if (infusioneId) {
      url += `&infusione_id=${infusioneId}`;
  }
  return fetchAuthenticated(url, { method: 'GET' });
};

export const getPreferredPersonaggio = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/personaggi/preferred/', { method: 'GET' }, onLogout);
};

export const setPreferredPersonaggio = (preferredPersonaggioId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/personaggi/preferred/',
    {
      method: 'POST',
      body: JSON.stringify({ preferred_personaggio_id: preferredPersonaggioId || null }),
    },
    onLogout
  );
};

/**
 * Invia un messaggio privato
 */
export const sendPrivateMessage = (messageData, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/messaggi/send/',
    {
      method: 'POST',
      body: JSON.stringify(messageData)
    },
    onLogout
  );
};

// Crea un oggetto fisico a partire da un'infusione
export const craftOggetto = (infusioneId) => {
  return fetchAuthenticated('/api/personaggi/api/oggetti/craft/', {
    method: 'POST',
    body: JSON.stringify({ infusione_id: infusioneId })
  });
};

// // Monta un potenziamento (Mod/Materia) su un oggetto ospite
// export const montaPotenziamento = (ospiteId, potenziamentoId) => {
//   return fetchAuthenticated(`/api/personaggi/api/oggetti/${ospiteId}/monta/`, {
//     method: 'POST',
//     body: JSON.stringify({ potenziamento_id: potenziamentoId })
//   });
// };

// Smonta un potenziamento
export const smontaPotenziamento = (ospiteId, potenziamentoId) => {
  return fetchAuthenticated(`/api/personaggi/api/oggetti/${ospiteId}/smonta/`, {
    method: 'POST',
    body: JSON.stringify({ potenziamento_id: potenziamentoId })
  });
};

// Usa una carica (Mod, Innesti, Oggetti)
export const usaCarica = (oggettoId) => {
  return fetchAuthenticated(`/api/personaggi/api/oggetti/${oggettoId}/usa_carica/`, {
    method: 'POST'
  });
};

// Ricarica oggetto (pagando crediti)
export const ricaricaOggetto = (oggettoId) => {
  return fetchAuthenticated(`/api/personaggi/api/oggetti/${oggettoId}/ricarica/`, {
    method: 'POST'
  });
};

// --- API INVENTARIO & OGGETTI ---

/**
 * Recupera i dettagli di un oggetto tramite ID
 * GET /api/personaggi/api/oggetti/<id>/
 */
export const getOggettoDetail = (oggettoId, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/oggetti/${oggettoId}/`,
    { method: 'GET' },
    onLogout
  );
};

/**
 * Equipaggia o disequipaggia un oggetto fisico.
 * POST /api/personaggi/api/oggetti/equipaggia/
 */
export const equipaggiaOggetto = (itemId, characterId, slotKey = null, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/equipaggia/', 
    {
      method: 'POST',
      // Invia anche char_id nel JSON
      body: JSON.stringify({ 
          item_id: itemId,
          char_id: characterId,
          slot_key: slotKey,
      })
    },
    onLogout
  );
};

export const danneggiaOggetto = (itemId, characterId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/danneggia/',
    {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
        char_id: characterId,
      }),
    },
    onLogout
  );
};

export const riparaOggetto = (itemId, characterId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/ripara/',
    {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
        char_id: characterId,
      }),
    },
    onLogout
  );
};

export const scartaOggetto = (itemId, characterId, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/scarta/',
    {
      method: 'POST',
      body: JSON.stringify({
        item_id: itemId,
        char_id: characterId,
      }),
    },
    onLogout
  );
};

export const assemblaOggetto = (hostId, modId, characterId, useAcademy = false, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/assembla/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        host_id: hostId, 
        mod_id: modId,
        char_id: characterId,
        use_academy: useAcademy // Parametro nuovo
      })
    },
    onLogout
  );
};

export const smontaOggetto = (hostId, modId, characterId, useAcademy = false, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/smonta/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        host_id: hostId, 
        mod_id: modId,
        char_id: characterId,
        use_academy: useAcademy
      })
    },
    onLogout
  );
};

// Se hai bisogno del crafting nel frontend in futuro:
export const craftOggettoFromInfusione = (infusioneId, targetId, qrCode, onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/oggetti/craft/',
    {
      method: 'POST',
      body: JSON.stringify({
        infusione_id: infusioneId,
        target_id: targetId,
        qr_code: qrCode
      })
    },
    onLogout
  );
};

export const startForging = (infusioneId, charId, slotTarget = null) => {
  return fetchAuthenticated(
    '/api/personaggi/api/crafting/avvia_forgiatura/',
    {
      method: 'POST',
      body: JSON.stringify({ 
        infusione_id: infusioneId, 
        char_id: charId,
        slot_target: slotTarget
      })
    }
  );
};

export const completeForging = (forgiaturaId, charId) => {
  return fetchAuthenticated(
    '/api/personaggi/api/crafting/completa_forgiatura/',
    {
      method: 'POST',
      body: JSON.stringify({ 
        forgiatura_id: forgiaturaId, 
        char_id: charId 
      })
    }
  );
};

export const getForgingQueue = (charId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/crafting/coda_forgiatura/?char_id=${charId}`,
    { method: 'GET' }
  );
};

// --- API NEGOZIO (SHOP) ---

export const getShopItems = () => {
  return fetchAuthenticated(
    '/api/personaggi/api/negozio/listino/',
    { method: 'GET' }
  );
};

export const buyShopItem = (oggettoId, charId) => {
  return fetchAuthenticated(
    '/api/personaggi/api/negozio/acquista/',
    {
      method: 'POST',
      body: JSON.stringify({ 
        oggetto_id: oggettoId, 
        char_id: charId 
      })
    }
  );
};

/**
 * Valida la compatibilità e le competenze per un assemblaggio.
 */
export const validateAssembly = (charId, hostId, modId) => {
  return fetchAuthenticated(
    '/api/personaggi/api/assembly/validate/', 
    {
      method: 'POST',
      body: JSON.stringify({
        char_id: charId,
        host_id: hostId,
        mod_id: modId
      })
    }
  );
};

/**
 * Crea una richiesta di lavoro (Installazione o Rimozione).
 * @param {string} operationType - 'INST' (Default) o 'RIMO'
 */
export const createAssemblyRequest = (charId, hostId, modId, artisanName, offer, operationType = 'INST') => {
  return fetchAuthenticated(
    '/api/personaggi/api/richieste-assemblaggio/crea/', 
    {
      method: 'POST',
      body: JSON.stringify({
        committente_id: charId,
        host_id: hostId,
        comp_id: modId,
        artigiano_nome: artisanName,
        offerta: offer,
        tipo_operazione: operationType // <--- Passa il tipo al backend
      })
    }
  );
};

/**
 * Accetta una richiesta di assemblaggio (Lato Artigiano).
 */
export const acceptAssemblyRequest = (requestId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/richieste-assemblaggio/${requestId}/accetta/`, 
    { method: 'POST' }
  );
};

/**
 * Rifiuta una richiesta di assemblaggio (Lato Artigiano).
 */
export const rejectAssemblyRequest = (requestId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/richieste-assemblaggio/${requestId}/rifiuta/`, 
    { method: 'POST' }
  );
};

/**
 * Recupera le richieste di assemblaggio (inviate o ricevute).
 */
export const getAssemblyRequests = () => {
  return fetchAuthenticated(
    '/api/personaggi/api/richieste-assemblaggio/', 
    { method: 'GET' }
  );
};

// Aggiungi questa funzione per recuperare gli artigiani capaci
// Questa va bene per entrambi (Assemblaggio e Forgiatura)
export const getCapableArtisans = (charId, hostId, modId, infusioneId) => {
  return fetchAuthenticated('/api/personaggi/api/assembly/artisans/', {
      method: 'POST',
      body: JSON.stringify({ 
        char_id: charId, 
        host_id: hostId, 
        mod_id: modId, 
        infusione_id: infusioneId 
      })
  });
};

export const forgiaOggetto = (infusioneId, charId, useAcademy = false) => {
  return fetchAuthenticated('/api/personaggi/api/oggetti/forgia/', {
      method: 'POST',
      body: JSON.stringify({ 
        infusione_id: infusioneId, 
        char_id: charId, 
        use_academy: useAcademy 
      })
  });
};

export const createForgingRequest = (charId, infusioneId, artisanName, offer) => {
  return fetchAuthenticated('/api/personaggi/api/richieste-assemblaggio/crea/', {
      method: 'POST',
      body: JSON.stringify({
        committente_id: charId,
        infusione_id: infusioneId,
        artigiano_nome: artisanName,
        offerta: offer,
        tipo_operazione: 'FORG'
      })
  });
};

export const validateForging = (charId, infusioneId) => {
  return fetchAuthenticated('/api/personaggi/api/forging/validate/', {
      method: 'POST',
      body: JSON.stringify({ 
        char_id: charId, 
        infusione_id: infusioneId 
      })
  });
};

export const getClassiOggetto = () => {
  return fetchAuthenticated('/api/personaggi/api/classi_oggetto/', { method: 'GET' });
};

/**
 * Esegue l'installazione di un innesto da una forgiatura completata.
 * (Operazione "Fai da te" o "Accettazione diretta")
 */
export const installaInnesto = (forgiaturaId, slot, characterId, targetId = null) => {
  return fetchAuthenticated(
    '/api/personaggi/api/crafting/completa_forgiatura/', 
    {
      method: 'POST',
      body: JSON.stringify({ 
        forgiatura_id: forgiaturaId, 
        char_id: characterId, // Chi esegue l'azione (Forgiatore)
        slot_scelto: slot,
        target_id: targetId   // NUOVO: Chi riceve l'innesto (Destinatario)
      })
    }
  );
}

/**
 * Crea una richiesta di operazione chirurgica a un altro giocatore.
 */
export const richiediOperazioneChirurgica = (forgiaturaId, slot, medicoNome, offerta, characterId) => {
  return fetchAuthenticated(
    '/api/personaggi/api/richieste-assemblaggio/crea/', 
    {
      method: 'POST',
      body: JSON.stringify({
        committente_id: characterId,
        forgiatura_id: forgiaturaId,
        slot_destinazione: slot,
        artigiano_nome: medicoNome,
        offerta: offerta,
        tipo_operazione: 'GRAF' // Codice per Graft/Innesto
      })
    }
  );
};

export const richiediAssemblaggio = (data) => {
  return fetchAuthenticated(
    '/api/personaggi/api/richieste-assemblaggio/crea/', 
    {
      method: 'POST',
      body: JSON.stringify(data)
    }
  );
};

/**
 * Rifiuta una richiesta (Wrapper per coerenza di naming).
 */
export const rifiutaRichiestaAssemblaggio = (requestId) => {
  return fetchAuthenticated(
    `/api/personaggi/api/richieste-assemblaggio/${requestId}/rifiuta/`, 
    { method: 'POST' }
  );
};

/**
 * Aggiorna parzialmente i dati del personaggio (es. impostazioni UI).
 */
export const updatePersonaggioSettings = (charId, settingsData, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/personaggi/${charId}/`, 
    {
      method: 'PATCH',
      body: JSON.stringify({ impostazioni_ui: settingsData })
    }, 
    onLogout
  );
};

// --- FUNZIONI CERIMONIALI ---

export const getAcquirableCerimoniali = (charId, onLogout) => {
    return fetchAuthenticated(
        `/api/personaggi/api/personaggio/me/cerimoniali_acquistabili/?char_id=${charId}`, 
        { method: 'GET' }, 
        onLogout
    );
}

// Modifica HP di un mostro in tempo reale
export const updateMostroHp = (mostroId, delta, onLogout) => {
  return fetchAuthenticated(
    `/api/plot/api/mostri-istanza/${mostroId}/modifica_hp/`,
    {
      method: 'POST',
      body: JSON.stringify({ delta })
    },
    onLogout
  );
};

// Associa un QR code scansionato a un oggetto "Vista" della quest
export const associaQrAVista = (vistaId, qrId, onLogout, force = false) => {
  return fetchAuthenticated(
    `/api/plot/api/viste-setup/${vistaId}/associa_qr/`,
    {
      method: 'POST',
      body: JSON.stringify({ qr_id: qrId, force: force })
    },
    onLogout
  );
};

// Associa QR direttamente a un elemento derivato da A_vista (Tessitura, Infusione, Cerimoniale, Oggetto, OggettoBase, Inventario)
export const associaQrDiretto = (aVistaId, qrId, onLogout, force = false) => {
  return fetchAuthenticated(
    `/api/personaggi/api/a-vista/${aVistaId}/associa-qr/`,
    {
      method: 'POST',
      body: JSON.stringify({ qr_id: qrId, force: force })
    },
    onLogout
  );
};

// --- EVENTI ---
export const getEventi = (onLogout) => fetchAuthenticated('/api/plot/api/eventi/', { method: 'GET' }, onLogout);
export const createEvento = (data, onLogout) => fetchAuthenticated('/api/plot/api/eventi/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const updateEvento = (id, data, onLogout) => fetchAuthenticated(`/api/plot/api/eventi/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const deleteEvento = (id, onLogout) => fetchAuthenticated(`/api/plot/api/eventi/${id}/`, { method: 'DELETE' }, onLogout);
export const iniziaEvento = (id, onLogout) =>
  fetchAuthenticated(`/api/plot/api/eventi/${id}/inizia/`, { method: 'POST', body: '{}' }, onLogout);
export const terminaEvento = (id, onLogout) =>
  fetchAuthenticated(`/api/plot/api/eventi/${id}/termina/`, { method: 'POST', body: '{}' }, onLogout);
export const reportRicompenseEvento = (id, onLogout) =>
  fetchAuthenticated(`/api/plot/api/eventi/${id}/report_ricompense/`, { method: 'GET' }, onLogout);

/** Elenco eventi con iscrizione aperta, requisiti utente e meta PayPal (client id per SDK). */
export const getIscrizioniEventoEligibility = (onLogout) =>
  fetchAuthenticated('/api/plot/iscrizioni-evento/eligibility/', { method: 'GET' }, onLogout);

/** Body: { evento_id, personaggio_id, tipo?, opzione_sync_ids? } → { paypal_order_id, sandbox } */
export const postIscrizioneEventoCreaOrdine = (body, onLogout) =>
  fetchAuthenticated('/api/plot/iscrizioni-evento/crea-ordine/', {
    method: 'POST',
    body: JSON.stringify(body),
  }, onLogout);

/** Body: { paypal_order_id } → conferma iscrizione dopo approve PayPal */
export const postIscrizioneEventoCattura = (body, onLogout) =>
  fetchAuthenticated('/api/plot/iscrizioni-evento/cattura/', {
    method: 'POST',
    body: JSON.stringify(body),
  }, onLogout);

/** Body: { paypal_order_id } -> marca tentativo annullato */
export const postIscrizioneEventoAnnulla = (body, onLogout) =>
  fetchAuthenticated('/api/plot/iscrizioni-evento/annulla/', {
    method: 'POST',
    body: JSON.stringify(body),
  }, onLogout);

/** POST idempotente: accredita PC/crediti d'evento se siamo in giornata evento (una tantum per PG/evento). */
export const postEventoPremiApplica = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/evento-premi/applica/', { method: 'POST', body: '{}' }, onLogout);

// --- NEGOZI MERCANTE ---
export const fetchNegoziCorporativi = (charId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/negozi-mercante/corporativi/?char_id=${charId}`,
    { method: 'GET' },
    onLogout,
  );

export const fetchNegozioMercanteListino = (negozioId, charId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/negozi-mercante/${negozioId}/listino/?char_id=${charId}`,
    { method: 'GET' },
    onLogout,
  );

export const acquistaNegozioMercante = (negozioId, body, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/negozi-mercante/${negozioId}/acquista/`,
    { method: 'POST', body: JSON.stringify(body) },
    onLogout,
  );

export const vendiOggettoNegozioMercante = (negozioId, charId, oggettoId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/negozi-mercante/${negozioId}/vendi/`,
    {
      method: 'POST',
      body: JSON.stringify({ char_id: charId, oggetto_id: oggettoId }),
    },
    onLogout,
  );

export const previewVenditaNegozioMercante = (negozioId, charId, oggettoId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/negozi-mercante/${negozioId}/preview-vendita/?char_id=${charId}&oggetto_id=${oggettoId}`,
    { method: 'GET' },
    onLogout,
  );

export const staffAssociaQrNegozioMercante = (negozioId, qrId, onLogout, force = false) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante/${negozioId}/associa-qr/`,
    {
      method: 'POST',
      body: JSON.stringify({ qr_id: qrId, force }),
    },
    onLogout,
  );

export const staffScollegaQrNegozioMercante = (negozioId, onLogout) =>
  staffAssociaQrNegozioMercante(negozioId, null, onLogout);

export const staffGetNegoziMercante = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/negozi-mercante/', { method: 'GET' }, onLogout);

export const staffCreateNegozioMercante = (data, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/negozi-mercante/',
    { method: 'POST', body: JSON.stringify(data) },
    onLogout,
  );

export const staffUpdateNegozioMercante = (id, data, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante/${id}/`,
    { method: 'PATCH', body: JSON.stringify(data) },
    onLogout,
  );

export const staffGetNegozioMercanteVoci = (negozioId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante-voci/?negozio=${negozioId}`,
    { method: 'GET' },
    onLogout,
  );

export const staffCreateNegozioMercanteVoce = (data, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/negozi-mercante-voci/',
    { method: 'POST', body: JSON.stringify(data) },
    onLogout,
  );

export const staffUpdateNegozioMercanteVoce = (id, data, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante-voci/${id}/`,
    { method: 'PATCH', body: JSON.stringify(data) },
    onLogout,
  );

export const staffDeleteNegozioMercanteVoce = (id, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante-voci/${id}/`,
    { method: 'DELETE' },
    onLogout,
  );

export const staffGetNegozioMercanteReadiness = (negozioId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante/${negozioId}/readiness/`,
    { method: 'GET' },
    onLogout,
  );

export const staffGetNegozioMercanteMovimenti = (negozioId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/staff/negozi-mercante/${negozioId}/movimenti/`,
    { method: 'GET' },
    onLogout,
  );

// --- GIORNI ---
export const createGiorno = (data, onLogout) => fetchAuthenticated('/api/plot/api/giorni/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const updateGiorno = (id, data, onLogout) => fetchAuthenticated(`/api/plot/api/giorni/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const deleteGiorno = (id, onLogout) => fetchAuthenticated(`/api/plot/api/giorni/${id}/`, { method: 'DELETE' }, onLogout);

// --- QUESTS ---
export const createQuest = (data, onLogout) => fetchAuthenticated('/api/plot/api/quests/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const updateQuest = (id, data, onLogout) => fetchAuthenticated(`/api/plot/api/quests/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const deleteQuest = (id, onLogout) => fetchAuthenticated(`/api/plot/api/quests/${id}/`, { method: 'DELETE' }, onLogout);

// Recupera tutte le liste per i dropdown dell'editor
export const getRisorseEditor = (onLogout) => fetchAuthenticated('/api/plot/api/eventi/risorse_editor/', { method: 'GET' }, onLogout);
export const getAVistaDisponibili = (onLogout) => fetchAuthenticated('/api/plot/api/eventi/a_vista_disponibili/', { method: 'GET' }, onLogout);

// Operazioni su PnG, Mostri e Viste
// export const addPngToQuest = (data, onLogout) => fetchAuthenticated('/api/plot/api/png-assegnati/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
// export const addMostroToQuest = (data, onLogout) => fetchAuthenticated('/api/plot/api/mostri-istanza/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
// export const addVistaToQuest = (data, onLogout) => fetchAuthenticated('/api/plot/api/viste-setup/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const removePngFromQuest = (id, onLogout) => fetchAuthenticated(`/api/plot/api/png-assegnati/${id}/`, { method: 'DELETE' }, onLogout);
export const removeMostroFromQuest = (id, onLogout) => fetchAuthenticated(`/api/plot/api/mostri-istanza/${id}/`, { method: 'DELETE' }, onLogout);
export const removeVistaFromQuest = (id, onLogout) => fetchAuthenticated(`/api/plot/api/viste-setup/${id}/`, { method: 'DELETE' }, onLogout);

export const addPngToQuest = (questId, personaggioId, stafferId, onLogout) => {
    const payload = {
        quest: parseInt(questId),
        personaggio: parseInt(personaggioId),
        staffer: stafferId ? parseInt(stafferId) : null
    };
    return fetchAuthenticated('/api/plot/api/png-assegnati/', { method: 'POST', body: JSON.stringify(payload) }, onLogout);
};

// Correzione Mostri
export const addMostroToQuest = (questId, templateId, stafferId, onLogout) => {
    const payload = {
        quest: parseInt(questId),
        template: parseInt(templateId),
        staffer: stafferId ? parseInt(stafferId) : null
    };
    return fetchAuthenticated('/api/plot/api/mostri-istanza/', { method: 'POST', body: JSON.stringify(payload) }, onLogout);
};

// Correzione Viste: accetta l'oggetto vistaPayload
export const addVistaToQuest = (questId, data, onLogout) => {
    const payload = {
        quest: parseInt(questId),
        tipo: data.tipo,
        a_vista_id: data.tipo === 'NEG' ? data.a_vista_id : parseInt(data.a_vista_id, 10),
    };
    return fetchAuthenticated('/api/plot/api/viste-setup/', { method: 'POST', body: JSON.stringify(payload) }, onLogout);
};

/** --- STRUMENTI MASTER --- **/

// Recupera la lista di tutte le statistiche definite nel sistema
export const getStatisticheList = (onLogout) => {
  return fetchAuthenticated('/api/personaggi/api/statistiche/', { method: 'GET' }, onLogout);
};

export const staffGetFormulaBuilderSchema = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/formula-builder/schema/', { method: 'GET' }, onLogout);

export const staffPreviewFormulaBuilder = (payload, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/staff/formula-builder/preview/',
    { method: 'POST', body: JSON.stringify(payload || {}) },
    onLogout
  );

export const staffGetFormulaSemanticOptions = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/formula-semantic-options/', { method: 'GET' }, onLogout);

// --- INFUSIONI ---
export const staffGetInfusioni = (onLogout, params = {}) => {
  // Costruiamo la query string (es: ?page=1&search=pippo)
  const queryString = new URLSearchParams(params).toString();
  return fetchAuthenticated(`/api/personaggi/api/staff/infusioni/?${queryString}`, { method: 'GET' }, onLogout);
};

export const staffCreateInfusione = (data, onLogout) => 
  fetchAuthenticated('/api/personaggi/api/staff/infusioni/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateInfusione = (id, data, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/infusioni/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);

export const staffGetInfusioneDetail = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/infusioni/${id}/`, { method: 'GET' }, onLogout);

export const staffDeleteInfusione = (id, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/infusioni/${id}/`, { method: 'DELETE' }, onLogout);

// --- TESSITURE ---
export const staffGetTessiture = (onLogout, params = {}) => {
  // Costruiamo la query string (es: ?page=1&search=pippo)
  const queryString = new URLSearchParams(params).toString();
  return fetchAuthenticated(`/api/personaggi/api/staff/tessiture/?${queryString}`, { method: 'GET' }, onLogout);
};

export const staffCreateTessitura = (data, onLogout) => 
  fetchAuthenticated('/api/personaggi/api/staff/tessiture/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateTessitura = (id, data, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/tessiture/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);

export const staffGetTessituraDetail = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/tessiture/${id}/`, { method: 'GET' }, onLogout);

export const staffDeleteTessitura = (id, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/tessiture/${id}/`, { method: 'DELETE' }, onLogout);

// --- CERIMONIALI ---
export const staffGetCerimoniali = (onLogout, params = {}) => {
  // Costruiamo la query string (es: ?page=1&search=pippo)
  const queryString = new URLSearchParams(params).toString();
  return fetchAuthenticated(`/api/personaggi/api/staff/cerimoniali/?${queryString}`, { method: 'GET' }, onLogout);
};

export const staffCreateCerimoniale = (data, onLogout) => 
  fetchAuthenticated('/api/personaggi/api/staff/cerimoniali/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateCerimoniale = (id, data, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/cerimoniali/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);

export const staffGetCerimonialeDetail = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/cerimoniali/${id}/`, { method: 'GET' }, onLogout);

export const staffDeleteCerimoniale = (id, onLogout) => 
  fetchAuthenticated(`/api/personaggi/api/staff/cerimoniali/${id}/`, { method: 'DELETE' }, onLogout);

// Gestione Oggetti (Istanze)
export const staffGetOggetti = (onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/oggetti/', { method: 'GET' }, onLogout);

export const staffCreateOggetto = (data, onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/oggetti/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateOggetto = (id, data, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/oggetti/${id}/`, { method: 'PUT', body: JSON.stringify(data) }, onLogout);

export const staffDeleteOggetto = (id, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/oggetti/${id}/`, { method: 'DELETE' }, onLogout);

// Gestione Oggetti Base (Listino/Template)
export const staffGetOggettiBase = (onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/oggetti-base/', { method: 'GET' }, onLogout);

export const staffCreateOggettoBase = (data, onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/oggetti-base/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateOggettoBase = (id, data, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/oggetti-base/${id}/`, { method: 'PUT', body: JSON.stringify(data) }, onLogout);

export const staffDeleteOggettoBase = (id, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/oggetti-base/${id}/`, { method: 'DELETE' }, onLogout);

// Utility
export const staffGetClassiOggetto = (onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/classi-oggetto/', { method: 'GET' }, onLogout);

// --- GESTIONE INVENTARI (Staff) ---
export const staffGetInventari = (onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/inventari/', { method: 'GET' }, onLogout);

export const staffCreateInventario = (data, onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/inventari/', { method: 'POST', body: JSON.stringify(data) }, onLogout);

export const staffUpdateInventario = (id, data, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/inventari/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);

export const staffDeleteInventario = (id, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/inventari/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetInventarioOggetti = (inventarioId, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/inventari/${inventarioId}/oggetti/`, { method: 'GET' }, onLogout);

export const staffGetManifesti = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/manifesti/', { method: 'GET' }, onLogout);
export const staffCreateManifesto = (data, onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/manifesti/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdateManifesto = (id, data, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/manifesti/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeleteManifesto = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/manifesti/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetNodi = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/nodi/', { method: 'GET' }, onLogout);
export const staffGetNodoRewardConfigs = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/nodi-reward-config/', { method: 'GET' }, onLogout);
export const staffCreateNodo = (data, onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/nodi/', { method: 'POST', body: data }, onLogout);
export const staffUpdateNodo = (id, data, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/nodi/${id}/`, { method: 'PATCH', body: data }, onLogout);
export const staffDeleteNodo = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/nodi/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetInnescoTimers = (onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/innesco-timer/', { method: 'GET' }, onLogout);
export const staffCreateInnescoTimer = (data, onLogout) =>
  fetchAuthenticated('/api/personaggi/api/staff/innesco-timer/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdateInnescoTimer = (id, data, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/innesco-timer/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeleteInnescoTimer = (id, onLogout) =>
  fetchAuthenticated(`/api/personaggi/api/staff/innesco-timer/${id}/`, { method: 'DELETE' }, onLogout);

export const staffAggiungiOggettoInventario = (inventarioId, oggettoId, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/inventari/${inventarioId}/aggiungi_oggetto/`, { 
        method: 'POST', 
        body: JSON.stringify({ oggetto_id: oggettoId }) 
    }, onLogout);

export const staffRimuoviOggettoInventario = (inventarioId, oggettoId, onLogout) => 
    fetchAuthenticated(`/api/personaggi/api/staff/inventari/${inventarioId}/rimuovi_oggetto/`, { 
        method: 'POST', 
        body: JSON.stringify({ oggetto_id: oggettoId }) 
    }, onLogout);

export const staffGetOggettiSenzaPosizione = (onLogout) => 
    fetchAuthenticated('/api/personaggi/api/staff/oggetti-senza-posizione/', { method: 'GET' }, onLogout);

// Sezione Personaggi

/**
 * Recupera le tipologie di personaggio disponibili.
 * Tenta di scaricarle dal server. Se fallisce o l'endpoint non esiste,
 * usa i valori di fallback per non rompere l'interfaccia.
 */
export const getTipologiePersonaggio = async (onLogout) => {
    try {
        // Tenta la chiamata all'API reale
        // Assicurati che nel backend esista: router.register(r'tipologie', TipologiaPersonaggioViewSet)
        const data = await fetchAuthenticated('/api/personaggi/api/tipologiepersonaggio/', { method: 'GET' }, onLogout);
        return data;
    } catch (error) {
        console.warn("API Tipologie non raggiungibile, uso fallback locale:", error);
        
        // Fallback locale nel caso il backend non sia ancora pronto
        return [
            { id: 1, label: 'Standard (Giocatore)' },
            { id: 2, label: 'PnG (Personaggio Non Giocante)' }
        ];
    }
};

// --- CRUD PERSONAGGI (Nuovo Endpoint) ---

export const getPersonaggiEditList = (onLogout, options = {}) => {
    const mineOnly = options?.mineOnly === true;
    const qs = mineOnly ? '?mine=1' : '';
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${qs}`, { method: 'GET' }, onLogout);
};

export const getEre = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/ere/', { method: 'GET' }, onLogout);
};

export const staffGetEre = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/ere/', { method: 'GET' }, onLogout);
};

export const staffCreateEra = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/ere/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffUpdateEra = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/ere/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffDeleteEra = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/ere/${id}/`, {
        method: 'DELETE',
    }, onLogout);
};

export const staffGetPrefetture = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/prefetture/', { method: 'GET' }, onLogout);
};

export const staffGetRegioni = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/regioni/', { method: 'GET' }, onLogout);
};

// --- CARRIERE / KORP (STAFF) ---
export const staffGetTipiCarriera = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/tipi-carriera/', { method: 'GET' }, onLogout);

export const staffGetCarriere = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/carriere/', { method: 'GET' }, onLogout);

export const staffCreateCarriera = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/carriere/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCarriera = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/carriere/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCarriera = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/carriere/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetCarrieraTiersSelezionabili = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/carriere/tiers_selezionabili/', { method: 'GET' }, onLogout);

export const staffGetCariche = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/cariche/', { method: 'GET' }, onLogout);

export const staffCreateCarica = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/cariche/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCarica = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/cariche/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCarica = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/cariche/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetCarriereMemberships = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/personaggi-carriere-membership/', { method: 'GET' }, onLogout);

export const staffCreateCarriereMembership = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/personaggi-carriere-membership/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCarriereMembership = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/personaggi-carriere-membership/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCarriereMembership = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/personaggi-carriere-membership/${id}/`, {
        method: 'DELETE',
    }, onLogout);

// --- PILOTAGGIO (STAFF) ---
export const staffGetPilotSottosistemi = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/sottosistemi/', { method: 'GET' }, onLogout);
/** Dettaglio completo (serializer «retrieve») per modali staff. */
export const staffGetPilotSottosistema = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sottosistemi/${id}/`, { method: 'GET' }, onLogout);
export const staffCreatePilotSottosistema = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/sottosistemi/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotSottosistema = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sottosistemi/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotSottosistema = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sottosistemi/${id}/`, { method: 'DELETE' }, onLogout);
export const staffAssociaPilotSottosistemaAVista = (id, aVistaId, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sottosistemi/${id}/associa-a-vista/`, { method: 'POST', body: JSON.stringify({ a_vista_id: aVistaId }) }, onLogout);

/** Collega un QR al sottosistema (risolve/c crea la vista lato server). */
export const staffAssociaPilotSottosistemaQr = (sottosistemaId, qrId, onLogout) =>
  fetchAuthenticated(
    `/api/pilot/staff/sottosistemi/${sottosistemaId}/associa-qr/`,
    { method: 'POST', body: JSON.stringify({ qr_id: qrId }) },
    onLogout
  );

export const staffGetPilotComandi = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/comandi/', { method: 'GET' }, onLogout);
export const staffCreatePilotComando = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/comandi/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotComando = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/comandi/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotComando = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/comandi/${id}/`, { method: 'DELETE' }, onLogout);

/** Pattern globali: codice in sessione → precipizio immediato (indipendente dall'evento). */
export const staffGetPilotComandiCritici = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/comandi-critici/', { method: 'GET' }, onLogout);
export const staffGetPilotComandoCritico = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/comandi-critici/${id}/`, { method: 'GET' }, onLogout);
export const staffCreatePilotComandoCritico = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/comandi-critici/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotComandoCritico = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/comandi-critici/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotComandoCritico = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/comandi-critici/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetPilotIntensita = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/intensita/', { method: 'GET' }, onLogout);
export const staffGetPilotIntensitaById = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/intensita/${id}/`, { method: 'GET' }, onLogout);
export const staffCreatePilotIntensita = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/intensita/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotIntensita = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/intensita/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotIntensita = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/intensita/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetPilotEventi = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/eventi/', { method: 'GET' }, onLogout);
export const staffGetPilotEvento = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/eventi/${id}/`, { method: 'GET' }, onLogout);
export const staffCreatePilotEvento = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/eventi/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotEvento = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/eventi/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotEvento = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/eventi/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetPilotSequenze = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/sequenze/', { method: 'GET' }, onLogout);

export const staffGetPilotStatiAllerta = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/stati-allerta/', { method: 'GET' }, onLogout);
export const staffGetPilotStatoAllerta = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/stati-allerta/${id}/`, { method: 'GET' }, onLogout);
export const staffUpdatePilotStatoAllerta = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/stati-allerta/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, onLogout);
export const staffCreatePilotSequenza = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/sequenze/', { method: 'POST', body: JSON.stringify(data) }, onLogout);
export const staffUpdatePilotSequenza = (id, data, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sequenze/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const staffDeletePilotSequenza = (id, onLogout) =>
  fetchAuthenticated(`/api/pilot/staff/sequenze/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetPilotCatalog = (onLogout) =>
  fetchAuthenticated('/api/pilot/catalog/', { method: 'GET' }, onLogout);

export const staffGetPilotRuntimeConfig = (onLogout) =>
  fetchAuthenticated('/api/pilot/staff/runtime-config/', { method: 'GET' }, onLogout);
export const staffUpdatePilotRuntimeConfig = (data, onLogout) =>
  fetchAuthenticated('/api/pilot/staff/runtime-config/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, onLogout);

export const staffGetKorps = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/korp/', { method: 'GET' }, onLogout);
};

export const staffCreateRegione = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/regioni/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffUpdateRegione = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/regioni/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffDeleteRegione = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/regioni/${id}/`, {
        method: 'DELETE',
    }, onLogout);
};

export const staffCreatePrefettura = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/prefetture/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffUpdatePrefettura = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/prefetture/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffDeletePrefettura = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/prefetture/${id}/`, {
        method: 'DELETE',
    }, onLogout);
};

export const staffGetDichiarazioni = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/dichiarazioni/', { method: 'GET' }, onLogout);
};

export const staffCreateDichiarazione = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/dichiarazioni/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffUpdateDichiarazione = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/dichiarazioni/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);
};

export const staffDeleteDichiarazione = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/dichiarazioni/${id}/`, {
        method: 'DELETE',
    }, onLogout);
};

export const createPersonaggio = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/gestione-personaggi/', {
        method: 'POST',
        body: JSON.stringify(data)
    }, onLogout);
};

export const updatePersonaggio = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    }, onLogout);
};

export const getGestionePersonaggio = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/`, { method: 'GET' }, onLogout);
};

export const rigeneraLikeInfluencer = (id, onLogout) => {
    return fetchAuthenticated(
        `/api/personaggi/api/gestione-personaggi/${id}/rigenera-like-influencer/`,
        { method: 'POST' },
        onLogout
    );
};

export const deletePersonaggio = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/`, {
        method: 'DELETE',
    }, onLogout);
};

// --- CREAZIONE GUIDATA PERSONAGGIO ---
const _creazioneGuidataQuery = (personaggioId, effetti, modalitaTest) => {
    const params = new URLSearchParams();
    if (personaggioId) params.set('personaggio_id', String(personaggioId));
    if (effetti?.length) params.set('effetti', JSON.stringify(effetti));
    if (modalitaTest) params.set('modalita_test', '1');
    return params.toString();
};

export const getCreazioneGuidataStato = (onLogout) =>
    fetchAuthenticated('/api/plot/api/creazione-guidata/stato/', { method: 'GET' }, onLogout);

export const getCreazioneGuidataImpostazioni = (onLogout) =>
    fetchAuthenticated('/api/plot/api/creazione-guidata/impostazioni/', { method: 'GET' }, onLogout);

export const patchCreazioneGuidataImpostazioni = (apertaGiocatori, onLogout) =>
    fetchAuthenticated(
        '/api/plot/api/creazione-guidata/impostazioni/',
        { method: 'PATCH', body: JSON.stringify({ aperta_giocatori: apertaGiocatori }) },
        onLogout,
    );

export const getCreazioneGuidataAvvio = (personaggioId, effetti, onLogout, modalitaTest = false) => {
    const qs = _creazioneGuidataQuery(personaggioId, effetti, modalitaTest);
    return fetchAuthenticated(
        `/api/plot/api/creazione-guidata/avvio${qs ? `?${qs}` : ''}`,
        { method: 'GET' },
        onLogout,
    );
};

export const getCreazioneGuidataPasso = (slug, personaggioId, effetti, onLogout, modalitaTest = false) => {
    const qs = _creazioneGuidataQuery(personaggioId, effetti, modalitaTest);
    return fetchAuthenticated(
        `/api/plot/api/creazione-guidata/passi/${encodeURIComponent(slug)}${qs ? `?${qs}` : ''}`,
        { method: 'GET' },
        onLogout,
    );
};

export const applyCreazioneGuidata = (personaggioId, effetti, onLogout) =>
    fetchAuthenticated(
        `/api/personaggi/api/gestione-personaggi/${personaggioId}/creazione-guidata/applica/`,
        { method: 'POST', body: JSON.stringify({ effetti }) },
        onLogout,
    );

export const getCreazioneGuidataProposte = (personaggioId, onLogout) =>
    fetchAuthenticated(
        `/api/personaggi/api/gestione-personaggi/${personaggioId}/creazione-guidata/proposte/`,
        { method: 'GET' },
        onLogout,
    );

export const salvaCreazioneGuidataProposte = (personaggioId, effetti, trail, onLogout) =>
    fetchAuthenticated(
        `/api/personaggi/api/gestione-personaggi/${personaggioId}/creazione-guidata/salva-proposte/`,
        { method: 'POST', body: JSON.stringify({ effetti, trail }) },
        onLogout,
    );

export const getCreazioneGuidataRiepilogo = (personaggioId, effetti, onLogout) => {
    const params = new URLSearchParams();
    if (effetti?.length) params.set('effetti', JSON.stringify(effetti));
    const qs = params.toString();
    return fetchAuthenticated(
        `/api/personaggi/api/gestione-personaggi/${personaggioId}/creazione-guidata/riepilogo${qs ? `?${qs}` : ''}`,
        { method: 'GET' },
        onLogout,
    );
};

export const listCreazioneGuidataFlussi = (onLogout) =>
    fetchAuthenticated('/api/plot/api/staff/creazione-guidata/flussi/', { method: 'GET' }, onLogout);

export const getCreazioneGuidataFlusso = (id, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/flussi/${id}/`, { method: 'GET' }, onLogout);

export const createCreazioneGuidataFlusso = (data, onLogout) =>
    fetchAuthenticated('/api/plot/api/staff/creazione-guidata/flussi/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const creaSandboxCreazioneGuidataFlusso = (flussoProduzioneId, onLogout) =>
    fetchAuthenticated(
        `/api/plot/api/staff/creazione-guidata/flussi/${flussoProduzioneId}/crea-sandbox/`,
        { method: 'POST' },
        onLogout,
    );

export const pubblicaCreazioneGuidataSandbox = (flussoTestId, onLogout) =>
    fetchAuthenticated(
        `/api/plot/api/staff/creazione-guidata/flussi/${flussoTestId}/pubblica-su-produzione/`,
        { method: 'POST' },
        onLogout,
    );

export const updateCreazioneGuidataFlusso = (id, data, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/flussi/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const deleteCreazioneGuidataFlusso = (id, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/flussi/${id}/`, { method: 'DELETE' }, onLogout);

export const createCreazioneGuidataPasso = (data, onLogout) =>
    fetchAuthenticated('/api/plot/api/staff/creazione-guidata/passi/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const updateCreazioneGuidataPasso = (id, data, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/passi/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const deleteCreazioneGuidataPasso = (id, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/passi/${id}/`, { method: 'DELETE' }, onLogout);

export const createCreazioneGuidataScelta = (data, onLogout) =>
    fetchAuthenticated('/api/plot/api/staff/creazione-guidata/scelte/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const updateCreazioneGuidataScelta = (id, data, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/scelte/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const deleteCreazioneGuidataScelta = (id, onLogout) =>
    fetchAuthenticated(`/api/plot/api/staff/creazione-guidata/scelte/${id}/`, { method: 'DELETE' }, onLogout);

export const resetPersonaggio = (id, reason, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/reset_personaggio/`, {
        method: 'POST',
        body: JSON.stringify({ reason: reason || 'Reset personaggio staff' })
    }, onLogout);
};

export const staffKillPersonaggio = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/kill/`, {
        method: 'POST',
    }, onLogout);
};

export const staffRevivePersonaggio = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${id}/revive/`, {
        method: 'POST',
    }, onLogout);
};

// --- STAFF RESOURCES ---
export const staffAddResources = (charId, tipo, amount, reason, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/gestione-personaggi/${charId}/add_resources/`, {
        method: 'POST',
        body: JSON.stringify({ tipo, amount, reason })
    }, onLogout);
};

/** Consuma un punto da una risorsa a pool (es. Fortuna FRT). */
export const gameConsumaRisorsa = (charId, statSigla, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/game/consuma_risorsa/', {
        method: 'POST',
        body: JSON.stringify({ char_id: charId, stat_sigla: statSigla }),
    }, onLogout);

export const gameAttivaTessituraRuntime = (charId, tessituraId, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/game/attiva_tessitura_runtime/', {
        method: 'POST',
        body: JSON.stringify({ char_id: charId, tessitura_id: tessituraId }),
    }, onLogout);

export const gameStopTessituraRuntime = (charId, runtimeId, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/game/stop_tessitura_runtime/', {
        method: 'POST',
        body: JSON.stringify({ char_id: charId, runtime_id: runtimeId }),
    }, onLogout);

export const gameDisequipTessituraRuntimeObject = (charId, runtimeObjectId, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/game/disequip_tessitura_runtime_object/', {
        method: 'POST',
        body: JSON.stringify({ char_id: charId, runtime_object_id: runtimeObjectId }),
    }, onLogout);

export const gameComaControl = (charId, action, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/game/coma_control/', {
        method: 'POST',
        body: JSON.stringify({ char_id: charId, action }),
    }, onLogout);

export const watchGetStatus = (charId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/device/watch/status/?char_id=${encodeURIComponent(String(charId))}`,
    { method: 'GET' },
    onLogout
  );

export const watchPairConfirm = (charId, code, transportMode, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/device/watch/pair/confirm/',
    {
      method: 'POST',
      body: JSON.stringify({
        char_id: charId,
        code: String(code || '').trim().toUpperCase(),
        transport_mode: transportMode || 'WIFI',
      }),
    },
    onLogout
  );

export const watchDisconnect = (charId, onLogout) =>
  fetchAuthenticated(
    '/api/personaggi/api/device/watch/disconnect/',
    {
      method: 'POST',
      body: JSON.stringify({ char_id: charId }),
    },
    onLogout
  );

export const watchWearManifest = (charId, onLogout) =>
  fetchAuthenticated(
    `/api/personaggi/api/device/watch/wearos/manifest/?char_id=${encodeURIComponent(String(charId))}`,
    { method: 'GET' },
    onLogout
  );

/** Staff: elenco personaggi con pool risorse (FRT, …). */
export const staffGetRisorsePool = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/risorse-pool/', { method: 'GET' }, onLogout);

/** Staff: +1 al pool corrente (non oltre il massimo). */
/** delta: positivo aggiunge, negativo toglie (clamp 0…max scheda). Default 1. */
export const staffIncrementaRisorsaPool = (personaggioId, statSigla, motivo, onLogout, delta = 1) =>
    fetchAuthenticated('/api/personaggi/api/staff/risorse-pool/incrementa/', {
        method: 'POST',
        body: JSON.stringify({
            personaggio_id: personaggioId,
            stat_sigla: statSigla,
            motivo: motivo || '',
            delta,
        }),
    }, onLogout);

/**
 * Recupera le proposte tecniche in stato VALUTAZIONE per lo staff.
 */
export const staffGetProposteInValutazione = (onLogout) => {
  return fetchAuthenticated(
    '/api/personaggi/api/staff/proposte/valutazione/', 
    { method: 'GET' }, 
    onLogout
  );
};

/**
 * Rifiuta una proposta tecnica, riportandola in BOZZA e inviando un messaggio.
 */
export const staffRifiutaProposta = (propostaId, noteStaff, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/staff/proposte/${propostaId}/rifiuta/`,
    {
      method: 'POST',
      body: JSON.stringify({ note_staff: noteStaff })
    },
    onLogout
  );
};

/**
 * Approva una proposta: crea la tecnica finale, scala i crediti e aggiorna lo stato.
 * 'finalData' contiene i dati definitivi compilati tramite l'editor (Infusione/Tessitura/Cerimoniale).
 */
export const staffApprovaProposta = (propostaId, finalData, onLogout) => {
  return fetchAuthenticated(
    `/api/personaggi/api/staff/proposta/${propostaId}/approva/`,
    {
      method: 'POST',
      body: JSON.stringify(finalData)
    },
    onLogout
  );
};

// --- GESTIONE MOSTRI (TEMPLATE) ---

export const staffGetMostriTemplates = (onLogout) => {
    return fetchAuthenticated('/api/plot/api/staff/mostri-templates/', { method: 'GET' }, onLogout);
};

export const staffCreateMostroTemplate = (data, onLogout) => {
    return fetchAuthenticated('/api/plot/api/staff/mostri-templates/', { 
        method: 'POST', 
        body: JSON.stringify(data) 
    }, onLogout);
};

export const staffUpdateMostroTemplate = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/plot/api/staff/mostri-templates/${id}/`, { 
        method: 'PUT', // Usa PUT per sostituire l'intero oggetto inclusi gli attacchi
        body: JSON.stringify(data) 
    }, onLogout);
};

export const staffDeleteMostroTemplate = (id, onLogout) => {
    return fetchAuthenticated(`/api/plot/api/staff/mostri-templates/${id}/`, { method: 'DELETE' }, onLogout);
};

// --- GESTIONE ABILITÀ ---

export const staffGetAbilitaList = (onLogout, params = {}) => {
    const query = new URLSearchParams();
    if (params.page) query.set('page', String(params.page));
    if (params.pageSize) query.set('page_size', String(params.pageSize));
    if (params.search) query.set('search', params.search);
    if (params.isTrattoAura !== undefined && params.isTrattoAura !== null) {
        query.set('is_tratto_aura', String(params.isTrattoAura));
    }
    const qs = query.toString();
    const url = `/api/personaggi/api/staff/abilita/${qs ? `?${qs}` : ''}`;
    return fetchAuthenticated(url, { method: 'GET' }, onLogout);
};

/** Elenco completo staff (tutte le pagine) — per combobox che devono includere anche abilità "nascoste in scheda". */
export const staffGetAbilitaListAll = async (onLogout, params = {}) => {
    const pageSize = params.pageSize || 200;
    const all = [];
    let page = 1;
    for (;;) {
        const data = await staffGetAbilitaList(onLogout, { ...params, page, pageSize });
        const rows = Array.isArray(data) ? data : (data?.results || []);
        all.push(...rows);
        if (Array.isArray(data) || !data?.next) break;
        page += 1;
    }
    return all;
};

/** Dettaglio completo (inlines incluse) per l'editor staff — necessario prima di PATCH per non azzerare relazioni. */
export const staffGetAbilita = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/abilita/${id}/`, { method: 'GET' }, onLogout);
};

export const staffCreateAbilita = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/abilita/', {
        method: 'POST',
        body: JSON.stringify(data)
    }, onLogout);
};

export const staffUpdateAbilita = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/abilita/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    }, onLogout);
};

export const staffDeleteAbilita = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/abilita/${id}/`, { method: 'DELETE' }, onLogout);
};

const EDITOR_PREFETCH_TTL_MS = 5 * 60 * 1000;
let abilitaEditorResourcesCache = null;
let abilitaEditorResourcesPromise = null;

const isAbilitaEditorCacheValid = () => {
    if (!abilitaEditorResourcesCache) return false;
    return (Date.now() - abilitaEditorResourcesCache.ts) < EDITOR_PREFETCH_TTL_MS;
};

const fetchAbilitaEditorResources = async (onLogout, { force = false } = {}) => {
    if (!force && isAbilitaEditorCacheValid()) {
        return abilitaEditorResourcesCache.data;
    }
    if (!force && abilitaEditorResourcesPromise) {
        return abilitaEditorResourcesPromise;
    }

    abilitaEditorResourcesPromise = Promise.all([
        fetchAuthenticated('/api/personaggi/api/punteggi/all/', { method: 'GET' }, onLogout),
        fetchAuthenticated('/api/personaggi/api/abilita/', { method: 'GET' }, onLogout),
        fetchAuthenticated('/api/personaggi/api/tier/', { method: 'GET' }, onLogout),
    ])
        .then(([punteggi, abilita, tiers]) => {
            const data = {
                punteggi: punteggi || [],
                abilita: abilita || [],
                tiers: tiers || [],
            };
            abilitaEditorResourcesCache = { data, ts: Date.now() };
            return data;
        })
        .finally(() => {
            abilitaEditorResourcesPromise = null;
        });

    return abilitaEditorResourcesPromise;
};

export const prefetchAbilitaEditorResources = (onLogout) => {
    return fetchAbilitaEditorResources(onLogout);
};

export const getAbilitaEditorResources = (onLogout, options = {}) => {
    return fetchAbilitaEditorResources(onLogout, options);
};

// Utile per l'editor: serve la lista di tutte le abilità per i prerequisiti
export const getAbilitaOptions = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/abilita/', { method: 'GET' }, onLogout);
};

export const getTiersList = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/tier/', { method: 'GET' }, onLogout);
};

export const staffCreateOffGame = async (data, onLogout) => {
    return await fetchAuthenticated('/api/plot/api/staff/staff-offgame/', 'POST', data, onLogout);
};

export const staffDeleteOffGame = async (id, onLogout) => {
    return await fetchAuthenticated(`/api/plot/api/staff/staff-offgame/${id}/`, 'DELETE', null, onLogout);
};

// src/api.js - Aggiungi queste esportazioni
export const addFaseToQuest = (payload, onLogout) => fetchAuthenticated('/api/plot/api/fasi/', { method: 'POST', body: JSON.stringify(payload) }, onLogout);
export const removeFaseFromQuest = (id, onLogout) => fetchAuthenticated(`/api/plot/api/fasi/${id}/`, { method: 'DELETE' }, onLogout);
export const addTaskToFase = (payload, onLogout) => fetchAuthenticated('/api/plot/api/tasks/', { method: 'POST', body: JSON.stringify(payload) }, onLogout);
export const updateTask = (id, data, onLogout) =>
    fetchAuthenticated(`/api/plot/api/tasks/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);
export const removeTaskFromFase = (id, onLogout) => fetchAuthenticated(`/api/plot/api/tasks/${id}/`, { method: 'DELETE' }, onLogout);
export const updateFase = (id, data, onLogout) => fetchAuthenticated(`/api/plot/api/fasi/${id}/`, { method: 'PATCH', body: JSON.stringify(data) }, onLogout);



// --- WIKI PAGINE REGOLAMENTO ---

export const getWikiMenu = async () => {
  const token = localStorage.getItem('kor35_token');
  // Puntiamo all'endpoint "smart" definito nelle urlpatterns di gestione_plot/urls.py
  const endpoint = '/api/plot/api/wiki/menu/'; 

  if (token) {
    // Se c'è il token, usiamo fetchAuthenticated: il backend riconoscerà lo Staff 
    // e restituirà anche bozze e pagine riservate.
    return fetchAuthenticated(endpoint, { method: 'GET' });
  } else {
    // Se non c'è token, usiamo fetchPublic: il backend applicherà i filtri di sicurezza.
    return fetchPublic(endpoint);
  }
};

export const getWikiPage = async (slug) => {
  const token = localStorage.getItem('kor35_token');
  const endpoint = `/api/plot/api/wiki/pagina/${slug}/`;

  if (token) {
    return fetchAuthenticated(endpoint, { method: 'GET' });
  } else {
    return fetchPublic(endpoint);
  }
};

const wikiPdfPath = (path) => (API_BASE_URL ? `${API_BASE_URL}${path}` : path);

export const getWikiManualPdfUrl = (manualeSlug = 'completo') => {
  const q = manualeSlug && manualeSlug !== 'completo' ? `?manuale=${encodeURIComponent(manualeSlug)}` : '';
  return wikiPdfPath(`/api/plot/api/wiki/manuale.pdf${q}`);
};

export const getWikiManualLatestPdfUrl = () => getWikiManualeLatestPdfUrl('completo');

export const getWikiManualeLatestPdfUrl = (slug) =>
  wikiPdfPath(`/api/plot/api/wiki/manuali/${encodeURIComponent(slug)}/latest.pdf`);

export const getPublicWikiManualeList = () =>
  fetchPublic('/api/plot/api/wiki/manuali/');

export const getStaffManualePdfList = (onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/manuali-pdf/', { method: 'GET' }, onLogout);

export const createStaffManualePdf = (formData, onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/manuali-pdf/', { method: 'POST', body: formData }, onLogout);

export const updateStaffManualePdf = (slug, formData, onLogout) =>
  fetchAuthenticated(`/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/`, {
    method: 'PATCH',
    body: formData,
  }, onLogout);

export const generateStaffManualePdf = (slug, onLogout) =>
  fetchAuthenticated(
    `/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/genera/`,
    { method: 'POST', body: '{}' },
    onLogout,
  );

export const getStaffManualePdfAnteprimaUrl = (slug) =>
  wikiPdfPath(`/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/anteprima/`);

export const getStaffManualePdfExportZipUrl = () =>
  wikiPdfPath('/api/plot/api/staff/manuali-pdf/export-zip/');

export const getWikiPdfDiagnostica = (onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/manuali-pdf/diagnostica/', { method: 'GET' }, onLogout);

export const getWikiManualeStorico = (slug, onLogout) =>
  fetchAuthenticated(
    `/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/storico/`,
    { method: 'GET' },
    onLogout,
  );

export const startWikiManualeBatchJob = (onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/manuali-pdf/genera-tutti/', {
    method: 'POST',
    body: '{}',
  }, onLogout);

export const getWikiManualeBatchJob = (jobId, onLogout) =>
  fetchAuthenticated(
    `/api/plot/api/staff/manuali-pdf/jobs/${jobId}/`,
    { method: 'GET' },
    onLogout,
  );

export const getStaffManualePdfPagine = (slug, onLogout) =>
  fetchAuthenticated(
    `/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/pagine/`,
    { method: 'GET' },
    onLogout,
  );

export const updateStaffManualePdfPagine = (slug, pagine, onLogout) =>
  fetchAuthenticated(
    `/api/plot/api/staff/manuali-pdf/${encodeURIComponent(slug)}/pagine/`,
    {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ pagine }),
    },
    onLogout,
  );

export const getStaffWikiPagesSmall = (onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/pagine-regolamento-small/', { method: 'GET' }, onLogout);

/** @deprecated Preferire generateStaffManualePdf per ogni manuale */
export const generateWikiManualPdfSnapshot = (onLogout) => {
  return fetchAuthenticated('/api/plot/api/wiki/manuale/genera/', { method: 'POST', body: '{}' }, onLogout);
};

/** Lista glossario dichiarazioni per auto-link nelle pagine wiki (cache HTTP lato server). */
export const getWikiGlossario = async () => {
  return fetchPublic('/api/plot/api/public/wiki-glossario/');
};


export const getWikiTable = (id) => {
  return fetchPublic(`/api/plot/api/public/wiki-tabelle/${id}/`);
};

export const getWikiAura = (id) => {
  return fetchPublic(`/api/plot/api/public/wiki-aure/${id}/`);
};

// --- WIDGET TIER: usa tier-display (accetta id Tier oppure id plugin CMS) ---
export const getWikiTier = (id) => {
  return fetchPublic(`/api/plot/api/wiki/tier-display/${encodeURIComponent(String(id))}/`);
};

// --- WIDGET COLLEZIONE TIER ---
export const getWikiTierCollectionDisplay = (id) => {
  const token = localStorage.getItem('kor35_token');
  const endpoint = `/api/plot/api/wiki/tier-collection-display/${encodeURIComponent(String(id))}/`;
  if (token) {
    return fetchAuthenticated(endpoint, { method: 'GET' });
  }
  return fetchPublic(endpoint);
};

export const getWikiTierCollectionWidgetList = () => {
  return fetchPublic('/api/plot/api/public/wiki-tier-collections/');
};

export const getWikiTierCollectionWidget = (id) => {
  return fetchPublic(`/api/plot/api/public/wiki-tier-collections/${id}/`);
};

export const createWikiTierCollectionWidget = (data, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-tier-collections/', {
    method: 'POST',
    body: JSON.stringify(data)
  }, onLogout);
};

export const updateWikiTierCollectionWidget = (id, data, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-tier-collections/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }, onLogout);
};

// --- WIDGET MATTONI ---
export const getWikiMattoniWidgetDisplay = (id) => {
  return fetchPublic(`/api/plot/api/wiki/mattoni-display/${encodeURIComponent(String(id))}/`);
};

export const getWikiEraDisplay = (id) => {
  return fetchPublic(`/api/plot/api/wiki/era-display/${encodeURIComponent(String(id))}/`);
};

export const getWikiPunteggi = (tipo) => {
  const t = tipo ? String(tipo).trim() : '';
  return fetchPublic(`/api/plot/api/wiki/punteggi/?tipo=${encodeURIComponent(t)}`);
};

export const getWikiMattoniWidgetList = () => {
  return fetchPublic('/api/plot/api/public/wiki-mattoni-widgets/');
};

export const getWikiMattoniWidget = (id) => {
  return fetchPublic(`/api/plot/api/public/wiki-mattoni-widgets/${id}/`);
};

export const createWikiMattoniWidget = (data, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-mattoni/', {
    method: 'POST',
    body: JSON.stringify(data)
  }, onLogout);
};

export const updateWikiMattoniWidget = (id, data, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-mattoni/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }, onLogout);
};

// Helper per avere la lista di tutti i Tier (per l'editor del Master)
export const getWikiTierList = () => {
  return fetchPublic('/api/plot/api/public/wiki-tiers/');
};

// Lista widget Tier configurabili (per inserire / modificare in pagina)
export const getWikiTierWidgetList = () => {
  return fetchPublic('/api/plot/api/public/wiki-tier-widgets/');
};

// Dettaglio singolo widget Tier (per modifica)
export const getWikiTierWidget = (id) => {
  return fetchPublic(`/api/plot/api/public/wiki-tier-widgets/${id}/`);
};

// Crea widget Tier (Staff)
export const createWikiTierWidget = (data, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-tiers/', {
    method: 'POST',
    body: JSON.stringify(data)
  }, onLogout);
};

// Aggiorna widget Tier (Staff)
export const updateWikiTierWidget = (id, data, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-tiers/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }, onLogout);
};

// --- WIDGET IMMAGINI WIKI ---
export const getWikiImage = (id) => {
  return fetchPublic(`/api/plot/api/wiki/image-display/${encodeURIComponent(String(id))}/`);
};

export const getWikiImageList = () => {
  return fetchPublic('/api/plot/api/public/wiki-immagini/');
};

// Crea una nuova immagine wiki (Staff) - Supporta FormData per immagini
export const createWikiImage = (formData, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-immagini/', {
    method: 'POST',
    body: formData // fetchAuthenticated gestisce automaticamente il Content-Type per FormData
  }, onLogout);
};

// Aggiorna un'immagine wiki esistente (Staff) - Supporta FormData per immagini
// Usa PATCH per aggiornamenti parziali (non sovrascrive l'immagine se non viene passata)
export const updateWikiImage = (id, formData, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-immagini/${id}/`, {
    method: 'PATCH',
    body: formData
  }, onLogout);
};

// Elimina un'immagine wiki (Staff)
export const deleteWikiImage = (id, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-immagini/${id}/`, {
    method: 'DELETE'
  }, onLogout);
};

// --- WIDGET BUTTONS WIKI ---
export const getWidgetButtons = (id) => {
  return fetchPublic(`/api/plot/api/wiki/buttons-display/${encodeURIComponent(String(id))}/`);
};

export const getWidgetButtonsList = () => {
  return fetchPublic('/api/plot/api/public/wiki-buttons/');
};

// Crea un nuovo widget buttons (Staff)
export const createWidgetButtons = (data, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-buttons/', {
    method: 'POST',
    body: JSON.stringify(data)
  }, onLogout);
};

// Aggiorna un widget buttons esistente (Staff)
export const updateWidgetButtons = (id, data, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-buttons/${id}/`, {
    method: 'PATCH',
    body: JSON.stringify(data)
  }, onLogout);
};

// Elimina un widget buttons (Staff)
export const deleteWidgetButtons = (id, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/wiki-buttons/${id}/`, {
    method: 'DELETE'
  }, onLogout);
};

// Recupera la lista delle immagini wiki (Staff) - versione autenticata
export const staffGetWikiImages = (onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/wiki-immagini/', {
    method: 'GET'
  }, onLogout);
};

// --- EVENTI PUBBLICI ---
export const getEventiPubblici = () => {
  return fetchPublic('/api/plot/api/public/eventi/');
};

// --- CONFIGURAZIONE SITO ---
export const getConfigurazioneSito = () => {
  return fetchPublic('/api/plot/api/public/configurazione-sito/1/');
};

export const getStaffDashboardLayout = (onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/dashboard-layout/', { method: 'GET' }, onLogout);

export const updateStaffDashboardLayout = (layout, onLogout) =>
  fetchAuthenticated('/api/plot/api/staff/dashboard-layout/', {
    method: 'PATCH',
    body: JSON.stringify({ staff_dashboard_layout: layout }),
  }, onLogout);

export const getAdminMaintenanceConfig = (onLogout) => {
  return fetchAuthenticated('/api/plot/api/admin/maintenance-config/', { method: 'GET' }, onLogout);
};

export const updateAdminMaintenanceConfig = (data, onLogout) => {
  return fetchAuthenticated('/api/plot/api/admin/maintenance-config/', {
    method: 'PATCH',
    body: JSON.stringify(data),
  }, onLogout);
};

// --- LINK SOCIAL ---
export const getLinkSocial = () => {
  return fetchPublic('/api/plot/api/public/link-social/');
};

// Crea una nuova pagina (Staff) - Supporta FormData per immagini
export const createWikiPage = (formData, onLogout) => {
  return fetchAuthenticated('/api/plot/api/staff/pagine-regolamento/', {
    method: 'POST',
    body: formData // fetchAuthenticated gestisce automaticamente il Content-Type per FormData
  }, onLogout);
};

// Aggiorna una pagina esistente (Staff)
export const updateWikiPage = (id, formData, onLogout) => {
  return fetchAuthenticated(`/api/plot/api/staff/pagine-regolamento/${id}/`, {
    method: 'PUT',
    body: formData
  }, onLogout);
};

// --- GESTIONE TABELLE (TIER) ---

export const getTiers = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/tiers/', { method: 'GET' }, onLogout);
};

export const createTier = (data, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/tiers/', {
        method: 'POST',
        body: JSON.stringify(data)
    }, onLogout);
};

export const updateTier = (id, data, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/tiers/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data)
    }, onLogout);
};

export const deleteTier = (id, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/tiers/${id}/`, {
        method: 'DELETE'
    }, onLogout);
};

export const getAllAbilitaSimple = (onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/staff/tiers/all_abilita/', { method: 'GET' }, onLogout);
};

export const updateTierAbilita = (tierId, abilitaList, onLogout) => {
    // abilitaList deve essere array di { abilita_id, ordine }
    return fetchAuthenticated(`/api/personaggi/api/staff/tiers/${tierId}/update_abilita_list/`, {
        method: 'POST',
        body: JSON.stringify({ abilita_list: abilitaList })
    }, onLogout);
};

// Helper per ottenere l'URL dell'immagine ottimizzata
// width = 0 ritorna l'originale
export const getWikiImageUrl = (slug, width = 0) => {
    const baseUrl = API_BASE_URL;
    const path = `/api/plot/api/wiki/image/${slug}/?w=${width}`;
    return baseUrl ? `${baseUrl}${path}` : path;
};

/** Origine del backend configurato (per riscrivere URL media assoluti “estranei”). */
function mediaApiOrigin() {
    const raw = (API_BASE_URL || '').trim();
    if (raw) {
        try {
            const href = /^https?:\/\//i.test(raw) ? raw : `http://${raw}`;
            return new URL(href).origin;
        } catch {
            return null;
        }
    }
    if (typeof window !== 'undefined' && window.location?.origin) {
        return window.location.origin;
    }
    return null;
}

/**
 * URL verso il backend per file media (icone, immagini upload, ecc.).
 * - Path relativo → prefisso API_BASE_URL (o origin finestra se base vuota).
 * - URL assoluto con host diverso dal backend configurato → stesso path sull’API corrente
 *   (evita che mirror/dev carichino media da produzione se il JSON contiene ancora URL assoluti).
 */
export const resolveMediaUrl = (path) => {
    if (path == null || path === '') return null;
    const s = String(path).trim();
    if (!s) return null;
    if (s.startsWith('http://') || s.startsWith('https://')) {
        try {
            const mediaUrl = new URL(s);
            const apiOrigin = mediaApiOrigin();
            if (apiOrigin && mediaUrl.origin !== apiOrigin) {
                return `${apiOrigin}${mediaUrl.pathname}${mediaUrl.search}${mediaUrl.hash}`;
            }
            return s;
        } catch {
            return s;
        }
    }
    const cleanBase = API_BASE_URL.endsWith('/') ? API_BASE_URL.slice(0, -1) : API_BASE_URL;
    const cleanPath = s.startsWith('/') ? s : `/${s}`;
    return `${cleanBase}${cleanPath}`;
};

// Alias storico (immagini wiki, editor, widget immagine)
export const getMediaUrl = (path) => resolveMediaUrl(path);

/**
 * Registra un nuovo utente.
 */
export const registerUser = async (userData) => {
    // userData deve contenere: username, password, email, first_name, last_name
    return fetchPublic('/api/personaggi/api/user/register/', {
        method: 'POST',
        body: JSON.stringify(userData)
    });
};

/**
 * Cambia la password dell'utente loggato.
 */
export const changePassword = async (oldPassword, newPassword, onLogout) => {
    return fetchAuthenticated('/api/personaggi/api/user/change-password/', {
        method: 'POST',
        body: JSON.stringify({
            old_password: oldPassword,
            new_password: newPassword
        })
    }, onLogout);
};

export const getArcanaPasswordStatus = async (onLogout) => {
    return fetchAuthenticated('/api/auth/arcana/password-status/', { method: 'GET' }, onLogout);
};

export const setArcanaLocalPassword = async (newPassword, confirmPassword, onLogout) => {
    return fetchAuthenticated('/api/auth/arcana/set-local-password/', {
        method: 'POST',
        body: JSON.stringify({
            new_password: newPassword,
            confirm_password: confirmPassword,
        })
    }, onLogout);
};

export const staffGetArcanaProfiles = async (onLogout) => {
    return fetchAuthenticated('/api/auth/arcana/staff/profiles/', { method: 'GET' }, onLogout);
};

/**
 * Attiva un utente (Solo Staff).
 */
export const activateUser = async (userIdToActivate, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/activate-user/${userIdToActivate}/`, {
        method: 'POST'
    }, onLogout);
};

/**
 * Elimina un utente (Solo Staff).
 */
export const deleteUser = async (userIdToDelete, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/delete-user/${userIdToDelete}/`, {
        method: 'DELETE'
    }, onLogout);
};

// --- STAFF: GESTIONE CAMPAGNE ---
export const staffGetCampagne = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne/', { method: 'GET' }, onLogout);

export const staffCreateCampagna = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCampagna = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCampagna = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetCampagnaUtenti = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne-utenti/', { method: 'GET' }, onLogout);

export const staffCreateCampagnaUtente = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne-utenti/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCampagnaUtente = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne-utenti/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCampagnaUtente = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne-utenti/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetCampagnaFeaturePolicy = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne-feature-policy/', { method: 'GET' }, onLogout);

export const staffCreateCampagnaFeaturePolicy = (data, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/staff/campagne-feature-policy/', {
        method: 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffUpdateCampagnaFeaturePolicy = (id, data, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne-feature-policy/${id}/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);

export const staffDeleteCampagnaFeaturePolicy = (id, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/staff/campagne-feature-policy/${id}/`, { method: 'DELETE' }, onLogout);

export const staffGetUsers = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/users/', { method: 'GET' }, onLogout);

/**
 * Recupera i messaggi indirizzati allo staff (is_staff_message=True)
 */
export const fetchStaffMessages = async (onLogout) => {
    // --- CORREZIONE: Usa l'endpoint specifico per lo staff invece di quello generico ---
    return fetchAuthenticated('/api/personaggi/api/staff/messages/', {
        method: 'GET'
    }, onLogout);
};

/**
 * Marca un messaggio staff come letto.
 */
export const markStaffMessageAsRead = async (messageId, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/messages/${messageId}/leggi/`, {
        method: 'POST'
    }, onLogout);
};

/**
 * Elimina un messaggio staff.
 */
export const deleteStaffMessage = async (messageId, onLogout) => {
    return fetchAuthenticated(`/api/personaggi/api/staff/messages/${messageId}/cancella/`, {
        method: 'POST'
    }, onLogout);
};

/**
 * Recupera conversazioni organizzate per thread.
 */
export const getConversazioni = async (personaggioId, onLogout) => {
    return fetchAuthenticated(
        `/api/personaggi/api/messaggi/conversazioni/?personaggio_id=${personaggioId}`,
        { method: 'GET' },
        onLogout
    );
};

/**
 * Risponde a un messaggio creando un thread.
 */
export const rispondiMessaggio = async (messaggioId, personaggioId, testo, titolo, onLogout) => {
    return fetchAuthenticated(
        `/api/personaggi/api/messaggi/${messaggioId}/rispondi/`,
        {
            method: 'POST',
            body: JSON.stringify({
                personaggio_id: personaggioId,
                testo,
                titolo
            })
        },
        onLogout
    );
};

// --- Scommesse in-game ---

export const scommesseGetCalendari = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/scommesse/calendari/', { method: 'GET' }, onLogout);

export const scommesseGetConfig = (onLogout) =>
    fetchAuthenticated('/api/personaggi/api/scommesse/config/', { method: 'GET' }, onLogout);

export const scommesseGetSquadraStorico = (squadraId, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/scommesse/squadre/${squadraId}/storico/`, { method: 'GET' }, onLogout);

export const scommesseGetCalendario = (calendarioId, onLogout) =>
    fetchAuthenticated(`/api/personaggi/api/scommesse/calendari/${calendarioId}/`, { method: 'GET' }, onLogout);

export const scommessePiazzaPuntata = (personaggioId, payload, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/scommesse/puntate/', {
        method: 'POST',
        body: JSON.stringify({ ...payload, personaggio_id: personaggioId }),
    }, onLogout);

export const scommesseGetMiePuntate = (personaggioId, onLogout) =>
    fetchAuthenticated(
        `/api/personaggi/api/scommesse/mie-puntate/?personaggio_id=${encodeURIComponent(personaggioId)}`,
        { method: 'GET' },
        onLogout,
    );

export const scommesseGeneraCodice = (personaggioId, onLogout) =>
    fetchAuthenticated('/api/personaggi/api/scommesse/codici/genera/', {
        method: 'POST',
        body: JSON.stringify({ personaggio_id: personaggioId }),
    }, onLogout);

export const scommesseGetMieiCodici = (personaggioId, onLogout) =>
    fetchAuthenticated(
        `/api/personaggi/api/scommesse/miei-codici/?personaggio_id=${encodeURIComponent(personaggioId)}`,
        { method: 'GET' },
        onLogout,
    );

const STAFF_SCOMMESSE = '/api/personaggi/api/staff/scommesse';

export const staffScommesseGetSport = (onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/sport/`, { method: 'GET' }, onLogout);

export const staffScommesseSaveSport = (data, onLogout, id = null) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/sport/${id ? `${id}/` : ''}`, {
        method: id ? 'PATCH' : 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffScommesseDeleteSport = (id, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/sport/${id}/`, { method: 'DELETE' }, onLogout);

export const staffScommesseGetSquadre = (sportId, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/squadre/${sportId ? `?sport=${sportId}` : ''}`, { method: 'GET' }, onLogout);

export const staffScommesseSaveSquadra = (data, onLogout, id = null) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/squadre/${id ? `${id}/` : ''}`, {
        method: id ? 'PATCH' : 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffScommesseDeleteSquadra = (id, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/squadre/${id}/`, { method: 'DELETE' }, onLogout);

export const staffScommesseGetCalendari = (onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/calendari/`, { method: 'GET' }, onLogout);

export const staffScommesseSaveCalendario = (data, onLogout, id = null) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/calendari/${id ? `${id}/` : ''}`, {
        method: id ? 'PATCH' : 'POST',
        body: JSON.stringify(data),
    }, onLogout);

export const staffScommesseDeleteCalendario = (id, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/calendari/${id}/`, { method: 'DELETE' }, onLogout);

export const staffScommesseRigeneraIncontri = (calendarioId, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/calendari/${calendarioId}/rigenera-incontri/`, { method: 'POST' }, onLogout);

export const staffScommesseGetConfig = (onLogout, campagnaId = null) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/config/${campagnaId ? `?campagna=${campagnaId}` : ''}`, { method: 'GET' }, onLogout);

export const staffScommesseSaveConfig = (data, onLogout) =>
    fetchAuthenticated(`${STAFF_SCOMMESSE}/config/`, {
        method: 'PATCH',
        body: JSON.stringify(data),
    }, onLogout);