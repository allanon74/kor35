/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import RichTextToolbar, { RICH_TEXT_MENU_Z_CLASS } from './RichTextToolbar';

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

const dummyActions = {
  undo: vi.fn(),
  redo: vi.fn(),
  toggleBold: vi.fn(),
  toggleItalic: vi.fn(),
  toggleUnderline: vi.fn(),
  toggleStrike: vi.fn(),
  toggleUnorderedList: vi.fn(),
  toggleOrderedList: vi.fn(),
  openLinkDialog: vi.fn(),
  clearFormatting: vi.fn(),
  toggleHtmlMode: vi.fn(),
  toggleFullscreen: vi.fn(),
  setBlock: vi.fn(),
  setAlign: vi.fn(),
  setFontFamily: vi.fn(),
  setFontSize: vi.fn(),
  setTextColor: vi.fn(),
  setHighlight: vi.fn(),
  applyCustomStyle: vi.fn(),
  insertHorizontalRule: vi.fn(),
  insertCollapsible: vi.fn(),
  insertTable: vi.fn(),
  insertEmoji: vi.fn(),
  addRow: vi.fn(),
  removeRow: vi.fn(),
  addColumn: vi.fn(),
  removeColumn: vi.fn(),
};

describe('RichTextToolbar overlay', () => {
  afterEach(() => {
    document.body.querySelectorAll('[data-testid="rich-text-format-panel"]').forEach((el) => el.remove());
  });

  it('apre i menu in portal sopra lo stacking dello staff fullscreen (z-110)', async () => {
    const { host, unmount } = mount(
      createElement(RichTextToolbar, {
        actions: dummyActions,
        formatState: {},
        blockTag: 'p',
        alignment: 'left',
        isHtmlMode: false,
        isFullscreen: false,
        hasTableContext: false,
      }),
    );

    const trigger = host.querySelector('button[aria-label="Tipo di paragrafo"]');
    expect(trigger).toBeTruthy();

    await act(async () => {
      trigger.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const panel = document.body.querySelector('[data-testid="rich-text-format-panel"]');
    expect(panel).toBeTruthy();
    expect(panel.className).toContain(RICH_TEXT_MENU_Z_CLASS);
    expect(RICH_TEXT_MENU_Z_CLASS).toBe('z-[145]');
    expect(panel.style.position).toBe('fixed');
    unmount();
  });
});
