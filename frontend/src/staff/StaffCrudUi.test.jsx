/**
 * @vitest-environment jsdom
 */
import { describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import { StaffListRow } from './StaffCrudUi';

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

describe('StaffListRow', () => {
  it('apre la modifica cliccando la riga, ma non se si clicca un extra action', async () => {
    const onEdit = vi.fn();
    const onExtra = vi.fn();
    const { host, unmount } = mount(
      createElement(
        StaffListRow,
        {
          onEdit,
          extraActions: createElement(
            'button',
            {
              type: 'button',
              'data-testid': 'extra-sorteggia',
              onClick: (event) => {
                event.stopPropagation();
                onExtra();
              },
            },
            'Sorteggia',
          ),
        },
        createElement('span', { 'data-testid': 'row-label' }, 'Tombola Plot'),
      ),
    );

    await act(async () => {
      host.querySelector('[data-testid="row-label"]').dispatchEvent(
        new MouseEvent('click', { bubbles: true }),
      );
    });
    expect(onEdit).toHaveBeenCalledTimes(1);

    await act(async () => {
      host.querySelector('[data-testid="extra-sorteggia"]').dispatchEvent(
        new MouseEvent('click', { bubbles: true }),
      );
    });
    expect(onExtra).toHaveBeenCalledTimes(1);
    expect(onEdit).toHaveBeenCalledTimes(1);
    unmount();
  });
});
