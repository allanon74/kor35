/**
 * Bonus caratteristica contestuali: valgono solo per tipo tecnica e aure indicate.
 * Non modificano il punteggio globale della scheda.
 */

const FLAG_PER_TIPO = {
  TES: 'vale_tessiture',
  INF: 'vale_infusioni',
  CER: 'vale_cerimoniali',
};

const ETICHETTE_AMBITO = [
  ['vale_tessiture', 'tessiture'],
  ['vale_infusioni', 'infusioni'],
  ['vale_cerimoniali', 'cerimoniali'],
];

export function idOf(value) {
  if (value == null || value === '') return null;
  if (typeof value === 'object') return value.id ?? null;
  return value;
}

export function normalizzaBonusContestuali(rows) {
  return (rows || []).map((row) => ({
    caratteristica: idOf(row.caratteristica),
    caratteristica_nome: row.caratteristica_nome || '',
    valore: row.valore ?? 1,
    vale_tessiture: !!row.vale_tessiture,
    vale_infusioni: !!row.vale_infusioni,
    vale_cerimoniali: !!row.vale_cerimoniali,
    aure: (row.aure || []).map((aura) => idOf(aura)).filter((id) => id != null),
  }));
}

export function normalizzaAbilitaConferite(rows) {
  return (rows || []).map((row) => ({
    abilita: idOf(row.abilita),
    abilita_nome: row.abilita_nome || '',
  }));
}

export function serializeBonusContestuali(rows) {
  return (rows || [])
    .map((row) => {
      const caratteristica = idOf(row.caratteristica);
      if (!caratteristica) return null;
      return {
        caratteristica: Number(caratteristica),
        valore: Math.max(1, parseInt(row.valore, 10) || 1),
        vale_tessiture: !!row.vale_tessiture,
        vale_infusioni: !!row.vale_infusioni,
        vale_cerimoniali: !!row.vale_cerimoniali,
        aure: (row.aure || []).map((aura) => idOf(aura)).filter((id) => id != null).map(Number),
      };
    })
    .filter(Boolean);
}

export function serializeAbilitaConferite(rows) {
  const seen = new Set();
  const out = [];
  (rows || []).forEach((row) => {
    const abilita = idOf(row.abilita);
    if (!abilita || seen.has(String(abilita))) return;
    seen.add(String(abilita));
    out.push({ abilita: Number(abilita) });
  });
  return out;
}

export function bonusContestualiCompleti(rows) {
  return (rows || []).every((row) => {
    if (!idOf(row.caratteristica)) return true;
    return !!(row.vale_tessiture || row.vale_infusioni || row.vale_cerimoniali);
  });
}

export function sommaBonus(rows, nome, tipo, auraIds) {
  const flag = FLAG_PER_TIPO[tipo];
  if (!flag || !nome) return 0;
  const ids = (auraIds || []).map((id) => String(id)).filter((id) => id && id !== 'null' && id !== 'undefined');
  let totale = 0;
  (rows || []).forEach((row) => {
    if (row.caratteristica_nome !== nome || !row[flag]) return;
    const aure = row.aure || [];
    if (aure.length === 0 || aure.some((aura) => ids.includes(String(idOf(aura) ?? aura)))) {
      totale += Number(row.valore) || 0;
    }
  });
  return totale;
}

export function etichettaBonus(row) {
  const ambiti = ETICHETTE_AMBITO.filter(([flag]) => row[flag]).map(([, label]) => label);
  const aure = (row.aure || []).map((aura) => aura.nome || aura.sigla).filter(Boolean);
  const auraTxt = aure.length ? aure.join(', ') : 'tutte le aure';
  const valore = Number(row.valore) || 0;
  return `+${valore} ${ambiti.join(' e ')} (${auraTxt})`;
}

export function didascalieBonus(rows) {
  const map = new Map();
  (rows || []).forEach((row) => {
    const nome = row.caratteristica_nome;
    if (!nome) return;
    const list = map.get(nome) || [];
    list.push(etichettaBonus(row));
    map.set(nome, list);
  });
  return map;
}
