import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { StaffEditorHeader, staffEditorShellClass } from './StaffToolShell';

describe('StaffEditorHeader', () => {
  it('mostra il titolo intero e impila le azioni (layout mobile-first)', () => {
    const html = renderToStaticMarkup(
      createElement(StaffEditorHeader, {
        title: 'Nuova Infusione',
        titleClassName: 'text-indigo-400',
        actions: createElement('button', { type: 'button' }, 'Salva tecnica'),
      }),
    );
    expect(html).toContain('Nuova Infusione');
    expect(html).toContain('Salva tecnica');
    expect(html).toContain('flex-col');
    expect(html).toContain('lg:flex-row');
    expect(html).toContain('break-words');
  });

  it('lo shell editor non forza overflow orizzontale su telefono', () => {
    expect(staffEditorShellClass).toContain('min-w-0');
    expect(staffEditorShellClass).toContain('lg:overflow-y-auto');
    expect(staffEditorShellClass).not.toMatch(/(^|\s)overflow-y-auto(\s|$)/);
  });
});
