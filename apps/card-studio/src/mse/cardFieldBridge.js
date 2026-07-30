import { normFieldKey } from "./fieldUtils";

const IMAGE_KEYS = new Set(["image", "art", "illustration", "picture", "immagine"]);

function isImageFieldKey(k) {
  return IMAGE_KEYS.has(k);
}

export function readCardFieldValue(cardForm, field) {
  const k = normFieldKey(field?.name);
  if (["name", "card_name", "title"].includes(k)) return cardForm.nome || "";
  if (["rules", "rules_text", "rule_text", "text", "card_text"].includes(k)) {
    return cardForm.testo_gioco || "";
  }
  if (["lore", "flavor", "flavor_text"].includes(k)) return cardForm.testo_lore || "";
  if (["type", "card_type"].includes(k)) return cardForm.tipo || "";
  if (["energy", "mana", "resource"].includes(k)) return cardForm.energia || "";
  if (["rarity"].includes(k)) return cardForm.rarita || "";
  if (["cost", "mana_cost", "casting_cost"].includes(k)) {
    if (k === "casting_cost") {
      return cardForm.mse_campi?.casting_cost ?? cardForm.mse_campi?.["casting cost"] ?? cardForm.costo_gioco ?? "";
    }
    return cardForm.costo_gioco ?? 0;
  }
  if (["attack", "power", "forza"].includes(k)) return cardForm.attacco ?? 0;
  if (["health", "toughness", "robustezza"].includes(k)) return cardForm.salute ?? 0;
  if (["initiative", "iniziativa"].includes(k)) return cardForm.iniziativa ?? 0;
  if (["codice", "code", "card_code"].includes(k)) return cardForm.codice || "";
  if (isImageFieldKey(k)) {
    return (
      cardForm.immagine_preview ||
      cardForm.immagine_url ||
      cardForm.mse_campi?.[k] ||
      cardForm.mse_campi?.image ||
      cardForm.mse_campi?.art ||
      ""
    );
  }
  return cardForm.mse_campi?.[k] ?? field?.initial ?? "";
}

export function writeCardFieldPatch(cardForm, field, rawValue) {
  const k = normFieldKey(field?.name);
  const fType = String(field?.type || "").toLowerCase();
  let v = rawValue;
  if (["number", "int"].includes(fType)) {
    v = Number(rawValue || 0);
  } else if (fType === "multiple choice") {
    v = Array.isArray(rawValue)
      ? rawValue
      : String(rawValue || "")
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean);
  } else if (fType === "boolean") {
    v = rawValue === true || rawValue === "yes" || rawValue === "true";
  }

  if (["name", "card_name", "title"].includes(k)) return { ...cardForm, nome: String(v) };
  if (["rules", "rules_text", "rule_text", "text", "card_text"].includes(k)) {
    return { ...cardForm, testo_gioco: String(v) };
  }
  if (["lore", "flavor", "flavor_text"].includes(k)) return { ...cardForm, testo_lore: String(v) };
  if (["type", "card_type"].includes(k)) return { ...cardForm, tipo: String(v) };
  if (["energy", "mana", "resource"].includes(k)) return { ...cardForm, energia: String(v) };
  if (["rarity"].includes(k)) return { ...cardForm, rarita: String(v) };
  if (["cost", "mana_cost"].includes(k)) return { ...cardForm, costo_gioco: Number(v) };
  if (["attack", "power", "forza"].includes(k)) return { ...cardForm, attacco: Number(v) };
  if (["health", "toughness", "robustezza"].includes(k)) return { ...cardForm, salute: Number(v) };
  if (["initiative", "iniziativa"].includes(k)) return { ...cardForm, iniziativa: Number(v) };
  if (["codice", "code", "card_code"].includes(k)) return { ...cardForm, codice: String(v) };
  if (isImageFieldKey(k) || fType === "image") {
    const next = {
      ...cardForm,
      mse_campi: {
        ...(cardForm.mse_campi || {}),
        [k]: v,
        image: v,
      },
    };
    if (typeof v === "string" && (v.startsWith("blob:") || v.startsWith("/media/") || v.startsWith("http"))) {
      next.immagine_preview = v;
    }
    return next;
  }

  return {
    ...cardForm,
    mse_campi: {
      ...(cardForm.mse_campi || {}),
      [k]: v,
    },
  };
}
