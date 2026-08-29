import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';
import { beforeEach, describe, expect, it } from 'vitest';
import RichHtml from './RichHtml';

const render = (element) => renderToStaticMarkup(element);

describe('RichHtml', () => {
    beforeEach(() => {
        document.head.innerHTML = '';
    });

    it('sanitizza il contenuto invece di iniettarlo grezzo', () => {
        const html = render(
            <RichHtml content={'<p>ok</p><script>alert(1)</script><img src="x" onerror="alert(1)">'} />
        );

        expect(html).toContain('ok');
        expect(html).not.toMatch(/&lt;script/i);
        expect(html).not.toMatch(/onerror/i);
    });

    it('applica la tipografia condivisa del viewer', () => {
        const html = render(<RichHtml content="<p>x</p>" className="text-sm" />);

        expect(html).toContain('ql-editor-view');
        expect(html).toContain('text-sm');
        expect(html).not.toContain('ql-editor-view--light');
    });

    it('su fondo chiaro neutralizza i colori di testo del tema scuro', () => {
        const html = render(
            <RichHtml content={'<p><span style="color: #d1d5db">x</span></p>'} tone="onLight" />
        );

        expect(html).toContain('ql-editor-view--light');
        expect(html).not.toMatch(/color/i);
    });

    it('rende visibili gli a capo del testo semplice', () => {
        const html = render(<RichHtml content={'riga 1\nriga 2'} />);
        expect(html).toContain('<br>');
    });

    it('non emette nulla per contenuto vuoto', () => {
        expect(render(<RichHtml content="" />)).toBe('');
        expect(render(<RichHtml content={null} />)).toBe('');
    });

    it('inserisce il foglio di stile condiviso una sola volta', () => {
        render(<RichHtml content="<p>a</p>" />);
        render(<RichHtml content="<p>b</p>" />);

        expect(document.head.querySelectorAll('style#kor-rich-text-shared-styles')).toHaveLength(1);
    });

    it('inoltra gli altri attributi al contenitore (troncamento cliccabile)', () => {
        const html = render(
            <RichHtml content="<p>x</p>" as="span" title="Espandi" className="line-clamp-1" />
        );

        expect(html).toMatch(/^<span /);
        expect(html).toContain('title="Espandi"');
        expect(html).toContain('line-clamp-1');
    });
});
