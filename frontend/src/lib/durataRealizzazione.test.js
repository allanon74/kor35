import { describe, expect, it } from 'vitest';
import { formatDurataRealizzazione } from './durataRealizzazione';

describe('formatDurataRealizzazione', () => {
  it('formatta secondi, minuti e ore', () => {
    expect(formatDurataRealizzazione(0)).toBe('0 s');
    expect(formatDurataRealizzazione(45)).toBe('45 s');
    expect(formatDurataRealizzazione(60)).toBe('1 min');
    expect(formatDurataRealizzazione(90)).toBe('1 min 30 s');
    expect(formatDurataRealizzazione(3600)).toBe('1 h');
    expect(formatDurataRealizzazione(5400)).toBe('1 h 30 min');
    expect(formatDurataRealizzazione(3661)).toBe('1 h 1 min 1 s');
  });
});
