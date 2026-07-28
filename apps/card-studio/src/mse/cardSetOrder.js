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

const CARTA_CODICE_MAX_LEN = 40;

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

/** Codice set = slug espansione (campo «code» nel tab Set). */
export function setCodeFromEspansione(espansione) {
  const slug = String(espansione?.slug || "").trim().toLowerCase();
  if (!slug) return "set";
  const maxSlugLen = CARTA_CODICE_MAX_LEN - 4; // trattino + 3 cifre
  return slug.length > maxSlugLen ? slug.slice(0, maxSlugLen).replace(/-+$/g, "") : slug;
}

export function buildCartaCodice(setSlug, number) {
  const code = setCodeFromEspansione({ slug: setSlug });
  return `${code}-${String(Number(number) || 1).padStart(3, "0")}`;
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
 * `{slug}-{NNN}` dopo sort colore → alfabetico.
 */
export function previewRenumberExpansionCards(expansionCards, espansione) {
  const setCode = setCodeFromEspansione(espansione);
  return sortCardsForSetOrder(expansionCards).map((card, idx) => ({
    ...card,
    ordine_set: idx + 1,
    codice: buildCartaCodice(setCode, idx + 1),
  }));
}
