/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import StaffDataTable from './StaffDataTable';

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

const columns = [
  {
    key: 'nome',
    header: 'Nome',
    mobileRole: 'title',
    render: (row) => row.nome,
  },
  {
    key: 'tipo',
    header: 'Tipo',
    mobileRole: 'badge',
    render: (row) => row.tipo,
  },
  {
    key: 'proprietario',
    header: 'Proprietario',
    mobileRole: 'subtitle',
    render: (row) => row.proprietario,
  },
  {
    key: 'era',
    header: 'Era',
    mobileRole: 'subtitle',
    render: (row) => row.era,
  },
  {
    key: 'cassa',
    header: 'Cassa',
    mobileHeader: 'CR',
    mobileRole: 'meta',
    render: (row) => `${row.cassa} CR`,
  },
  {
    key: 'note',
    header: 'Note',
    mobileRole: 'detail',
    render: (row) => row.note,
  },
];

const items = [
  { id: 1, nome: 'Bottega', tipo: 'QR', proprietario: 'Ada', era: 'Vittoriana', cassa: 12, note: 'Aperta' },
];

describe('StaffDataTable mobile', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('compatta titolo, sottotitolo e chip e tiene Ordina chiuso', () => {
    const { host, unmount } = mount(
      createElement(StaffDataTable, {
        columns,
        items,
        onCycleSort: () => {},
        onRowClick: () => {},
      }),
    );

    const cards = host.querySelector('[data-testid="staff-mobile-cards"]');
    expect(cards).toBeTruthy();
    expect(cards.textContent).toContain('Bottega');
    expect(host.querySelector('[data-testid="staff-mobile-subtitle"]').textContent).toContain('Ada');
    expect(host.querySelector('[data-testid="staff-mobile-subtitle"]').textContent).toContain('Vittoriana');
    const meta = host.querySelector('[data-testid="staff-mobile-meta"]');
    expect(meta.textContent).toContain('CR');
    expect(meta.textContent).toContain('12 CR');
    expect(host.querySelector('[data-testid="staff-mobile-detail"]').textContent).toContain('Note');
    expect(host.querySelector('[data-testid="staff-mobile-detail"]').textContent).toContain('Aperta');
    expect(host.querySelector('[data-testid="staff-mobile-sort-chips"]')).toBeNull();
    expect(host.querySelector('[data-testid="staff-mobile-sort-toggle"]').getAttribute('aria-expanded')).toBe('false');
    unmount();
  });

  it('apre i chip di ordinamento al tap su Ordina', () => {
    const onCycleSort = vi.fn();
    const { host, unmount } = mount(
      createElement(StaffDataTable, {
        columns,
        items,
        sorts: [{ key: 'nome', dir: 'asc' }],
        onCycleSort,
      }),
    );

    const toggle = host.querySelector('[data-testid="staff-mobile-sort-toggle"]');
    expect(toggle.textContent).toContain('Nome');
    act(() => {
      toggle.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    const chips = host.querySelector('[data-testid="staff-mobile-sort-chips"]');
    expect(chips).toBeTruthy();
    const nomeChip = [...chips.querySelectorAll('button')].find((btn) => btn.textContent.includes('Nome'));
    act(() => {
      nomeChip.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(onCycleSort).toHaveBeenCalledWith('nome');
    unmount();
  });
});
