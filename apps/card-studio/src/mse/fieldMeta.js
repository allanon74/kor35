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
  const typeRank = (field) => {
    const t = String(field?.type || "").toLowerCase();
    if (t === "info") return 0;
    if (field?.identifying) return 1;
    if (t === "image") return 2;
    return 3;
  };
  return [...(fields || [])].sort((a, b) => {
    const ra = typeRank(a);
    const rb = typeRank(b);
    if (ra !== rb) return ra - rb;
    return String(a?.name || "").localeCompare(String(b?.name || ""));
  });
}
