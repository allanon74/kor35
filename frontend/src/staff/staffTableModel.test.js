import { describe, expect, it } from 'vitest';
import { columnMobileRole } from './staffTableModel';

describe('columnMobileRole', () => {
  it('rispetta mobileRole esplicito', () => {
    expect(columnMobileRole({ header: 'X', mobileRole: 'hidden' })).toBe('hidden');
    expect(columnMobileRole({ header: 'Nome', mobileRole: 'title' }, { titleAssigned: true })).toBe('title');
  });

  it('tratta colonne strette centrate come badge', () => {
    expect(columnMobileRole({ header: 'QR', align: 'center', width: '44px' })).toBe('badge');
    expect(columnMobileRole({ header: 'Lvl', align: 'center', width: '60px' })).toBe('badge');
  });

  it('non tratta width percentuali come badge', () => {
    expect(columnMobileRole({ header: 'Costo PC', align: 'center', width: '15%' })).toBe('detail');
  });

  it('usa la prima colonna testuale come titolo', () => {
    expect(columnMobileRole({ header: 'Nome' })).toBe('title');
    expect(columnMobileRole({ header: 'Mattoni' }, { titleAssigned: true })).toBe('detail');
  });
});
