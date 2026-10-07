import { describe, expect, it } from 'vitest';
import { NEGOZIO_COLUMNS } from './negozioMercanteColumns';

describe('colonne elenco negozi su mobile', () => {
  it('tiene nome e stato in evidenza e i numeri come chip', () => {
    const byKey = Object.fromEntries(NEGOZIO_COLUMNS.map((col) => [col.key, col]));
    expect(byKey.nome.mobileRole).toBe('title');
    expect(byKey.tipo_negozio.mobileRole).toBe('badge');
    expect(byKey.attivo.mobileRole).toBe('badge');
    expect(byKey.negozio_prestiti.mobileRole).toBe('meta');
    expect(byKey.saldo_crediti.mobileRole).toBe('meta');
    expect(byKey.voci_count.mobileRole).toBe('meta');
    expect(byKey.qr_code.mobileRole).toBe('meta');
  });
});