import { describe, expect, it } from 'vitest';
import {
  caratteristichePersonaggio,
  isCaratteristicaPersonaggio,
  isColoreComponenteNave,
} from './caratteristicheScheda';

describe('caratteristicheScheda', () => {
  it('accetta le 10 caratteristiche PG', () => {
    expect(isCaratteristicaPersonaggio({ tipo: 'CA', sigla: 'For', nome: 'Forza' })).toBe(true);
    expect(isCaratteristicaPersonaggio({ tipo: 'CA', sigla: 'Rob', nome: 'Robustezza' })).toBe(true);
  });

  it('esclude i colori componenti nave 0C0–0C9', () => {
    expect(isColoreComponenteNave({ sigla: '0C2', nome: 'Rosso' })).toBe(true);
    expect(isCaratteristicaPersonaggio({ tipo: 'CA', sigla: '0C2', nome: 'Rosso' })).toBe(false);
    expect(isCaratteristicaPersonaggio({ tipo: 'CA', sigla: '0C0', nome: 'Nero' })).toBe(false);
  });

  it('esclude Condizioni (Tier 2) e altri tipi', () => {
    expect(isCaratteristicaPersonaggio({ tipo: 'CO', sigla: 'FO1', nome: 'Tier 2 - Forza' })).toBe(false);
    expect(isCaratteristicaPersonaggio({ tipo: 'ST', sigla: 'P01', nome: 'Uso Specchio Anima' })).toBe(false);
  });

  it('filtra una lista mista', () => {
    const out = caratteristichePersonaggio([
      { tipo: 'CA', sigla: 'For', nome: 'Forza' },
      { tipo: 'CA', sigla: '0C2', nome: 'Rosso' },
      { tipo: 'CO', sigla: 'TI1', nome: 'Tier 2' },
      { tipo: 'CA', sigla: 'Dex', nome: 'Destrezza' },
    ]);
    expect(out.map((p) => p.sigla)).toEqual(['For', 'Dex']);
  });
});
