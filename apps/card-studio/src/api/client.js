const STAFF_CARTE = "/api/personaggi/api/staff/carte";
const STAFF_PLATFORM = `${STAFF_CARTE}/platform`;
const LOGIN_PATH = import.meta.env.VITE_LOGIN_PATH || "/login";
import { formatApiError } from "./errors";
let loginRedirectTriggered = false;

function getAuthToken() {
  return String(localStorage.getItem("kor35_token") || "").trim();
}

function getActiveCampaignSlug() {
  return String(localStorage.getItem("kor35_active_campaign") || "").trim().toLowerCase();
}

function redirectToLogin() {
  if (loginRedirectTriggered) return;
  loginRedirectTriggered = true;
  const next = window.location.pathname + window.location.search + window.location.hash;
  const sep = LOGIN_PATH.includes("?") ? "&" : "?";
  window.location.assign(`${LOGIN_PATH}${sep}next=${encodeURIComponent(next)}`);
}

async function fetchJson(url, options = {}) {
  const token = getAuthToken();
  const activeCampaign = getActiveCampaignSlug();
  const authHeaders = token ? { Authorization: `Token ${token}` } : {};
  const campaignHeaders = activeCampaign ? { "X-Campagna": activeCampaign } : {};
  const method = String(options.method || "GET").toUpperCase();
  const res = await fetch(url, {
    credentials: "include",
    cache: method === "GET" ? "no-store" : options.cache,
    headers: {
      "Content-Type": "application/json",
      ...authHeaders,
      ...campaignHeaders,
      ...(options.headers || {}),
    },
    ...options,
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error("Sessione non valida o permessi insufficienti.");
  }
  if (res.status === 403) {
    throw new Error("Permessi insufficienti: serve un account staff abilitato.");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(formatApiError(data, `Errore API (${res.status})`));
  }
  return data;
}

const toList = (payload) => (Array.isArray(payload) ? payload : payload?.results || []);

export async function loadInitialData() {
  const [espansioni, carte, keywords, templates, giochi, packages] = await Promise.all([
    fetchJson(`${STAFF_CARTE}/espansioni/`),
    fetchJson(`${STAFF_CARTE}/catalogo/`),
    fetchJson(`${STAFF_CARTE}/keywords/`),
    fetchJson(`${STAFF_PLATFORM}/templates/`).catch(() => []),
    fetchJson(`${STAFF_PLATFORM}/gioco/`).catch(() => []),
    fetchJson(`${STAFF_PLATFORM}/packages/`).catch(() => []),
  ]);
  return {
    espansioni: toList(espansioni),
    carte: toList(carte),
    keywords: toList(keywords),
    templates: toList(templates),
    giochi: toList(giochi),
    packages: toList(packages),
  };
}

export const saveEspansione = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/espansioni/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });

export const deleteEspansione = (id) =>
  fetchJson(`${STAFF_CARTE}/espansioni/${id}/`, { method: "DELETE" });

export const saveCarta = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/catalogo/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });

export const deleteCarta = (id) =>
  fetchJson(`${STAFF_CARTE}/catalogo/${id}/`, { method: "DELETE" });

export const saveKeyword = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/keywords/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });

export const saveGioco = (id, payload) =>
  fetchJson(`${STAFF_PLATFORM}/gioco/${id}/`, {
    method: "PATCH",
    body: JSON.stringify(payload),
  });

export async function importMseStyleTemplate({
  file,
  gioco_definizione,
  nome,
  slug,
  is_default_for_new_cards = false,
}) {
  const fd = new FormData();
  fd.append("file", file);
  if (gioco_definizione) fd.append("gioco_definizione", gioco_definizione);
  if (nome) fd.append("nome", nome);
  if (slug) fd.append("slug", slug);
  fd.append("is_default_for_new_cards", is_default_for_new_cards ? "true" : "false");

  const token = getAuthToken();
  const activeCampaign = getActiveCampaignSlug();
  const headers = {};
  if (token) headers.Authorization = `Token ${token}`;
  if (activeCampaign) headers["X-Campagna"] = activeCampaign;

  const res = await fetch(`${STAFF_PLATFORM}/templates/import-mse-style/`, {
    method: "POST",
    credentials: "include",
    headers,
    body: fd,
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error("Sessione non valida o permessi insufficienti.");
  }
  if (res.status === 403) {
    throw new Error("Permessi insufficienti: serve un account staff abilitato.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || data?.error || `Import fallito (${res.status})`);
  }
  return data;
}

export async function importMseSet({
  file,
  gioco_definizione,
  nome,
  slug,
  create_cards = true,
  update_existing = true,
}) {
  const fd = new FormData();
  fd.append("file", file);
  if (gioco_definizione) fd.append("gioco_definizione", gioco_definizione);
  if (nome) fd.append("nome", nome);
  if (slug) fd.append("slug", slug);
  fd.append("create_cards", create_cards ? "true" : "false");
  fd.append("update_existing", update_existing ? "true" : "false");

  const token = getAuthToken();
  const activeCampaign = getActiveCampaignSlug();
  const headers = {};
  if (token) headers.Authorization = `Token ${token}`;
  if (activeCampaign) headers["X-Campagna"] = activeCampaign;

  const res = await fetch(`${STAFF_CARTE}/espansioni/import-mse-set/`, {
    method: "POST",
    credentials: "include",
    headers,
    body: fd,
  });
  if (res.status === 401) {
    redirectToLogin();
    throw new Error("Sessione non valida o permessi insufficienti.");
  }
  if (res.status === 403) {
    throw new Error("Permessi insufficienti: serve un account staff abilitato.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || data?.error || `Import fallito (${res.status})`);
  }
  return data;
}
