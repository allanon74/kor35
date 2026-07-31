/**
 * Subset evaluator per script MSE (clean-room, non GPL).
 * Uso staff-only in Card Studio preview.
 */

import { isTrustedBlobUrl } from "./assetUrl";

function normalizeBool(value) {
  if (typeof value === "boolean") return value;
  const s = String(value ?? "").trim().toLowerCase();
  if (["true", "yes", "1"].includes(s)) return true;
  if (["false", "no", "0", ""].includes(s)) return false;
  return Boolean(value);
}

function mseToJs(expr) {
  let s = String(expr || "").trim();
  if (!s) return "null";

  s = s.replace(/\byes\b/gi, "true").replace(/\bno\b/gi, "false");
  s = s.replace(/\band\b/gi, "&&").replace(/\bor\b/gi, "||").replace(/\bnot\b/gi, "!");

  s = s.replace(/\bif\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$/gis, (_, cond, thenV, elseV) => {
    const e = elseV !== undefined ? elseV.trim() : "null";
    return `(${mseToJs(cond)}) ? (${mseToJs(thenV)}) : (${mseToJs(e)})`;
  });

  s = s.replace(
    /\b(card|styling|set|card_style)\.([a-zA-Z0-9_ ]+)/g,
    (_, root, field) => {
      const key = String(field).trim();
      if (/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key)) {
        return `${root}.${key}`;
      }
      return `${root}[${JSON.stringify(key)}]`;
    }
  );

  s = s.replace(/\brgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)/gi, '"rgb($1,$2,$3)"');
  return s;
}

export function evalMseScript(expr, ctx, fallback = null) {
  if (expr === null || expr === undefined || expr === "") return fallback;
  try {
    let js = mseToJs(expr);
    // Funzioni MSE comuni non implementate: evita throw e lascia fallback layer.
    js = js.replace(/\bmax\s*\(/g, "Math.max(").replace(/\bmin\s*\(/g, "Math.min(");
    js = js.replace(/\bdefault_image\s*\([^)]*\)/g, '""');
    js = js.replace(/\btemplate\s*\([^)]*\)/g, '""');
    js = js.replace(/\bframe_image\s*\([^)]*\)/g, '""');
    js = js.replace(/\bhas_identity\s*\([^)]*\)/g, "false");
    js = js.replace(/\bhas_identity\b/g, "false");
    js = js.replace(/\bchosen\s*\([^)]*\)/g, "false");
    js = js.replace(/\bcontains\s*\([^)]*\)/g, "false");
    js = js.replace(/\bcard_color\s*\([^)]*\)/g, '""');
    js = js.replace(/\bmana_filter\s*\([^)]*\)/g, '""');
    js = js.replace(/\bfilter_text\s*\([^)]*\)/g, '""');
    js = js.replace(/\bto_text\s*\(([^)]*)\)/g, "($1)");
    js = js.replace(/\bto_number\s*\(([^)]*)\)/g, "Number($1)||0");
    js = js.replace(/\bto_int\s*\(([^)]*)\)/g, "Number($1)||0");
    js = js.replace(/\bforward\s*\([^)]*\)/g, '""');
    js = js.replace(/\bcombine\s*\([^)]*\)/g, '""');
    js = js.replace(/\bfrom_script\s*\([^)]*\)/g, '""');
    js = js.replace(/\bset_code\s*\([^)]*\)/g, '""');
    js = js.replace(/\brarity_code\s*\([^)]*\)/g, '""');
    js = js.replace(/\benglish_double_sided_symbol\s*\([^)]*\)/g, '""');
    js = js.replace(/\bexpand\s*\([^)]*\)/g, '""');
    js = js.replace(/\breplace\s*\([^)]*\)/g, '""');
    js = js.replace(/\bsort_text\s*\([^)]*\)/g, '""');
    js = js.replace(/\bnumber_filter\s*\([^)]*\)/g, "0");
    js = js.replace(/\btext_filter\s*\([^)]*\)/g, '""');
    js = js.replace(/\bhorizontal_overlap\s*\([^)]*\)/g, "0");
    js = js.replace(/\bvertical_overlap\s*\([^)]*\)/g, "0");
    js = js.replace(/\blayout_function\s*\([^)]*\)/g, "0");
    js = js.replace(/\bdrop_shadow\s*\([^)]*\)/g, '""');
    js = js.replace(/\bmask\s*\([^)]*\)/g, '""');
    js = js.replace(/\bsymbol_font\s*\([^)]*\)/g, '""');
    js = js.replace(/\buse_large_v_mana\s*\([^)]*\)/g, "false");
    js = js.replace(/\buse_v_mana\s*\([^)]*\)/g, "false");
    const card = ctx.card || {};
    const styling = ctx.styling || {};
    const set = ctx.set || {};
    const card_style = withContentWidthStubs(ctx.card_style || {});
    // eslint-disable-next-line no-new-func
    const fn = new Function("card", "styling", "set", "card_style", `return (${js});`);
    const out = fn(card, styling, set, card_style);
    return out === undefined ? fallback : out;
  } catch {
    return fallback;
  }
}

function withContentWidthStubs(cardStyle) {
  const out = { ...cardStyle };
  Object.keys(out).forEach((k) => {
    const v = out[k];
    if (v && typeof v === "object" && v.content_width === undefined) {
      out[k] = { ...v, content_width: 40, content_lines: 1 };
    }
  });
  return new Proxy(out, {
    get(target, prop) {
      if (prop in target) return target[prop];
      return { content_width: 40, content_lines: 1 };
    },
  });
}

export function evalMseProp(prop, ctx, fallback = null) {
  if (prop === null || prop === undefined) return fallback;
  if (typeof prop === "object" && prop.kind === "script") {
    return evalMseScript(prop.expr, ctx, fallback);
  }
  if (typeof prop === "object" && prop.kind === "literal") {
    const raw = prop.value;
    if (raw === "true" || raw === "false") return raw === "true";
    const num = Number(raw);
    if (raw !== "" && !Number.isNaN(num) && String(num) === String(raw).trim()) {
      return num;
    }
    return raw;
  }
  if (typeof prop === "string" && prop.startsWith("{") && prop.endsWith("}")) {
    return evalMseScript(prop.slice(1, -1), ctx, fallback);
  }
  if (typeof prop === "boolean" || typeof prop === "number") return prop;
  const num = Number(prop);
  if (prop !== "" && !Number.isNaN(num) && /^-?\d+(\.\d+)?$/.test(String(prop).trim())) {
    return num;
  }
  if (["true", "false", "yes", "no"].includes(String(prop).toLowerCase())) {
    return normalizeBool(prop);
  }
  return prop;
}

export function buildCardScriptContext(cardForm, gameCardFields, getFieldValue) {
  const toMedia = (raw) => {
    const s = String(raw || "").trim();
    if (!s) return "";
    if (s.startsWith("blob:")) return isTrustedBlobUrl(s) ? s : "";
    if (s.startsWith("data:") || s.startsWith("/media/")) return s;
    if (/^https?:\/\//i.test(s)) {
      try {
        const u = new URL(s);
        return `${u.pathname}${u.search || ""}`;
      } catch {
        return s;
      }
    }
    if (s.startsWith("media/")) return `/${s}`;
    if (s.startsWith("/")) return s;
    return `/media/${s.replace(/^\/+/, "")}`;
  };

  const card = {
    codice: cardForm?.codice || "",
    immagine_url: toMedia(cardForm?.immagine_url || ""),
    immagine_preview: toMedia(cardForm?.immagine_preview || ""),
  };
  const imageFallback = toMedia(
    cardForm?.immagine_preview || cardForm?.immagine_url || cardForm?.mse_campi?.image || ""
  );
  if (imageFallback) {
    card.image = imageFallback;
    card.art = imageFallback;
    card.illustration = imageFallback;
  }
  (gameCardFields || []).forEach((field) => {
    const val = getFieldValue(field);
    const fType = String(field?.type || "").toLowerCase();
    const out = fType === "image" ? toMedia(val) : val;
    card[field.name] = out;
    const norm = String(field.name || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_");
    card[norm] = out;
  });
  // Alias catalogo ↔ MSE (sempre, anche se il campo non è nella spec filtrata)
  if (!card.name) card.name = cardForm?.nome || "";
  if (!card.nome) card.nome = cardForm?.nome || "";
  if (card.rule_text == null || card.rule_text === "") {
    card.rule_text = card.rules || card.text || cardForm?.testo_gioco || "";
  }
  if (card.text == null || card.text === "") card.text = card.rule_text || card.rules || "";
  if (card.casting_cost == null || card.casting_cost === "") {
    card.casting_cost =
      card.mana_cost ??
      cardForm?.mse_campi?.["casting cost"] ??
      cardForm?.mse_campi?.casting_cost ??
      "";
  }
  if (!card.pt && (card.power != null || card.toughness != null || cardForm?.attacco != null)) {
    const p = card.power ?? cardForm?.attacco ?? "";
    const t = card.toughness ?? cardForm?.salute ?? "";
    if (p !== "" || t !== "") card.pt = `${p}/${t}`;
  }
  if ((card.image == null || card.image === "") && imageFallback) card.image = imageFallback;
  return card;
}
