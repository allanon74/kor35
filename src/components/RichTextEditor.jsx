import React, { useRef, useEffect, useState } from 'react';
import { 
    Bold, Italic, Underline, 
    List, ListOrdered, 
    AlignLeft, AlignCenter,
    Trash2, Paintbrush, Type, Heading, FileText,
    Minus, Smile, Link as LinkIcon, Search,
    PanelTopClose
} from 'lucide-react';
import { getWikiMenu } from '../api';

// ============================================
// CONFIGURAZIONE STILI PERSONALIZZATI
// ============================================

// Stile di visualizzazione di default per tutti gli elementi
const DEFAULT_EDITOR_STYLE = {
    fontFamily: 'Inter, system-ui, sans-serif',
    fontSize: '14px',
    lineHeight: '1.6',
    color: '#e5e7eb'
};

// Paragrafi HTML standard
const HTML_BLOCKS = [
    { value: 'p', label: 'Paragrafo', tag: 'p' },
    { value: 'h1', label: 'Titolo H1', tag: 'h1' },
    { value: 'h2', label: 'Titolo H2', tag: 'h2' },
    { value: 'h3', label: 'Titolo H3', tag: 'h3' },
    { value: 'h4', label: 'Titolo H4', tag: 'h4' },
    { value: 'h5', label: 'Titolo H5', tag: 'h5' },
    { value: 'h6', label: 'Titolo H6', tag: 'h6' },
    { value: 'div', label: 'Blocco Div', tag: 'div' },
    { value: 'pre', label: 'Preformattato', tag: 'pre' }
];

// Font disponibili
const FONT_FAMILIES = [
    { value: 'Inter, system-ui, sans-serif', label: 'Inter (Default)' },
    { value: 'Arial, sans-serif', label: 'Arial' },
    { value: 'Georgia, serif', label: 'Georgia' },
    { value: 'Times New Roman, serif', label: 'Times New Roman' },
    { value: 'Courier New, monospace', label: 'Courier New' },
    { value: 'Verdana, sans-serif', label: 'Verdana' },
    { value: 'Trebuchet MS, sans-serif', label: 'Trebuchet MS' },
    { value: 'Comic Sans MS, cursive', label: 'Comic Sans MS' },
    { value: 'Impact, sans-serif', label: 'Impact' }
];

// Emoji organizzate per Wiki Fantasy/GdR
const COMMON_EMOJIS = [
    // === INDICATORI E SIMBOLI DI ENFASI ===
    '📌', '📍', '🔖', '⚠️', '❗', '❕', '‼️', '⁉️', '❓', '❔',
    '💡', '🔆', '💫', '✨', '⭐', '🌟', '💥', '💢', '🔥', '⚡',
    '☄️', '💧', '💦', '💨', '🌪️', '❄️', '☃️', '🌊', '🌈', '☀️',
    
    // === SIMBOLI FANTASY E COMBATTIMENTO ===
    '⚔️', '🗡️', '🔪', '🏹', '🛡️', '🪓', '⚒️', '🔨', '⛏️', '🪃',
    '🎯', '💣', '🧨', '🔮', '🪄', '✨', '💎', '💠', '🔷', '🔶',
    '🔹', '🔸', '🔺', '🔻', '🔘', '⚪', '⚫', '🟤', '🟣', '🟢',
    
    // === CREATURE FANTASY ===
    '🐉', '🐲', '🦎', '🐍', '🦂', '🕷️', '🦇', '🦅', '🦉', '🦌',
    '🐺', '🦊', '🐗', '🐻', '🦁', '🐯', '🦈', '🐙', '🦑', '🐘',
    '🦏', '🦒', '🦘', '🦥', '🦦', '🦨', '🦡', '🐾', '🦴', '☠️',
    
    // === CORONE, NOBILTÀ E POTERE ===
    '👑', '💍', '💰', '💴', '💵', '💶', '💷', '🪙', '🏆', '🥇',
    '🥈', '🥉', '🎖️', '🏅', '🎗️', '🔱', '⚜️', '🔰', '🛡️', '🗝️',
    
    // === LUOGHI E EDIFICI ===
    '🏰', '🏯', '🗼', '🗿', '🏛️', '⛪', '🕌', '🛕', '🗻', '⛰️',
    '🏔️', '🌋', '🏕️', '⛺', '🏞️', '🏜️', '🏝️', '🌍', '🌎', '🌏',
    '🗺️', '🧭', '📍', '🚩', '🏴', '🏳️', '🏁', '⛳', '🕳️', '🌌',
    
    // === MAGIA E ALCHIMIA ===
    '🔮', '🪄', '✨', '💫', '⚗️', '🧪', '🧬', '🧫', '🩸', '💉',
    '🧿', '📿', '🔗', '⛓️', '🕯️', '💀', '⚰️', '🪦', '🌙', '☪️',
    '☸️', '✝️', '☦️', '☯️', '🕎', '🔯', '♈', '♉', '♊', '♋',
    
    // === LIBRI, SCROLL E CONOSCENZA ===
    '📜', '📋', '📃', '📄', '📰', '🗞️', '📑', '🔖', '📚', '📖',
    '📕', '📗', '📘', '📙', '📓', '📔', '📒', '✍️', '✒️', '🖊️',
    '🖋️', '🖌️', '🖍️', '📝', '💼', '🗂️', '📂', '📁', '🗃️', '🗄️',
    
    // === TEMPO E METEO ===
    '⏰', '⏱️', '⏲️', '⌛', '⏳', '🕐', '🕑', '🕒', '🌅', '🌄',
    '🌠', '🌌', '🌃', '🌆', '🌇', '🌁', '☁️', '⛈️', '🌩️', '⚡',
    
    // === EMOZIONI BASE (ridotte) ===
    '😀', '😃', '😄', '😊', '😎', '🤔', '😮', '😱', '😡', '😈',
    '👿', '💀', '☠️', '👹', '👺', '🤡', '👻', '👽', '🤖', '💩',
    
    // === FRECCE E DIREZIONI ===
    '⬆️', '⬇️', '⬅️', '➡️', '↗️', '↘️', '↙️', '↖️', '↕️', '↔️',
    '↩️', '↪️', '⤴️', '⤵️', '🔄', '🔃', '🔁', '🔂', '▶️', '◀️',
    '⏸️', '⏹️', '⏺️', '⏏️', '🔼', '🔽', '⏫', '⏬', '⏮️', '⏭️',
    
    // === SIMBOLI SPECIALI ===
    '✅', '❌', '⭕', '🚫', '💯', '♾️', '🆕', '🆙', '🆒', '🆓',
    '🆗', '🔞', '⛔', '📵', '🚷', '🚯', '🚱', '🚳', '🚭', '🔇'
];

// Stili personalizzati con definizione CSS completa
const CUSTOM_STYLES = [
    {
        id: 'title-general',
        label: '📋 Titolo Generale',
        css: {
            fontSize: '1.75em',
            fontWeight: '700',
            color: '#818cf8',
            borderBottom: '3px solid #6366f1',
            paddingBottom: '8px',
            marginTop: '12px',
            marginBottom: '12px',
            display: 'block',
            letterSpacing: '0.5px'
        }
    },
    {
        id: 'title-section',
        label: '📑 Titolo Sezione',
        css: {
            fontSize: '1.25em',
            fontWeight: '600',
            color: '#a5b4fc',
            borderLeft: '4px solid #6366f1',
            paddingLeft: '12px',
            marginTop: '10px',
            marginBottom: '8px',
            display: 'block',
            textTransform: 'uppercase',
            letterSpacing: '1px'
        }
    },
    {
        id: 'title-subsection',
        label: '📑 Titolo Sottosezione',
        css: {
            fontSize: '1.15em',
            fontWeight: '500',
            color: '#a5b4fc',
            // borderLeft: '4px solid #6366f1',
            paddingLeft: '12px',
            marginTop: '8px',
            marginBottom: '6px',
            display: 'block',
            textTransform: 'uppercase',
            letterSpacing: '1px'
        }
    },
    {
        id: 'highlight-yellow',
        label: '📌 Evidenziato Giallo',
        css: {
            backgroundColor: '#fef3c7',
            color: '#92400e',
            padding: '2px 6px',
            borderRadius: '3px',
            fontWeight: '500'
        }
    },
    {
        id: 'highlight-blue',
        label: '💙 Evidenziato Blu',
        css: {
            backgroundColor: '#dbeafe',
            color: '#1e40af',
            padding: '2px 6px',
            borderRadius: '3px',
            fontWeight: '500'
        }
    },
    {
        id: 'highlight-green',
        label: '✅ Evidenziato Verde',
        css: {
            backgroundColor: '#d1fae5',
            color: '#065f46',
            padding: '2px 6px',
            borderRadius: '3px',
            fontWeight: '500'
        }
    },
    {
        id: 'highlight-red',
        label: '🔴 Evidenziato Rosso',
        css: {
            backgroundColor: '#fee2e2',
            color: '#991b1b',
            padding: '2px 6px',
            borderRadius: '3px',
            fontWeight: '500'
        }
    },
    {
        id: 'code-inline',
        label: '💻 Codice Inline',
        css: {
            backgroundColor: '#1f2937',
            color: '#10b981',
            padding: '2px 6px',
            borderRadius: '4px',
            fontFamily: 'Courier New, monospace',
            fontSize: '0.9em',
            border: '1px solid #374151'
        }
    },
    {
        id: 'quote',
        label: '💬 Citazione',
        css: {
            borderLeft: '4px solid #6366f1',
            paddingLeft: '12px',
            fontStyle: 'italic',
            color: '#d1d5db',
            marginLeft: '8px'
        }
    },
    {
        id: 'warning',
        label: '⚠️ Avviso',
        css: {
            backgroundColor: '#fef3c7',
            color: '#92400e',
            padding: '8px 12px',
            borderRadius: '6px',
            borderLeft: '4px solid #f59e0b',
            fontWeight: '500'
        }
    },
    {
        id: 'success',
        label: '✨ Successo',
        css: {
            backgroundColor: '#d1fae5',
            color: '#065f46',
            padding: '8px 12px',
            borderRadius: '6px',
            borderLeft: '4px solid #10b981',
            fontWeight: '500'
        }
    }
];

const ToolbarButton = ({ icon: Icon, onClick, active, title }) => (
    <button
        type="button"
        onClick={onClick}
        title={title}
        className={`p-1.5 rounded hover:bg-gray-600 transition-colors ${
            active ? 'bg-indigo-600 text-white' : 'text-gray-300'
        }`}
    >
        <Icon size={16} />
    </button>
);

const SmallActionButton = ({ label, onClick, title, className = '' }) => (
    <button
        type="button"
        onClick={onClick}
        title={title}
        className={`px-2 py-1 text-xs rounded bg-gray-800 border border-gray-600 text-gray-200 hover:bg-gray-700 hover:border-gray-500 transition-colors ${className}`}
    >
        {label}
    </button>
);

const RichTextEditor = ({ value, onChange, placeholder, label }) => {
    const editorRef = useRef(null);
    const colorInputRef = useRef(null);
    const [currentBlockType, setCurrentBlockType] = useState('p');
    const [currentFont, setCurrentFont] = useState(DEFAULT_EDITOR_STYLE.fontFamily);
    const [showEmojiPicker, setShowEmojiPicker] = useState(false);
    const [showLinkModal, setShowLinkModal] = useState(false);
    const [linkText, setLinkText] = useState('');
    const [linkUrl, setLinkUrl] = useState('');
    const [wikiPages, setWikiPages] = useState([]);
    const [filteredPages, setFilteredPages] = useState([]);
    const [pageFilter, setPageFilter] = useState('');
    const [loadingPages, setLoadingPages] = useState(false);
    const [isHtmlMode, setIsHtmlMode] = useState(false);
    const savedSelectionRef = useRef(null);

    // Sincronizza il contenuto iniziale o esterno
    useEffect(() => {
        if (editorRef.current && editorRef.current.innerHTML !== value) {
            if (!value) {
                editorRef.current.innerHTML = '';
            } else {
                editorRef.current.innerHTML = value;
            }
        }
    }, [value]);

    // Applica lo stile di default all'editor
    useEffect(() => {
        if (editorRef.current) {
            Object.assign(editorRef.current.style, DEFAULT_EDITOR_STYLE);
        }
    }, []);

    // Gestione input utente
    const handleInput = (e) => {
        const html = e.currentTarget.innerHTML;
        onChange(html); 
    };

    // Sanificazione incolla (Paste) per evitare HTML sporco
    const handlePaste = (e) => {
        e.preventDefault();
        const text = e.clipboardData.getData('text/plain');
        document.execCommand('insertText', false, text);
    };

    // Esegue i comandi di formattazione
    const execCommand = (command, value = null) => {
        document.execCommand('styleWithCSS', false, true);
        document.execCommand(command, false, value);
        
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }
    };

    // Cambia il tipo di blocco HTML (H1, H2, P, etc.)
    const changeBlockType = (tagName) => {
        execCommand('formatBlock', tagName);
        setCurrentBlockType(tagName);
    };

    // Cambia il font family
    const changeFontFamily = (fontFamily) => {
        execCommand('fontName', fontFamily);
        setCurrentFont(fontFamily);
    };

    // Applica uno stile personalizzato
    const applyCustomStyle = (style) => {
        const selection = window.getSelection();
        if (!selection.rangeCount) return;

        const range = selection.getRangeAt(0);
        const selectedText = range.toString();

        if (!selectedText) {
            alert('Seleziona del testo prima di applicare lo stile personalizzato');
            return;
        }

        // Crea un elemento span con lo stile personalizzato
        const span = document.createElement('span');
        span.textContent = selectedText;
        span.setAttribute('data-custom-style', style.id);
        
        // Applica gli stili CSS
        Object.assign(span.style, style.css);

        // Sostituisci il testo selezionato con lo span stilizzato
        range.deleteContents();
        range.insertNode(span);

        // Aggiorna il contenuto
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }
    };

    // Inserisce una riga orizzontale
    const insertHorizontalRule = () => {
        execCommand('insertHorizontalRule');
    };

    // Inserisce una sezione collapsible (details/summary) per le pagine Wiki
    const insertCollapsibleSection = () => {
        const html = `<details class="wiki-collapsible" style="margin: 0.75em auto; width: 90%; max-width: 100%; border: 1px solid #9ca3af; border-radius: 6px; overflow: hidden; background: #e5e7eb;">
  <summary style="padding: 10px 14px; cursor: pointer; font-weight: 600; background: #d1d5db; color: #111827;">Titolo sezione (clic per espandere)</summary>
  <div style="padding: 14px; background: #e5e7eb; color: #111827;">
    <p style="margin: 0 0 0.5em 0; color: #111827;">Contenuto della sezione. Modifica qui.</p>
  </div>
</details>`;
        document.execCommand('insertHTML', false, html);
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }
    };

    // Inserisce un'emoji
    const insertEmoji = (emoji) => {
        document.execCommand('insertText', false, emoji);
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }
        setShowEmojiPicker(false);
    };

    // Apre il modal per inserire un link
    const openLinkModal = async () => {
        const selection = window.getSelection();
        if (selection.rangeCount > 0) {
            savedSelectionRef.current = selection.getRangeAt(0);
            const selectedText = selection.toString();
            setLinkText(selectedText || '');
        }
        setLinkUrl('');
        setPageFilter('');
        setShowLinkModal(true);
        
        // Carica le pagine wiki
        setLoadingPages(true);
        try {
            const menuData = await getWikiMenu();
            // Flatten della struttura del menu per ottenere tutte le pagine
            const allPages = flattenMenuPages(menuData);
            setWikiPages(allPages);
            setFilteredPages(allPages);
        } catch (err) {
            console.error('Errore caricamento pagine wiki:', err);
            setWikiPages([]);
            setFilteredPages([]);
        } finally {
            setLoadingPages(false);
        }
    };

    // Funzione helper per appiattire la struttura del menu wiki
    const flattenMenuPages = (menuItems) => {
        let pages = [];
        const traverse = (items) => {
            items.forEach(item => {
                if (item.slug) {
                    pages.push({
                        titolo: item.titolo,
                        slug: item.slug,
                        path: `/regolamento/${item.slug}`
                    });
                }
                if (item.children && item.children.length > 0) {
                    traverse(item.children);
                }
            });
        };
        traverse(menuItems);
        return pages;
    };

    // Filtra le pagine in base al testo di ricerca
    const handlePageFilterChange = (text) => {
        setPageFilter(text);
        if (!text.trim()) {
            setFilteredPages(wikiPages);
        } else {
            const filtered = wikiPages.filter(page =>
                page.titolo.toLowerCase().includes(text.toLowerCase()) ||
                page.slug.toLowerCase().includes(text.toLowerCase())
            );
            setFilteredPages(filtered);
        }
    };

    // Seleziona una pagina dalla lista
    const selectWikiPage = (page) => {
        setLinkUrl(page.path);
        if (!linkText.trim()) {
            setLinkText(page.titolo);
        }
    };

    // Inserisce il link nell'editor
    const insertLink = () => {
        if (!linkText || !linkUrl) {
            alert('Inserisci sia il testo che l\'URL del link');
            return;
        }

        // Ripristina la selezione salvata
        if (savedSelectionRef.current) {
            const selection = window.getSelection();
            selection.removeAllRanges();
            selection.addRange(savedSelectionRef.current);
        }

        // Crea il link HTML
        const linkHtml = `<a href="${linkUrl}" class="wiki-link" style="color: #818cf8; text-decoration: underline; cursor: pointer;">${linkText}</a>`;
        
        // Inserisce il link
        document.execCommand('insertHTML', false, linkHtml);
        
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }

        // Resetta e chiudi modal
        setLinkText('');
        setLinkUrl('');
        setShowLinkModal(false);
        savedSelectionRef.current = null;
    };

    // Chiude il modal senza inserire
    const closeLinkModal = () => {
        setShowLinkModal(false);
        setLinkText('');
        setLinkUrl('');
        setPageFilter('');
        setWikiPages([]);
        setFilteredPages([]);
        savedSelectionRef.current = null;
    };

    const toggleEditorMode = () => {
        if (!isHtmlMode && editorRef.current) {
            onChange(editorRef.current.innerHTML);
        }
        setIsHtmlMode((prev) => !prev);
    };

    const getCurrentTableContext = () => {
        const selection = window.getSelection();
        if (!selection.rangeCount) return null;

        const range = selection.getRangeAt(0);
        const startNode = range.startContainer;
        const element = startNode.nodeType === Node.ELEMENT_NODE ? startNode : startNode.parentElement;
        if (!element) return null;

        const cell = element.closest('td, th');
        const row = element.closest('tr');
        const table = element.closest('table');

        if (!table || !row) return null;
        return { table, row, cell };
    };

    const insertTablePreset = (preset) => {
        const gridHtml = `
<table data-table-style="grid" style="width: 100%; border-collapse: collapse; margin: 1em 0;">
  <thead>
    <tr>
      <th>Intestazione 1</th>
      <th>Intestazione 2</th>
      <th>Intestazione 3</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Cella 1</td>
      <td>Cella 2</td>
      <td>Cella 3</td>
    </tr>
    <tr>
      <td>Cella 4</td>
      <td>Cella 5</td>
      <td>Cella 6</td>
    </tr>
  </tbody>
</table>
<p><br></p>`;

        const duoHtml = `
<table data-table-style="duo" style="width: 100%; border-collapse: collapse; margin: 1em 0;">
  <thead>
    <tr>
      <th>Testo</th>
      <th>Descrizione</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <td>Voce</td>
      <td>Descrizione della voce</td>
    </tr>
    <tr>
      <td>Voce</td>
      <td>Descrizione della voce</td>
    </tr>
  </tbody>
</table>
<p><br></p>`;

        document.execCommand('insertHTML', false, preset === 'grid' ? gridHtml : duoHtml);
        if (editorRef.current) {
            onChange(editorRef.current.innerHTML);
            editorRef.current.focus();
        }
    };

    const addRowAfter = () => {
        const context = getCurrentTableContext();
        if (!context) {
            alert('Posiziona il cursore dentro una tabella.');
            return;
        }

        const { row } = context;
        const newRow = row.cloneNode(true);
        Array.from(newRow.cells).forEach((cell) => {
            cell.innerHTML = '&nbsp;';
        });
        row.parentNode.insertBefore(newRow, row.nextSibling);

        onChange(editorRef.current.innerHTML);
        editorRef.current.focus();
    };

    const removeCurrentRow = () => {
        const context = getCurrentTableContext();
        if (!context) {
            alert('Posiziona il cursore dentro una tabella.');
            return;
        }

        const { table, row } = context;
        const rows = table.querySelectorAll('tr');
        if (rows.length <= 1) {
            alert('La tabella deve avere almeno una riga.');
            return;
        }

        row.remove();
        onChange(editorRef.current.innerHTML);
        editorRef.current.focus();
    };

    const addColumnAfter = () => {
        const context = getCurrentTableContext();
        if (!context || !context.cell) {
            alert('Posiziona il cursore dentro una cella della tabella.');
            return;
        }

        const { table, cell } = context;
        const colIndex = cell.cellIndex;
        const rows = table.querySelectorAll('tr');

        rows.forEach((currentRow) => {
            const baseCell = currentRow.cells[colIndex] || currentRow.cells[currentRow.cells.length - 1];
            const tagName = baseCell && baseCell.tagName === 'TH' ? 'th' : 'td';
            const newCell = document.createElement(tagName);
            newCell.innerHTML = tagName === 'th' ? `Intestazione ${colIndex + 2}` : '&nbsp;';
            currentRow.insertBefore(newCell, currentRow.cells[colIndex + 1] || null);
        });

        onChange(editorRef.current.innerHTML);
        editorRef.current.focus();
    };

    const removeCurrentColumn = () => {
        const context = getCurrentTableContext();
        if (!context || !context.cell) {
            alert('Posiziona il cursore dentro una cella della tabella.');
            return;
        }

        const { table, cell } = context;
        const colIndex = cell.cellIndex;
        const firstRow = table.querySelector('tr');
        if (!firstRow || firstRow.cells.length <= 1) {
            alert('La tabella deve avere almeno una colonna.');
            return;
        }

        table.querySelectorAll('tr').forEach((currentRow) => {
            if (currentRow.cells[colIndex]) {
                currentRow.deleteCell(colIndex);
            }
        });

        onChange(editorRef.current.innerHTML);
        editorRef.current.focus();
    };

    return (
        <div className="flex flex-col gap-1 w-full">
            {label && <label className="text-sm font-medium text-gray-300 ml-1">{label}</label>}
            
            <div className="border border-gray-600 rounded-md bg-gray-800 overflow-hidden focus-within:ring-2 focus-within:ring-indigo-500 focus-within:border-transparent transition-all">
                
                {/* Toolbar */}
                <div className="flex flex-wrap items-center gap-1 p-2 bg-gray-700 border-b border-gray-600">
                    {!isHtmlMode && (
                        <>
                            {/* Gruppo Paragrafi HTML */}
                            <div className="flex gap-1 items-center border-r border-gray-500 pr-2 mr-1">
                                <Heading size={16} className="text-gray-400" />
                                <select 
                                    value={currentBlockType}
                                    onChange={(e) => changeBlockType(e.target.value)}
                                    className="bg-gray-800 text-gray-200 text-xs px-2 py-1 rounded border border-gray-600 hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                                    title="Tipo di Paragrafo"
                                >
                                    {HTML_BLOCKS.map(block => (
                                        <option key={block.value} value={block.tag}>
                                            {block.label}
                                        </option>
                                    ))}
                                </select>
                            </div>

                            {/* Gruppo Font Family */}
                            <div className="flex gap-1 items-center border-r border-gray-500 pr-2 mr-1">
                                <FileText size={16} className="text-gray-400" />
                                <select 
                                    value={currentFont}
                                    onChange={(e) => changeFontFamily(e.target.value)}
                                    className="bg-gray-800 text-gray-200 text-xs px-2 py-1 rounded border border-gray-600 hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer max-w-[140px]"
                                    title="Tipo di Font"
                                >
                                    {FONT_FAMILIES.map(font => (
                                        <option key={font.value} value={font.value}>
                                            {font.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            
                            {/* Gruppo Base */}
                            <div className="flex gap-0.5 border-r border-gray-500 pr-2 mr-1">
                                <ToolbarButton icon={Bold} onClick={() => execCommand('bold')} title="Grassetto" />
                                <ToolbarButton icon={Italic} onClick={() => execCommand('italic')} title="Corsivo" />
                                <ToolbarButton icon={Underline} onClick={() => execCommand('underline')} title="Sottolineato" />
                            </div>

                            {/* Gruppo Liste & Allineamento */}
                            <div className="flex gap-0.5 border-r border-gray-500 pr-2 mr-1">
                                <ToolbarButton icon={List} onClick={() => execCommand('insertUnorderedList')} title="Lista Puntata" />
                                <ToolbarButton icon={ListOrdered} onClick={() => execCommand('insertOrderedList')} title="Lista Numerata" />
                                <ToolbarButton icon={AlignLeft} onClick={() => execCommand('justifyLeft')} title="Allinea Sinistra" />
                                <ToolbarButton icon={AlignCenter} onClick={() => execCommand('justifyCenter')} title="Allinea Centro" />
                            </div>

                            {/* Gruppo Elementi Speciali */}
                            <div className="flex gap-0.5 border-r border-gray-500 pr-2 mr-1">
                                <ToolbarButton icon={Minus} onClick={insertHorizontalRule} title="Riga Orizzontale" />
                                <ToolbarButton icon={PanelTopClose} onClick={insertCollapsibleSection} title="Inserisci sezione collapsible" />
                                <ToolbarButton icon={LinkIcon} onClick={openLinkModal} title="Inserisci Link Wiki" />
                                <div className="relative">
                                    <ToolbarButton 
                                        icon={Smile} 
                                        onClick={() => setShowEmojiPicker(!showEmojiPicker)} 
                                        title="Inserisci Emoji" 
                                        active={showEmojiPicker}
                                    />
                                    {showEmojiPicker && (
                                        <div className="absolute top-full right-0 mt-1 bg-gray-800 border border-gray-600 rounded-md shadow-lg p-3 z-50 w-[480px] max-h-[350px] overflow-y-auto">
                                            <div className="grid grid-cols-12 gap-1">
                                                {COMMON_EMOJIS.map((emoji, idx) => (
                                                    <button
                                                        key={idx}
                                                        type="button"
                                                        onClick={() => insertEmoji(emoji)}
                                                        className="text-xl hover:bg-gray-700 rounded p-2 transition-colors flex items-center justify-center min-w-[36px] min-h-[36px]"
                                                        title={emoji}
                                                    >
                                                        {emoji}
                                                    </button>
                                                ))}
                                            </div>
                                        </div>
                                    )}
                                </div>
                            </div>

                            {/* Gruppo Stile Avanzato */}
                            <div className="flex gap-1 items-center border-r border-gray-500 pr-2 mr-1">
                                {/* Selettore Dimensione Font */}
                                <div className="relative group">
                                    <button type="button" title="Dimensione Testo" className="text-gray-300 hover:text-white p-1">
                                        <Type size={16} />
                                    </button>
                                    <select 
                                        className="absolute top-0 left-0 w-full h-full opacity-0 cursor-pointer"
                                        onChange={(e) => execCommand('fontSize', e.target.value)}
                                        defaultValue="3"
                                    >
                                        <option value="1">Molto Piccolo</option>
                                        <option value="2">Piccolo</option>
                                        <option value="3">Normale</option>
                                        <option value="4">Medio</option>
                                        <option value="5">Grande</option>
                                        <option value="6">Molto Grande</option>
                                        <option value="7">Enorme</option>
                                    </select>
                                </div>

                                {/* Selettore Colore */}
                                <div className="relative">
                                    <ToolbarButton 
                                        icon={Paintbrush} 
                                        onClick={() => colorInputRef.current?.click()} 
                                        title="Colore Testo" 
                                    />
                                    <input 
                                        type="color" 
                                        ref={colorInputRef}
                                        className="absolute opacity-0 w-0 h-0" 
                                        onChange={(e) => execCommand('foreColor', e.target.value)}
                                    />
                                </div>
                            </div>

                            {/* Gruppo Stili Personalizzati */}
                            <div className="flex gap-1 items-center border-r border-gray-500 pr-2 mr-1">
                                <select 
                                    onChange={(e) => {
                                        if (e.target.value) {
                                            const style = CUSTOM_STYLES.find(s => s.id === e.target.value);
                                            if (style) applyCustomStyle(style);
                                            e.target.value = ''; // Reset
                                        }
                                    }}
                                    className="bg-gray-800 text-gray-200 text-xs px-2 py-1 rounded border border-gray-600 hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                                    title="Stili Personalizzati"
                                    defaultValue=""
                                >
                                    <option value="">🎨 Stili Custom</option>
                                    {CUSTOM_STYLES.map(style => (
                                        <option key={style.id} value={style.id}>
                                            {style.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        </>
                    )}

                    {/* Gruppo Utility */}
                    <div className="flex gap-0.5 ml-auto items-center">
                        {!isHtmlMode && (
                            <div className="flex items-center gap-1 border-r border-gray-500 pr-2 mr-1">
                                <select
                                    onChange={(e) => {
                                        if (e.target.value) {
                                            insertTablePreset(e.target.value);
                                            e.target.value = '';
                                        }
                                    }}
                                    className="bg-gray-800 text-gray-200 text-xs px-2 py-1 rounded border border-gray-600 hover:border-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer"
                                    title="Inserisci tabella"
                                    defaultValue=""
                                >
                                    <option value="">📊 Tabelle</option>
                                    <option value="grid">Con intestazione + righe alternate</option>
                                    <option value="duo">2 colonne Testo/Descrizione</option>
                                </select>
                                <SmallActionButton label="+Riga" onClick={addRowAfter} title="Aggiungi riga dopo" />
                                <SmallActionButton label="-Riga" onClick={removeCurrentRow} title="Rimuovi riga corrente" />
                                <SmallActionButton label="+Col" onClick={addColumnAfter} title="Aggiungi colonna dopo" />
                                <SmallActionButton label="-Col" onClick={removeCurrentColumn} title="Rimuovi colonna corrente" />
                            </div>
                        )}
                        {!isHtmlMode && (
                            <ToolbarButton 
                                icon={Trash2} 
                                onClick={() => execCommand('removeFormat')} 
                                title="Rimuovi Formattazione" 
                            />
                        )}
                        <SmallActionButton
                            label={isHtmlMode ? 'Modalita RichText' : 'Modalita HTML'}
                            onClick={toggleEditorMode}
                            title="Alterna visuale rich text e codice HTML"
                            className="ml-1"
                        />
                    </div>
                </div>

                {/* Area di Editazione */}
                {isHtmlMode ? (
                    <textarea
                        value={value || ''}
                        onChange={(e) => onChange(e.target.value)}
                        className="w-full p-3 text-sm text-gray-200 bg-gray-900 outline-none overflow-y-auto min-h-[120px] max-h-[300px] font-mono leading-relaxed custom-scrollbar"
                        placeholder="Inserisci o modifica HTML..."
                        spellCheck={false}
                    />
                ) : (
                    <div
                        ref={editorRef}
                        contentEditable
                        onInput={handleInput}
                        onPaste={handlePaste}
                        className="p-3 text-sm text-gray-200 outline-none overflow-y-auto min-h-[120px] max-h-[300px] leading-relaxed custom-scrollbar"
                        style={{ whiteSpace: 'pre-wrap' }}
                        data-placeholder={placeholder}
                    />
                )}
                
                <style>{`
                    [contenteditable]:empty:before {
                        content: attr(data-placeholder);
                        color: #9ca3af;
                        font-style: italic;
                        pointer-events: none;
                        display: block;
                    }
                    .custom-scrollbar::-webkit-scrollbar { width: 6px; }
                    .custom-scrollbar::-webkit-scrollbar-track { background: #1f2937; }
                    .custom-scrollbar::-webkit-scrollbar-thumb { background: #4b5563; border-radius: 3px; }
                    .custom-scrollbar::-webkit-scrollbar-thumb:hover { background: #6b7280; }
                    
                    /* Stili per i vari heading HTML */
                    [contenteditable] h1 { font-size: 2em; font-weight: bold; margin: 0.67em 0; }
                    [contenteditable] h2 { font-size: 1.5em; font-weight: bold; margin: 0.75em 0; }
                    [contenteditable] h3 { font-size: 1.17em; font-weight: bold; margin: 0.83em 0; }
                    [contenteditable] h4 { font-size: 1em; font-weight: bold; margin: 1em 0; }
                    [contenteditable] h5 { font-size: 0.83em; font-weight: bold; margin: 1.5em 0; }
                    [contenteditable] h6 { font-size: 0.67em; font-weight: bold; margin: 2em 0; }
                    [contenteditable] p { margin: 0.5em 0; }
                    [contenteditable] pre { 
                        background-color: #1f2937; 
                        padding: 8px; 
                        border-radius: 4px; 
                        overflow-x: auto;
                        font-family: monospace;
                    }
                    
                    /* Stili per le liste */
                    [contenteditable] ul {
                        list-style-type: disc;
                        margin: 0.5em 0;
                        padding-left: 2em;
                    }
                    [contenteditable] ol {
                        list-style-type: decimal;
                        margin: 0.5em 0;
                        padding-left: 2em;
                    }
                    [contenteditable] li {
                        margin: 0.25em 0;
                        display: list-item;
                    }
                    [contenteditable] ul ul {
                        list-style-type: circle;
                        margin: 0.25em 0;
                    }
                    [contenteditable] ul ul ul {
                        list-style-type: square;
                    }
                    
                    /* Stile per la riga orizzontale */
                    [contenteditable] hr {
                        border: none;
                        border-top: 2px solid #4b5563;
                        margin: 1em 0;
                    }
                    
                    /* Stili per i link wiki */
                    [contenteditable] a.wiki-link {
                        color: #818cf8;
                        text-decoration: underline;
                        cursor: pointer;
                    }
                    [contenteditable] a.wiki-link:hover {
                        color: #a5b4fc;
                    }
                    /* Sezioni collapsible (details/summary): riquadro grigio chiaro, 90% larghezza, centrato */
                    [contenteditable] details.wiki-collapsible {
                        margin: 0.75em auto;
                        width: 90%;
                        max-width: 100%;
                        border: 1px solid #9ca3af;
                        border-radius: 6px;
                        overflow: hidden;
                        background: #e5e7eb;
                    }
                    [contenteditable] details summary {
                        padding: 10px 14px;
                        cursor: pointer;
                        font-weight: 600;
                        background: #d1d5db;
                        color: #111827;
                    }
                    [contenteditable] details summary::-webkit-details-marker { display: none; }
                    [contenteditable] details > div {
                        padding: 14px;
                        background: #e5e7eb;
                        color: #111827;
                    }

                    /* Tabelle: preset griglia */
                    [contenteditable] table[data-table-style="grid"] {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 1em 0;
                    }
                    [contenteditable] table[data-table-style="grid"] th,
                    [contenteditable] table[data-table-style="grid"] td {
                        border: 1px solid #4b5563;
                        padding: 8px 10px;
                    }
                    [contenteditable] table[data-table-style="grid"] th {
                        background: #374151;
                        color: #f3f4f6;
                        font-weight: 600;
                        text-align: left;
                    }
                    [contenteditable] table[data-table-style="grid"] tbody tr:nth-child(even) {
                        background: #1f2937;
                    }
                    [contenteditable] table[data-table-style="grid"] tbody tr:nth-child(odd) {
                        background: #111827;
                    }

                    /* Tabelle: preset due colonne testo/descrizione */
                    [contenteditable] table[data-table-style="duo"] {
                        width: 100%;
                        border-collapse: collapse;
                        margin: 1em 0;
                    }
                    [contenteditable] table[data-table-style="duo"] th,
                    [contenteditable] table[data-table-style="duo"] td {
                        border: 0;
                        border-bottom: 1px solid #4b5563;
                        padding: 8px 10px;
                        vertical-align: top;
                    }
                    [contenteditable] table[data-table-style="duo"] th {
                        font-weight: 600;
                        color: #f3f4f6;
                        text-align: left;
                    }
                `}</style>
            </div>

            {/* Modal per Inserire Link Wiki */}
            {showLinkModal && (
                <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={closeLinkModal}>
                    <div className="bg-gray-800 rounded-lg shadow-xl p-6 w-full max-w-2xl border border-gray-600 max-h-[90vh] overflow-hidden flex flex-col" onClick={(e) => e.stopPropagation()}>
                        <div className="flex items-center justify-between mb-4">
                            <h3 className="text-lg font-semibold text-gray-100 flex items-center gap-2">
                                <LinkIcon size={20} className="text-indigo-400" />
                                Inserisci Link Wiki
                            </h3>
                            <button
                                onClick={closeLinkModal}
                                className="text-gray-400 hover:text-gray-200 transition-colors"
                                title="Chiudi"
                            >
                                ✕
                            </button>
                        </div>

                        <div className="space-y-4 flex-1 overflow-y-auto">
                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">
                                    Testo del Link
                                </label>
                                <input
                                    type="text"
                                    value={linkText}
                                    onChange={(e) => setLinkText(e.target.value)}
                                    placeholder="es. Guida alle Classi"
                                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                />
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-2">
                                    Seleziona Pagina Wiki
                                </label>
                                
                                {/* Campo di ricerca */}
                                <div className="relative mb-2">
                                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
                                    <input
                                        type="text"
                                        value={pageFilter}
                                        onChange={(e) => handlePageFilterChange(e.target.value)}
                                        placeholder="Cerca pagina..."
                                        className="w-full pl-9 pr-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                        autoFocus
                                    />
                                </div>

                                {/* Lista pagine */}
                                <div className="border border-gray-600 rounded-md bg-gray-900 max-h-[280px] overflow-y-auto">
                                    {loadingPages ? (
                                        <div className="p-4 text-center text-gray-400">
                                            Caricamento pagine...
                                        </div>
                                    ) : filteredPages.length === 0 ? (
                                        <div className="p-4 text-center text-gray-400">
                                            Nessuna pagina trovata
                                        </div>
                                    ) : (
                                        <div className="divide-y divide-gray-700">
                                            {filteredPages.map((page, idx) => (
                                                <button
                                                    key={idx}
                                                    type="button"
                                                    onClick={() => selectWikiPage(page)}
                                                    className={`w-full text-left px-4 py-2.5 hover:bg-gray-700 transition-colors ${
                                                        linkUrl === page.path ? 'bg-indigo-600/30 border-l-4 border-indigo-500' : ''
                                                    }`}
                                                >
                                                    <div className="font-medium text-gray-200">{page.titolo}</div>
                                                    <div className="text-xs text-gray-400 mt-0.5">{page.path}</div>
                                                </button>
                                            ))}
                                        </div>
                                    )}
                                </div>
                            </div>

                            <div>
                                <label className="block text-sm font-medium text-gray-300 mb-1">
                                    URL Manuale (opzionale)
                                </label>
                                <input
                                    type="text"
                                    value={linkUrl}
                                    onChange={(e) => setLinkUrl(e.target.value)}
                                    placeholder="es. /regolamento/pagina o #sezione"
                                    className="w-full px-3 py-2 bg-gray-700 border border-gray-600 rounded-md text-gray-200 placeholder-gray-400 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent"
                                />
                                <p className="text-xs text-gray-400 mt-1">
                                    Puoi anche inserire manualmente un URL o un anchor (#sezione)
                                </p>
                            </div>
                        </div>

                        <div className="flex gap-2 justify-end pt-4 border-t border-gray-700 mt-4">
                            <button
                                onClick={closeLinkModal}
                                className="px-4 py-2 bg-gray-700 text-gray-300 rounded-md hover:bg-gray-600 transition-colors"
                            >
                                Annulla
                            </button>
                            <button
                                onClick={insertLink}
                                className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-500 transition-colors flex items-center gap-2"
                                disabled={!linkText || !linkUrl}
                            >
                                <LinkIcon size={16} />
                                Inserisci Link
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default RichTextEditor;