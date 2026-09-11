/** Symbol font package helpers (MSE .mse-symbol-font). */

import { mediaUrl } from "./assetUrl";
import { normFieldKey, wildcardMatch } from "./fieldUtils";

/** Strip MSE package suffix for matching (magic-mana-large.mse-symbol-font → magic-mana-large). */
export function normalizeMsePackageName(name) {
  return String(name || "")
    .trim()
    .replace(/\.mse-(symbol-font|style|game|include|font)$/i, "");
}

export function packageDisplayName(pkg) {
  return (
    pkg?.package_name ||
    pkg?.parsed_meta?.short_name ||
    pkg?.parsed_meta?.full_name ||
    ""
  );
}

export function findPackageByName(packages, name) {
  if (!name) return null;
  const want = normalizeMsePackageName(name).toLowerCase();
  return (
    (packages || []).find((p) => normalizeMsePackageName(packageDisplayName(p)).toLowerCase() === want) ||
    null
  );
}

export function findSymbolFontPackage(packages, matchPattern, selectedName) {
  if (selectedName) {
    const hit = findPackageByName(packages, selectedName);
    if (hit?.package_type === "mse-symbol-font") return hit;
  }
  if (!matchPattern) return null;
  const pat = normalizeMsePackageName(matchPattern);
  return (packages || []).find((p) => {
    if (p.package_type !== "mse-symbol-font") return false;
    const name = normalizeMsePackageName(packageDisplayName(p));
    return wildcardMatch(pat, name) || wildcardMatch(matchPattern, packageDisplayName(p));
  });
}

export function findGameSymbolFontField(gameCardFields) {
  return (gameCardFields || []).find((f) => {
    const t = String(f.type || "").toLowerCase();
    if (t !== "package choice") return false;
    const hay = `${f.match || ""} ${f.name || ""}`;
    return /symbol.?font|mana/i.test(hay);
  });
}

function pickStylingSymbolFontName(styling, mseV1) {
  if (!styling || typeof styling !== "object") return "";
  const fields = mseV1?.styling_fields || [];
  for (const field of fields) {
    const hay = `${field.match || ""} ${field.name || ""}`;
    if (!/symbol.?font|mana/i.test(hay)) continue;
    const k = normFieldKey(field.name);
    const val = styling[field.name] ?? styling[k] ?? "";
    if (val) return String(val);
  }
  for (const [k, v] of Object.entries(styling)) {
    if (/symbol.?font|mana.?symbol/i.test(k) && v) return String(v);
  }
  return "";
}

/** Preferenze tipiche Magic / fallback KOR35. */
const SYMBOL_FONT_FALLBACKS = ["magic-mana-large", "magic-mana-small", "KOR35 Aure"];

export function resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm, options = {}) {
  const { mseV1 = null, styling = null, preferredName = "" } = options;

  if (preferredName) {
    const hit = findSymbolFontPackage(packages, "", preferredName);
    if (hit) return hit;
  }

  const field = findGameSymbolFontField(gameCardFields);
  if (field) {
    const k = normFieldKey(field.name);
    const selected =
      cardForm?.mse_campi?.[k] ??
      cardForm?.mse_campi?.[field.name] ??
      field.initial ??
      "";
    const hit = findSymbolFontPackage(packages, field.match, selected);
    if (hit) return hit;
  }

  const fromStyling = pickStylingSymbolFontName(styling, mseV1);
  if (fromStyling) {
    const hit = findSymbolFontPackage(packages, "", fromStyling);
    if (hit) return hit;
  }

  for (const name of SYMBOL_FONT_FALLBACKS) {
    const hit = findPackageByName(packages, name);
    if (hit?.package_type === "mse-symbol-font") return hit;
  }

  return (packages || []).find((p) => p.package_type === "mse-symbol-font") || null;
}

const TOKEN_RE = /\{[^}]+\}/g;
const TOKEN_TEST_RE = /\{[^}]+\}/;

/** Espande `{12}` in `{1}{2}` per costi multi-cifra. */
function expandSymbolToken(token) {
  const inner = String(token || "")
    .trim()
    .replace(/^\{|\}$/g, "");
  if (/^\d{2,}$/.test(inner)) {
    return inner.split("").map((d) => `{${d}}`);
  }
  return [token];
}

export function tokenizeSymbolText(text) {
  const s = String(text || "");
  if (!s) return [];
  const parts = [];
  let last = 0;
  for (const m of s.matchAll(TOKEN_RE)) {
    if (m.index > last) parts.push({ kind: "text", value: s.slice(last, m.index) });
    for (const tok of expandSymbolToken(m[0])) {
      parts.push({ kind: "symbol", value: tok });
    }
    last = m.index + m[0].length;
  }
  if (last < s.length) parts.push({ kind: "text", value: s.slice(last) });
  return parts.length ? parts : [{ kind: "text", value: s }];
}

const KOR35_AURA_CODES = new Set(["MAR", "TEC", "INN", "MAG", "SAC", "PSI", "ARC"]);

/** Percorso relativo PNG KOR35 quando parsed_meta è incompleto (package non ri-bootstrapato). */
function kor35SymbolImageRelPath(code) {
  const inner = String(code || "")
    .trim()
    .replace(/^\{|\}$/g, "")
    .trim();
  if (!inner) return "";
  if (/^\d$/.test(inner)) return `symbols/cost-${inner}.png`;
  const aura = inner.toUpperCase();
  if (KOR35_AURA_CODES.has(aura)) return `symbols/${aura.toLowerCase()}.png`;
  return "";
}

export function symbolImageUrl(symbolFontPkg, code) {
  const symbols = symbolFontPkg?.parsed_meta?.symbols || {};
  const raw = String(code || "").trim();
  const candidates = [raw];
  if (raw && !raw.startsWith("{")) {
    candidates.push(`{${raw}}`, `{${raw.toUpperCase()}}`);
  }
  for (const key of candidates) {
    const entry = symbols[key] || symbols[key.toLowerCase()];
    const image = entry?.image;
    if (image && symbolFontPkg?.extracted_root) {
      return mediaUrl(symbolFontPkg.extracted_root, image);
    }
  }
  const root = symbolFontPkg?.extracted_root;
  if (root) {
    for (const key of candidates) {
      const rel = kor35SymbolImageRelPath(key);
      if (rel) return mediaUrl(root, rel);
    }
  }
  return "";
}

export function normalizeSymbolFieldText(text, alwaysSymbol = false) {
  const s = String(text || "").trim();
  if (!s) return s;
  if (textContainsSymbolTokens(s)) {
    return tokenizeSymbolText(s)
      .map((p) => p.value)
      .join("");
  }
  if (alwaysSymbol && /^[A-Za-z]{2,4}$/.test(s)) return `{${s.toUpperCase()}}`;
  if (alwaysSymbol && /^\d+$/.test(s)) return [...s].map((d) => `{${d}}`).join("");
  return s;
}

export function textContainsSymbolTokens(text) {
  return TOKEN_TEST_RE.test(String(text || ""));
}

/** Dimensione glifo simbolo in px (anteprima / export PNG). */
export function computeSymbolGlyphSize({ fontSize = 14, boxHeight = 0, boxWidth = 0, fieldName = "" } = {}) {
  const nk = normFieldKey(fieldName);
  const boxMin = boxHeight > 0 && boxWidth > 0 ? Math.min(boxHeight, boxWidth) : 0;
  if (/^energy$|^cost$|^casting_cost|^mana_cost/.test(nk)) {
    return Math.max(28, Math.round((boxMin || fontSize * 1.75) * 0.92));
  }
  if (/^rules|rule_text|^text$|testo_gioco/.test(nk)) {
    return Math.max(20, Math.round(fontSize * 1.55));
  }
  return Math.max(18, Math.round(fontSize * 1.35));
}

export function resolveSymbolLayersForText(text, symbolFontPkg, fontSize = 14, options = {}) {
  const { boxHeight = 0, boxWidth = 0, fieldName = "" } = options;
  const glyphSize = computeSymbolGlyphSize({ fontSize, boxHeight, boxWidth, fieldName });
  const parts = tokenizeSymbolText(text);
  const glyphs = parts.map((part) => {
    if (part.kind === "text") return { type: "text", value: part.value };
    const src = symbolImageUrl(symbolFontPkg, part.value);
    return src
      ? { type: "image", value: part.value, src, size: glyphSize }
      : { type: "text", value: part.value };
  });
  return glyphs;
}

/** Spezza testo in parole/spazi per permettere il wrap in anteprima/export. */
export function splitGlyphsIntoWrappableUnits(glyphs) {
  const out = [];
  for (const g of glyphs || []) {
    if (g.type === "image") {
      out.push(g);
      continue;
    }
    const raw = String(g.value || "");
    if (!raw) continue;
    const chunks = raw.split(/(\s+)/);
    for (const chunk of chunks) {
      if (chunk) out.push({ type: "text", value: chunk });
    }
  }
  return out;
}

/** Sette Aure KOR35 + costi numerici (testo regole / costo carta). */
export const KOR35_AURA_SYMBOL_INSERTS = [
  "{MAR}",
  "{TEC}",
  "{INN}",
  "{MAG}",
  "{SAC}",
  "{PSI}",
  "{ARC}",
];

export const KOR35_COST_SYMBOL_INSERTS = ["{0}", "{1}", "{2}", "{3}", "{4}", "{5}", "{6}", "{7}", "{8}", "{9}"];

/** Token per inserimento rapido (KOR35 + Magic generici). */
export const COMMON_SYMBOL_INSERTS = [
  ...KOR35_AURA_SYMBOL_INSERTS,
  ...KOR35_COST_SYMBOL_INSERTS,
  "{W}",
  "{U}",
  "{B}",
  "{R}",
  "{G}",
  "{C}",
  "{X}",
  "{T}",
];

export function fieldWantsSymbolInsert(field) {
  const k = normFieldKey(field?.name);
  if (/casting_cost|mana_cost|^cost$|^energy$|rule_text|rules|text|testo_gioco/.test(k)) return true;
  if (field?.always_symbol) return true;
  const desc = String(field?.description || "").toLowerCase();
  return desc.includes("{w}") || desc.includes("mana") || desc.includes("symbol");
}
