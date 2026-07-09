/**
 * Subset evaluator per script MSE (clean-room, non GPL).
 * Uso staff-only in Card Studio preview.
 */

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
    const js = mseToJs(expr);
    const card = ctx.card || {};
    const styling = ctx.styling || {};
    const set = ctx.set || {};
    const card_style = ctx.card_style || {};
    // eslint-disable-next-line no-new-func
    const fn = new Function("card", "styling", "set", "card_style", `return (${js});`);
    const out = fn(card, styling, set, card_style);
    return out === undefined ? fallback : out;
  } catch {
    return fallback;
  }
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
  const card = { codice: cardForm?.codice || "" };
  (gameCardFields || []).forEach((field) => {
    const val = getFieldValue(field);
    card[field.name] = val;
    const norm = String(field.name || "")
      .trim()
      .toLowerCase()
      .replace(/[^a-z0-9]+/g, "_");
    card[norm] = val;
  });
  return card;
}
