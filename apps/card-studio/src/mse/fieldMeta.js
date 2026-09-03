/** Metadati tipi campo MSE (da doc/type/field.txt). */

export const MSE_FIELD_TYPE_LABELS = {
  text: "Text",
  choice: "Choice",
  "multiple choice": "Multiple choice",
  "package choice": "Package choice",
  boolean: "Boolean",
  color: "Color",
  image: "Image",
  symbol: "Symbol",
  info: "Info",
  number: "Number",
  int: "Integer",
};

export function fieldTypeLabel(field) {
  const t = String(field?.type || "text").toLowerCase();
  return MSE_FIELD_TYPE_LABELS[t] || t;
}

export const FIELD_DESCRIPTION_PLACEHOLDER =
  "Passa il mouse su un campo (o selezionalo) per vederne la descrizione.";

export function fieldStatusDescription(field) {
  const custom = String(field?.description || "").trim();
  if (custom) return custom;

  const t = String(field?.type || "text").toLowerCase();
  const name = field?.name || "field";
  const bits = [`${name} (${fieldTypeLabel(field)})`];

  if (field?.identifying) bits.push("identifying");
  if (field?.editable === false) bits.push("read-only");
  if (field?.multi_line) bits.push("multi-line");
  if (field?.required === false) bits.push(`optional, empty="${field?.empty_name || "None"}"`);
  if (field?.card_list_visible) bits.push("shown in card list");
  if (field?.show_statistics === false) bits.push("hidden from statistics");

  const typeHints = {
    text: "Tagged text for rules, names, etc.",
    choice: "Single value from the choices list.",
    "multiple choice": "Zero or more choices; stored as comma-separated values.",
    "package choice": "Installed package matching the game match pattern.",
    boolean: "yes or no.",
    color: "Color value (rgb or choice).",
    image: "Carica un'illustrazione (Browse…) oppure incolla un percorso/URL.",
    symbol: "Symbol edited with the MSE symbol editor (path).",
    info: "Informational label; not editable.",
    number: "Numeric value.",
    int: "Integer value.",
  };
  if (typeHints[t]) bits.push(typeHints[t]);

  return bits.join(" · ");
}

export function sortCardFieldsForEditor(fields) {
  const priority = (field) => {
    const k = String(field?.name || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_");
    const map = {
      name: 10,
      full_name: 11,
      casting_cost: 20,
      casting_cost_2: 21,
      image: 30,
      type: 40,
      super_type: 41,
      subtype: 42,
      rarity: 50,
      rule_text: 60,
      text: 61,
      flavor_text: 62,
      power: 70,
      toughness: 71,
      pt: 72,
      illustrator: 80,
      card_number: 90,
    };
    return map[k] ?? 500;
  };
  const typeRank = (field) => {
    const t = String(field?.type || "").toLowerCase();
    if (t === "info") return 0;
    if (field?.identifying) return 1;
    if (t === "image") return 2;
    return 3;
  };
  return [...(fields || [])].sort((a, b) => {
    const pa = priority(a);
    const pb = priority(b);
    if (pa !== pb) return pa - pb;
    const ra = typeRank(a);
    const rb = typeRank(b);
    if (ra !== rb) return ra - rb;
    return String(a?.name || "").localeCompare(String(b?.name || ""));
  });
}

/** Spec MSE enormi (Magic completo): nasconde campi calcolati/non editabili. */
export function filterEditorCardFields(fields) {
  const list = Array.isArray(fields) ? fields : [];
  if (list.length < 40) return list;
  return list.filter((f) => {
    if (f?.identifying) return true;
    if (f?.editable === false) return false;
    const t = String(f?.type || "").toLowerCase();
    if (t === "info") return false;
    return true;
  });
}
