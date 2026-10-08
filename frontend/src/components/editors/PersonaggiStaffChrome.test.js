/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import {
  PERSONAGGI_STAFF_TABS,
  PersonaggiStaffTabStrip,
  personaggiExtraFiltersActive,
} from './PersonaggiStaffChrome';
import { buildPersonaggioListColumns } from './personaggioListColumns';
import { columnMobileRole } from '../../staff/staffTableModel';

function mount(element) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(element);
  });
  return {
    host,
    unmount() {
      act(() => root.unmount());
      host.remove();
    },
  };
}

describe('PersonaggiStaffChrome', () => {
  afterEach(() => {
    document.body.querySelectorAll('[data-testid="personaggi-staff-tabs"]').forEach((el) => el.remove());
  });

  it('include il tab tecniche possedute', () => {
    const tab = PERSONAGGI_STAFF_TABS.find((t) => t.id === 'tecniche');
    expect(tab).toBeTruthy();
    expect(tab.label).toBe('Tecniche');
    expect(tab.short.length).toBeLessThanOrEqual(8);
  });

  it('ogni tab ha etichetta corta per il telefono', () => {
    expect(PERSONAGGI_STAFF_TABS.length).toBeGreaterThanOrEqual(12);
    PERSONAGGI_STAFF_TABS.forEach((tab) => {
      expect(tab.short).toBeTruthy();
      expect(tab.short.length).toBeLessThanOrEqual(8);
    });
  });

  it('le tab sono tap-friendly e scorrono in orizzontale', () => {
    const { host, unmount } = mount(
      createElement(PersonaggiStaffTabStrip, { active: 'bg', onChange: () => {} }),
    );
    const strip = host.querySelector('[data-testid="personaggi-staff-tabs"]');
    expect(strip).toBeTruthy();
    expect(strip.className).toContain('overflow-x-auto');
    const buttons = strip.querySelectorAll('button');
    expect(buttons.length).toBe(PERSONAGGI_STAFF_TABS.length);
    buttons.forEach((btn) => {
      expect(btn.className).toContain('min-h-11');
      expect(btn.className).toContain('shrink-0');
    });
    unmount();
  });

  it('personaggiExtraFiltersActive ignora i default', () => {
    expect(personaggiExtraFiltersActive({ tipo: 'all', era: '', carriera: '', morto: 'vivo' })).toBe(false);
    expect(personaggiExtraFiltersActive({ tipo: 'pg', era: '', carriera: '', morto: 'vivo' })).toBe(true);
    expect(personaggiExtraFiltersActive({ tipo: 'all', era: '3', carriera: '', morto: 'vivo' })).toBe(true);
    expect(personaggiExtraFiltersActive({ tipo: 'all', era: '', carriera: '', morto: 'morto' })).toBe(true);
  });

  it('personaggiExtraFiltersActive segnala il filtro iscritti all evento', () => {
    const base = { q: '', evento: '', tipo: 'all', era: '', carriera: '', morto: 'vivo' };
    expect(personaggiExtraFiltersActive(base)).toBe(false);
    expect(personaggiExtraFiltersActive({ ...base, evento: '12' })).toBe(true);
    expect(personaggiExtraFiltersActive({ ...base, q: 'aiace' })).toBe(false);
  });
});

describe('colonne elenco Personaggi su mobile', () => {
  it('compatta la card: titolo, sottotitolo e chip, nasconde i campi secondari', () => {
    const byKey = Object.fromEntries(buildPersonaggioListColumns().map((col) => [col.key, col]));
    expect(byKey.nome.mobileRole).toBe('title');
    expect(byKey.tipo.mobileRole).toBe('badge');
    expect(byKey.proprietario.mobileRole).toBe('subtitle');
    expect(byKey.era.mobileRole).toBe('subtitle');
    expect(byKey.korp.mobileRole).toBe('meta');
    expect(byKey.korp.mobileHeader).toBe('KORP');
    expect(byKey.corrente.mobileRole).toBe('meta');
    expect(byKey.prestigio.mobileRole).toBe('meta');
    expect(byKey.qr.mobileRole).toBe('hidden');
    expect(byKey.deposito.mobileRole).toBe('hidden');
    expect(byKey.allineamento.mobileRole).toBe('hidden');
    expect(columnMobileRole(byKey.nome)).toBe('title');
    expect(columnMobileRole(byKey.corrente)).toBe('meta');
  });
});
