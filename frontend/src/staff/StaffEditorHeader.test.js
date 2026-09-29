/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import { StaffEditorHeader, staffEditorShellClass } from './StaffToolShell';

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

describe('StaffEditorHeader', () => {
  afterEach(() => {
    document.body.querySelectorAll('[data-testid="staff-editor-mobile-footer"]').forEach((el) => el.remove());
  });

  it('mostra il titolo e porta le azioni mobile in portal fisso in basso', () => {
    const { host, unmount } = mount(
      createElement(StaffEditorHeader, {
        title: 'Nuova Infusione',
        titleClassName: 'text-indigo-400',
        actions: createElement('button', { type: 'button' }, 'Salva tecnica'),
      }),
    );

    expect(host.textContent).toContain('Nuova Infusione');
    expect(host.innerHTML).toContain('lg:block');
    expect(host.innerHTML).toContain('hidden');

    const footer = document.body.querySelector('[data-testid="staff-editor-mobile-footer"]');
    expect(footer).toBeTruthy();
    expect(footer.className).toContain('fixed');
    expect(footer.className).toContain('bottom-0');
    expect(footer.className).toContain('lg:hidden');
    expect(footer.textContent).toContain('Salva tecnica');
    // Il footer non deve restare dentro lo shell (overflow/transform lo ritaglierebbero)
    expect(host.contains(footer)).toBe(false);

    unmount();
  });

  it('lo shell editor lascia spazio in basso per la barra Salva su telefono', () => {
    expect(staffEditorShellClass).toContain('min-w-0');
    expect(staffEditorShellClass).toContain('pb-36');
    expect(staffEditorShellClass).toContain('overflow-x-hidden');
    expect(staffEditorShellClass).not.toContain('max-h-');
    expect(staffEditorShellClass).not.toContain('overflow-y-auto');
  });
});
