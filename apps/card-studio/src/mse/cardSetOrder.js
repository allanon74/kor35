/** Ordine aure KOR35: naturali → soprannaturali (come CARTA_ENERGIA_CHOICES). */
export const KOR35_AURA_RANK = {
  MAR: 10,
  TEC: 20,
  INN: 30,
  MAG: 40,
  SAC: 50,
  PSI: 60,
  ARC: 70,
};

const SIGLA_MAX_LEN = 8;
const CARTA_CODICE_MAX_LEN = 40;

const STOPWORDS = new Set([
  "a", "an", "and", "at", "by", "da", "dei", "del", "della", "delle", "di",
  "e", "for", "from", "il", "in", "into", "la", "le", "lo", "of", "on", "or",
  "the", "to", "un", "una", "uno",
]);

/**
 * Ordine stile Magic: colore (energia) → alfabetico nome → codice.
 * `ordine_set` non guida il sort (viene riassegnato dalla rinumerazione).
 */
export function compareCardsForSetOrder(a, b) {
  const auraA = KOR35_AURA_RANK[a?.energia] ?? 999;
  const auraB = KOR35_AURA_RANK[b?.energia] ?? 999;
  if (auraA !== auraB) return auraA - auraB;
  const nomeCmp = String(a?.nome || "").localeCompare(String(b?.nome || ""), "it", {
    sensitivity: "base",
  });
  if (nomeCmp !== 0) return nomeCmp;
  return String(a?.codice || "").localeCompare(String(b?.codice || ""), "it");
}

export function sortCardsForSetOrder(cards) {
  return [...(cards || [])].sort(compareCardsForSetOrder);
}

export function normalizeSigla(raw) {
  return String(raw || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^A-Za-z0-9]/g, "")
    .toUpperCase()
    .slice(0, SIGLA_MAX_LEN);
}

/**
 * Suggerisce sigla da titolo (es. «KOR: the beginning» → KBE).
 */
export function suggestSiglaFromNome(nome, maxLen = 3) {
  const limit = Math.max(2, Math.min(Number(maxLen) || 3, SIGLA_MAX_LEN));
  const raw = String(nome || "")
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "");
  const tokens = raw.split(/[^A-Za-z0-9]+/).filter(Boolean);
  const words = tokens.filter((t) => !STOPWORDS.has(t.toLowerCase()));
  const parts = words.length ? words : tokens;
  if (!parts.length) return "SET";
  if (parts.length === 1) return normalizeSigla(parts[0]).slice(0, limit) || "SET";

  let initials = normalizeSigla(parts.map((w) => w[0]).join(""));
  if (initials.length >= limit) return initials.slice(0, limit);

  const last = parts[parts.length - 1].replace(/[^A-Za-z0-9]/g, "");
  let extra = last.slice(1);
  while (initials.length < limit && extra) {
    initials += extra[0].toUpperCase();
    extra = extra.slice(1);
  }
  return normalizeSigla(initials).slice(0, limit) || "SET";
}

/** Prefisso codice carta = sigla set (KBE), fallback da nome/slug. */
export function setCodeFromEspansione(espansione) {
  const fromSigla = normalizeSigla(espansione?.sigla || "");
  if (fromSigla) return fromSigla;
  if (espansione?.nome) return suggestSiglaFromNome(espansione.nome);
  const slug = String(espansione?.slug || "").trim();
  if (!slug) return "SET";
  const compact = normalizeSigla(slug.replace(/-/g, ""));
  if (compact.length >= 2 && compact.length <= SIGLA_MAX_LEN && !slug.includes("-")) {
    return compact;
  }
  return suggestSiglaFromNome(slug.replace(/-/g, " "));
}

export function buildCartaCodice(setPrefix, number) {
  let prefix = normalizeSigla(setPrefix) || "SET";
  const num = String(Number(number) || 1).padStart(3, "0");
  const maxPrefix = CARTA_CODICE_MAX_LEN - 1 - num.length;
  if (prefix.length > maxPrefix) prefix = prefix.slice(0, Math.max(1, maxPrefix));
  return `${prefix}-${num}`;
}

/**
 * Anteprima codice/ordine per una nuova carta: posizione in lista
 * colore → alfabetico tra le carte esistenti + draft.
 */
export function suggestCardIdentity({ expansionCards, espansione, draftCard }) {
  const setCode = setCodeFromEspansione(espansione);
  const draft = {
    id: "__draft__",
    nome: draftCard?.nome || "",
    energia: draftCard?.energia || "MAR",
    codice: "",
  };
  const sorted = sortCardsForSetOrder([...(expansionCards || []), draft]);
  const index = sorted.findIndex((c) => c.id === "__draft__");
  const next = index >= 0 ? index + 1 : sorted.length;
  return {
    ordine_set: next,
    codice: buildCartaCodice(setCode, next),
  };
}

/**
 * Anteprima locale di rinumerazione (non persiste): assegna ordine_set e codice
 * `{SIGLA}-{NNN}` dopo sort colore → alfabetico.
 */
export function previewRenumberExpansionCards(expansionCards, espansione) {
  const setCode = setCodeFromEspansione(espansione);
  return sortCardsForSetOrder(expansionCards).map((card, idx) => ({
    ...card,
    ordine_set: idx + 1,
    codice: buildCartaCodice(setCode, idx + 1),
  }));
}
