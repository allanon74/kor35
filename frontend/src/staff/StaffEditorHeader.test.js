import { describe, expect, it } from 'vitest';
import { createElement } from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { StaffEditorHeader, staffEditorShellClass } from './StaffToolShell';

describe('StaffEditorHeader', () => {
  it('mostra il titolo e nasconde le azioni in header su viewport mobile (lg:hidden footer)', () => {
    const html = renderToStaticMarkup(
      createElement(StaffEditorHeader, {
        title: 'Nuova Infusione',
        titleClassName: 'text-indigo-400',
        actions: createElement('button', { type: 'button' }, 'Salva tecnica'),
      }),
    );
    expect(html).toContain('Nuova Infusione');
    expect(html).toContain('Salva tecnica');
    expect(html).toContain('hidden');
    expect(html).toContain('lg:block');
    expect(html).toContain('fixed');
    expect(html).toContain('bottom-0');
    expect(html).toContain('break-words');
  });

  it('lo shell editor lascia spazio in basso per la barra Salva su telefono', () => {
    expect(staffEditorShellClass).toContain('min-w-0');
    expect(staffEditorShellClass).toContain('pb-36');
    expect(staffEditorShellClass).toContain('overflow-x-hidden');
    expect(staffEditorShellClass).not.toContain('max-h-');
    expect(staffEditorShellClass).not.toContain('overflow-y-auto');
  });
});
