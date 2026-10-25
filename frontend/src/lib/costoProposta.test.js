import { describe, expect, it } from 'vitest';
import { costoInvioStimato, dettaglioCostoInvio, messaggioConfermaInvio } from './costoProposta';

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

  it('legge la scheda anche da statistiche_base_dict e scala solo il delta già versato', () => {
    const dettaglio = dettaglioCostoInvio({
      tipo: 'CER',
      aura: auraCerimoniale,
      char: { statistiche_base_dict: { invio_cer: 2 }, modificatori_calcolati: {} },
      quantita: 5,
      giaPagato: 4,
    });
    expect(dettaglio.totale).toBe(10);
    expect(dettaglio.daAddebitare).toBe(6);
    expect(messaggioConfermaInvio(dettaglio)).toContain('all\'invio 6 CR');
    expect(messaggioConfermaInvio(dettaglio)).not.toContain('500');
  });
});
