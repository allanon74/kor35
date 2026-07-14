/** Formatta errori DRF in messaggio leggibile per l’UI. */
export function formatApiError(data, fallback = "Errore API") {
  if (!data || typeof data !== "object") return fallback;
  if (typeof data.detail === "string") return data.detail;
  if (typeof data.error === "string") return data.error;
  if (typeof data.message === "string") return data.message;

  const parts = [];
  Object.entries(data).forEach(([field, value]) => {
    if (Array.isArray(value)) {
      parts.push(`${field}: ${value.map((v) => String(v)).join(", ")}`);
    } else if (typeof value === "string") {
      parts.push(`${field}: ${value}`);
    } else if (value && typeof value === "object") {
      parts.push(`${field}: ${JSON.stringify(value)}`);
    }
  });
  return parts.length ? parts.join(" · ") : fallback;
}

export function slugifySetCode(name) {
  return String(name || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "")
    .slice(0, 80);
}

export function sanitizeEspansionePayload(payload) {
  const out = { ...payload };
  ["gioco_definizione", "default_studio_template", "immagine"].forEach((k) => {
    if (out[k] === "" || out[k] === undefined) out[k] = null;
  });
  ["vendita_dal", "vendita_al"].forEach((k) => {
    if (out[k] === "" || out[k] === undefined) out[k] = null;
  });
  if (out.nome != null) out.nome = String(out.nome).trim();
  if (out.slug != null) out.slug = String(out.slug).trim();
  if (!out.slug && out.nome) out.slug = slugifySetCode(out.nome);
  return out;
}
