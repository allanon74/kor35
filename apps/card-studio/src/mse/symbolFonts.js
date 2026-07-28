/** Symbol font package helpers (MSE .mse-symbol-font). */

import { mediaUrl } from "./assetUrl";
import { normFieldKey, wildcardMatch } from "./fieldUtils";

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
  return (packages || []).find((p) => packageDisplayName(p) === name) || null;
}

export function findSymbolFontPackage(packages, matchPattern, selectedName) {
  if (selectedName) {
    const hit = findPackageByName(packages, selectedName);
    if (hit?.package_type === "mse-symbol-font") return hit;
  }
  if (!matchPattern) return null;
  return (packages || []).find(
    (p) =>
      p.package_type === "mse-symbol-font" &&
      wildcardMatch(matchPattern, packageDisplayName(p))
  );
}

export function findGameSymbolFontField(gameCardFields) {
  return (gameCardFields || []).find(
    (f) => String(f.type || "").toLowerCase() === "package choice" && /symbol-font/i.test(String(f.match || ""))
  );
}

export function resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm) {
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
  return (
    (packages || []).find(
      (p) => p.package_type === "mse-symbol-font" && p.package_name === "KOR35 Aure"
    ) || null
  );
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
