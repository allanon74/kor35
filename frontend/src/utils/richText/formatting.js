/**
 * Motore di formattazione del RichTextEditor.
 *
 * `document.execCommand` viene usato solo dove i browser lo implementano bene
 * (grassetto/corsivo/liste/undo). Tutto il resto - stili inline sostitutivi e
 * rimozione completa della formattazione - e gestito qui sul DOM, perche
 * `removeFormat` non tocca blocchi, liste, allineamenti e span con background/bordi.
 */
import {
    INLINE_FORMAT_SELECTOR,
    clampRangeToNode,
    closestBlock,
    getBlocksInRange,
    getSelectionRangeWithin,
    isMarker,
    selectNodeContents,
    tidyInlineWrappers,
    unwrapElement,
    withRangeMarkers,
} from './domRange';

/** Comandi che devono produrre tag semantici (<strong>, <em>, ...) e non span con style. */
const SEMANTIC_COMMANDS = new Set(['bold', 'italic', 'underline', 'strikeThrough']);

/** Attributi di formattazione da azzerare sui blocchi. */
const BLOCK_FORMAT_ATTRIBUTES = ['style', 'class', 'align', 'data-custom-style', 'data-table-style'];

const WORD_BOUNDARY = /[\s\u00a0.,;:!?()[\]{}"'«»]/;

export const execFormatCommand = (command, value = null) => {
    if (typeof document.execCommand !== 'function') return false;

    try {
        document.execCommand('styleWithCSS', false, !SEMANTIC_COMMANDS.has(command));
    } catch {
        /* browser che non espone styleWithCSS: si procede comunque */
    }

    try {
        return document.execCommand(command, false, value);
    } catch {
        return false;
    }
};

/** Imposta il separatore di paragrafo su <p>: evita i <div> impliciti di Chrome. */
export const configureParagraphSeparator = () => {
    try {
        document.execCommand?.('defaultParagraphSeparator', false, 'p');
    } catch {
        /* non supportato: nessun impatto funzionale */
    }
};

/** Espande un range collassato alla parola sotto il cursore. */
const expandRangeToWord = (range) => {
    const { startContainer, startOffset } = range;
    if (startContainer.nodeType !== 3) return null;

    const text = startContainer.nodeValue || '';
    let start = startOffset;
    let end = startOffset;

    while (start > 0 && !WORD_BOUNDARY.test(text[start - 1])) start -= 1;
    while (end < text.length && !WORD_BOUNDARY.test(text[end])) end += 1;
    if (start === end) return null;

    const expanded = document.createRange();
    expanded.setStart(startContainer, start);
    expanded.setEnd(startContainer, end);
    return expanded;
};

/**
 * Range su cui operare: la selezione, la parola sotto il cursore oppure il blocco corrente.
 */
const resolveTargetRange = (editor) => {
    const range = getSelectionRangeWithin(editor);
    if (!range) return null;
    if (!range.collapsed) return range;

    const word = expandRangeToWord(range);
    if (word) return word;

    const block = closestBlock(range.startContainer, editor);
    if (!block || !block.textContent.trim()) return null;

    const blockRange = document.createRange();
    blockRange.selectNodeContents(block);
    return blockRange;
};

/** Applica un'operazione a ogni blocco attraversato dal range, un blocco per volta. */
const forEachBlockPortion = (editor, range, handler) => {
    const markers = withRangeMarkers(range);
    let touched = false;

    try {
        const blocks = getBlocksInRange(markers.currentRange(), editor);
        blocks.forEach((block) => {
            const portion = clampRangeToNode(markers.currentRange(), block);
            if (!portion) return;
            handler(portion, block);
            touched = true;
        });
    } finally {
        markers.release();
    }

    return touched;
};

const removeDeclarations = (root, properties) => {
    root.querySelectorAll('[style]').forEach((el) => {
        properties.forEach((property) => el.style.removeProperty(property));
        if (!el.getAttribute('style')?.trim()) el.removeAttribute('style');
    });
};

const isInlineFormatElement = (node) =>
    node?.nodeType === 1 && !isMarker(node) && node.matches?.(INLINE_FORMAT_SELECTOR);

/** Vero se il nodo contiene testo o elementi reali (i marcatori temporanei non contano). */
const hasMeaningfulContent = (node) =>
    [...node.childNodes].some((child) => {
        if (child.nodeType === 3) return child.nodeValue.length > 0;
        if (child.nodeType !== 1) return false;
        return !isMarker(child) || hasMeaningfulContent(child);
    });

/**
 * Scorpora `parent` in tre parti (prima / child / dopo) lasciando `parent` a contenere
 * il solo `child`. Serve per intervenire su un elemento che formatta piu testo di
 * quello selezionato senza toccare il resto.
 *
 * Le porzioni che conterrebbero solo marcatori vengono riversate senza wrapper:
 * altrimenti resterebbero span vuoti con lo stile vecchio.
 */
const splitAroundChild = (parent, child) => {
    const grandParent = parent.parentNode;
    if (!grandParent) return;

    const emitPart = (part, reference) => {
        if (hasMeaningfulContent(part)) {
            grandParent.insertBefore(part, reference);
            return;
        }
        while (part.firstChild) grandParent.insertBefore(part.firstChild, reference);
    };

    if (child.previousSibling) {
        const before = parent.cloneNode(false);
        while (parent.firstChild && parent.firstChild !== child) before.appendChild(parent.firstChild);
        emitPart(before, parent);
    }

    if (child.nextSibling) {
        const after = parent.cloneNode(false);
        while (child.nextSibling) after.appendChild(child.nextSibling);
        emitPart(after, parent.nextSibling);
    }
};

/**
 * Toglie dagli antenati inline di `node` le proprieta in conflitto.
 * Senza questo passaggio applicare un colore a una parola dentro uno span colorato
 * annidava gli span (il vecchio valore restava attivo sul resto dell'albero).
 */
const dissolveConflictingAncestors = (node, properties, boundary) => {
    let current = node;
    let parent = current.parentNode;

    while (parent && parent !== boundary && isInlineFormatElement(parent)) {
        const conflicts = properties.some((property) => parent.style?.getPropertyValue(property));
        const nextParent = parent.parentNode;

        if (conflicts) {
            splitAroundChild(parent, current);
            properties.forEach((property) => parent.style.removeProperty(property));
            if (!parent.getAttribute('style')?.trim()) parent.removeAttribute('style');
        }

        current = parent;
        parent = nextParent;
    }
};

/**
 * Rimuove completamente gli antenati inline di `node` (grassetto, corsivo, span,
 * link, ...) scorporandoli quando coprono anche testo non selezionato.
 * E il passaggio che rende "cancella formato" davvero totale.
 */
const dissolveInlineAncestors = (node, boundary) => {
    let parent = node.parentNode;

    while (parent && parent !== boundary && isInlineFormatElement(parent)) {
        const nextParent = parent.parentNode;
        splitAroundChild(parent, node);
        unwrapElement(parent);
        parent = nextParent;
    }
};

/**
 * Applica stili inline sostituendo i valori in conflitto gia presenti nella selezione.
 * Senza questa rimozione preventiva gli span si annidavano e il nuovo stile
 * "non sovrascriveva" quello vecchio.
 *
 * @param {HTMLElement} editor
 * @param {Record<string,string>} declarations proprieta CSS in kebab-case
 * @param {{customStyleId?: string|null, replaceCustomStyles?: boolean}} [options]
 */
export const applyInlineStyle = (editor, declarations, options = {}) => {
    const { customStyleId = null, replaceCustomStyles = false } = options;
    const range = resolveTargetRange(editor);
    if (!range) return false;

    const properties = Object.keys(declarations);

    return forEachBlockPortion(editor, range, (portion, block) => {
        const contents = portion.extractContents();

        removeDeclarations(contents, properties);
        if (replaceCustomStyles) {
            contents.querySelectorAll('[data-custom-style]').forEach((el) => {
                if (el.tagName === 'SPAN') unwrapElement(el);
                else el.removeAttribute('data-custom-style');
            });
        }
        tidyInlineWrappers(contents);

        const wrapper = document.createElement('span');
        properties.forEach((property) => wrapper.style.setProperty(property, declarations[property]));
        if (customStyleId) wrapper.setAttribute('data-custom-style', customStyleId);
        wrapper.appendChild(contents);

        portion.insertNode(wrapper);
        dissolveConflictingAncestors(wrapper, properties, block);
        if (replaceCustomStyles) dissolveCustomStyleAncestors(wrapper, block);
        tidyInlineWrappers(block);
    });
};

/** Come sopra, ma per gli antenati che portano uno stile personalizzato. */
const dissolveCustomStyleAncestors = (node, boundary) => {
    let current = node;
    let parent = current.parentNode;

    while (parent && parent !== boundary && isInlineFormatElement(parent)) {
        const nextParent = parent.parentNode;

        if (parent.hasAttribute('data-custom-style')) {
            splitAroundChild(parent, current);
            if (parent.tagName === 'SPAN') {
                unwrapElement(parent);
                parent = nextParent;
                continue;
            }
            parent.removeAttribute('data-custom-style');
        }

        current = parent;
        parent = nextParent;
    }
};

/** Rimuove specifiche proprieta CSS dalla selezione (es. azzerare il colore). */
export const removeInlineStyle = (editor, properties) => {
    const range = resolveTargetRange(editor);
    if (!range) return false;

    return forEachBlockPortion(editor, range, (portion, block) => {
        const contents = portion.extractContents();
        removeDeclarations(contents, properties);

        const holder = document.createElement('span');
        holder.appendChild(contents);
        portion.insertNode(holder);
        dissolveConflictingAncestors(holder, properties, block);
        unwrapElement(holder);
        tidyInlineWrappers(block);
    });
};

/** Toglie da un frammento ogni traccia di formattazione inline. */
const stripInlineFormatting = (fragment) => {
    fragment.querySelectorAll(INLINE_FORMAT_SELECTOR).forEach((el) => {
        if (isMarker(el)) return;
        unwrapElement(el);
    });

    fragment.querySelectorAll('*').forEach((el) => {
        if (isMarker(el)) return;
        BLOCK_FORMAT_ATTRIBUTES.forEach((attribute) => el.removeAttribute(attribute));
    });
};

/**
 * Rimuove TUTTA la formattazione dalla selezione: marcatori inline, colori, stili custom,
 * link, titoli, liste, allineamenti e attributi residui.
 */
export const clearFormatting = (editor) => {
    let range = getSelectionRangeWithin(editor);
    if (!range) return false;

    if (range.collapsed) {
        const block = closestBlock(range.startContainer, editor);
        if (!block) return false;
        range = selectNodeContents(block);
    }

    const markers = withRangeMarkers(range);

    try {
        // 1. formattazione inline dentro ogni blocco toccato
        getBlocksInRange(markers.currentRange(), editor).forEach((block) => {
            const portion = clampRangeToNode(markers.currentRange(), block);
            if (!portion) return;
            const contents = portion.extractContents();
            stripInlineFormatting(contents);

            const holder = document.createElement('span');
            holder.appendChild(contents);
            portion.insertNode(holder);
            dissolveInlineAncestors(holder, block);
            unwrapElement(holder);
        });

        // 2. liste: il toggle nativo gestisce correttamente lo scorporo degli <li>
        const selection = window.getSelection();
        const applySelection = () => {
            selection?.removeAllRanges();
            selection?.addRange(markers.currentRange());
        };

        applySelection();
        const blocksBeforeUnwrap = getBlocksInRange(markers.currentRange(), editor);
        if (blocksBeforeUnwrap.some((block) => block.closest?.('ul'))) {
            applySelection();
            execFormatCommand('insertUnorderedList');
        }
        if (getBlocksInRange(markers.currentRange(), editor).some((block) => block.closest?.('ol'))) {
            applySelection();
            execFormatCommand('insertOrderedList');
        }

        // 3. titoli, pre e citazioni tornano paragrafi
        applySelection();
        execFormatCommand('formatBlock', 'p');

        // 4. attributi di formattazione residui sui blocchi
        getBlocksInRange(markers.currentRange(), editor).forEach((block) => {
            if (block === editor) return;
            BLOCK_FORMAT_ATTRIBUTES.forEach((attribute) => block.removeAttribute(attribute));
        });

        tidyInlineWrappers(editor);
    } finally {
        markers.release();
    }

    return true;
};

/** Cambia il tipo di blocco della selezione. */
export const setBlockType = (editor, tag) => {
    execFormatCommand('formatBlock', tag);

    if (tag === 'p') {
        const range = getSelectionRangeWithin(editor);
        if (range) {
            getBlocksInRange(range, editor).forEach((block) => {
                if (block !== editor) block.removeAttribute('style');
            });
        }
    }
    return true;
};

/** Allinea i blocchi della selezione usando `text-align` (sopravvive alla sanitizzazione). */
export const setBlockAlignment = (editor, alignment) => {
    const range = getSelectionRangeWithin(editor);
    if (!range) return false;

    getBlocksInRange(range, editor).forEach((block) => {
        if (block === editor) return;
        if (alignment === 'left') block.style.removeProperty('text-align');
        else block.style.setProperty('text-align', alignment);
        if (!block.getAttribute('style')?.trim()) block.removeAttribute('style');
    });

    return true;
};

/** Inserisce un frammento DOM alla posizione corrente, posizionando il cursore dopo. */
export const insertFragmentAtSelection = (editor, fragment) => {
    const range = getSelectionRangeWithin(editor) || selectNodeContents(editor);
    range.deleteContents();

    const lastNode = fragment.lastChild;
    range.insertNode(fragment);

    if (lastNode) {
        const after = document.createRange();
        after.setStartAfter(lastNode);
        after.collapse(true);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(after);
    }

    return true;
};

/** Inserisce HTML (già sanitizzato) alla posizione corrente. */
export const insertHtmlAtSelection = (editor, html) => {
    const template = document.createElement('template');
    template.innerHTML = html;
    return insertFragmentAtSelection(editor, template.content);
};

/** Stato dei comandi inline, per evidenziare i pulsanti della toolbar. */
export const queryFormatState = () => {
    const state = { bold: false, italic: false, underline: false, strikeThrough: false, ul: false, ol: false };
    if (typeof document.queryCommandState !== 'function') return state;

    try {
        state.bold = document.queryCommandState('bold');
        state.italic = document.queryCommandState('italic');
        state.underline = document.queryCommandState('underline');
        state.strikeThrough = document.queryCommandState('strikeThrough');
        state.ul = document.queryCommandState('insertUnorderedList');
        state.ol = document.queryCommandState('insertOrderedList');
    } catch {
        /* queryCommandState non disponibile */
    }
    return state;
};

/** Blocco corrente (tag minuscolo) per il selettore di paragrafo. */
export const queryCurrentBlockTag = (editor) => {
    const range = getSelectionRangeWithin(editor);
    if (!range) return 'p';
    const block = closestBlock(range.startContainer, editor);
    if (!block || block === editor) return 'p';
    return block.tagName.toLowerCase();
};
