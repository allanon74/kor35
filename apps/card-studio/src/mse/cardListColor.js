import {
  cardFieldValue,
  lookupChoiceColor,
  mseColorToCss,
  normFieldKey,
} from "./fieldUtils";

function firstChoiceColorsCardlistField(cardFields) {
  if (!Array.isArray(cardFields)) return null;
  return (
    cardFields.find(
      (f) => f.choice_colors_cardlist && Object.keys(f.choice_colors_cardlist).length > 0
    ) || null
  );
}

function fieldByName(cardFields, name) {
  if (!name || !Array.isArray(cardFields)) return null;
  const target = normFieldKey(name);
  return cardFields.find((f) => normFieldKey(f.name) === target) || null;
}

/**
 * Estrae il campo carta referenziato da uno script MSE card list color (subset).
 * Pattern supportati: card.field, card:field, card["field"], member su choice_colors map.
 */
export function extractColorScriptField(script, cardFields) {
  const src = String(script || "").trim();
  if (!src) return null;

  const cardRef = src.match(/card\s*[.:]\s*([a-z0-9 _-]+)/i);
  if (cardRef) {
    const hit = fieldByName(cardFields, cardRef[1]);
    if (hit) return hit;
  }

  for (const field of cardFields || []) {
    const name = String(field.name || "");
    if (!name) continue;
    const escaped = name.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
    if (new RegExp(escaped, "i").test(src)) {
      if (field.choice_colors_cardlist && Object.keys(field.choice_colors_cardlist).length > 0) {
        return field;
      }
    }
  }

  return null;
}

function evalSimpleColorExpression(expr, cardFields, getFieldValue) {
  const trimmed = String(expr || "").trim();
  if (!trimmed) return "";

  const rgbOnly = trimmed.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
  if (rgbOnly) return mseColorToCss(trimmed);

  const ifMatch = trimmed.match(/^if\s+(.+?)\s+then\s+(.+?)(?:\s+else\s+(.+))?$/is);
  if (ifMatch) {
    const cond = ifMatch[1].trim();
    const thenBranch = ifMatch[2].trim();
    const elseBranch = (ifMatch[3] || "rgb(0,0,0)").trim();
    const condField = extractColorScriptField(cond, cardFields) || fieldByName(cardFields, cond);
    const condVal = condField ? getFieldValue(condField) : cond;
    const truthy = Boolean(String(condVal ?? "").trim() && String(condVal) !== "0");
    return evalSimpleColorExpression(truthy ? thenBranch : elseBranch, cardFields, getFieldValue);
  }

  const mapField = extractColorScriptField(trimmed, cardFields);
  if (mapField) {
    const val = getFieldValue(mapField);
    return lookupChoiceColor(mapField.choice_colors_cardlist, val) || mseColorToCss("rgb(0,0,0)");
  }

  return mseColorToCss(trimmed);
}

/**
 * Risolve il colore riga card list (background) come MSE:
 * - script esplicito (subset) se presente
 * - altrimenti primo campo choice con choice_colors_cardlist
 */
export function resolveCardListRowColor({ gameSpec, cardFields, row }) {
  const fields = cardFields || gameSpec?.card_fields || [];
  const getFieldValue = (field) => cardFieldValue(row, field);

  const script = String(gameSpec?.card_list_color_script || "").trim();
  if (script) {
    const lines = script
      .split("\n")
      .map((l) => l.trim())
      .filter(Boolean);
    const lastLine = lines[lines.length - 1] || script;
    const css = evalSimpleColorExpression(lastLine, fields, getFieldValue);
    if (css) {
      return { backgroundColor: css, color: pickReadableTextColor(css) };
    }
  }

  const colorField = firstChoiceColorsCardlistField(fields);
  if (!colorField) return undefined;

  const css =
    lookupChoiceColor(colorField.choice_colors_cardlist, getFieldValue(colorField)) ||
    mseColorToCss("rgb(0,0,0)");
  if (!css) return undefined;
  return { backgroundColor: css, color: pickReadableTextColor(css) };
}

function pickReadableTextColor(cssColor) {
  const rgb = cssColor.match(/^rgb\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i);
  if (!rgb) return "#111827";
  const lum = (Number(rgb[1]) * 299 + Number(rgb[2]) * 587 + Number(rgb[3]) * 114) / 1000;
  return lum > 150 ? "#111827" : "#f9fafb";
}
