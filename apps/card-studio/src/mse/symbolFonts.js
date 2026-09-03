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

export function tokenizeSymbolText(text) {
  const s = String(text || "");
  if (!s) return [];
  const parts = [];
  let last = 0;
  for (const m of s.matchAll(TOKEN_RE)) {
    if (m.index > last) parts.push({ kind: "text", value: s.slice(last, m.index) });
    parts.push({ kind: "symbol", value: m[0] });
    last = m.index + m[0].length;
  }
  if (last < s.length) parts.push({ kind: "text", value: s.slice(last) });
  return parts.length ? parts : [{ kind: "text", value: s }];
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
  return "";
}

export function normalizeSymbolFieldText(text, alwaysSymbol = false) {
  const s = String(text || "").trim();
  if (!s) return s;
  if (textContainsSymbolTokens(s)) return s;
  if (alwaysSymbol && /^[A-Za-z]{2,4}$/.test(s)) return `{${s.toUpperCase()}}`;
  if (alwaysSymbol && /^\d+$/.test(s)) return `{${s}}`;
  return s;
}

export function textContainsSymbolTokens(text) {
  return TOKEN_RE.test(String(text || ""));
}

export function resolveSymbolLayersForText(text, symbolFontPkg, fontSize = 14) {
  const parts = tokenizeSymbolText(text);
  const glyphs = parts.map((part) => {
    if (part.kind === "text") return { type: "text", value: part.value };
    const src = symbolImageUrl(symbolFontPkg, part.value);
    return src
      ? { type: "image", value: part.value, src, size: Math.max(12, fontSize) }
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

/** Token comuni per inserimento rapido (Magic + generici). */
export const COMMON_SYMBOL_INSERTS = [
  "{W}",
  "{U}",
  "{B}",
  "{R}",
  "{G}",
  "{C}",
  "{1}",
  "{2}",
  "{3}",
  "{4}",
  "{X}",
  "{T}",
];

export function fieldWantsSymbolInsert(field) {
  const k = normFieldKey(field?.name);
  if (/casting_cost|mana_cost|rule_text|rules|text/.test(k)) return true;
  if (field?.always_symbol) return true;
  const desc = String(field?.description || "").toLowerCase();
  return desc.includes("{w}") || desc.includes("mana") || desc.includes("symbol");
}
