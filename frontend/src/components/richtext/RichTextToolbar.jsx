import React, { useCallback, useEffect, useLayoutEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import {
    AlignCenter, AlignJustify, AlignLeft, AlignRight,
    Bold, ChevronDown, Code2, Columns3, Eraser, Highlighter, Italic,
    Link2, List, ListOrdered, Maximize2, Minimize2, Minus, PanelTopClose,
    Palette, Plus, Redo2, Rows3, Smile, Strikethrough, Table2, Type,
    Underline, Undo2,
} from 'lucide-react';
import {
    CUSTOM_STYLES, EMOJI_GROUPS, FONT_FAMILIES, FONT_SIZES,
    HIGHLIGHT_COLORS, HTML_BLOCKS, TABLE_PRESETS, TEXT_COLORS,
} from './richTextConfig';

/**
 * Toolbar del RichTextEditor.
 *
 * Vincolo di progetto: su smartphone la vecchia toolbar andava a capo su 6-7 righe
 * e mangiava tutto lo spazio di scrittura. Qui i controlli stanno su UNA riga a
 * scorrimento orizzontale (altezza costante) e i gruppi avanzati si aprono in un
 * pannello a tutta larghezza sotto la toolbar, cosi nessuna funzione viene perduta.
 */

const PANEL_BLOCK = 'block';
const PANEL_TEXT = 'text';
const PANEL_INSERT = 'insert';
const PANEL_TABLE = 'table';
const PANEL_EMOJI = 'emoji';

/** Impedisce che il click sulla toolbar rubi il focus (e quindi la selezione) all'editor. */
const keepSelection = (event) => event.preventDefault();

const ToolButton = ({ icon, label, onClick, active = false, disabled = false, className = '' }) => {
    const Icon = icon;
    return (
        <button
            type="button"
            onMouseDown={keepSelection}
            onClick={onClick}
            disabled={disabled}
            title={label}
            aria-label={label}
            aria-pressed={active}
            className={`shrink-0 inline-flex items-center justify-center rounded-md h-9 min-w-9 px-2 transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                active ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-600 hover:text-white'
            } ${className}`}
        >
            <Icon size={17} />
        </button>
    );
};

const ToolToggle = ({ icon, label, text, onClick, open, className = '' }) => {
    const Icon = icon;
    return (
        <button
            type="button"
            onMouseDown={keepSelection}
            onClick={onClick}
            title={label}
            aria-label={label}
            aria-expanded={open}
            className={`shrink-0 inline-flex items-center gap-1 rounded-md h-9 px-2 transition-colors ${
                open ? 'bg-indigo-600 text-white' : 'text-gray-300 hover:bg-gray-600 hover:text-white'
            } ${className}`}
        >
            <Icon size={17} />
            {text ? <span className="text-xs font-medium max-w-24 truncate">{text}</span> : null}
            <ChevronDown size={13} className="opacity-70" />
        </button>
    );
};

const Separator = () => <span className="shrink-0 w-px h-6 bg-gray-600/80 mx-0.5" aria-hidden="true" />;

const PanelSection = ({ title, children }) => (
    <div className="space-y-1.5">
        <div className="text-[10px] font-bold uppercase tracking-widest text-gray-400">{title}</div>
        {children}
    </div>
);

const PanelChip = ({ children, onClick, active = false, title }) => (
    <button
        type="button"
        onMouseDown={keepSelection}
        onClick={onClick}
        title={title}
        className={`px-2.5 py-1.5 rounded-md text-xs font-medium border transition-colors ${
            active
                ? 'bg-indigo-600 border-indigo-400 text-white'
                : 'bg-gray-800 border-gray-600 text-gray-200 hover:bg-gray-700 hover:border-gray-500'
        }`}
    >
        {children}
    </button>
);

const ColorSwatches = ({ colors, onPick, label }) => (
    <div className="flex flex-wrap gap-1.5" role="group" aria-label={label}>
        {colors.map((color) => (
            <button
                key={color.value || 'reset'}
                type="button"
                onMouseDown={keepSelection}
                onClick={() => onPick(color.value)}
                title={color.label}
                aria-label={color.label}
                className="w-7 h-7 rounded-md border border-gray-500 hover:scale-110 transition-transform flex items-center justify-center"
                style={color.value ? { backgroundColor: color.value } : undefined}
            >
                {!color.value ? <Eraser size={13} className="text-gray-300" /> : null}
            </button>
        ))}
    </div>
);

const RichTextToolbar = ({
    actions,
    formatState,
    blockTag,
    alignment,
    isHtmlMode,
    isFullscreen,
    hasTableContext,
}) => {
    const [openPanel, setOpenPanel] = useState(null);
    const [emojiGroupId, setEmojiGroupId] = useState(EMOJI_GROUPS[0].id);
    const [panelPosition, setPanelPosition] = useState(null);
    const rootRef = useRef(null);
    const panelRef = useRef(null);

    const togglePanel = useCallback((panel) => {
        setOpenPanel((current) => (current === panel ? null : panel));
    }, []);

    const closePanel = useCallback(() => setOpenPanel(null), []);

    /**
     * I pannelli vivono in un portale su document.body: molti contenitori che ospitano
     * l'editor hanno `overflow-hidden` e li ritaglierebbero.
     */
    const updatePanelPosition = useCallback(() => {
        const root = rootRef.current;
        if (!root) return;

        const rect = root.getBoundingClientRect();
        const spaceBelow = window.innerHeight - rect.bottom;
        const maxHeight = Math.max(180, Math.min(window.innerHeight * 0.45, Math.max(spaceBelow, rect.top) - 12));
        const openUpwards = spaceBelow < maxHeight && rect.top > spaceBelow;

        setPanelPosition({
            left: rect.left,
            width: rect.width,
            maxHeight,
            ...(openUpwards ? { bottom: window.innerHeight - rect.top } : { top: rect.bottom }),
        });
    }, []);

    useLayoutEffect(() => {
        if (!openPanel) {
            setPanelPosition(null);
            return undefined;
        }

        updatePanelPosition();
        window.addEventListener('resize', updatePanelPosition);
        window.addEventListener('scroll', updatePanelPosition, true);
        return () => {
            window.removeEventListener('resize', updatePanelPosition);
            window.removeEventListener('scroll', updatePanelPosition, true);
        };
    }, [openPanel, updatePanelPosition]);

    useEffect(() => {
        if (!openPanel) return undefined;

        const handlePointerDown = (event) => {
            const insideToolbar = rootRef.current?.contains(event.target);
            const insidePanel = panelRef.current?.contains(event.target);
            if (!insideToolbar && !insidePanel) closePanel();
        };
        const handleKeyDown = (event) => {
            if (event.key === 'Escape') closePanel();
        };

        document.addEventListener('pointerdown', handlePointerDown, true);
        document.addEventListener('keydown', handleKeyDown);
        return () => {
            document.removeEventListener('pointerdown', handlePointerDown, true);
            document.removeEventListener('keydown', handleKeyDown);
        };
    }, [openPanel, closePanel]);

    useEffect(() => {
        if (isHtmlMode) setOpenPanel(null);
    }, [isHtmlMode]);

    /** Esegue un'azione e chiude il pannello (l'emoji picker resta aperto per inserimenti multipli). */
    const run = (action, ...args) => {
        action?.(...args);
        closePanel();
    };

    const currentBlockLabel = HTML_BLOCKS.find((block) => block.value === blockTag)?.label || 'Paragrafo';
    const activeEmojiGroup = EMOJI_GROUPS.find((group) => group.id === emojiGroupId) || EMOJI_GROUPS[0];

    return (
        <div ref={rootRef} className="relative bg-gray-700 border-b border-gray-600 rounded-t-lg">
            <div
                className="flex items-center gap-0.5 p-1.5 flex-nowrap overflow-x-auto lg:flex-wrap lg:overflow-visible kor-rich-toolbar-scroll"
                role="toolbar"
                aria-label="Formattazione testo"
            >
                <ToolButton icon={Undo2} label="Annulla" onClick={actions.undo} />
                <ToolButton icon={Redo2} label="Ripeti" onClick={actions.redo} />

                {!isHtmlMode && (
                    <>
                        <Separator />

                        <ToolToggle
                            icon={Type}
                            label="Tipo di paragrafo"
                            text={currentBlockLabel}
                            open={openPanel === PANEL_BLOCK}
                            onClick={() => togglePanel(PANEL_BLOCK)}
                        />

                        <Separator />

                        <ToolButton icon={Bold} label="Grassetto" onClick={actions.toggleBold} active={formatState.bold} />
                        <ToolButton icon={Italic} label="Corsivo" onClick={actions.toggleItalic} active={formatState.italic} />
                        <ToolButton icon={Underline} label="Sottolineato" onClick={actions.toggleUnderline} active={formatState.underline} />
                        <ToolButton icon={Strikethrough} label="Barrato" onClick={actions.toggleStrike} active={formatState.strikeThrough} />

                        <Separator />

                        <ToolButton icon={List} label="Elenco puntato" onClick={actions.toggleUnorderedList} active={formatState.ul} />
                        <ToolButton icon={ListOrdered} label="Elenco numerato" onClick={actions.toggleOrderedList} active={formatState.ol} />

                        <Separator />

                        <ToolButton icon={Link2} label="Inserisci link" onClick={actions.openLinkDialog} />
                        <ToolToggle
                            icon={Palette}
                            label="Colori, font e stili"
                            open={openPanel === PANEL_TEXT}
                            onClick={() => togglePanel(PANEL_TEXT)}
                        />
                        <ToolToggle
                            icon={Plus}
                            label="Inserisci elemento"
                            open={openPanel === PANEL_INSERT}
                            onClick={() => togglePanel(PANEL_INSERT)}
                        />
                        <ToolToggle
                            icon={Table2}
                            label="Tabelle"
                            open={openPanel === PANEL_TABLE}
                            onClick={() => togglePanel(PANEL_TABLE)}
                        />

                        <Separator />

                        <ToolButton
                            icon={Eraser}
                            label="Rimuovi tutta la formattazione (anche titoli, elenchi e link)"
                            onClick={actions.clearFormatting}
                        />
                    </>
                )}

                <span className="shrink-0 flex-1 min-w-1" aria-hidden="true" />

                <ToolButton
                    icon={Code2}
                    label={isHtmlMode ? 'Torna alla modalita visuale' : 'Modifica codice HTML'}
                    onClick={actions.toggleHtmlMode}
                    active={isHtmlMode}
                />
                <ToolButton
                    icon={isFullscreen ? Minimize2 : Maximize2}
                    label={isFullscreen ? 'Riduci' : 'Schermo intero'}
                    onClick={actions.toggleFullscreen}
                    active={isFullscreen}
                />
            </div>

            {openPanel && panelPosition && createPortal(
                <div
                    ref={panelRef}
                    style={{ position: 'fixed', ...panelPosition }}
                    className="z-[75] overflow-y-auto rounded-lg border border-gray-600 bg-gray-800 p-3 shadow-2xl shadow-black/60 space-y-3 custom-scrollbar"
                >
                    {openPanel === PANEL_BLOCK && (
                        <>
                            <PanelSection title="Tipo di paragrafo">
                                <div className="flex flex-wrap gap-1.5">
                                    {HTML_BLOCKS.map((block) => (
                                        <PanelChip
                                            key={block.value}
                                            active={blockTag === block.value}
                                            onClick={() => run(actions.setBlock, block.value)}
                                        >
                                            {block.label}
                                        </PanelChip>
                                    ))}
                                </div>
                            </PanelSection>

                            <PanelSection title="Allineamento">
                                <div className="flex gap-1">
                                    <ToolButton icon={AlignLeft} label="Allinea a sinistra" active={alignment === 'left'} onClick={() => run(actions.setAlign, 'left')} />
                                    <ToolButton icon={AlignCenter} label="Centra" active={alignment === 'center'} onClick={() => run(actions.setAlign, 'center')} />
                                    <ToolButton icon={AlignRight} label="Allinea a destra" active={alignment === 'right'} onClick={() => run(actions.setAlign, 'right')} />
                                    <ToolButton icon={AlignJustify} label="Giustifica" active={alignment === 'justify'} onClick={() => run(actions.setAlign, 'justify')} />
                                </div>
                            </PanelSection>
                        </>
                    )}

                    {openPanel === PANEL_TEXT && (
                        <>
                            <div className="grid gap-3 sm:grid-cols-2">
                                <PanelSection title="Font">
                                    <select
                                        className="w-full bg-gray-900 border border-gray-600 text-gray-100 text-xs rounded-md px-2 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                        defaultValue=""
                                        onChange={(event) => {
                                            const { value } = event.target;
                                            event.target.value = '';
                                            run(actions.setFontFamily, value);
                                        }}
                                    >
                                        <option value="" disabled>Scegli un font…</option>
                                        {FONT_FAMILIES.map((font) => (
                                            <option key={font.value || 'default'} value={font.value}>{font.label}</option>
                                        ))}
                                    </select>
                                </PanelSection>

                                <PanelSection title="Dimensione">
                                    <select
                                        className="w-full bg-gray-900 border border-gray-600 text-gray-100 text-xs rounded-md px-2 py-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                                        defaultValue=""
                                        onChange={(event) => {
                                            const { value } = event.target;
                                            event.target.value = '';
                                            run(actions.setFontSize, value);
                                        }}
                                    >
                                        <option value="" disabled>Scegli una dimensione…</option>
                                        {FONT_SIZES.map((size) => (
                                            <option key={size.value || 'default'} value={size.value}>{size.label}</option>
                                        ))}
                                    </select>
                                </PanelSection>
                            </div>

                            <PanelSection title="Colore testo">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <ColorSwatches colors={TEXT_COLORS} onPick={(value) => run(actions.setTextColor, value)} label="Colore testo" />
                                    <label className="inline-flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer px-2 py-1.5 rounded-md border border-gray-600 bg-gray-900 hover:border-gray-500">
                                        <Palette size={14} />
                                        Personalizzato
                                        <input
                                            type="color"
                                            className="w-5 h-5 bg-transparent border-0 p-0 cursor-pointer"
                                            onChange={(event) => run(actions.setTextColor, event.target.value)}
                                        />
                                    </label>
                                </div>
                            </PanelSection>

                            <PanelSection title="Evidenziazione">
                                <div className="flex items-center gap-2 flex-wrap">
                                    <ColorSwatches colors={HIGHLIGHT_COLORS} onPick={(value) => run(actions.setHighlight, value)} label="Evidenziazione" />
                                    <span className="inline-flex items-center gap-1 text-[11px] text-gray-400">
                                        <Highlighter size={13} /> applicata alla selezione
                                    </span>
                                </div>
                            </PanelSection>

                            <PanelSection title="Stili predefiniti">
                                <div className="flex flex-wrap gap-1.5">
                                    {CUSTOM_STYLES.map((style) => (
                                        <PanelChip key={style.id} onClick={() => run(actions.applyCustomStyle, style)}>
                                            {style.label}
                                        </PanelChip>
                                    ))}
                                </div>
                            </PanelSection>
                        </>
                    )}

                    {openPanel === PANEL_INSERT && (
                        <>
                            <PanelSection title="Elementi">
                                <div className="flex flex-wrap gap-1.5">
                                    <PanelChip onClick={() => run(actions.insertHorizontalRule)} title="Linea di separazione">
                                        <span className="inline-flex items-center gap-1.5"><Minus size={14} /> Separatore</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => run(actions.insertCollapsible)} title="Sezione richiudibile">
                                        <span className="inline-flex items-center gap-1.5"><PanelTopClose size={14} /> Sezione richiudibile</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => run(actions.openLinkDialog)} title="Link a pagina wiki o URL">
                                        <span className="inline-flex items-center gap-1.5"><Link2 size={14} /> Link</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => setOpenPanel(PANEL_EMOJI)} title="Emoji">
                                        <span className="inline-flex items-center gap-1.5"><Smile size={14} /> Emoji</span>
                                    </PanelChip>
                                </div>
                            </PanelSection>

                            <PanelSection title="Tabelle">
                                <div className="flex flex-wrap gap-1.5">
                                    {TABLE_PRESETS.map((preset) => (
                                        <PanelChip key={preset.id} onClick={() => run(actions.insertTable, preset)}>
                                            {preset.label}
                                        </PanelChip>
                                    ))}
                                </div>
                            </PanelSection>
                        </>
                    )}

                    {openPanel === PANEL_TABLE && (
                        <PanelSection title="Modifica tabella">
                            {hasTableContext ? (
                                <div className="flex flex-wrap gap-1.5">
                                    <PanelChip onClick={() => run(actions.addRow)}>
                                        <span className="inline-flex items-center gap-1.5"><Rows3 size={14} /> Aggiungi riga</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => run(actions.removeRow)}>
                                        <span className="inline-flex items-center gap-1.5"><Rows3 size={14} /> Rimuovi riga</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => run(actions.addColumn)}>
                                        <span className="inline-flex items-center gap-1.5"><Columns3 size={14} /> Aggiungi colonna</span>
                                    </PanelChip>
                                    <PanelChip onClick={() => run(actions.removeColumn)}>
                                        <span className="inline-flex items-center gap-1.5"><Columns3 size={14} /> Rimuovi colonna</span>
                                    </PanelChip>
                                </div>
                            ) : (
                                <p className="text-xs text-gray-400">
                                    Posiziona il cursore in una cella per modificare righe e colonne, oppure inserisci
                                    una nuova tabella dal pannello <strong className="text-gray-200">Inserisci</strong>.
                                </p>
                            )}
                        </PanelSection>
                    )}

                    {openPanel === PANEL_EMOJI && (
                        <PanelSection title="Emoji">
                            <div className="flex flex-wrap gap-1 mb-2">
                                {EMOJI_GROUPS.map((group) => (
                                    <PanelChip
                                        key={group.id}
                                        active={group.id === emojiGroupId}
                                        onClick={() => setEmojiGroupId(group.id)}
                                    >
                                        {group.label}
                                    </PanelChip>
                                ))}
                            </div>
                            <div className="grid grid-cols-8 sm:grid-cols-12 gap-1">
                                {activeEmojiGroup.emojis.map((emoji, index) => (
                                    <button
                                        key={`${activeEmojiGroup.id}-${index}`}
                                        type="button"
                                        onMouseDown={keepSelection}
                                        onClick={() => actions.insertEmoji(emoji)}
                                        title={emoji}
                                        className="text-xl rounded-md p-1.5 hover:bg-gray-700 transition-colors min-h-9"
                                    >
                                        {emoji}
                                    </button>
                                ))}
                            </div>
                        </PanelSection>
                    )}
                </div>,
                document.body
            )}
        </div>
    );
};

export default RichTextToolbar;
