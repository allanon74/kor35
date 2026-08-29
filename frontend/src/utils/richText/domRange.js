/**
 * Primitive DOM/Range condivise dal motore di formattazione del RichTextEditor.
 * Lavorare per blocchi (e non sull'intero documento) rende le operazioni prevedibili
 * anche su selezioni parziali.
 */

/** Elementi che si comportano da blocco nel contenuto rich text. */
const BLOCK_TAGS = [
    'p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'li', 'blockquote', 'pre', 'td', 'th', 'caption', 'summary', 'figcaption',
];

export const BLOCK_SELECTOR = BLOCK_TAGS.join(',');

const BLOCK_TAG_SET = new Set(BLOCK_TAGS.map((tag) => tag.toUpperCase()));

/** Tag inline che rappresentano formattazione rimovibile. */
export const INLINE_FORMAT_SELECTOR = [
    'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'del', 'ins', 'mark',
    'font', 'span', 'small', 'big', 'sub', 'sup', 'code', 'tt', 'a',
].join(',');

/** Marcatore temporaneo per conservare i confini di selezione tra piu operazioni DOM. */
const MARKER_ATTR = 'data-kor-rt-marker';

export const isMarker = (node) => node?.nodeType === 1 && node.hasAttribute(MARKER_ATTR);

export const createMarker = () => {
    const marker = document.createElement('span');
    marker.setAttribute(MARKER_ATTR, '1');
    return marker;
};

/** Sostituisce un elemento con i suoi figli. */
export const unwrapElement = (el) => {
    const parent = el.parentNode;
    if (!parent) return;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    parent.removeChild(el);
};

/** Blocco piu vicino contenente `node`, limitato a `root`. */
export const closestBlock = (node, root) => {
    let current = node?.nodeType === 1 ? node : node?.parentNode;
    while (current && current !== root) {
        if (current.nodeType === 1 && BLOCK_TAG_SET.has(current.tagName)) return current;
        current = current.parentNode;
    }
    return root;
};

/**
 * Blocchi "foglia" attraversati dal range. Se la selezione tocca testo non incapsulato
 * in un blocco, si restituisce `root` e il range viene trattato come unita singola.
 */
export const getBlocksInRange = (range, root) => {
    if (closestBlock(range.startContainer, root) === root || closestBlock(range.endContainer, root) === root) {
        return [root];
    }

    const candidates = [...root.querySelectorAll(BLOCK_SELECTOR)].filter((el) => {
        try {
            return range.intersectsNode(el);
        } catch {
            return false;
        }
    });

    // Solo i blocchi piu interni: un <td> che contiene <p> non va trattato come blocco.
    const leaves = candidates.filter((el) => !candidates.some((other) => other !== el && el.contains(other)));
    return leaves.length ? leaves : [root];
};

/** Porzione di `range` contenuta in `node` (null se non si intersecano). */
export const clampRangeToNode = (range, node) => {
    const clamped = document.createRange();
    clamped.selectNodeContents(node);

    if (range.compareBoundaryPoints(Range.START_TO_START, clamped) > 0) {
        clamped.setStart(range.startContainer, range.startOffset);
    }
    if (range.compareBoundaryPoints(Range.END_TO_END, clamped) < 0) {
        clamped.setEnd(range.endContainer, range.endOffset);
    }

    if (clamped.collapsed) return null;
    return clamped;
};

/** Inserisce due marcatori attorno al range e restituisce le funzioni per riusarlo. */
export const withRangeMarkers = (range) => {
    const startMarker = createMarker();
    const endMarker = createMarker();

    const endPoint = range.cloneRange();
    endPoint.collapse(false);
    endPoint.insertNode(endMarker);

    const startPoint = range.cloneRange();
    startPoint.collapse(true);
    startPoint.insertNode(startMarker);

    const currentRange = () => {
        const next = document.createRange();
        next.setStartAfter(startMarker);
        next.setEndBefore(endMarker);
        return next;
    };

    /**
     * Rimuove i marcatori e riporta la selezione sull'area appena elaborata.
     * I confini vanno letti come (genitore, indice) *dopo* la rimozione di ciascun
     * marcatore, altrimenti gli offset slittano e la selezione finisce fuori posto.
     */
    const release = ({ restoreSelection = true } = {}) => {
        const startParent = startMarker.parentNode;
        const startIndex = startParent ? [...startParent.childNodes].indexOf(startMarker) : -1;
        startMarker.remove();

        const endParent = endMarker.parentNode;
        const endIndex = endParent ? [...endParent.childNodes].indexOf(endMarker) : -1;
        endMarker.remove();

        if (!restoreSelection || startIndex < 0) return;

        try {
            const selectionRange = document.createRange();
            selectionRange.setStart(startParent, startIndex);
            if (endIndex >= 0) selectionRange.setEnd(endParent, endIndex);
            else selectionRange.collapse(true);

            const selection = window.getSelection();
            selection?.removeAllRanges();
            selection?.addRange(selectionRange);
        } catch {
            /* i nodi di riferimento non esistono piu: si lascia la selezione al browser */
        }
    };

    return { currentRange, release, startMarker, endMarker };
};

/** Range corrente se e interno a `root`, altrimenti null. */
export const getSelectionRangeWithin = (root) => {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0) return null;

    const range = selection.getRangeAt(0);
    if (!root.contains(range.commonAncestorContainer)) return null;
    return range;
};

/** Seleziona il contenuto di un nodo. */
export const selectNodeContents = (node) => {
    const range = document.createRange();
    range.selectNodeContents(node);
    const selection = window.getSelection();
    selection?.removeAllRanges();
    selection?.addRange(range);
    return range;
};

/** Unisce span adiacenti identici e rimuove span privi di attributi utili. */
export const tidyInlineWrappers = (root) => {
    root.querySelectorAll('span').forEach((span) => {
        if (isMarker(span)) return;
        const hasStyle = Boolean(span.getAttribute('style')?.trim());
        const hasClass = Boolean(span.getAttribute('class')?.trim());
        const hasCustomStyle = span.hasAttribute('data-custom-style');
        if (!hasStyle && !hasClass && !hasCustomStyle) unwrapElement(span);
    });

    root.querySelectorAll('span[style]').forEach((span) => {
        const next = span.nextSibling;
        if (
            next?.nodeType === 1
            && next.tagName === 'SPAN'
            && !isMarker(next)
            && next.getAttribute('style') === span.getAttribute('style')
            && next.getAttribute('data-custom-style') === span.getAttribute('data-custom-style')
        ) {
            while (next.firstChild) span.appendChild(next.firstChild);
            next.remove();
        }
    });
};
