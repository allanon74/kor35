import { cardFieldValue, normFieldKey } from "./fieldUtils";
import { evalMseProp, evalMseScript } from "./scriptEngine";

function buildCardContextFromRow(row, gameCardFields) {
  const card = {
    codice: row?.codice || "",
    nome: row?.nome || "",
    rarity: row?.rarita || "",
    rarita: row?.rarita || "",
    type: row?.tipo || "",
    tipo: row?.tipo || "",
    energy: row?.energia || "",
    energia: row?.energia || "",
  };
  (gameCardFields || []).forEach((field) => {
    const val = cardFieldValue(row, field);
    card[field.name] = val;
    card[normFieldKey(field.name)] = val;
  });
  return card;
}

function evalAmount(amountProp, ctx, fallback = 1) {
  const n = Number(evalMseProp(amountProp, ctx, fallback));
  return Number.isFinite(n) && n > 0 ? Math.floor(n) : fallback;
}

function cardPassesFilter(row, filterProp, gameCardFields) {
  if (!filterProp) return true;
  const card = buildCardContextFromRow(row, gameCardFields);
  return Boolean(evalMseProp(filterProp, { card, styling: {}, set: {} }, true));
}

function pickRandom(pool, rng = Math.random) {
  if (!pool.length) return null;
  return pool[Math.floor(rng() * pool.length)];
}

function pickMany(pool, count, select, rng = Math.random) {
  if (!pool.length || count <= 0) return [];
  const mode = String(select || "no replace").toLowerCase().replace(/_/g, " ");
  if (mode === "replace") {
    return Array.from({ length: count }, () => pickRandom(pool, rng)).filter(Boolean);
  }
  if (mode === "no replace") {
    const shuffled = [...pool].sort(() => rng() - 0.5);
    return shuffled.slice(0, Math.min(count, shuffled.length));
  }
  if (mode === "first") {
    return [pool[0]];
  }
  const shuffled = [...pool].sort(() => rng() - 0.5);
  return shuffled.slice(0, Math.min(count, shuffled.length));
}

export function buildPackRegistry(gameSpec) {
  const items = {};
  (gameSpec?.pack_items || []).forEach((item) => {
    if (item?.name) items[item.name] = item;
  });
  (gameSpec?.pack_types || []).forEach((pack) => {
    (pack.items || []).forEach((item) => {
      if (item?.name && item.filter) items[item.name] = item;
    });
  });
  return items;
}

export function resolveItemPool(itemRef, registry, cards, gameCardFields) {
  const name = itemRef?.name;
  if (!name) return [];
  const def = registry[name] || itemRef;
  const filter = def.filter || itemRef.filter;
  const select = def.select || itemRef.select || "no replace";
  let pool = cards.filter((c) => cardPassesFilter(c, filter, gameCardFields));
  if (!pool.length && itemRef !== def && def.filter) {
    pool = cards.filter((c) => cardPassesFilter(c, def.filter, gameCardFields));
  }
  return { pool, select, name };
}

export function simulatePackInstance(packType, registry, cards, gameCardFields, rng = Math.random) {
  const select = String(packType?.select || "all").toLowerCase().replace(/_/g, " ");
  const result = [];

  if (select === "first") {
    for (const itemRef of packType.items || []) {
      const { pool, select: itemSelect } = resolveItemPool(itemRef, registry, cards, gameCardFields);
      if (pool.length) {
        const ctx = { card: {}, styling: {}, set: {} };
        const amount = evalAmount(itemRef.amount, ctx, 1);
        result.push(...pickMany(pool, amount, itemSelect, rng));
        break;
      }
    }
    return result;
  }

  if (select === "replace" || select === "no replace" || select === "proportional" || select === "nonempty") {
    const filter = packType.filter;
    const pool = cards.filter((c) => cardPassesFilter(c, filter, gameCardFields));
    return pickMany(pool, 1, select, rng);
  }

  if (packType.filter && (!packType.items || packType.items.length === 0)) {
    const pool = cards.filter((c) => cardPassesFilter(c, packType.filter, gameCardFields));
    return [...pool];
  }

  for (const itemRef of packType.items || []) {
    const { pool, select: itemSelect, name } = resolveItemPool(itemRef, registry, cards, gameCardFields);
    if (!pool.length) continue;
    const ctx = { card: {}, styling: {}, set: {} };
    const amount = evalAmount(itemRef.amount, ctx, 1);
    const picked = pickMany(pool, amount, itemSelect || "no replace", rng);
    picked.forEach((card) => {
      result.push({ ...card, _pack_from: name });
    });
  }

  return result;
}

export function simulateRandomPacks({
  packType,
  registry,
  cards,
  gameCardFields,
  copies = 1,
  rng = Math.random,
}) {
  const packs = [];
  let total = 0;
  for (let i = 0; i < copies; i += 1) {
    const cardsInPack = simulatePackInstance(packType, registry, cards, gameCardFields, rng);
    packs.push(cardsInPack);
    total += cardsInPack.length;
  }
  return { packs, total, flat: packs.flat() };
}

export function summarizePackTypes(gameSpec, registry, cards, gameCardFields, copies = 1) {
  return (gameSpec?.pack_types || [])
    .filter((p) => p.summary !== false)
    .map((packType) => {
      const sim = simulateRandomPacks({
        packType,
        registry,
        cards,
        gameCardFields,
        copies,
      });
      return {
        name: packType.name,
        count: sim.total,
        enabled: packType.enabled !== false,
      };
    })
    .filter((row) => row.enabled);
}

export function selectablePackTypes(gameSpec) {
  return (gameSpec?.pack_types || []).filter(
    (p) => p.selectable !== false && p.enabled !== false && p.name
  );
}
