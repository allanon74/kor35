/** Serializza/deserializza filtri e amount pack MSE per l'editor. */

export function filterToText(filter) {
  if (!filter) return "";
  if (typeof filter === "string") return filter;
  if (filter.kind === "script") return filter.expr || "";
  if (filter.kind === "literal") return filter.value || "";
  return "";
}

export function filterFromText(text) {
  const raw = String(text || "").trim();
  if (!raw) return null;
  if (raw.startsWith("{") && raw.endsWith("}")) {
    return { kind: "script", expr: raw.slice(1, -1).trim() };
  }
  return { kind: "script", expr: raw };
}

export function amountToText(amount) {
  if (amount == null || amount === "") return "1";
  if (typeof amount === "number") return String(amount);
  if (typeof amount === "string") return amount || "1";
  if (amount.kind === "literal") return String(amount.value ?? "1");
  if (amount.kind === "script") return `{${amount.expr || ""}}`;
  return "1";
}

export function amountFromText(text) {
  const raw = String(text ?? "").trim();
  if (!raw) return { kind: "literal", value: "1" };
  if (raw.startsWith("{") && raw.endsWith("}")) {
    return { kind: "script", expr: raw.slice(1, -1).trim() };
  }
  return { kind: "literal", value: raw };
}

export function emptyPackItem() {
  return {
    name: "",
    select: "no replace",
    filter: null,
  };
}

export function emptyPackType() {
  return {
    name: "",
    select: "all",
    selectable: true,
    summary: true,
    enabled: true,
    items: [],
  };
}

export function emptyPackTypeItemRef() {
  return {
    name: "",
    amount: { kind: "literal", value: "1" },
  };
}

export function clonePackDraft(gameSpec) {
  const spec = gameSpec || {};
  return {
    pack_items: JSON.parse(JSON.stringify(spec.pack_items || [])),
    pack_types: JSON.parse(JSON.stringify(spec.pack_types || [])),
  };
}

export function buildMetaWithPackDraft(gameMeta, draft) {
  const meta = JSON.parse(JSON.stringify(gameMeta || {}));
  const spec = { ...(meta.mse_game_spec || {}), version: meta.mse_game_spec?.version || "1" };
  spec.pack_items = (draft.pack_items || []).filter((p) => p?.name);
  spec.pack_types = (draft.pack_types || [])
    .filter((p) => p?.name)
    .map((pack) => ({
      ...pack,
      items: (pack.items || []).filter((item) => item?.name),
    }));
  meta.mse_game_spec = spec;
  return meta;
}
