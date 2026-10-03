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
});

describe('colonne elenco Personaggi su mobile', () => {
  it('nasconde QR/deposito/allineamento e tiene nome come titolo', () => {
    expect(columnMobileRole({ header: 'Nome', mobileRole: 'title' })).toBe('title');
    expect(columnMobileRole({ header: 'Tipo', mobileRole: 'badge' })).toBe('badge');
    expect(columnMobileRole({ header: 'QR', mobileRole: 'hidden' })).toBe('hidden');
    expect(columnMobileRole({ header: 'Deposito', mobileRole: 'hidden' })).toBe('hidden');
    expect(columnMobileRole({ header: 'L/O/G', mobileRole: 'hidden' })).toBe('hidden');
    expect(columnMobileRole({ header: 'Corrente', mobileRole: 'detail' })).toBe('detail');
  });
});
