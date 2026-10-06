import { describe, expect, it } from 'vitest';
import { dettaglioRicarica, findOggettoInInventario, patchCaricheInOggetti } from './ricaricaOggetto';

describe('dettaglioRicarica', () => {
  it('moltiplica il costo unitario per le cariche mancanti', () => {
    const scan = dettaglioRicarica({ cariche_attuali: 8, cariche_massime: 10, costo_ricarica: 3 });
    expect(scan).toEqual({ mancanti: 2, unitario: 3, totale: 6 });

    const traslazione = dettaglioRicarica({ cariche_attuali: 3, cariche_massime: 10, costo_ricarica: 20 });
    expect(traslazione).toEqual({ mancanti: 7, unitario: 20, totale: 140 });
  });
});

describe('patchCaricheInOggetti', () => {
  it('aggiorna una mod montata, non solo gli oggetti in radice', () => {
    const oggetti = [
      {
        id: 1885,
        nome: 'Pistola',
        potenziamenti_installati: [{ id: 1884, cariche_attuali: 3, cariche_massime: 10 }],
      },
    ];
    const next = patchCaricheInOggetti(oggetti, 1884, (mod) => ({
      ...mod,
      cariche_attuali: mod.cariche_massime,
    }));
    expect(findOggettoInInventario(next, 1884).cariche_attuali).toBe(10);
    expect(next[0].cariche_attuali).toBeUndefined();
  });
});
