/**
 * API pubblica di sanitizzazione per il blocco RichText.
 * Motore: DOMPurify + policy in `richText/htmlPolicy.js`.
 *
 * Garanzie rispetto alla versione precedente:
 * - gli stili inline legittimi (colore, allineamento, dimensioni, stili custom) sopravvivono;
 * - gli "a capo" non vengono piu persi (paragrafi vuoti conservati, `\n` reali convertiti in <br>);
 * - i tag e gli attributi pericolosi (script, on*, iframe, javascript:) vengono rimossi davvero.
 */
import { purifyToFragment, fragmentToHtml } from './richText/htmlPolicy';

const HTML_TAG_RE = /<[a-z][\s\S]*>/i;

/** Elementi in cui i newline del sorgente sono struttura, non testo. */
const NEWLINE_SKIP_ANCESTORS = new Set([
    'PRE', 'CODE', 'TABLE', 'THEAD', 'TBODY', 'TFOOT', 'TR', 'COLGROUP',
]);

/** Blocchi considerati "vuoti" quando si ripulisce solo l'inizio e la fine del contenuto. */
const TRIMMABLE_EMPTY_BLOCKS = new Set(['P', 'DIV', 'BR']);

export const escapeHtml = (text) => String(text)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');

/** Rimuove l'attributo open da tutti i <details> nell'HTML (collapsible chiusi di default). */
export const ensureDetailsClosed = (html) => {
    if (!html || typeof html !== 'string') return html || '';
    return html.replace(/<details(\s[^>]*)>/gi, (_, attrs) => {
        const cleaned = attrs.replace(/\s+open(?:\s*=\s*["'][^"']*["'])?/gi, '').replace(/\s+/g, ' ').trim();
        return '<details' + (cleaned ? ' ' + cleaned : '') + '>';
    });
};

/** Se il contenuto e testo semplice, lo trasforma in HTML preservando gli a capo. */
export const prepareRichHtmlForView = (content) => {
    if (!content) return '';
    const trimmed = String(content).trim();
    if (!trimmed) return '';
    if (HTML_TAG_RE.test(trimmed)) return trimmed;
    return escapeHtml(trimmed).replace(/\r\n|\r|\n/g, '<br>');
};

const hasSkippedAncestor = (node, root) => {
    let current = node.parentNode;
    while (current && current !== root) {
        if (current.nodeType === 1 && NEWLINE_SKIP_ANCESTORS.has(current.tagName)) return true;
        current = current.parentNode;
    }
    return false;
};

/**
 * Converte in <br> gli a capo reali presenti nei nodi di testo.
 *
 * Editor e viewer usano `white-space: normal`: un `\n` nel testo non produrrebbe alcuna
 * interruzione visibile, ed era il motivo per cui gli a capo incollati (o salvati da
 * contenuti storici in testo semplice) sparivano in lettura.
 * I nodi di sola spaziatura (indentazione del sorgente HTML) restano intatti.
 */
const convertRealNewlinesToBreaks = (root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    const targets = [];

    let node = walker.nextNode();
    while (node) {
        const text = node.nodeValue || '';
        if (/\S/.test(text) && /\r|\n/.test(text) && !hasSkippedAncestor(node, root)) targets.push(node);
        node = walker.nextNode();
    }

    targets.forEach((textNode) => {
        const parts = (textNode.nodeValue || '').split(/[ \t]*(?:\r\n|\r|\n)[ \t]*/);
        const replacement = document.createDocumentFragment();

        parts.forEach((part, index) => {
            if (index > 0) replacement.appendChild(document.createElement('br'));
            if (part) replacement.appendChild(document.createTextNode(part));
        });

        textNode.parentNode?.replaceChild(replacement, textNode);
    });
};

/** Avvolge le tabelle in un contenitore scrollabile: su smartphone altrimenti sfondano il layout. */
const wrapTablesForScroll = (root) => {
    root.querySelectorAll('table').forEach((table) => {
        const parent = table.parentNode;
        if (!parent || (parent.nodeType === 1 && parent.classList?.contains('rich-table-scroll'))) return;

        const wrapper = document.createElement('div');
        wrapper.className = 'rich-table-scroll';
        parent.insertBefore(wrapper, table);
        wrapper.appendChild(table);
    });
};

const isEmptyBlock = (node) => {
    if (node.nodeType === 3) return !/\S/.test(node.nodeValue || '');
    if (node.nodeType !== 1) return true;
    if (!TRIMMABLE_EMPTY_BLOCKS.has(node.tagName)) return false;
    if (node.tagName === 'BR') return true;
    if (node.querySelector('img, table, hr, iframe, details')) return false;
    return !node.textContent.replace(/\u00a0/g, ' ').trim();
};

/**
 * Elimina i blocchi vuoti solo a inizio e fine contenuto.
 * I paragrafi vuoti interni sono a capo voluti dall'autore e vanno conservati:
 * la vecchia implementazione li cancellava tutti, ed era il motivo per cui
 * le righe bianche sparivano in visualizzazione.
 */
const trimEdgeEmptyBlocks = (root) => {
    while (root.firstChild && isEmptyBlock(root.firstChild)) root.removeChild(root.firstChild);
    while (root.lastChild && isEmptyBlock(root.lastChild)) root.removeChild(root.lastChild);
};

/**
 * Sanitizza HTML per la visualizzazione.
 * @param {string} htmlContent
 * @param {{dropTextColors?: boolean}} [options] `dropTextColors` neutralizza i colori di testo
 *        senza sfondo proprio (serve sulle pagine a fondo chiaro).
 * @returns {string} HTML sicuro
 */
export const sanitizeHtml = (htmlContent, options = {}) => {
    if (!htmlContent) return '';

    const prepared = prepareRichHtmlForView(htmlContent);
    if (!prepared) return '';

    const fragment = purifyToFragment(prepared, options);
    if (!fragment) return escapeHtml(String(htmlContent));

    const holder = document.createElement('div');
    holder.appendChild(fragment);

    convertRealNewlinesToBreaks(holder);
    wrapTablesForScroll(holder);
    trimEdgeEmptyBlocks(holder);

    return holder.innerHTML;
};

/**
 * Sanitizza HTML destinato all'inserimento nell'editor (incolla da altre app).
 * Non applica le trasformazioni di sola visualizzazione (wrapper tabelle, trim bordi).
 * @returns {DocumentFragment}
 */
export const sanitizeHtmlForEditor = (html) => {
    const fragment = purifyToFragment(String(html || ''));
    if (!fragment) return document.createDocumentFragment();

    const holder = document.createElement('div');
    holder.appendChild(fragment);
    convertRealNewlinesToBreaks(holder);

    const result = document.createDocumentFragment();
    while (holder.firstChild) result.appendChild(holder.firstChild);
    return result;
};

/** Versione stringa di `sanitizeHtmlForEditor`. */
export const sanitizeHtmlForEditorString = (html) => fragmentToHtml(sanitizeHtmlForEditor(html));

/** true se il contenuto rich text ha testo o media significativi. */
export const richTextHasContent = (html) => {
    if (!html) return false;
    const raw = String(html);
    if (/<(?:img|table|hr|iframe|video|details)\b/i.test(raw)) return true;
    return Boolean(raw.replace(/<[^>]*>/g, '').replace(/&nbsp;|\u00a0/g, ' ').trim());
};
