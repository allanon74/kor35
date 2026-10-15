import { describe, expect, it } from 'vitest';
import { plotConcluso, plotPredefinito, primoPlotNonConcluso } from './plotSelezione';

const now = new Date('2026-10-15T12:00:00Z');

const plot = (over) => ({
  id: 1,
  titolo: 'Plot',
  data_inizio: '2026-10-01T00:00:00Z',
  data_fine: '2026-10-02T00:00:00Z',
  ...over,
});

describe('plotPredefinito', () => {
  it('apre il primo plot non concluso, saltando i conclusi più vecchi', () => {
    const eventi = [
      plot({ id: 1, titolo: 'Vecchio', data_inizio: '2026-05-01T00:00:00Z', data_fine: '2026-05-03T00:00:00Z' }),
      plot({ id: 2, titolo: 'In corso', data_inizio: '2026-10-14T00:00:00Z', data_fine: '2026-10-16T00:00:00Z' }),
      plot({ id: 3, titolo: 'Futuro', data_inizio: '2026-11-01T00:00:00Z', data_fine: '2026-11-03T00:00:00Z' }),
    ];
    expect(primoPlotNonConcluso(eventi, now)?.id).toBe(2);
    expect(plotPredefinito(eventi, now)?.id).toBe(2);
  });

  it('non apre un plot archiviato e ignora un concluso con data futura già terminato', () => {
    const eventi = [
      plot({
        id: 9,
        titolo: 'Archivio',
        data_inizio: '2026-01-01T00:00:00Z',
        data_fine: '2026-12-01T00:00:00Z',
        archiviato_at: '2026-09-01T00:00:00Z',
      }),
      plot({
        id: 4,
        titolo: 'Terminato in anticipo',
        data_inizio: '2026-10-20T00:00:00Z',
        data_fine: '2026-10-22T00:00:00Z',
        ended_at: '2026-10-10T00:00:00Z',
      }),
      plot({ id: 5, titolo: 'Prossimo', data_inizio: '2026-10-20T08:00:00Z', data_fine: '2026-10-22T00:00:00Z' }),
    ];
    expect(plotConcluso(eventi[1], now)).toBe(true);
    expect(plotPredefinito(eventi, now)?.id).toBe(5);
  });

  it('tiene aperto un evento avviato anche se la data di fine è passata', () => {
    const eventi = [
      plot({
        id: 7,
        titolo: 'Live',
        data_inizio: '2026-10-01T00:00:00Z',
        data_fine: '2026-10-02T00:00:00Z',
        started_at: '2026-10-01T10:00:00Z',
      }),
      plot({ id: 8, titolo: 'Dopo', data_inizio: '2026-11-01T00:00:00Z', data_fine: '2026-11-02T00:00:00Z' }),
    ];
    expect(plotConcluso(eventi[0], now)).toBe(false);
    expect(plotPredefinito(eventi, now)?.id).toBe(7);
  });

  it('se tutti i plot attivi sono conclusi apre il primo non archiviato', () => {
    const eventi = [
      plot({ id: 1, titolo: 'A', data_inizio: '2026-01-02T00:00:00Z' }),
      plot({ id: 2, titolo: 'B', data_inizio: '2026-03-02T00:00:00Z' }),
    ];
    expect(primoPlotNonConcluso(eventi, now)).toBeNull();
    expect(plotPredefinito(eventi, now)?.id).toBe(1);
  });
});
