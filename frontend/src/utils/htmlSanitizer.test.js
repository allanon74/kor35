import { describe, expect, it } from 'vitest';
import { ensureDetailsClosed, richTextHasContent, sanitizeHtml } from './htmlSanitizer';

describe('sanitizeHtml — sicurezza', () => {
    it('rimuove script, iframe e attributi on*', () => {
        const dirty = '<p>ciao</p><script>alert(1)</script><iframe src="x"></iframe>'
            + '<img src="x" onerror="alert(1)"><div onclick="alert(1)">testo</div>';
        const clean = sanitizeHtml(dirty);

        expect(clean).not.toMatch(/<script/i);
        expect(clean).not.toMatch(/<iframe/i);
        expect(clean).not.toMatch(/onerror/i);
        expect(clean).not.toMatch(/onclick/i);
        expect(clean).toContain('ciao');
        expect(clean).toContain('testo');
    });

    it('scarta i link con protocollo javascript', () => {
        const clean = sanitizeHtml('<a href="javascript:alert(1)">link</a>');
        expect(clean).not.toMatch(/javascript:/i);
        expect(clean).toContain('link');
    });

    it('rimuove le proprieta CSS pericolose ma tiene quelle tipografiche', () => {
        const clean = sanitizeHtml(
            '<p style="color: #ff0000; position: fixed; z-index: 99; background-image: url(http://x/y.png)">x</p>'
        );

        expect(clean).toContain('color');
        expect(clean).not.toMatch(/position/i);
        expect(clean).not.toMatch(/z-index/i);
        expect(clean).not.toMatch(/url\(/i);
    });

    it('conserva solo le classi del progetto', () => {
        const clean = sanitizeHtml('<a class="wiki-link MsoNormal bg-red-500" href="/regolamento/x">x</a>');
        expect(clean).toContain('wiki-link');
        expect(clean).not.toContain('MsoNormal');
        expect(clean).not.toContain('bg-red-500');
    });

    it('apre in una nuova scheda solo i link esterni, con rel di sicurezza', () => {
        const external = sanitizeHtml('<a href="https://example.com">x</a>');
        expect(external).toContain('target="_blank"');
        expect(external).toContain('noopener');

        const internal = sanitizeHtml('<a href="/regolamento/pagina">x</a>');
        expect(internal).not.toContain('target=');
    });
});

describe('sanitizeHtml — stili applicati nell\'editor', () => {
    it('mantiene gli stili inline della formattazione', () => {
        const clean = sanitizeHtml(
            '<p style="text-align: center"><span style="color: #818cf8; font-size: 1.35em">titolo</span></p>'
        );

        expect(clean).toContain('text-align: center');
        expect(clean).toContain('font-size: 1.35em');
        expect(clean).toContain('color');
    });

    it('mantiene gli stili personalizzati e il loro marcatore', () => {
        const clean = sanitizeHtml(
            '<span data-custom-style="warning" style="background-color: #fef3c7; color: #92400e">attenzione</span>'
        );

        expect(clean).toContain('data-custom-style="warning"');
        expect(clean).toContain('background-color');
    });

    it('con dropTextColors neutralizza i colori senza sfondo proprio', () => {
        const clean = sanitizeHtml('<span style="color: #f9fafb">testo chiaro</span>', { dropTextColors: true });
        expect(clean).not.toMatch(/(^|[;"\s])color\s*:/);
        expect(clean).toContain('testo chiaro');
    });

    it('con dropTextColors conserva i colori dei chip con sfondo', () => {
        const clean = sanitizeHtml(
            '<span style="background-color: #fef3c7; color: #92400e">chip</span>',
            { dropTextColors: true }
        );
        expect(clean).toMatch(/[;\s]color\s*:/);
        expect(clean).toContain('background-color');
    });
});

describe('sanitizeHtml — a capo', () => {
    it('conserva i paragrafi vuoti interni (righe bianche volute)', () => {
        const clean = sanitizeHtml('<p>prima</p><p><br></p><p>dopo</p>');
        expect(clean).toBe('<p>prima</p><p><br></p><p>dopo</p>');
    });

    it('converte in <br> gli a capo reali del testo incollato', () => {
        const clean = sanitizeHtml('<p>riga uno\nriga due</p>');
        expect(clean).toContain('riga uno<br>riga due');
    });

    it('non tocca la spaziatura strutturale del sorgente HTML', () => {
        const clean = sanitizeHtml('<table>\n  <tbody>\n    <tr>\n      <td>a</td>\n    </tr>\n  </tbody>\n</table>');
        expect(clean).not.toContain('<br>');
        expect(clean).toContain('<td>a</td>');
    });

    it('trasforma il testo semplice multiriga in HTML con interruzioni', () => {
        const clean = sanitizeHtml('riga uno\nriga due');
        expect(clean).toBe('riga uno<br>riga due');
    });

    it('rimuove i blocchi vuoti solo a inizio e fine', () => {
        const clean = sanitizeHtml('<p><br></p><p>centro</p><p><br></p>');
        expect(clean).toBe('<p>centro</p>');
    });
});

describe('sanitizeHtml — tabelle e collapsible', () => {
    it('avvolge le tabelle in un contenitore scrollabile', () => {
        const clean = sanitizeHtml('<table data-table-style="grid"><tbody><tr><td>a</td></tr></tbody></table>');
        expect(clean).toContain('class="rich-table-scroll"');
        expect(clean).toContain('data-table-style="grid"');
    });

    it('chiude i details aperti', () => {
        const clean = sanitizeHtml('<details open><summary>t</summary><div>c</div></details>');
        expect(clean).not.toContain('open');
    });
});

describe('helper', () => {
    it('ensureDetailsClosed rimuove open preservando gli altri attributi', () => {
        expect(ensureDetailsClosed('<details class="wiki-collapsible" open>')).toBe('<details class="wiki-collapsible">');
    });

    it('richTextHasContent distingue contenuto reale da markup vuoto', () => {
        expect(richTextHasContent('<p><br></p>')).toBe(false);
        expect(richTextHasContent('<p>&nbsp;</p>')).toBe(false);
        expect(richTextHasContent('<p>ciao</p>')).toBe(true);
        expect(richTextHasContent('<p><img src="/x.png"></p>')).toBe(true);
        expect(richTextHasContent('')).toBe(false);
    });
});
