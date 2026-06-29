/**
 * Client API per la console pilota.
 *
 * Regole architetturali:
 * - tutte le URL sono RELATIVE (Nginx instrada in base al dominio/IP usato).
 * - in dev Vite proxy a Django.
 * - autenticazione header: "Authorization: PilotToken <token>".
 *
 * Errore di rete -> espone flag `online=false` al chiamante che attiva il
 * fallback locale (vedi engine.js).
 */

const API_BASE = '';

const TOKEN_KEY = 'kor35_pilot_token';

export function getToken() {
  return localStorage.getItem(TOKEN_KEY) || '';
}
export function setToken(token) {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

async function request(path, { method = 'GET', body = null, auth = true } = {}) {
  const headers = { 'Content-Type': 'application/json' };
  if (auth) {
    const tk = getToken();
    if (tk) headers.Authorization = `PilotToken ${tk}`;
  }
  let res;
  try {
    res = await fetch(`${API_BASE}${path}`, {
      method,
      headers,
      body: body ? JSON.stringify(body) : null,
    });
  } catch (e) {
    const err = new Error('network_offline');
    err.network = true;
    throw err;
  }
  let data = null;
  try { data = await res.json(); } catch (_) { /* no body */ }
  if (!res.ok) {
    const err = new Error(data?.error || `HTTP ${res.status}`);
    err.status = res.status;
    err.payload = data;
    throw err;
  }
  return data;
}

export const api = {
  consoleEnabled: () => request('/api/pilot/console-enabled/', { auth: false }),
  autoLogin: () => request('/api/pilot/auth/auto-login/', { method: 'POST', body: {}, auth: false }),
  createConsoleTicket: () => request('/api/pilot/auth/console-ticket/', {
    method: 'POST', body: {}, auth: false,
  }),
  ticketStatus: (ticketId, codice) => request(`/api/pilot/auth/console-ticket/${ticketId}/status/?c=${encodeURIComponent(codice)}`, {
    auth: false,
  }),
  loginQr: (qrId) => request('/api/pilot/auth/qr-login/', {
    method: 'POST', body: { qr_id: qrId }, auth: false,
  }),
  logout: () => request('/api/pilot/auth/logout/', { method: 'POST' }),
  resetSession: () => request('/api/pilot/session/reset/', { method: 'POST' }),
  state: ({ advanceTick = true } = {}) => {
    const path = advanceTick
      ? '/api/pilot/session/state/'
      : '/api/pilot/session/state/?tick=0';
    return request(path);
  },
  catalog: () => request('/api/pilot/catalog/'),
  prefetture: () => request('/api/pilot/prefetture/'),
  startSession: (partenzaId, arrivoId) => request('/api/pilot/session/start/', {
    method: 'POST',
    body: { prefettura_partenza_id: partenzaId, prefettura_arrivo_id: arrivoId },
  }),
  command: (codice) => request('/api/pilot/session/command/', {
    method: 'POST', body: { codice },
  }),
  subsystemSet: (payload) => request('/api/pilot/session/subsystem-set/', {
    method: 'POST', body: payload,
  }),
  emergencyLanding: () => request('/api/pilot/session/emergency-landing/', { method: 'POST' }),
  takeoffPrepare: () => request('/api/pilot/session/takeoff/', { method: 'POST' }),
  takeoffComplete: () => request('/api/pilot/session/takeoff/complete/', { method: 'POST' }),
  landing: () => request('/api/pilot/session/landing/', { method: 'POST' }),
  setAllarmeEquipaggio: (allarme) => request('/api/pilot/session/allarme-equipaggio/', {
    method: 'POST',
    body: { allarme },
  }),
  allarmeLedState: () => request('/api/pilot/allarme-led/state/', { auth: false }),
  abort: () => request('/api/pilot/session/abort/', { method: 'POST' }),
  history: () => request('/api/pilot/session/history/'),
  diario: (sessioneId) => {
    const q = sessioneId ? `?sessione_id=${encodeURIComponent(sessioneId)}` : '';
    return request(`/api/pilot/session/diario/${q}`);
  },
  voli: () => request('/api/pilot/session/voli/'),
  tickStatus: () => request('/api/pilot/runtime/tick-status/'),
  tickControl: (action) => request('/api/pilot/runtime/tick-control/', {
    method: 'POST',
    body: { action },
  }),
  compattatoreState: () => request('/api/pilot/compattatore/state/'),
  compattatoreCompressione: (mattoneId) => request('/api/pilot/compattatore/compressione/', {
    method: 'POST',
    body: { mattone_id: mattoneId },
  }),
  compattatoreDecompressione: (mattoneId) => request('/api/pilot/compattatore/decompressione/', {
    method: 'POST',
    body: { mattone_id: mattoneId },
  }),
  compattatoreRisonanza: (mattoneId) => request('/api/pilot/compattatore/risonanza/', {
    method: 'POST',
    body: { mattone_id: mattoneId },
  }),
  compattatoreQuantico: (body) => request('/api/pilot/compattatore/quantico/', {
    method: 'POST',
    body,
  }),
};
