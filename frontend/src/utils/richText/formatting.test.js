import { afterEach, describe, expect, it } from 'vitest';
import {
    applyInlineStyle,
    clearFormatting,
    removeInlineStyle,
    setBlockAlignment,
} from './formatting';

/**
 * jsdom non implementa `document.execCommand`, quindi i comandi nativi (formatBlock,
 * liste) restano no-op. Questi test coprono il motore DOM: la parte che nel browser
 * sostituisce `removeFormat`/`foreColor`, storicamente inaffidabili.
 */
let editor;

const mountEditor = (html) => {
    document.body.innerHTML = '';
    editor = document.createElement('div');
    editor.contentEditable = 'true';
    editor.innerHTML = html;
    document.body.appendChild(editor);
    return editor;
};

/** Seleziona la prima occorrenza di `text` dentro l'editor. */
const selectText = (text) => {
    const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        const node = walker.currentNode;
        const index = node.textContent.indexOf(text);
        if (index >= 0) {
            const range = document.createRange();
            range.setStart(node, index);
            range.setEnd(node, index + text.length);
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(range);
            return range;
        }
    }
    throw new Error(`Testo non trovato nell'editor: ${text}`);
};

/** Seleziona il contenuto del blocco indicato (come un "seleziona tutto" nel paragrafo). */
const selectBlock = (selector) => {
    const block = editor.querySelector(selector);
    const range = document.createRange();
    range.selectNodeContents(block);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    return range;
};

const styleAttributes = () =>
    Array.from(editor.querySelectorAll('[style]')).map((el) => el.getAttribute('style')).join(' | ');

/** Colore effettivo del testo: vince l'antenato piu interno con `color`. */
const effectiveColor = (text) => {
    const walker = document.createTreeWalker(editor, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
        if (!walker.currentNode.textContent.includes(text)) continue;
        let node = walker.currentNode.parentElement;
        while (node && node !== editor) {
            const color = node.style?.getPropertyValue('color');
            if (color) return color;
            node = node.parentElement;
        }
        return '';
    }
    throw new Error(`Testo non trovato: ${text}`);
};

afterEach(() => {
    document.body.innerHTML = '';
});

describe('applyInlineStyle', () => {
    it('applica lo stile alla sola selezione', () => {
        mountEditor('<p>alfa beta gamma</p>');
        selectText('beta');
        applyInlineStyle(editor, { color: '#ff0000' });

        const styled = editor.querySelector('[style*="color"]');
        expect(styled.textContent).toBe('beta');
        expect(editor.textContent).toBe('alfa beta gamma');
    });

    it('sovrascrive lo stile quando la selezione copre lo span esistente', () => {
        mountEditor('<p><span style="color: rgb(255, 0, 0)">testo</span></p>');
        selectBlock('p');
        applyInlineStyle(editor, { color: 'rgb(0, 255, 0)' });

        expect(styleAttributes()).not.toContain('255, 0, 0');
        expect(effectiveColor('testo')).toBe('rgb(0, 255, 0)');
        expect(editor.textContent).toBe('testo');
    });

    it('sovrascrive lo stile ereditato da un antenato piu ampio', () => {
        mountEditor('<p><span style="color: rgb(255, 0, 0)">rosso tutto</span></p>');
        selectText('tutto');
        applyInlineStyle(editor, { color: 'rgb(0, 0, 255)' });

        expect(effectiveColor('tutto')).toBe('rgb(0, 0, 255)');
        expect(effectiveColor('rosso')).toBe('rgb(255, 0, 0)');
    });

    it('non annida piu span con la stessa proprieta', () => {
        mountEditor('<p><span style="color: rgb(255, 0, 0)">parola</span></p>');
        selectText('parola');
        applyInlineStyle(editor, { color: 'rgb(0, 0, 255)' });

        expect(editor.querySelectorAll('[style*="color"]').length).toBe(1);
    });

    it('conserva le altre proprieta dello span attraversato', () => {
        mountEditor('<p><span style="color: rgb(255, 0, 0); font-weight: 700">parola</span></p>');
        selectText('parola');
        applyInlineStyle(editor, { color: 'rgb(0, 0, 255)' });

        expect(styleAttributes()).toContain('font-weight');
        expect(effectiveColor('parola')).toBe('rgb(0, 0, 255)');
    });

    it('sostituisce lo stile personalizzato precedente', () => {
        mountEditor('<p><span data-custom-style="warning" style="color: rgb(146, 64, 14)">chip</span></p>');
        selectText('chip');
        applyInlineStyle(
            editor,
            { color: 'rgb(17, 24, 39)' },
            { customStyleId: 'muted', replaceCustomStyles: true }
        );

        const marked = editor.querySelectorAll('[data-custom-style]');
        expect(marked.length).toBe(1);
        expect(marked[0].getAttribute('data-custom-style')).toBe('muted');
    });
});

describe('removeInlineStyle', () => {
    it('azzera la proprieta anche se applicata da un antenato', () => {
        mountEditor('<p><span style="color: rgb(255, 0, 0)">rosso tutto</span></p>');
        selectText('tutto');
        removeInlineStyle(editor, ['color']);

        expect(effectiveColor('tutto')).toBe('');
        expect(effectiveColor('rosso')).toBe('rgb(255, 0, 0)');
    });
});

describe('clearFormatting', () => {
    it('rimuove tag inline annidati e stili della selezione', () => {
        mountEditor(
            '<p><strong><em><u><span style="color: rgb(255, 0, 0); font-size: 2em">testo formattato</span></u></em></strong></p>'
        );
        selectBlock('p');
        clearFormatting(editor);

        expect(editor.querySelector('strong')).toBeNull();
        expect(editor.querySelector('em')).toBeNull();
        expect(editor.querySelector('u')).toBeNull();
        expect(editor.querySelector('[style]')).toBeNull();
        expect(editor.textContent).toBe('testo formattato');
    });

    it('rimuove la formattazione portata dagli antenati della selezione parziale', () => {
        mountEditor('<p><strong>uno due</strong></p>');
        selectText('due');
        clearFormatting(editor);

        const bold = editor.querySelector('strong');
        expect(bold).not.toBeNull();
        expect(bold.textContent).toBe('uno ');
        expect(editor.textContent).toBe('uno due');
    });

    it('rimuove evidenziazioni, codice e stili personalizzati', () => {
        mountEditor(
            '<p><mark>evidenziato</mark> <code>codice</code> '
            + '<span data-custom-style="warning" style="background-color: rgb(254, 243, 199)">chip</span></p>'
        );
        selectBlock('p');
        clearFormatting(editor);

        expect(editor.querySelector('mark')).toBeNull();
        expect(editor.querySelector('code')).toBeNull();
        expect(editor.querySelector('[data-custom-style]')).toBeNull();
        expect(editor.querySelector('[style]')).toBeNull();
        expect(editor.textContent).toBe('evidenziato codice chip');
    });

    it('azzera allineamento e attributi di formattazione del blocco', () => {
        mountEditor('<h2 style="text-align: center" class="wiki-link">titolo</h2>');
        selectBlock('h2');
        clearFormatting(editor);

        const block = editor.querySelector('h2');
        expect(block.getAttribute('style')).toBeNull();
        expect(block.getAttribute('class')).toBeNull();
    });

    it('conserva le interruzioni di riga', () => {
        mountEditor('<p><strong>uno</strong><br><em>due</em></p>');
        selectBlock('p');
        clearFormatting(editor);

        expect(editor.querySelector('br')).not.toBeNull();
        expect(editor.querySelector('strong')).toBeNull();
        expect(editor.querySelector('em')).toBeNull();
    });

    it('lascia intatto il testo fuori dalla selezione', () => {
        mountEditor('<p><strong>uno</strong></p><p><em>due</em></p>');
        selectBlock('p');
        clearFormatting(editor);

        expect(editor.querySelector('strong')).toBeNull();
        expect(editor.querySelector('em')).not.toBeNull();
    });
});

describe('setBlockAlignment', () => {
    it('imposta e rimuove l\'allineamento del blocco', () => {
        mountEditor('<p>testo</p>');
        selectText('testo');
        setBlockAlignment(editor, 'center');
        expect(editor.querySelector('p').style.textAlign).toBe('center');

        selectText('testo');
        setBlockAlignment(editor, 'left');
        expect(editor.querySelector('p').getAttribute('style')).toBeNull();
    });
});
