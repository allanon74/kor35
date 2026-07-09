export function normFieldKey(name) {
  return String(name || "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "_")
    .replace(/^_+|_+$/g, "");
}

export function wildcardMatch(pattern, text) {
  if (!pattern) return true;
  const esc = String(pattern)
    .replace(/[.+^${}()|[\]\\]/g, "\\$&")
    .replace(/\*/g, ".*")
    .replace(/\?/g, ".");
  return new RegExp(`^${esc}$`, "i").test(String(text || ""));
}

export function mseColorToCss(raw) {
  const s = String(raw || "").trim();
  if (!s) return "";
  if (s.startsWith("#") || s.startsWith("rgb")) return s;
  const rgb = s.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
  if (rgb) return `rgb(${rgb[1]},${rgb[2]},${rgb[3]})`;
  return s;
}

export function cardFieldValue(row, field) {
  const k = normFieldKey(field?.name);
  if (["name", "card_name", "title"].includes(k)) return row.nome || "";
  if (["rules", "rules_text", "text", "card_text"].includes(k)) return row.testo_gioco || "";
  if (["lore", "flavor", "flavor_text"].includes(k)) return row.testo_lore || "";
  if (["type", "card_type"].includes(k)) return row.tipo || "";
  if (["energy", "mana", "resource"].includes(k)) return row.energia || "";
  if (["rarity"].includes(k)) return row.rarita || "";
  if (["cost", "mana_cost"].includes(k)) return row.costo_gioco ?? "";
  if (["attack", "power", "forza"].includes(k)) return row.attacco ?? "";
  if (["health", "toughness", "robustezza"].includes(k)) return row.salute ?? "";
  if (["initiative", "iniziativa"].includes(k)) return row.iniziativa ?? "";
  if (k === "codice" || k === "code") return row.codice || "";
  return row.mse_campi?.[k] ?? field?.initial ?? "";
}

export function formatFieldValueForDisplay(value, field) {
  const fType = String(field?.type || "text").toLowerCase();
  if (fType === "multiple choice") {
    if (Array.isArray(value)) return value.join(", ");
    return String(value || "")
      .split(",")
      .map((x) => x.trim())
      .filter(Boolean)
      .join(", ");
  }
  if (value === null || value === undefined || value === "") return "—";
  return String(value);
}

export function lookupChoiceColor(colorMap, rawValue) {
  if (!colorMap || typeof colorMap !== "object") return "";
  const val = String(rawValue ?? "").trim();
  if (!val) return "";
  return (
    mseColorToCss(colorMap[val]) ||
    mseColorToCss(colorMap[val.toLowerCase()]) ||
    mseColorToCss(colorMap[val.toUpperCase()])
  );
}
