/**
 * Policy unica di sanitizzazione HTML per il blocco RichText (editor + viewer).
 *
 * Prima questa logica rimuoveva `style` e `class` da tutti gli elementi: il risultato
 * era che colori, allineamenti, dimensioni e stili personalizzati applicati
 * nell'editor sparivano in visualizzazione. Qui invece si usa DOMPurify con una
 * allowlist di tag/attributi e un filtro esplicito sulle proprieta CSS: gli stili
 * legittimi sopravvivono, quelli pericolosi o che rompono il layout no.
 */
import createDOMPurify from 'dompurify';

/** Tag ammessi nel contenuto rich text (allowlist stretta: niente svg/math/script/form). */
export const ALLOWED_TAGS = [
    'p', 'br', 'div', 'span',
    'strong', 'b', 'em', 'i', 'u', 's', 'strike', 'del', 'ins', 'mark', 'small', 'sub', 'sup',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'blockquote', 'pre', 'code', 'hr',
    'ul', 'ol', 'li',
    'a', 'img', 'figure', 'figcaption',
    'table', 'caption', 'colgroup', 'col', 'thead', 'tbody', 'tfoot', 'tr', 'th', 'td',
    'details', 'summary',
];

/** Attributi ammessi (i data-* consentiti sono filtrati a parte in ALLOWED_DATA_ATTR). */
export const ALLOWED_ATTR = [
    'href', 'target', 'rel', 'title', 'id',
    'src', 'alt', 'width', 'height', 'loading',
    'colspan', 'rowspan', 'scope', 'span',
    'class', 'style', 'align', 'dir', 'lang',
];

/** Data attribute usati dall'editor per riconoscere i propri costrutti. */
const ALLOWED_DATA_ATTR = new Set([
    'data-table-style',
    'data-custom-style',
    'data-placeholder',
]);

/**
 * Proprieta CSS inline ammesse. Escluse volutamente: position, z-index, top/left/right/bottom,
 * transform, filter, animation, transition, content, cursor, pointer-events, visibility
 * (vettori di clickjacking o di contenuto invisibile).
 */
const ALLOWED_CSS_PROPERTIES = new Set([
    'color', 'background', 'background-color',
    'font', 'font-family', 'font-size', 'font-style', 'font-variant', 'font-weight',
    'text-align', 'text-decoration', 'text-decoration-color', 'text-decoration-line',
    'text-decoration-style', 'text-indent', 'text-shadow', 'text-transform',
    'letter-spacing', 'line-height', 'word-spacing', 'word-break', 'overflow-wrap', 'white-space',
    'vertical-align', 'direction',
    'margin', 'margin-top', 'margin-right', 'margin-bottom', 'margin-left',
    'padding', 'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'border', 'border-top', 'border-right', 'border-bottom', 'border-left',
    'border-color', 'border-style', 'border-width', 'border-radius',
    'border-collapse', 'border-spacing',
    'display', 'width', 'min-width', 'max-width', 'height', 'min-height', 'max-height',
    'list-style', 'list-style-position', 'list-style-type',
    'opacity', 'box-shadow', 'overflow', 'overflow-x', 'overflow-y',
    'float', 'clear', 'caption-side', 'table-layout',
]);

/**
 * Valori CSS rifiutati a prescindere dalla proprieta: risorse esterne, vecchie
 * `expression()` di IE, URL script e sequenze di escape usate per offuscare.
 */
const UNSAFE_CSS_VALUE = /url\s*\(|expression\s*\(|javascript\s*:|@import|\\/i;

/** Classi conservate: solo i prefissi usati dal progetto (evita di trascinarsi classi da Word/Tailwind). */
const ALLOWED_CLASS = /^(?:wiki|rich|kor|ql)-[a-z0-9-]+$/i;

/** Elementi su cui width/height come attributo HTML hanno senso. */
const DIMENSION_ATTR_TAGS = new Set(['IMG', 'TABLE', 'TH', 'TD', 'COL', 'COLGROUP']);

let purifier = null;

/**
 * Opzioni della chiamata corrente: DOMPurify invoca gli hook in modo sincrono
 * durante `sanitize`, quindi passare il contesto tramite modulo e sicuro.
 */
let activeOptions = { dropTextColors: false };

/** Rimuove le proprieta CSS non ammesse dall'attributo style, usando il parser CSS del browser. */
const filterInlineStyle = (el) => {
    if (!el.hasAttribute || !el.hasAttribute('style')) return;

    const { style } = el;
    if (!style || typeof style.item !== 'function') {
        el.removeAttribute('style');
        return;
    }

    const properties = [];
    for (let i = 0; i < style.length; i += 1) properties.push(style.item(i));

    // Un elemento con sfondo esplicito porta con se il proprio contrasto: il suo
    // `color` resta valido anche su pagina chiara (es. chip evidenziati).
    const background = `${style.getPropertyValue('background')} ${style.getPropertyValue('background-color')}`;
    const hasOwnBackground = Boolean(background.trim()) && !/^\s*(transparent|none)\s*$/i.test(background.trim());

    properties.forEach((property) => {
        const value = style.getPropertyValue(property);

        if (!ALLOWED_CSS_PROPERTIES.has(property) || UNSAFE_CSS_VALUE.test(value)) {
            style.removeProperty(property);
            return;
        }

        if (activeOptions.dropTextColors && property === 'color' && !hasOwnBackground) {
            style.removeProperty(property);
        }
    });

    if (!el.getAttribute('style')?.trim()) el.removeAttribute('style');
};

/** Tiene solo le classi del progetto (wiki-*, rich-*, kor-*, ql-*). */
const filterClassAttribute = (el) => {
    if (!el.hasAttribute || !el.hasAttribute('class')) return;

    const kept = (el.getAttribute('class') || '')
        .split(/\s+/)
        .filter((name) => name && ALLOWED_CLASS.test(name));

    if (kept.length) el.setAttribute('class', kept.join(' '));
    else el.removeAttribute('class');
};

/** Rimuove i data-* non previsti dalla policy. */
const filterDataAttributes = (el) => {
    if (!el.attributes) return;
    [...el.attributes].forEach(({ name }) => {
        if (name.startsWith('data-') && !ALLOWED_DATA_ATTR.has(name)) el.removeAttribute(name);
    });
};

const applyElementRules = (el) => {
    const tag = el.tagName;

    if (tag === 'DETAILS') {
        // I collapsible partono sempre chiusi in visualizzazione.
        el.removeAttribute('open');
    }

    if (tag === 'A') {
        const href = el.getAttribute('href') || '';
        const isExternal = /^https?:\/\//i.test(href);
        if (isExternal) {
            el.setAttribute('target', '_blank');
            el.setAttribute('rel', 'noopener noreferrer');
        } else if (el.getAttribute('target') === '_blank') {
            el.setAttribute('rel', 'noopener noreferrer');
        } else {
            el.removeAttribute('target');
        }
    }

    if (tag === 'IMG') {
        el.setAttribute('loading', 'lazy');
        el.setAttribute('decoding', 'async');
    }

    if (!DIMENSION_ATTR_TAGS.has(tag)) {
        // width/height su div/p/span arrivano da copia-incolla e rompono il layout mobile.
        el.removeAttribute('width');
        el.removeAttribute('height');
    }
};

const getPurifier = () => {
    if (purifier) return purifier;
    if (typeof window === 'undefined') return null;

    purifier = createDOMPurify(window);
    purifier.addHook('afterSanitizeAttributes', (node) => {
        if (node.nodeType !== 1) return;
        filterDataAttributes(node);
        filterClassAttribute(node);
        filterInlineStyle(node);
        applyElementRules(node);
    });

    return purifier;
};

const PURIFY_CONFIG = {
    ALLOWED_TAGS,
    ALLOWED_ATTR,
    ALLOW_DATA_ATTR: true, // filtrato puntualmente nell'hook
    ALLOW_ARIA_ATTR: false,
    ALLOW_UNKNOWN_PROTOCOLS: false,
    RETURN_DOM_FRAGMENT: true,
    SANITIZE_DOM: true,
    FORBID_CONTENTS: ['script', 'style'],
};

/**
 * Sanitizza `html` restituendo un DocumentFragment (nessuna riserializzazione intermedia).
 * @param {string} html
 * @param {{dropTextColors?: boolean}} [options]
 * @returns {DocumentFragment|null}
 */
export const purifyToFragment = (html, options = {}) => {
    const dom = getPurifier();
    if (!dom) return null;

    activeOptions = { dropTextColors: Boolean(options.dropTextColors) };
    try {
        return dom.sanitize(String(html), PURIFY_CONFIG);
    } finally {
        activeOptions = { dropTextColors: false };
    }
};

/** Serializza un fragment/nodo in stringa HTML. */
export const fragmentToHtml = (fragment) => {
    if (!fragment) return '';
    const holder = document.createElement('div');
    holder.appendChild(fragment);
    return holder.innerHTML;
};
