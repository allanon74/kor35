import { mediaUrl } from "./assetUrl";
import { evalMseProp } from "./scriptEngine";
import { mseColorToCss, normFieldKey } from "./fieldUtils";

function pickProp(styleDef, ...keys) {
  for (const k of keys) {
    if (styleDef[k] !== undefined) return styleDef[k];
    const norm = k.replace(/ /g, "_");
    if (styleDef[norm] !== undefined) return styleDef[norm];
  }
  return undefined;
}

function resolveBox(styleDef, ctx, cardW, cardH) {
  let left = Number(evalMseProp(pickProp(styleDef, "left"), ctx, 0));
  let top = Number(evalMseProp(pickProp(styleDef, "top"), ctx, 0));
  let width = Number(evalMseProp(pickProp(styleDef, "width"), ctx, 0));
  let height = Number(evalMseProp(pickProp(styleDef, "height"), ctx, 0));
  const right = evalMseProp(pickProp(styleDef, "right"), ctx, null);
  const bottom = evalMseProp(pickProp(styleDef, "bottom"), ctx, null);

  if (!width && right !== null && left) width = Number(right) - left;
  if (!height && bottom !== null && top) height = Number(bottom) - top;
  if (!width) width = Math.max(40, cardW - left - 20);
  if (!height) height = 24;

  return {
    left: Math.max(0, left),
    top: Math.max(0, top),
    width: Math.max(1, width),
    height: Math.max(1, height),
    angle: Number(evalMseProp(pickProp(styleDef, "angle", "z index"), ctx, 0)) || 0,
  };
}

function inferRenderStyle(fieldName, cardFields) {
  const field = (cardFields || []).find(
    (f) => f.name === fieldName || normFieldKey(f.name) === normFieldKey(fieldName)
  );
  const t = String(field?.type || "").toLowerCase();
  if (t === "image" || t === "symbol") return "image";
  if (t === "choice" || t === "multiple choice" || t === "boolean") return "text";
  return "text";
}

function resolveFont(styleDef) {
  const font = pickProp(styleDef, "font") || {};
    const sizeRaw = evalMseProp(font.size, {}, 14);
    const colorRaw = evalMseProp(font.color, {}, "#f9fafb");
  return {
    family: font.name || font.family || "inherit",
    size: Number(sizeRaw) || 14,
    color: mseColorToCss(String(colorRaw)) || "#f9fafb",
    weight: font.weight || "normal",
  };
}

function fieldValueForName(fieldName, card, cardFields) {
  const field = (cardFields || []).find(
    (f) => f.name === fieldName || normFieldKey(f.name) === normFieldKey(fieldName)
  );
  if (field) {
    return card[field.name] ?? card[normFieldKey(field.name)] ?? "";
  }
  return card[fieldName] ?? card[normFieldKey(fieldName)] ?? "";
}

function resolveLayersFromStyles(stylesMap, options) {
  const { mseV1, card, styling, set, cardFields, extractedRoot, ctxBase } = options;
  const cardW = mseV1?.card_size?.width || 375;
  const cardH = mseV1?.card_size?.height || 523;
  const layers = [];

  Object.entries(stylesMap || {}).forEach(([fieldName, styleDef]) => {
    const ctx = {
      ...ctxBase,
      card,
      styling,
      set,
      card_style: { [fieldName]: styleDef },
    };
    const visible = evalMseProp(pickProp(styleDef, "visible"), ctx, true);
    if (visible === false || visible === "false" || visible === 0) return;

    const box = resolveBox(styleDef, ctx, cardW, cardH);
    const z = Number(evalMseProp(pickProp(styleDef, "z_index", "z index"), ctx, 0)) || 0;
    const renderStyle = String(
      evalMseProp(pickProp(styleDef, "render_style", "render style"), ctx, "") ||
        inferRenderStyle(fieldName, cardFields)
    ).toLowerCase();

    const imageProp = pickProp(styleDef, "image", "mask");
    const imageRaw = imageProp
      ? evalMseProp(imageProp, ctx, "")
      : fieldValueForName(fieldName, card, cardFields);

    if (renderStyle === "image" || (String(imageRaw).match(/\.(png|jpg|jpeg|webp|gif|bmp|svg)$/i))) {
      const src = mediaUrl(extractedRoot, String(imageRaw || "").trim());
      if (src) {
        layers.push({
          type: "image",
          fieldName,
          z,
          box,
          src,
        });
      }
      return;
    }

    const text =
      String(
        evalMseProp(pickProp(styleDef, "text"), ctx, "") ||
          fieldValueForName(fieldName, card, cardFields)
      ) || "";

    if (!text && fieldName !== "name") return;

    layers.push({
      type: "text",
      fieldName,
      z,
      box,
      text,
      font: resolveFont(styleDef),
      alignment: String(evalMseProp(pickProp(styleDef, "alignment"), ctx, "left top")),
    });
  });

  return layers;
}

export function resolveMseLayers({
  mseV1,
  card,
  styling = {},
  set = {},
  cardFields = [],
  extractedRoot = "",
}) {
  if (!mseV1) return { width: 375, height: 523, background: "#111827", layers: [] };

  const ctxBase = { card, styling, set, card_style: {} };
  const cardStyles = { ...(mseV1.card_styles || {}), ...(mseV1.extra_card_styles || {}) };
  const layers = resolveLayersFromStyles(cardStyles, {
    mseV1,
    card,
    styling,
    set,
    cardFields,
    extractedRoot,
    ctxBase,
  }).sort((a, b) => a.z - b.z || a.box.top - b.box.top);

  const bg = mseColorToCss(mseV1.card_background) || "#1f2937";
  const framePath = findFrameOverlay(mseV1);
  if (framePath) {
    layers.push({
      type: "image",
      fieldName: "__frame__",
      z: 1000,
      box: { left: 0, top: 0, width: mseV1.card_size?.width || 375, height: mseV1.card_size?.height || 523 },
      src: mediaUrl(extractedRoot, framePath),
    });
  }

  return {
    width: mseV1.card_size?.width || 375,
    height: mseV1.card_size?.height || 523,
    background: bg,
    layers,
  };
}

function findFrameOverlay(mseV1) {
  const styles = mseV1.card_styles || {};
  for (const [name, def] of Object.entries(styles)) {
    if (/frame|border|template/i.test(name)) {
      const img = def.image || def.mask;
      if (img?.kind === "literal") return img.value;
      if (typeof img === "string") return img;
    }
  }
  return "";
}

export function defaultStylingFromSpec(mseV1) {
  const styling = {};
  (mseV1?.styling_fields || []).forEach((field) => {
    const initial = field.initial ?? field.default ?? "";
    const t = String(field.type || "text").toLowerCase();
    if (t === "boolean") {
      styling[field.name] = !["false", "no", "0"].includes(String(initial).toLowerCase());
    } else {
      styling[field.name] = initial;
    }
    styling[normFieldKey(field.name)] = styling[field.name];
  });
  return styling;
}
