import { describe, expect, it } from 'vitest';
import { costoInvioStimato } from './costoProposta';

const auraCerimoniale = {
  costi_stat_meta: {
    stat_costo_invio_proposta_cerimoniale: {
      nome: 'costo invio cerimoniale',
      sigla: 'CIC',
      parametro: 'invio_cer',
      valore_base_predefinito: 100,
    },
  },
};

describe('costoInvioStimato', () => {
  it('usa la statistica di scheda dell\'aura, non 100 a mattone', () => {
    const char = {
      punteggi_base: { 'costo invio cerimoniale': 2 },
      modificatori_calcolati: {},
    };
    expect(costoInvioStimato({
      tipo: 'CER',
      aura: auraCerimoniale,
      char,
      quantita: 5,
    })).toBe(10);
  });

  it('se la scheda non ha il valore, usa il catalogo della statistica', () => {
    expect(costoInvioStimato({
      tipo: 'CER',
      aura: auraCerimoniale,
      char: { punteggi_base: {}, modificatori_calcolati: {} },
      quantita: 5,
    })).toBe(500);
  });
});
