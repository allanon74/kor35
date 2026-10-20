import { describe, expect, it } from 'vitest';
import {
  isAumentoCorporeo,
  mappaSlotOccupati,
  slotLiberoSelezionabile,
} from './slotCorpoStaff';

describe('slot corporei staff', () => {
  it('segna occupato solo uno slot equipaggiato', () => {
    const occupati = mappaSlotOccupati([
      { id: 1, nome: 'Pelle', slot_corpo: 'HD1', is_equipaggiato: true },
      { id: 2, nome: 'Sciolta', slot_corpo: 'TR1', is_equipaggiato: false },
      { id: 3, nome: 'Spada', tipo_oggetto: 'FIS' },
    ]);
    expect(occupati).toEqual({ HD1: 'Pelle' });
    expect(slotLiberoSelezionabile('HD1', { occupati, permessi: ['HD1', 'TR1'] })).toBe(false);
    expect(slotLiberoSelezionabile('TR1', { occupati, permessi: ['HD1', 'TR1'] })).toBe(true);
    expect(slotLiberoSelezionabile('HD2', { occupati, permessi: ['HD1', 'TR1'] })).toBe(false);
    expect(slotLiberoSelezionabile('RA', { occupati, permessi: [] })).toBe(true);
  });

  it('distingue aumento corporeo da materia/mod', () => {
    expect(isAumentoCorporeo({ tipo_risultato: 'AUM' })).toBe(true);
    expect(isAumentoCorporeo({ tipo_risultato: 'POT' })).toBe(false);
  });
});
