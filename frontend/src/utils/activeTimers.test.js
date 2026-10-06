import { describe, expect, it } from 'vitest';
import { mergeActiveTimers, nextTimerCorner, normalizeTimerRow, timerStateKey } from './activeTimers';

describe('activeTimers', () => {
  it('distingue due istanze con lo stesso nome', () => {
    const a = normalizeTimerRow({
      id: 'innesco:1',
      nome: 'Allarme',
      data_fine: '2026-10-06T22:00:00.000Z',
    });
    const b = normalizeTimerRow({
      id: 'innesco:2',
      nome: 'Allarme',
      data_fine: '2026-10-06T22:05:00.000Z',
    });
    expect(timerStateKey(a)).toBe('innesco:1');
    expect(timerStateKey(b)).toBe('innesco:2');
    expect(a.endTime).not.toBe(b.endTime);
  });

  it('toglie gli innesco assenti dal payload e tiene i timer legacy', () => {
    const prev = {
      'innesco:1': { id: 'innesco:1', nome: 'A', endTime: 10 },
      'innesco:9': { id: 'innesco:9', nome: 'Vecchio', endTime: 10 },
      Protezione: { nome: 'Protezione', endTime: 99 },
    };
    const next = mergeActiveTimers(prev, [
      { id: 'innesco:1', nome: 'A', data_fine: '2026-10-06T22:00:00.000Z', scaduto: true },
    ]);
    expect(next['innesco:1'].scaduto).toBe(true);
    expect(next['innesco:9']).toBeUndefined();
    expect(next.Protezione.nome).toBe('Protezione');
  });

  it('ruota i quattro angoli', () => {
    expect(nextTimerCorner('tr')).toBe('br');
    expect(nextTimerCorner('br')).toBe('bl');
    expect(nextTimerCorner('bl')).toBe('tl');
    expect(nextTimerCorner('tl')).toBe('tr');
    expect(nextTimerCorner('nope')).toBe('br');
  });
});
