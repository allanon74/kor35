import { isTrustedBlobUrl, mediaUrl } from "./assetUrl";
import { evalMseProp } from "./scriptEngine";
import {
  findPackageByName,
  normalizeMsePackageName,
  normalizeSymbolFieldText,
  resolveSymbolLayersForText,
  symbolImageUrl,
  textContainsSymbolTokens,
} from "./symbolFonts";
import { mseColorToCss, normFieldKey, lookupChoiceColor } from "./fieldUtils";

function pickProp(styleDef, ...keys) {
  for (const k of keys) {
    if (styleDef[k] !== undefined) return styleDef[k];
    const norm = k.replace(/ /g, "_");
    if (styleDef[norm] !== undefined) return styleDef[norm];
  }
  return undefined;
}

function isAbsoluteMediaSrc(raw) {
  const s = String(raw || "").trim();
  return (
    /^(https?:)?\/\//i.test(s) ||
    s.startsWith("/media/") ||
    isTrustedBlobUrl(s) ||
    s.startsWith("data:")
  );
}

function resolveImageSrc(extractedRoot, raw) {
  const s = String(raw || "").trim();
  if (!s) return "";
  if (s.startsWith("blob:") && !isTrustedBlobUrl(s)) return "";
  if (isAbsoluteMediaSrc(s)) return s;
  return mediaUrl(extractedRoot, s);
}

function resolveBox(styleDef, ctx, cardW, cardH) {
  let left = Number(evalMseProp(pickProp(styleDef, "left"), ctx, 0));
  let top = Number(evalMseProp(pickProp(styleDef, "top"), ctx, 0));
  let width = Number(evalMseProp(pickProp(styleDef, "width"), ctx, 0));
  let height = Number(evalMseProp(pickProp(styleDef, "height"), ctx, 0));
  const right = evalMseProp(pickProp(styleDef, "right"), ctx, null);
  const bottom = evalMseProp(pickProp(styleDef, "bottom"), ctx, null);

  if ((!width || Number.isNaN(width)) && right !== null && right !== undefined && !Number.isNaN(Number(right))) {
    width = Number(right) - (Number.isNaN(left) ? 0 : left);
  }
  if ((!height || Number.isNaN(height)) && bottom !== null && bottom !== undefined && !Number.isNaN(Number(bottom))) {
    height = Number(bottom) - (Number.isNaN(top) ? 0 : top);
  }
  if (!width || Number.isNaN(width)) width = Math.max(40, cardW - (Number.isNaN(left) ? 0 : left) - 20);
  if (!height || Number.isNaN(height)) height = 24;
  if (Number.isNaN(left)) left = 0;
  if (Number.isNaN(top)) top = 0;

  return {
    left: Math.max(0, left),
    top: Math.max(0, top),
    width: Math.max(1, width),
    height: Math.max(1, height),
    angle: Number(evalMseProp(pickProp(styleDef, "angle"), ctx, 0)) || 0,
  };
}

function inferRenderStyle(fieldName, cardFields) {
  const field = (cardFields || []).find(
    (f) => f.name === fieldName || normFieldKey(f.name) === normFieldKey(fieldName)
  );
  const t = String(field?.type || "").toLowerCase();
  if (t === "image" || t === "symbol") return "image";
  if (t === "choice" || t === "multiple choice" || t === "boolean") return "text";
  const nk = normFieldKey(fieldName);
  if (["image", "art", "illustration", "card_frame", "frame", "watermark"].includes(nk)) return "image";
  return "text";
}

function fieldDefForName(fieldName, cardFields) {
  return (cardFields || []).find(
    (f) => f.name === fieldName || normFieldKey(f.name) === normFieldKey(fieldName)
  );
}

function choiceTextColor(fieldName, text, cardFields) {
  const field = fieldDefForName(fieldName, cardFields);
  if (!field) return "";
  const map = field.choice_colors_cardlist || field.choice_colors || {};
  return lookupChoiceColor(map, text);
}

/** Font MSE desktop → stack web leggibile (i .ttf MSE non sono serviti come @font-face). */
const WEB_FONT_FALLBACKS = {
  matrix: '"Matrix", "Times New Roman", Times, Georgia, serif',
  matrixbold: '"Matrix", "Times New Roman", Times, Georgia, serif',
  mplantin: '"MPlantin", Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif',
  "mplantin-italic": '"MPlantin", Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif',
  "mplantin-bold": '"MPlantin", Palatino, "Palatino Linotype", "Book Antiqua", Georgia, serif',
  beleren: 'Beleren, Georgia, "Times New Roman", serif',
  "beleren small caps": 'Beleren, Georgia, "Times New Roman", serif',
  goudymedieval: 'Goudy Medieval, "Palatino Linotype", Palatino, Georgia, serif',
  arial: "Arial, Helvetica, sans-serif",
};

function mapFontFamily(name) {
  const raw = String(name || "").trim();
  if (!raw || raw === "inherit") return 'Georgia, "Times New Roman", serif';
  const key = raw.toLowerCase();
  if (WEB_FONT_FALLBACKS[key]) return WEB_FONT_FALLBACKS[key];
  const compact = key.replace(/\s+/g, "");
  if (WEB_FONT_FALLBACKS[compact]) return WEB_FONT_FALLBACKS[compact];
  // Beleren Bold → Beleren
  const base = key.replace(/\s+bold$/, "").replace(/\s+/g, "");
  if (WEB_FONT_FALLBACKS[base]) return WEB_FONT_FALLBACKS[base];
  return `"${raw}", Georgia, "Times New Roman", serif`;
}

function resolveFont(styleDef) {
  const font = pickProp(styleDef, "font") || {};
  const sizeRaw = evalMseProp(font.size, {}, 14);
  const colorRaw = evalMseProp(font.color, {}, "#f9fafb");
  const nameRaw = evalMseProp(font.name, {}, null);
  const familyRaw = evalMseProp(font.family, {}, null);
  const weightRaw = evalMseProp(font.weight, {}, "normal");
  const familyName =
    (typeof nameRaw === "string" && nameRaw) ||
    (typeof familyRaw === "string" && familyRaw) ||
    "";
  let color = mseColorToCss(String(colorRaw ?? "#f9fafb")) || "#f9fafb";
  // MSE Magic usa spesso "black" su carta chiara
  if (["black", "rgb(0,0,0)", "#000", "#000000"].includes(String(colorRaw).trim().toLowerCase())) {
    color = "#111827";
  }
  if (["white", "rgb(255,255,255)", "#fff", "#ffffff"].includes(String(colorRaw).trim().toLowerCase())) {
    color = "#f8fafc";
  }
  let weight = typeof weightRaw === "string" || typeof weightRaw === "number" ? weightRaw : "normal";
  if (/bold/i.test(familyName) && weight === "normal") weight = "700";
  return {
    family: mapFontFamily(familyName || "inherit"),
    size: Number(sizeRaw) || 14,
    color,
    weight,
  };
}

/** Nome package symbol-font dichiarato nello style (o legacy parse bug). */
function styleSymbolFontName(styleDef) {
  const fromFont = styleDef?.font?.symbol_font || styleDef?.font?.["symbol font"];
  if (fromFont) {
    const n = evalMseProp(fromFont, {}, "");
    if (n) return normalizeMsePackageName(n);
  }
  const sf = pickProp(styleDef, "symbol_font", "symbol font");
  if (sf && typeof sf === "object") {
    const n = evalMseProp(sf.name, {}, "");
    if (n) return normalizeMsePackageName(n);
  }
  if (sf) {
    const n = evalMseProp(sf, {}, "");
    if (n) return normalizeMsePackageName(n);
  }
  // Parser legacy: `symbol font:` non annidato → name/size finivano sul card style.
  const rootName = evalMseProp(pickProp(styleDef, "name"), {}, "");
  if (rootName && /mana|symbol|aure/i.test(String(rootName))) {
    return normalizeMsePackageName(rootName);
  }
  return "";
}

function fieldValueForName(fieldName, card, cardFields) {
  const nk = normFieldKey(fieldName);
  const aliases = {
    text: ["rule_text", "rules", "rules_text", "card_text", "text", "testo_gioco"],
    rule_text: ["rule_text", "rules", "text", "testo_gioco"],
    casting_cost: ["casting_cost", "mana_cost"],
    name: ["name", "nome", "title", "card_name"],
    image: ["image", "art", "illustration", "immagine", "immagine_url", "immagine_preview"],
    art: ["art", "image", "illustration", "immagine", "immagine_url", "immagine_preview"],
    pt: ["pt", "power_toughness"],
    power: ["power", "attack", "forza", "attacco"],
    toughness: ["toughness", "health", "robustezza", "salute"],
    cost: ["cost", "mana_cost", "casting_cost", "costo_gioco"],
    type: ["type", "card_type", "tipo"],
    rarity: ["rarity", "rarita"],
  };
  const keys = aliases[nk] || [nk, fieldName];
  for (const key of keys) {
    if (card[key] !== undefined && card[key] !== null && card[key] !== "") return card[key];
    const spaced = String(key).replace(/_/g, " ");
    if (card[spaced] !== undefined && card[spaced] !== null && card[spaced] !== "") return card[spaced];
  }
  const field = (cardFields || []).find(
    (f) => f.name === fieldName || normFieldKey(f.name) === nk
  );
  if (field) {
    return card[field.name] ?? card[normFieldKey(field.name)] ?? "";
  }
  return card[fieldName] ?? card[nk] ?? "";
}

function isArtLikeField(fieldName) {
  return ["art", "image", "illustration", "picture"].includes(normFieldKey(fieldName));
}

function cardColorFramePath(card, assetsManifest) {
  const colorRaw = String(
    card.card_color || card.card_colour || card.color || card.colour || ""
  )
    .toLowerCase()
    .trim();
  const map = {
    white: "wcard.jpg",
    w: "wcard.jpg",
    blue: "ucard.jpg",
    u: "ucard.jpg",
    black: "bcard.jpg",
    b: "bcard.jpg",
    red: "rcard.jpg",
    r: "rcard.jpg",
    green: "gcard.jpg",
    g: "gcard.jpg",
    artifact: "acard.jpg",
    a: "acard.jpg",
    colorless: "ccard.jpg",
    colourless: "ccard.jpg",
    c: "ccard.jpg",
    multicolor: "mcard.jpg",
    multicolour: "mcard.jpg",
    gold: "mcard.jpg",
    m: "mcard.jpg",
    land: "lcard.jpg",
  };
  const preferred = map[colorRaw];
  const images = (assetsManifest || [])
    .filter((a) => a?.asset_type === "image" || /\.(png|jpe?g|webp)$/i.test(a?.path || ""))
    .map((a) => String(a.path || "").replace(/^\/+/, ""));
  const has = (name) => images.find((p) => p === name || p.endsWith(`/${name}`) || p.toLowerCase().endsWith(name));
  if (preferred) {
    const hit = has(preferred);
    if (hit) return hit;
  }
  for (const cand of ["card-sample.png", "wcard.jpg", "ccard.jpg", "mcard.jpg", "bcard.jpg"]) {
    const hit = has(cand);
    if (hit) return hit;
  }
  const anyCard = images.find((p) => /(^|\/)[a-z]*card\.jpg$/i.test(p) || /card-sample/i.test(p));
  return anyCard || "";
}

function resolveLayersFromStyles(stylesMap, options) {
  const {
    mseV1,
    card,
    styling,
    set,
    cardFields,
    extractedRoot,
    ctxBase,
    symbolFontPackage,
    packages = [],
  } = options;
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

    const layerSymbolName = styleSymbolFontName(styleDef);
    const layerSymbolPkg =
      (layerSymbolName && findPackageByName(packages, layerSymbolName)) || symbolFontPackage;

    const imageProp = pickProp(styleDef, "image", "mask");
    let imageRaw = imageProp ? evalMseProp(imageProp, ctx, "") : "";
    if (!imageRaw) {
      imageRaw = evalMseProp(pickProp(styleDef, "default"), ctx, "") || "";
    }
    if (!imageRaw && (renderStyle === "image" || isArtLikeField(fieldName))) {
      imageRaw = fieldValueForName(fieldName, card, cardFields);
    }
    // Script MSE falliti (es. default_image(...)): usa illustrazione carta se presente.
    if (!imageRaw && isArtLikeField(fieldName)) {
      imageRaw = card.immagine_preview || card.immagine_url || card.image || card.art || "";
    }

    if (renderStyle === "image" || String(imageRaw).match(/\.(png|jpg|jpeg|webp|gif|bmp|svg)$/i) || isAbsoluteMediaSrc(imageRaw)) {
      const raw = String(imageRaw || "").trim();
      const looksLikeFile =
        isAbsoluteMediaSrc(raw) || /\.(png|jpg|jpeg|webp|gif|bmp|svg)$/i.test(raw) || raw.includes("/");
      let src = looksLikeFile ? resolveImageSrc(extractedRoot, raw) : "";
      if (!src && layerSymbolPkg && raw) {
        src = symbolImageUrl(layerSymbolPkg, raw);
      }
      if (!src && layerSymbolPkg && raw && renderStyle === "symbol") {
        src = symbolImageUrl(layerSymbolPkg, normalizeSymbolFieldText(raw, true));
      }
      if (src) {
        layers.push({
          type: "image",
          fieldName,
          z,
          box,
          src,
        });
        return;
      }
      if (renderStyle === "image" && !raw) return;
    }

    const text =
      String(
        evalMseProp(pickProp(styleDef, "text"), ctx, "") ||
          fieldValueForName(fieldName, card, cardFields)
      ) || "";

    if (!text && fieldName !== "name") return;

    const font = resolveFont(styleDef);
    const choiceColor = choiceTextColor(fieldName, text, cardFields);
    if (choiceColor) font.color = choiceColor;
    const alwaysSymbolProp = styleDef?.font?.always_symbol || styleDef?.font?.["always symbol"] || styleDef?.always_symbol;
    const alwaysSymbol =
      Boolean(evalMseProp(alwaysSymbolProp, ctx, false)) ||
      /casting_cost|mana_cost|^cost$/i.test(normFieldKey(fieldName));
    const symbolText = normalizeSymbolFieldText(text, alwaysSymbol);

    if (
      layerSymbolPkg &&
      (renderStyle === "symbol" || alwaysSymbol || textContainsSymbolTokens(symbolText))
    ) {
      layers.push({
        type: "symbols",
        fieldName,
        z,
        box,
        glyphs: resolveSymbolLayersForText(symbolText, layerSymbolPkg, font.size, {
          boxHeight: box.height,
          boxWidth: box.width,
          fieldName,
        }),
        font,
        alignment: String(evalMseProp(pickProp(styleDef, "alignment"), ctx, "left top")),
        wrap: renderStyle === "symbol" || /^(rules|rule_text|text|testo_gioco)$/i.test(normFieldKey(fieldName)),
      });
      return;
    }

    layers.push({
      type: "text",
      fieldName,
      z,
      box,
      text,
      font,
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
  assetsManifest = null,
  symbolFontPackage = null,
  packages = [],
}) {
  if (!mseV1) return { width: 375, height: 523, dpi: 300, background: "#111827", layers: [] };

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
    symbolFontPackage,
    packages,
  }).sort((a, b) => a.z - b.z || a.box.top - b.box.top);

  const bgRaw = mseV1.card_background;
  let bg = mseColorToCss(bgRaw) || "#1f2937";
  const styleKeys = Object.keys(cardStyles);
  const looksMagic = styleKeys.some((k) => /casting cost|card color|rule text/i.test(k));
  // Preview Magic: carta chiara (i font MSE sono neri).
  if (looksMagic) bg = "#f3efe6";
  // KOR35 / altri: resta lo sfondo dello style.
  const hasFrameLayer = layers.some(
    (l) => l.type === "image" && /frame|border|card_frame|__frame__/i.test(l.fieldName)
  );
  const framePath = hasFrameLayer
    ? ""
    : findFrameOverlay(mseV1) || cardColorFramePath(card, assetsManifest);
  if (framePath) {
    layers.unshift({
      type: "image",
      fieldName: "__frame__",
      z: -10,
      box: { left: 0, top: 0, width: mseV1.card_size?.width || 375, height: mseV1.card_size?.height || 523 },
      src: resolveImageSrc(extractedRoot, framePath),
    });
  }

  return {
    width: mseV1.card_size?.width || 375,
    height: mseV1.card_size?.height || 523,
    dpi: Number(mseV1.card_size?.dpi) || 300,
    background: bg,
    layers: layers.sort((a, b) => a.z - b.z || a.box.top - b.box.top),
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
