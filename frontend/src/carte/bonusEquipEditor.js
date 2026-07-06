/** Helper per editor staff bonus_equip (reliquiario + duello). */

export const DUEL_STAT_ROWS = [
  { key: 'forza', label: 'Forza' },
  { key: 'robustezza', label: 'Robustezza' },
  { key: 'iniziativa', label: 'Iniziativa' },
];

export const REL_SIGLE_OPTIONS = [
  { value: '', label: '— Nessuno —' },
  { value: 'FOR', label: 'FOR — Forza' },
  { value: 'RES', label: 'RES — Robustezza' },
  { value: 'INI', label: 'INI — Iniziativa' },
];

export const DUEL_STAT_OPTIONS = [
  { value: 'forza', label: 'Forza' },
  { value: 'robustezza', label: 'Robustezza' },
  { value: 'iniziativa', label: 'Iniziativa' },
];

function numOrEmpty(raw) {
  if (raw === null || raw === undefined || raw === '') return '';
  const n = Number(raw);
  return Number.isNaN(n) ? '' : n;
}

function normalizeBonusRaw(bonus) {
  if (!bonus) return {};
  if (typeof bonus === 'string') {
    try {
      return JSON.parse(bonus);
    } catch {
      return {};
    }
  }
  return typeof bonus === 'object' ? bonus : {};
}

export function parseBonusEquip(bonus) {
  const b = normalizeBonusRaw(bonus);
  return {
    relSigla: b.stat_sigla || '',
    relValore: numOrEmpty(b.valore),
    flat: {
      forza: numOrEmpty(b.forza),
      robustezza: numOrEmpty(b.robustezza),
      iniziativa: numOrEmpty(b.iniziativa),
      forza_se_leader: numOrEmpty(b.forza_se_leader),
      robustezza_se_leader: numOrEmpty(b.robustezza_se_leader),
      iniziativa_se_leader: numOrEmpty(b.iniziativa_se_leader),
    },
    extraDuello: Array.isArray(b.duello)
      ? b.duello.map((e) => ({
          stat: (e.stat || e.stat_sigla || 'forza').toLowerCase(),
          valore: numOrEmpty(e.valore),
          se_leader: !!e.se_leader,
        }))
      : [],
  };
}

function writeNum(out, key, raw) {
  if (raw === '' || raw === null || raw === undefined) return;
  const n = Number(raw);
  if (!Number.isNaN(n) && n !== 0) out[key] = n;
}

export function buildBonusEquip({ relSigla, relValore, flat, extraDuello }) {
  const out = {};
  if (relSigla) {
    out.stat_sigla = relSigla;
    const v = Number(relValore);
    if (!Number.isNaN(v)) out.valore = v;
  }
  DUEL_STAT_ROWS.forEach(({ key }) => {
    writeNum(out, key, flat[key]);
    writeNum(out, `${key}_se_leader`, flat[`${key}_se_leader`]);
  });
  const cleaned = (extraDuello || [])
    .map((row) => ({
      stat: row.stat,
      valore: Number(row.valore) || 0,
      se_leader: !!row.se_leader,
    }))
    .filter((row) => row.stat && (row.valore !== 0 || row.se_leader));
  if (cleaned.length) out.duello = cleaned;
  return out;
}

export function bonusEquipIsEmpty(bonus) {
  const b = normalizeBonusRaw(bonus);
  return Object.keys(b).length === 0;
}
