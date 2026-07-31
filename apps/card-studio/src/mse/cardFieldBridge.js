/**
 * Ponte campi MSE (name, rule text, …) ↔ campi catalogo KOR35 (nome, testo_gioco, …).
 * Evita di scrivere valori freeform Magic nei CharField a scelta ristretta (tipo/energia/rarita).
 */

import { normFieldKey } from "./fieldUtils";
import { isTrustedBlobUrl } from "./assetUrl";

const IMAGE_KEYS = new Set(["image", "art", "illustration", "picture", "immagine"]);

const KOR35_TIPI = new Set(["PG", "OG", "LU", "EV"]);
const KOR35_ENERGIE = new Set(["MAR", "TEC", "INN", "MAG", "SAC", "PSI", "ARC"]);
const KOR35_RARITA = new Set(["COM", "NON", "RAR", "EPI", "LEG", "UNI"]);

const NAME_KEYS = new Set(["name", "card_name", "title", "full_name"]);
const RULES_KEYS = new Set(["rules", "rules_text", "rule_text", "text", "card_text"]);
const LORE_KEYS = new Set(["lore", "flavor", "flavor_text"]);

function isImageFieldKey(k) {
  return IMAGE_KEYS.has(k);
}

function mseCampiGet(mse, ...keys) {
  const obj = mse || {};
  for (const key of keys) {
    if (obj[key] !== undefined && obj[key] !== null && obj[key] !== "") return obj[key];
    const spaced = String(key).replace(/_/g, " ");
    if (obj[spaced] !== undefined && obj[spaced] !== null && obj[spaced] !== "") return obj[spaced];
  }
  return "";
}

function isValidKor35Choice(value, allowed) {
  return allowed.has(String(value || "").trim().toUpperCase());
}

function asNumberOrNull(raw) {
  if (raw === null || raw === undefined || raw === "") return null;
  const n = Number(raw);
  return Number.isFinite(n) ? n : null;
}

/** Estrae nome catalogo da form / mse_campi (Name, full name, …). */
export function resolveCatalogNome(cardForm) {
  const direct = String(cardForm?.nome || "").trim();
  if (direct) return direct;
  const fromMse = String(
    mseCampiGet(cardForm?.mse_campi, "name", "nome", "full_name", "full name", "title", "card_name") || ""
  ).trim();
  return fromMse;
}

/**
 * Prima del save: assicura che i campi catalogo richiesti siano popolati
 * dai campi MSE compilati (Name → nome, ecc.).
 */
export function hydrateCatalogFieldsFromMse(cardForm) {
  const next = {
    ...cardForm,
    mse_campi: { ...(cardForm?.mse_campi || {}) },
  };
  const nome = resolveCatalogNome(next);
  if (nome) next.nome = nome;

  const rules = String(
    next.testo_gioco ||
      mseCampiGet(next.mse_campi, "rule_text", "rule text", "rules", "text", "card_text") ||
      ""
  );
  if (rules && !String(next.testo_gioco || "").trim()) next.testo_gioco = rules;

  const lore = String(
    next.testo_lore || mseCampiGet(next.mse_campi, "flavor_text", "flavor text", "lore", "flavor") || ""
  );
  if (lore && !String(next.testo_lore || "").trim()) next.testo_lore = lore;

  // Mantieni tipo/energia/rarita KOR35 validi; valori Magic restano solo in mse_campi.
  if (!isValidKor35Choice(next.tipo, KOR35_TIPI)) next.tipo = next.tipo && KOR35_TIPI.has(next.tipo) ? next.tipo : "PG";
  if (!isValidKor35Choice(next.energia, KOR35_ENERGIE)) next.energia = "MAR";
  if (!isValidKor35Choice(next.rarita, KOR35_RARITA)) next.rarita = "COM";

  return next;
}

export function readCardFieldValue(cardForm, field) {
  const k = normFieldKey(field?.name);
  const fType = String(field?.type || "").toLowerCase();

  if (NAME_KEYS.has(k)) return cardForm.nome || mseCampiGet(cardForm.mse_campi, k, "name") || "";
  if (RULES_KEYS.has(k)) {
    return cardForm.testo_gioco || mseCampiGet(cardForm.mse_campi, k, "rule_text", "rule text") || "";
  }
  if (LORE_KEYS.has(k)) {
    return cardForm.testo_lore || mseCampiGet(cardForm.mse_campi, k, "flavor_text") || "";
  }
  if (["type", "card_type"].includes(k)) {
    // Preferisci testo MSE freeform se presente (Magic), altrimenti codice KOR35.
    const fromMse = mseCampiGet(cardForm.mse_campi, k, "type");
    if (fromMse) return fromMse;
    return cardForm.tipo || "";
  }
  if (["energy", "mana", "resource"].includes(k)) {
    const fromMse = mseCampiGet(cardForm.mse_campi, k);
    if (fromMse) return fromMse;
    return cardForm.energia || "";
  }
  if (["rarity"].includes(k)) {
    const fromMse = mseCampiGet(cardForm.mse_campi, k, "rarity");
    if (fromMse) return fromMse;
    return cardForm.rarita || "";
  }
  if (["cost", "mana_cost", "casting_cost"].includes(k)) {
    if (k === "casting_cost" || k === "mana_cost") {
      return mseCampiGet(cardForm.mse_campi, "casting_cost", "casting cost", "mana_cost") || "";
    }
    return cardForm.costo_gioco ?? 0;
  }
  if (["attack", "power", "forza"].includes(k)) {
    if (fType === "text") {
      return mseCampiGet(cardForm.mse_campi, k, "power", "attack") || cardForm.attacco || "";
    }
    const fromMse = asNumberOrNull(mseCampiGet(cardForm.mse_campi, k));
    if (fromMse !== null) return fromMse;
    return cardForm.attacco ?? 0;
  }
  if (["health", "toughness", "robustezza"].includes(k)) {
    if (fType === "text") {
      return mseCampiGet(cardForm.mse_campi, k, "toughness", "health") || cardForm.salute || "";
    }
    const fromMse = asNumberOrNull(mseCampiGet(cardForm.mse_campi, k));
    if (fromMse !== null) return fromMse;
    return cardForm.salute ?? 0;
  }
  if (["pt", "power_toughness"].includes(k)) {
    return (
      mseCampiGet(cardForm.mse_campi, "pt", "power_toughness") ||
      (cardForm.attacco != null && cardForm.salute != null ? `${cardForm.attacco}/${cardForm.salute}` : "")
    );
  }
  if (["initiative", "iniziativa"].includes(k)) return cardForm.iniziativa ?? 0;
  if (["codice", "code", "card_code", "card_number"].includes(k)) {
    return cardForm.codice || mseCampiGet(cardForm.mse_campi, k) || "";
  }
  if (isImageFieldKey(k)) {
    return (
      cardForm.immagine_preview ||
      cardForm.immagine_url ||
      mseCampiGet(cardForm.mse_campi, k, "image", "art") ||
      ""
    );
  }
  return mseCampiGet(cardForm.mse_campi, k) || field?.initial || "";
}

function patchMse(cardForm, entries) {
  return {
    ...cardForm,
    mse_campi: {
      ...(cardForm.mse_campi || {}),
      ...entries,
    },
  };
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

  if (NAME_KEYS.has(k)) {
    const name = String(v ?? "");
    return patchMse({ ...cardForm, nome: name }, { [k]: name, name, nome: name });
  }
  if (RULES_KEYS.has(k)) {
    const text = String(v ?? "");
    return patchMse({ ...cardForm, testo_gioco: text }, { [k]: text, rule_text: text, "rule text": text });
  }
  if (LORE_KEYS.has(k)) {
    const text = String(v ?? "");
    return patchMse({ ...cardForm, testo_lore: text }, { [k]: text });
  }
  if (["type", "card_type"].includes(k)) {
    const s = String(v ?? "");
    const upper = s.trim().toUpperCase();
    if (isValidKor35Choice(upper, KOR35_TIPI)) {
      return patchMse({ ...cardForm, tipo: upper }, { [k]: upper, type: upper });
    }
    // Magic / freeform: non sporcare il CharField a 3 caratteri.
    return patchMse(cardForm, { [k]: s, type: s });
  }
  if (["energy", "mana", "resource"].includes(k)) {
    const s = String(v ?? "");
    const upper = s.trim().toUpperCase();
    if (isValidKor35Choice(upper, KOR35_ENERGIE)) {
      return patchMse({ ...cardForm, energia: upper }, { [k]: upper });
    }
    return patchMse(cardForm, { [k]: s });
  }
  if (["rarity"].includes(k)) {
    const s = String(v ?? "");
    const upper = s.trim().toUpperCase();
    if (isValidKor35Choice(upper, KOR35_RARITA)) {
      return patchMse({ ...cardForm, rarita: upper }, { [k]: upper, rarity: upper });
    }
    return patchMse(cardForm, { [k]: s, rarity: s });
  }
  if (["cost"].includes(k) && fType !== "text") {
    return { ...cardForm, costo_gioco: Number(v) || 0 };
  }
  if (["casting_cost", "mana_cost"].includes(k) || (k === "cost" && fType === "text")) {
    const s = String(v ?? "");
    return patchMse(cardForm, { casting_cost: s, "casting cost": s, mana_cost: s, [k]: s });
  }
  if (["attack", "power", "forza"].includes(k)) {
    if (fType === "text") {
      const s = String(v ?? "");
      const n = asNumberOrNull(s);
      const base = n !== null ? { ...cardForm, attacco: n } : cardForm;
      return patchMse(base, { [k]: s, power: s });
    }
    return { ...cardForm, attacco: Number(v) || 0 };
  }
  if (["health", "toughness", "robustezza"].includes(k)) {
    if (fType === "text") {
      const s = String(v ?? "");
      const n = asNumberOrNull(s);
      const base = n !== null ? { ...cardForm, salute: n } : cardForm;
      return patchMse(base, { [k]: s, toughness: s });
    }
    return { ...cardForm, salute: Number(v) || 0 };
  }
  if (["pt", "power_toughness"].includes(k)) {
    const s = String(v ?? "");
    const m = s.match(/^([^/]*)\/(.*)$/);
    let next = patchMse(cardForm, { pt: s, [k]: s });
    if (m) {
      const atk = asNumberOrNull(m[1]);
      const hp = asNumberOrNull(m[2]);
      if (atk !== null) next = { ...next, attacco: atk };
      if (hp !== null) next = { ...next, salute: hp };
    }
    return next;
  }
  if (["initiative", "iniziativa"].includes(k)) return { ...cardForm, iniziativa: Number(v) || 0 };
  if (["codice", "code", "card_code"].includes(k)) return { ...cardForm, codice: String(v) };
  if (isImageFieldKey(k) || fType === "image") {
    const next = patchMse(cardForm, { [k]: v, image: v });
    if (typeof v === "string" && (isTrustedBlobUrl(v) || v.startsWith("/media/") || v.startsWith("http"))) {
      next.immagine_preview = v;
    }
    return next;
  }

  return patchMse(cardForm, { [k]: v });
}
