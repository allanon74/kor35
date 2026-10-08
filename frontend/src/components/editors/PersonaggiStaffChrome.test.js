import { describe, expect, it } from 'vitest';
import { personaggiExtraFiltersActive } from './PersonaggiStaffChrome';

const baseFilters = { q: '', evento: '', tipo: 'all', era: '', carriera: '', morto: 'vivo', page: 1 };

describe('personaggiExtraFiltersActive', () => {
  it('è falso con i filtri di default', () => {
    expect(personaggiExtraFiltersActive(baseFilters)).toBe(false);
  });

  it('segnala il filtro «Iscritti all\'evento» attivo', () => {
    expect(personaggiExtraFiltersActive({ ...baseFilters, evento: '12' })).toBe(true);
  });

  it('ignora la sola ricerca testuale', () => {
    expect(personaggiExtraFiltersActive({ ...baseFilters, q: 'aiace' })).toBe(false);
  });
});
