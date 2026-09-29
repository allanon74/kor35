/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import SearchableSelect from './SearchableSelect';

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

describe('SearchableSelect dropdown positioning', () => {
  afterEach(() => {
    document.body.querySelectorAll('[id^="dropdown-searchable-"]').forEach((el) => el.remove());
  });

  it('posiziona il menu in coordinate viewport (fixed) senza scrollY', async () => {
    Object.defineProperty(window, 'scrollY', { configurable: true, value: 800 });
    Object.defineProperty(window, 'scrollX', { configurable: true, value: 40 });
    Object.defineProperty(window, 'innerHeight', { configurable: true, value: 700 });
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 390 });

    const options = Array.from({ length: 15 }, (_, i) => ({
      id: i + 1,
      nome: `Opzione ${i + 1}`,
    }));

    const { host, unmount } = mount(
      createElement(SearchableSelect, {
        options,
        value: '',
        onChange: vi.fn(),
        placeholder: 'Seleziona',
        minOptionsForSearch: 1,
      }),
    );

    const trigger = host.querySelector('[class*="cursor-pointer"]');
    expect(trigger).toBeTruthy();

    // Simula trigger a metà viewport (form scrollata su telefono)
    trigger.getBoundingClientRect = () => ({
      top: 300,
      bottom: 344,
      left: 16,
      right: 374,
      width: 358,
      height: 44,
      x: 16,
      y: 300,
      toJSON() {
        return {};
      },
    });

    await act(async () => {
      trigger.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const portal = document.body.querySelector('[id^="dropdown-searchable-"]');
    expect(portal).toBeTruthy();
    expect(portal.className).toContain('fixed');
    // Nessun offset document: top ≈ 344+4, non 344+800
    expect(portal.style.top).toBe('348px');
    expect(portal.style.left).toBe('16px');
    expect(Number.parseFloat(portal.style.top)).toBeLessThan(700);

    unmount();
  });

  it('con liste corte usa select nativo (UX telefono)', () => {
    const { host, unmount } = mount(
      createElement(SearchableSelect, {
        options: [
          { id: 1, nome: 'A' },
          { id: 2, nome: 'B' },
        ],
        value: '',
        onChange: vi.fn(),
      }),
    );
    expect(host.querySelector('select')).toBeTruthy();
    unmount();
  });
});
