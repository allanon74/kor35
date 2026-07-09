const STAFF_CARTE = "/api/personaggi/api/staff/carte";
const STAFF_PLATFORM = `${STAFF_CARTE}/platform`;
const LOGIN_PATH = import.meta.env.VITE_LOGIN_PATH || "/login";
let loginRedirectTriggered = false;

function redirectToLogin() {
  if (loginRedirectTriggered) return;
  loginRedirectTriggered = true;
  const next = window.location.pathname + window.location.search + window.location.hash;
  const sep = LOGIN_PATH.includes("?") ? "&" : "?";
  window.location.assign(`${LOGIN_PATH}${sep}next=${encodeURIComponent(next)}`);
}

async function fetchJson(url, options = {}) {
  const res = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });
  if (res.status === 401 || res.status === 403) {
    redirectToLogin();
    throw new Error("Sessione non valida o permessi insufficienti.");
  }
  if (res.status === 204) return null;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(
      data?.detail ||
        data?.error ||
        data?.message ||
        `Errore API (${res.status})`
    );
  }
  return data;
}

const toList = (payload) => (Array.isArray(payload) ? payload : payload?.results || []);

export async function loadInitialData() {
  const [espansioni, carte, keywords, templates, giochi] = await Promise.all([
    fetchJson(`${STAFF_CARTE}/espansioni/`),
    fetchJson(`${STAFF_CARTE}/catalogo/`),
    fetchJson(`${STAFF_CARTE}/keywords/`),
    fetchJson(`${STAFF_PLATFORM}/templates/`).catch(() => []),
    fetchJson(`${STAFF_PLATFORM}/gioco/`).catch(() => []),
  ]);
  return {
    espansioni: toList(espansioni),
    carte: toList(carte),
    keywords: toList(keywords),
    templates: toList(templates),
    giochi: toList(giochi),
  };
}

export const saveEspansione = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/espansioni/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });

export const saveCarta = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/catalogo/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
    body: JSON.stringify(payload),
  });

export const saveKeyword = (id, payload) =>
  fetchJson(`${STAFF_CARTE}/keywords/${id ? `${id}/` : ""}`, {
    method: id ? "PATCH" : "POST",
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

  const res = await fetch(`${STAFF_PLATFORM}/templates/import-mse-style/`, {
    method: "POST",
    credentials: "include",
    body: fd,
  });
  if (res.status === 401 || res.status === 403) {
    redirectToLogin();
    throw new Error("Sessione non valida o permessi insufficienti.");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data?.detail || data?.error || `Import fallito (${res.status})`);
  }
  return data;
}
