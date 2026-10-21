import { describe, expect, it } from 'vitest';
import {
  didascalieBonus,
  serializeAbilitaConferite,
  serializeBonusContestuali,
  sommaBonus,
} from './bonusContesto';

const rows = [
  {
    caratteristica_nome: 'Forza',
    valore: 1,
    vale_tessiture: true,
    vale_infusioni: false,
    vale_cerimoniali: false,
    aure: [{ id: 4, nome: 'Magica', sigla: 'AMA' }],
  },
  {
    caratteristica_nome: 'Forza',
    valore: 2,
    vale_tessiture: true,
    vale_infusioni: true,
    vale_cerimoniali: false,
    aure: [],
  },
];

describe('bonusContesto', () => {
  it('somma solo l\'ambito e le aure che combaciano', () => {
    expect(sommaBonus(rows, 'Forza', 'TES', [4])).toBe(3);
    expect(sommaBonus(rows, 'Forza', 'TES', [9])).toBe(2);
    expect(sommaBonus(rows, 'Forza', 'INF', [4])).toBe(2);
    expect(sommaBonus(rows, 'Forza', 'CER', [4])).toBe(0);
  });

  it('serializza i pk e scarta le righe vuote', () => {
    expect(serializeBonusContestuali([
      { caratteristica: { id: 7 }, valore: 0, vale_tessiture: true, aure: [{ id: 4 }] },
      { caratteristica: null, vale_infusioni: true },
    ])).toEqual([
      {
        caratteristica: 7,
        valore: 1,
        vale_tessiture: true,
        vale_infusioni: false,
        vale_cerimoniali: false,
        aure: [4],
      },
    ]);
  });

  it('deduplica le abilità conferite', () => {
    expect(serializeAbilitaConferite([
      { abilita: 3 },
      { abilita: { id: 3 } },
      { abilita: 8 },
    ])).toEqual([{ abilita: 3 }, { abilita: 8 }]);
  });

  it('raggruppa le didascalie per caratteristica', () => {
    const map = didascalieBonus(rows);
    expect(map.get('Forza')).toEqual([
      '+1 tessiture (Magica)',
      '+2 tessiture e infusioni (tutte le aure)',
    ]);
  });
});
