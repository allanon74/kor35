/**
 * Raggruppamento, filtri e ordinamento collezione carte possedute.
 */

const RARITA_RANK = {
  COM: 1,
  NC: 2,
  RAR: 3,
  EPI: 4,
  LEG: 5,
  UNI: 6,
};

const norm = (v) => String(v || '').toLowerCase().trim();

/**
 * Raggruppa istanze CartaPosseduta per definizione catalogo (carta.id).
 * @returns {Array<{ key, carta, copies, count, representative, inReliquarioCount, latestOttenutaAt }>}
 */
export function groupCollezioneStacks(carte = []) {
  const map = new Map();
  for (const item of carte) {
    const carta = item?.carta;
    if (!carta?.id) continue;
    const key = String(carta.id);
    let stack = map.get(key);
    if (!stack) {
      stack = {
        key,
        carta,
        copies: [],
        count: 0,
        representative: item,
        inReliquarioCount: 0,
        latestOttenutaAt: item.ottenuta_at || '',
      };
      map.set(key, stack);
    }
    stack.copies.push(item);
    stack.count += 1;
    if (item.in_reliquiario) stack.inReliquarioCount += 1;
    const ts = item.ottenuta_at || '';
    if (ts > stack.latestOttenutaAt) {
      stack.latestOttenutaAt = ts;
      stack.representative = item;
    }
  }
  return Array.from(map.values());
}

export function filterCollezioneStacks(stacks, filters = {}) {
  const {
    search = '',
    tipo = '',
    energia = '',
    rarita = '',
    espansioneId = '',
    soloNonEquip = false,
  } = filters;
  const q = norm(search);

  return stacks.filter((stack) => {
    const c = stack.carta;
    if (tipo && c.tipo !== tipo) return false;
    if (energia && c.energia !== energia) return false;
    if (rarita && c.rarita !== rarita) return false;
    if (espansioneId && String(c.espansione_id || '') !== String(espansioneId)) return false;
    if (soloNonEquip && stack.inReliquarioCount >= stack.count) return false;
    if (!q) return true;
    const hay = [
      c.nome, c.codice, c.espansione_nome, c.set_collezione,
      ...(c.tag_tematici || []),
      ...((c.tags || []).map((t) => (typeof t === 'string' ? t : t.nome || t.codice))),
    ]
      .filter(Boolean)
      .join(' ')
      .toLowerCase();
    return hay.includes(q);
  });
}

export function sortCollezioneStacks(stacks, sortKey = 'nome_asc') {
  const list = [...stacks];
  const byNome = (a, b) => norm(a.carta.nome).localeCompare(norm(b.carta.nome), 'it');
  const byRarita = (a, b) => (RARITA_RANK[a.carta.rarita] || 0) - (RARITA_RANK[b.carta.rarita] || 0);
  const byTipo = (a, b) => norm(a.carta.tipo).localeCompare(norm(b.carta.tipo));
  const byEnergia = (a, b) => norm(a.carta.energia).localeCompare(norm(b.carta.energia));
  const byCosto = (a, b) => (a.carta.costo_gioco ?? 0) - (b.carta.costo_gioco ?? 0);
  const byRecente = (a, b) => String(b.latestOttenutaAt).localeCompare(String(a.latestOttenutaAt));
  const byCopie = (a, b) => b.count - a.count;
  const byOrdineSet = (a, b) => (a.carta.ordine_set ?? 0) - (b.carta.ordine_set ?? 0) || byNome(a, b);

  switch (sortKey) {
    case 'nome_desc':
      list.sort((a, b) => -byNome(a, b));
      break;
    case 'rarita_desc':
      list.sort((a, b) => -byRarita(a, b) || byNome(a, b));
      break;
    case 'rarita_asc':
      list.sort((a, b) => byRarita(a, b) || byNome(a, b));
      break;
    case 'tipo':
      list.sort((a, b) => byTipo(a, b) || byNome(a, b));
      break;
    case 'energia':
      list.sort((a, b) => byEnergia(a, b) || byNome(a, b));
      break;
    case 'costo_desc':
      list.sort((a, b) => -byCosto(a, b) || byNome(a, b));
      break;
    case 'costo_asc':
      list.sort((a, b) => byCosto(a, b) || byNome(a, b));
      break;
    case 'recente':
      list.sort((a, b) => byRecente(a, b) || byNome(a, b));
      break;
    case 'copie_desc':
      list.sort((a, b) => byCopie(a, b) || byNome(a, b));
      break;
    case 'ordine_set':
      list.sort((a, b) => byOrdineSet(a, b));
      break;
    case 'nome_asc':
    default:
      list.sort((a, b) => byNome(a, b));
      break;
  }
  return list;
}

export function buildCollezioneView(carte, filters, sortKey) {
  const stacks = groupCollezioneStacks(carte);
  const filtered = filterCollezioneStacks(stacks, filters);
  const sorted = sortCollezioneStacks(filtered, sortKey);
  const totalCopie = carte.length;
  const uniqueCount = stacks.length;
  return { stacks: sorted, totalCopie, uniqueCount, filteredCount: sorted.length };
}

export const COLLEZIONE_SORT_OPTIONS = [
  { value: 'nome_asc', label: 'Nome A→Z' },
  { value: 'nome_desc', label: 'Nome Z→A' },
  { value: 'rarita_desc', label: 'Rarità (alta prima)' },
  { value: 'rarita_asc', label: 'Rarità (bassa prima)' },
  { value: 'tipo', label: 'Tipo' },
  { value: 'energia', label: 'Energia' },
  { value: 'costo_desc', label: 'Costo gioco ↓' },
  { value: 'costo_asc', label: 'Costo gioco ↑' },
  { value: 'recente', label: 'Più recenti' },
  { value: 'copie_desc', label: 'Più copie' },
  { value: 'ordine_set', label: 'Ordine set' },
];
