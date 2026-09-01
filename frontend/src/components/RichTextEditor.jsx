import React, {
    forwardRef,
    useCallback,
    useEffect,
    useImperativeHandle,
    useMemo,
    useRef,
    useState,
} from 'react';
import { Info } from 'lucide-react';
import RichTextToolbar from './richtext/RichTextToolbar';
import RichTextLinkDialog from './richtext/RichTextLinkDialog';
import { COLLAPSIBLE_TEMPLATE } from './richtext/richTextConfig';
import { ensureRichTextStyles } from '../styles/richTextStyleSheet';
import {
    escapeHtml,
    richTextHasContent,
    sanitizeHtmlForEditor,
    sanitizeHtmlForEditorString,
} from '../utils/htmlSanitizer';
import {
    applyInlineStyle,
    clearFormatting,
    configureParagraphSeparator,
    execFormatCommand,
    insertFragmentAtSelection,
    insertHtmlAtSelection,
    queryCurrentBlockTag,
    queryFormatState,
    removeInlineStyle,
    setBlockAlignment,
    setBlockType,
} from '../utils/richText/formatting';
import { closestBlock, getSelectionRangeWithin } from '../utils/richText/domRange';

/**
 * Editor rich text del progetto (contentEditable + motore di formattazione dedicato).
 *
 * Scelte di progetto:
 * - l'area editabile porta la classe `.ql-editor-view` del viewer: quello che si scrive
 *   e' esattamente quello che si vedra' in lettura;
 * - la toolbar sta su una riga a scorrimento orizzontale, con pannelli a comparsa:
 *   su smartphone lo spazio di scrittura resta sempre utilizzabile;
 * - la modalita' schermo intero e' la via rapida per scrivere testi lunghi da telefono.
 *
 * Ref imperativa: ``insertHtml(html)`` inserisce HTML alla selezione corrente.
 *
 * @param {object} props
 * @param {string} props.value HTML corrente
 * @param {(html: string) => void} props.onChange
 * @param {string} [props.editorHeightClass] Classi altezza legacy: se passate vincono sulle misure.
 * @param {boolean} [props.stickyToolbar=true] Toolbar ancorata durante lo scroll.
 * @param {number|string} [props.minHeight=180] Altezza minima dell'area di scrittura.
 * @param {number|string} [props.maxHeight='50vh'] Altezza massima prima dello scroll interno.
 * @param {boolean} [props.fillHeight=false] Occupa tutta l'altezza disponibile del contenitore flex.
 */
const RichTextEditor = forwardRef(function RichTextEditor({
    value,
    onChange,
    placeholder = 'Scrivi qui…',
    label,
    editorHeightClass,
    stickyToolbar = true,
    minHeight = 180,
    maxHeight = '50vh',
    fillHeight = false,
    ariaLabel,
}, ref) {
    ensureRichTextStyles();

    const editorRef = useRef(null);
    const lastEmittedRef = useRef(null);
    const savedRangeRef = useRef(null);

    const [isHtmlMode, setIsHtmlMode] = useState(false);
    const [isFullscreen, setIsFullscreen] = useState(false);
    const [linkDialogOpen, setLinkDialogOpen] = useState(false);
    const [linkDialogText, setLinkDialogText] = useState('');
    const [formatState, setFormatState] = useState({
        bold: false, italic: false, underline: false, strikeThrough: false, ul: false, ol: false,
    });
    const [blockTag, setBlockTag] = useState('p');
    const [alignment, setAlignment] = useState('left');
    const [hasTableContext, setHasTableContext] = useState(false);

    const isEmpty = !richTextHasContent(value);

    useEffect(() => {
        configureParagraphSeparator();
    }, []);

    /**
     * Allinea il DOM al valore esterno senza spostare il cursore quando il valore arriva da noi.
     *
     * Il contenuto viene normalizzato con le stesse regole del viewer: gli a capo salvati
     * come `\n` (contenuti storici o testo semplice) diventano <br> anche in scrittura,
     * quindi l'autore vede esattamente il risultato finale.
     */
    useEffect(() => {
        const editor = editorRef.current;
        if (!editor || isHtmlMode) return;

        const incoming = value || '';
        if (incoming === lastEmittedRef.current) return;
        if (editor.innerHTML === incoming) return;

        editor.innerHTML = sanitizeHtmlForEditorString(incoming);
        lastEmittedRef.current = incoming;
    }, [value, isHtmlMode]);

    const emitChange = useCallback(() => {
        const editor = editorRef.current;
        if (!editor) return;
        const html = editor.innerHTML;
        lastEmittedRef.current = html;
        onChange(html);
    }, [onChange]);

    const readTableContext = useCallback(() => {
        const editor = editorRef.current;
        if (!editor) return null;

        const range = getSelectionRangeWithin(editor);
        if (!range) return null;

        const node = range.startContainer;
        const element = node.nodeType === 1 ? node : node.parentElement;
        const cell = element?.closest('td, th');
        const row = element?.closest('tr');
        const table = element?.closest('table');
        if (!table || !row || !editor.contains(table)) return null;

        return { table, row, cell };
    }, []);

    const refreshSelectionState = useCallback(() => {
        const editor = editorRef.current;
        if (!editor) return;

        setFormatState(queryFormatState());
        setBlockTag(queryCurrentBlockTag(editor));
        setHasTableContext(Boolean(readTableContext()));

        const range = getSelectionRangeWithin(editor);
        if (!range) return;

        const block = closestBlock(range.startContainer, editor);
        const align = block && block !== editor
            ? (block.style?.textAlign || window.getComputedStyle(block).textAlign)
            : 'left';
        setAlignment(['center', 'right', 'justify'].includes(align) ? align : 'left');
    }, [readTableContext]);

    /** Traccia l'ultima selezione valida: serve dopo l'uso di select/color picker/dialog. */
    useEffect(() => {
        const handleSelectionChange = () => {
            const editor = editorRef.current;
            if (!editor) return;

            const range = getSelectionRangeWithin(editor);
            if (!range) return;

            savedRangeRef.current = range.cloneRange();
            refreshSelectionState();
        };

        document.addEventListener('selectionchange', handleSelectionChange);
        return () => document.removeEventListener('selectionchange', handleSelectionChange);
    }, [refreshSelectionState]);

    const restoreSelection = useCallback(() => {
        const editor = editorRef.current;
        if (!editor) return;

        const current = getSelectionRangeWithin(editor);
        if (current) return;

        const saved = savedRangeRef.current;
        const selection = window.getSelection();

        if (saved && editor.contains(saved.startContainer) && saved.startContainer.isConnected) {
            selection?.removeAllRanges();
            selection?.addRange(saved);
            return;
        }

        const fallback = document.createRange();
        fallback.selectNodeContents(editor);
        fallback.collapse(false);
        selection?.removeAllRanges();
        selection?.addRange(fallback);
    }, []);

    /** Esegue un'operazione sull'editor garantendo focus, selezione e propagazione del valore. */
    const runCommand = useCallback((operation) => {
        const editor = editorRef.current;
        if (!editor) return;

        editor.focus({ preventScroll: true });
        restoreSelection();
        operation(editor);
        emitChange();
        refreshSelectionState();
    }, [emitChange, refreshSelectionState, restoreSelection]);

    useImperativeHandle(ref, () => ({
        insertHtml: (html) => {
            if (!html) return;
            runCommand((editor) => insertHtmlAtSelection(editor, html));
        },
        focus: () => {
            editorRef.current?.focus({ preventScroll: true });
            restoreSelection();
        },
    }), [restoreSelection, runCommand]);

    const handleInput = useCallback(() => {
        emitChange();
        refreshSelectionState();
    }, [emitChange, refreshSelectionState]);

    /**
     * Incolla mantenendo la formattazione utile ma sanitizzata.
     * La versione precedente scartava tutto l'HTML (solo testo grezzo) e trasformava
     * gli a capo in `\n` letterali, che poi sparivano in visualizzazione.
     */
    const handlePaste = useCallback((event) => {
        event.preventDefault();
        const clipboard = event.clipboardData;
        if (!clipboard) return;

        const html = clipboard.getData('text/html');
        const text = clipboard.getData('text/plain');

        runCommand((editor) => {
            if (html) {
                insertFragmentAtSelection(editor, sanitizeHtmlForEditor(html));
                return;
            }
            if (!text) return;

            // Righe vuote -> nuovi paragrafi, singoli a capo -> <br>: mai `\n` grezzi nel DOM.
            const paragraphs = text
                .replace(/\r\n|\r/g, '\n')
                .split(/\n{2,}/)
                .map((block) => escapeHtml(block).replace(/\n/g, '<br>'))
                .filter(Boolean);

            if (paragraphs.length <= 1) {
                insertHtmlAtSelection(editor, paragraphs[0] || '');
                return;
            }
            insertHtmlAtSelection(editor, paragraphs.map((block) => `<p>${block}</p>`).join(''));
        });
    }, [runCommand]);

    const handleKeyDown = useCallback((event) => {
        // Tab dentro una tabella: passa alla cella successiva invece di uscire dal campo.
        if (event.key !== 'Tab') return;

        const context = readTableContext();
        if (!context?.cell) return;

        const cells = [...context.table.querySelectorAll('th, td')];
        const index = cells.indexOf(context.cell);
        const target = cells[event.shiftKey ? index - 1 : index + 1];
        if (!target) return;

        event.preventDefault();
        const range = document.createRange();
        range.selectNodeContents(target);
        range.collapse(true);
        const selection = window.getSelection();
        selection?.removeAllRanges();
        selection?.addRange(range);
    }, [readTableContext]);

    const toggleHtmlMode = useCallback(() => {
        if (!isHtmlMode) emitChange();
        lastEmittedRef.current = null;
        savedRangeRef.current = null;
        setIsHtmlMode((current) => !current);
    }, [emitChange, isHtmlMode]);

    const toggleFullscreen = useCallback(() => setIsFullscreen((current) => !current), []);

    useEffect(() => {
        if (!isFullscreen) return undefined;

        const previousOverflow = document.body.style.overflow;
        document.body.style.overflow = 'hidden';

        const handleKeyDown = (event) => {
            if (event.key === 'Escape') setIsFullscreen(false);
        };
        document.addEventListener('keydown', handleKeyDown);

        return () => {
            document.body.style.overflow = previousOverflow;
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [isFullscreen]);

    const openLinkDialog = useCallback(() => {
        const editor = editorRef.current;
        if (editor) {
            editor.focus({ preventScroll: true });
            restoreSelection();
        }
        const selectedText = window.getSelection()?.toString() || '';
        setLinkDialogText(selectedText);
        setLinkDialogOpen(true);
    }, [restoreSelection]);

    const confirmLink = useCallback(({ text, url }) => {
        setLinkDialogOpen(false);
        runCommand((editor) => {
            const anchor = document.createElement('a');
            anchor.setAttribute('href', url);
            anchor.className = 'wiki-link';
            anchor.textContent = text;

            const fragment = document.createDocumentFragment();
            fragment.appendChild(anchor);
            fragment.appendChild(document.createTextNode('\u00a0'));
            insertFragmentAtSelection(editor, fragment);
        });
    }, [runCommand]);

    const modifyTable = useCallback((operation) => {
        runCommand(() => {
            const context = readTableContext();
            if (!context) return;
            operation(context);
        });
    }, [readTableContext, runCommand]);

    const actions = useMemo(() => ({
        undo: () => runCommand(() => execFormatCommand('undo')),
        redo: () => runCommand(() => execFormatCommand('redo')),
        toggleBold: () => runCommand(() => execFormatCommand('bold')),
        toggleItalic: () => runCommand(() => execFormatCommand('italic')),
        toggleUnderline: () => runCommand(() => execFormatCommand('underline')),
        toggleStrike: () => runCommand(() => execFormatCommand('strikeThrough')),
        toggleUnorderedList: () => runCommand(() => execFormatCommand('insertUnorderedList')),
        toggleOrderedList: () => runCommand(() => execFormatCommand('insertOrderedList')),
        setBlock: (tag) => runCommand((editor) => setBlockType(editor, tag)),
        setAlign: (align) => runCommand((editor) => setBlockAlignment(editor, align)),
        setFontFamily: (family) => runCommand((editor) => (
            family
                ? applyInlineStyle(editor, { 'font-family': family })
                : removeInlineStyle(editor, ['font-family'])
        )),
        setFontSize: (size) => runCommand((editor) => (
            size
                ? applyInlineStyle(editor, { 'font-size': size })
                : removeInlineStyle(editor, ['font-size'])
        )),
        setTextColor: (color) => runCommand((editor) => (
            color
                ? applyInlineStyle(editor, { color })
                : removeInlineStyle(editor, ['color'])
        )),
        setHighlight: (color) => runCommand((editor) => (
            color
                ? applyInlineStyle(editor, { 'background-color': color, color: '#111827', 'border-radius': '2px', padding: '0 2px' })
                : removeInlineStyle(editor, ['background-color', 'border-radius', 'padding'])
        )),
        applyCustomStyle: (style) => runCommand((editor) => applyInlineStyle(
            editor,
            style.declarations,
            { customStyleId: style.id, replaceCustomStyles: true }
        )),
        clearFormatting: () => runCommand((editor) => clearFormatting(editor)),
        insertHorizontalRule: () => runCommand((editor) => insertHtmlAtSelection(editor, '<hr><p><br></p>')),
        insertCollapsible: () => runCommand((editor) => insertHtmlAtSelection(editor, COLLAPSIBLE_TEMPLATE)),
        insertTable: (preset) => runCommand((editor) => insertHtmlAtSelection(editor, preset.html)),
        insertEmoji: (emoji) => runCommand(() => execFormatCommand('insertText', emoji)),
        openLinkDialog,
        toggleHtmlMode,
        toggleFullscreen,
        addRow: () => modifyTable(({ row }) => {
            const newRow = row.cloneNode(true);
            [...newRow.cells].forEach((cell) => {
                cell.innerHTML = '<br>';
            });
            row.parentNode?.insertBefore(newRow, row.nextSibling);
        }),
        removeRow: () => modifyTable(({ table, row }) => {
            if (table.querySelectorAll('tr').length <= 1) return;
            row.remove();
        }),
        addColumn: () => modifyTable(({ table, cell }) => {
            if (!cell) return;
            const columnIndex = cell.cellIndex;
            table.querySelectorAll('tr').forEach((currentRow) => {
                const reference = currentRow.cells[columnIndex] || currentRow.cells[currentRow.cells.length - 1];
                const tagName = reference?.tagName === 'TH' ? 'th' : 'td';
                const newCell = document.createElement(tagName);
                newCell.innerHTML = tagName === 'th' ? `Intestazione ${columnIndex + 2}` : '<br>';
                currentRow.insertBefore(newCell, currentRow.cells[columnIndex + 1] || null);
            });
        }),
        removeColumn: () => modifyTable(({ table, cell }) => {
            if (!cell) return;
            const columnIndex = cell.cellIndex;
            const firstRow = table.querySelector('tr');
            if (!firstRow || firstRow.cells.length <= 1) return;
            table.querySelectorAll('tr').forEach((currentRow) => {
                if (currentRow.cells[columnIndex]) currentRow.deleteCell(columnIndex);
            });
        }),
    }), [modifyTable, openLinkDialog, runCommand, toggleFullscreen, toggleHtmlMode]);

    const shellClassName = isFullscreen
        ? 'fixed inset-0 z-[60] flex flex-col bg-gray-900 border-0'
        : [
            'relative flex flex-col rounded-lg border border-gray-600 bg-gray-800',
            'focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-shadow',
            fillHeight ? 'flex-1 min-h-0' : '',
        ].filter(Boolean).join(' ');

    const editorAreaClassName = [
        'ql-editor-view kor-rich-editor px-3 py-2.5 text-sm text-gray-200 overflow-y-auto custom-scrollbar',
        isFullscreen ? 'flex-1 min-h-0' : '',
        !isFullscreen && fillHeight ? 'flex-1' : '',
        !isFullscreen && editorHeightClass ? editorHeightClass : '',
    ].filter(Boolean).join(' ');

    /**
     * In modalita `fillHeight` si mantiene comunque `min-height`: il contenitore padre
     * puo avere altezza automatica e senza minimo l'area di scrittura collasserebbe.
     */
    const editorAreaStyle = useMemo(() => {
        if (isFullscreen || editorHeightClass) return undefined;
        if (fillHeight) return { minHeight };
        return { minHeight, maxHeight };
    }, [editorHeightClass, fillHeight, isFullscreen, maxHeight, minHeight]);

    return (
        <div className={`flex flex-col gap-1 w-full ${fillHeight ? 'min-h-0 flex-1' : ''}`}>
            {label && !isFullscreen ? (
                <label className="text-sm font-medium text-gray-300 ml-1">{label}</label>
            ) : null}

            <div className={shellClassName} style={isFullscreen ? { height: '100dvh' } : undefined}>
                {isFullscreen ? (
                    <div className="flex items-center justify-between gap-3 px-3 py-2 border-b border-gray-700 bg-gray-900">
                        <span className="text-sm font-semibold text-gray-200 truncate">
                            {label || 'Composizione testo'}
                        </span>
                        <button
                            type="button"
                            onClick={toggleFullscreen}
                            className="px-3 py-1.5 rounded-md bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-500 transition-colors"
                        >
                            Fatto
                        </button>
                    </div>
                ) : null}

                <div className={stickyToolbar && !isFullscreen ? 'sticky top-0 z-30 rounded-t-lg' : ''}>
                    <RichTextToolbar
                        actions={actions}
                        formatState={formatState}
                        blockTag={blockTag}
                        alignment={alignment}
                        isHtmlMode={isHtmlMode}
                        isFullscreen={isFullscreen}
                        hasTableContext={hasTableContext}
                    />
                </div>

                {isHtmlMode ? (
                    <>
                        <textarea
                            value={value || ''}
                            onChange={(event) => onChange(event.target.value)}
                            className={[
                                'w-full px-3 py-2.5 text-xs font-mono text-gray-200 bg-gray-900 outline-none overflow-y-auto custom-scrollbar resize-none',
                                isFullscreen || fillHeight ? 'flex-1 min-h-0' : '',
                                !isFullscreen && editorHeightClass ? editorHeightClass : '',
                            ].filter(Boolean).join(' ')}
                            style={editorAreaStyle}
                            placeholder="<p>HTML del contenuto…</p>"
                            spellCheck={false}
                        />
                        <div className="flex items-start gap-2 px-3 py-2 border-t border-gray-700 bg-gray-900/70 text-[11px] text-gray-400 rounded-b-lg">
                            <Info size={13} className="mt-0.5 shrink-0" />
                            <span>
                                Modalita codice: i tag non ammessi (script, iframe, attributi <code>on*</code>)
                                vengono rimossi in visualizzazione.
                            </span>
                        </div>
                    </>
                ) : (
                    <div
                        ref={editorRef}
                        contentEditable
                        suppressContentEditableWarning
                        role="textbox"
                        aria-multiline="true"
                        aria-label={ariaLabel || label || 'Editor di testo'}
                        onInput={handleInput}
                        onPaste={handlePaste}
                        onKeyDown={handleKeyDown}
                        onBlur={emitChange}
                        className={editorAreaClassName}
                        style={editorAreaStyle}
                        data-placeholder={placeholder}
                        data-empty={isEmpty ? 'true' : 'false'}
                        spellCheck
                        autoCorrect="on"
                        autoCapitalize="sentences"
                    />
                )}
            </div>

            <RichTextLinkDialog
                open={linkDialogOpen}
                initialText={linkDialogText}
                onCancel={() => setLinkDialogOpen(false)}
                onConfirm={confirmLink}
            />
        </div>
    );
});

export default RichTextEditor;
