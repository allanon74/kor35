import { describe, expect, it } from 'vitest';
import { auraDelegaMattoni, etichettaMattone, paletteAuraId } from './paletteMattoni';

const tecnologica = { id: 1, nome: 'Aura Tecnologica', aure_infusione_consentite: [1] };
const innata = { id: 2, nome: 'Aura Innata', aure_infusione_consentite: [2] };
const trasmutatore = { id: 3, nome: 'Aura mondana - Trasmutatore', aure_infusione_consentite: [10, 11, 12, 13] };

describe('paletteMattoni', () => {
  it('tecnologica e innata usano i mattoni dell\'aura primaria', () => {
    expect(auraDelegaMattoni(tecnologica)).toBe(false);
    expect(auraDelegaMattoni(innata)).toBe(false);
    expect(paletteAuraId({ isInfusion: true, primaria: tecnologica, secondariaId: 11 })).toBe(1);
    expect(paletteAuraId({ isInfusion: true, primaria: innata, secondariaId: null })).toBe(2);
  });

  it('il trasmutatore usa l\'aura di infusione scelta', () => {
    expect(auraDelegaMattoni(trasmutatore)).toBe(true);
    expect(paletteAuraId({ isInfusion: true, primaria: trasmutatore, secondariaId: 11 })).toBe(11);
    expect(paletteAuraId({ isInfusion: true, primaria: trasmutatore, secondariaId: null })).toBe(null);
  });

  it('le tessiture restano sull\'aura richiesta', () => {
    expect(paletteAuraId({ isInfusion: false, primaria: trasmutatore, secondariaId: 11 })).toBe(3);
  });

  it('formato nome mattone con sigla caratteristica', () => {
    expect(etichettaMattone('Fuoco', 'DEX')).toBe('Fuoco (DEX)');
    expect(etichettaMattone('Fuoco', '')).toBe('Fuoco');
    expect(etichettaMattone('', 'DEX')).toBe('DEX');
  });
});
