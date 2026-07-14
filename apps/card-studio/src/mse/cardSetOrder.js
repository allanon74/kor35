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

export function compareCardsForSetOrder(a, b) {
  const auraA = KOR35_AURA_RANK[a?.energia] ?? 999;
  const auraB = KOR35_AURA_RANK[b?.energia] ?? 999;
  if (auraA !== auraB) return auraA - auraB;
  const byOrdine = (Number(a?.ordine_set) || 0) - (Number(b?.ordine_set) || 0);
  if (byOrdine !== 0) return byOrdine;
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

function cardNumberFromCodice(codice, setCode) {
  const raw = String(codice || "").trim().toLowerCase();
  const prefix = `${setCode}-`;
  if (!raw.startsWith(prefix)) return 0;
  const m = raw.match(/-(\d{3})$/);
  return m ? Number(m[1]) : 0;
}

/**
 * Prossimo codice `{slug-set}-{NNN}` e ordine_set per una nuova carta.
 */
export function suggestCardIdentity({ expansionCards, espansione }) {
  const setCode = setCodeFromEspansione(espansione);
  const maxNum = (expansionCards || []).reduce((max, card) => {
    const fromOrdine = Number(card?.ordine_set) || 0;
    const fromCode = cardNumberFromCodice(card?.codice, setCode);
    return Math.max(max, fromOrdine, fromCode);
  }, 0);
  const next = maxNum + 1;
  return {
    ordine_set: next,
    codice: buildCartaCodice(setCode, next),
  };
}
