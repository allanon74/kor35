/**
 * Configurazione dichiarativa del RichTextEditor (blocchi, font, colori, stili, snippet).
 * Tenuta fuori dal componente per rendere la toolbar riorganizzabile senza toccare la logica.
 *
 * Nota: le proprieta CSS sono in kebab-case perche vengono applicate con
 * `style.setProperty` / `style.removeProperty` dal motore di formattazione.
 */

export const HTML_BLOCKS = [
    { value: 'p', label: 'Paragrafo' },
    { value: 'h1', label: 'Titolo 1' },
    { value: 'h2', label: 'Titolo 2' },
    { value: 'h3', label: 'Titolo 3' },
    { value: 'h4', label: 'Titolo 4' },
    { value: 'h5', label: 'Titolo 5' },
    { value: 'h6', label: 'Titolo 6' },
    { value: 'blockquote', label: 'Citazione' },
    { value: 'pre', label: 'Preformattato' },
];

export const FONT_FAMILIES = [
    { value: '', label: 'Font predefinito' },
    { value: 'Inter, system-ui, sans-serif', label: 'Inter' },
    { value: 'Arial, sans-serif', label: 'Arial' },
    { value: 'Georgia, serif', label: 'Georgia' },
    { value: '"Times New Roman", serif', label: 'Times New Roman' },
    { value: '"Courier New", monospace', label: 'Courier New' },
    { value: 'Verdana, sans-serif', label: 'Verdana' },
    { value: '"Trebuchet MS", sans-serif', label: 'Trebuchet MS' },
    { value: '"Comic Sans MS", cursive', label: 'Comic Sans MS' },
    { value: 'Impact, sans-serif', label: 'Impact' },
];

/** Dimensioni in em: scalano con il contesto (viewer chat, wiki, stampa). */
export const FONT_SIZES = [
    { value: '', label: 'Normale' },
    { value: '0.75em', label: 'Molto piccolo' },
    { value: '0.875em', label: 'Piccolo' },
    { value: '1.125em', label: 'Medio' },
    { value: '1.35em', label: 'Grande' },
    { value: '1.6em', label: 'Molto grande' },
    { value: '2em', label: 'Enorme' },
];

export const TEXT_COLORS = [
    { value: '', label: 'Colore predefinito' },
    { value: '#f9fafb', label: 'Bianco' },
    { value: '#9ca3af', label: 'Grigio' },
    { value: '#f87171', label: 'Rosso' },
    { value: '#fb923c', label: 'Arancio' },
    { value: '#fbbf24', label: 'Oro' },
    { value: '#4ade80', label: 'Verde' },
    { value: '#38bdf8', label: 'Azzurro' },
    { value: '#818cf8', label: 'Indaco' },
    { value: '#e879f9', label: 'Magenta' },
];

export const HIGHLIGHT_COLORS = [
    { value: '', label: 'Nessuna evidenziazione' },
    { value: '#fef08a', label: 'Giallo' },
    { value: '#bbf7d0', label: 'Verde' },
    { value: '#bfdbfe', label: 'Azzurro' },
    { value: '#fecaca', label: 'Rosso' },
    { value: '#e9d5ff', label: 'Viola' },
];

/**
 * Stili applicati come <span data-custom-style="..."> con dichiarazioni inline.
 * Sono preservati dalla sanitizzazione, quindi si vedono identici in visualizzazione.
 */
export const CUSTOM_STYLES = [
    {
        id: 'title-general',
        label: 'Titolo generale',
        declarations: {
            'font-size': '1.75em',
            'font-weight': '700',
            color: '#818cf8',
            'border-bottom': '3px solid #6366f1',
            'padding-bottom': '8px',
            'margin-top': '12px',
            'margin-bottom': '12px',
            display: 'block',
            'letter-spacing': '0.5px',
        },
    },
    {
        id: 'title-section',
        label: 'Titolo sezione',
        declarations: {
            'font-size': '1.25em',
            'font-weight': '600',
            color: '#a5b4fc',
            'border-left': '4px solid #6366f1',
            'padding-left': '12px',
            'margin-top': '10px',
            'margin-bottom': '8px',
            display: 'block',
            'text-transform': 'uppercase',
            'letter-spacing': '1px',
        },
    },
    {
        id: 'title-subsection',
        label: 'Titolo sottosezione',
        declarations: {
            'font-size': '1.15em',
            'font-weight': '500',
            color: '#a5b4fc',
            'padding-left': '12px',
            'margin-top': '8px',
            'margin-bottom': '6px',
            display: 'block',
            'text-transform': 'uppercase',
            'letter-spacing': '1px',
        },
    },
    {
        id: 'highlight-yellow',
        label: 'Evidenziato giallo',
        declarations: {
            'background-color': '#fef3c7',
            color: '#92400e',
            padding: '2px 6px',
            'border-radius': '3px',
            'font-weight': '500',
        },
    },
    {
        id: 'highlight-blue',
        label: 'Evidenziato blu',
        declarations: {
            'background-color': '#dbeafe',
            color: '#1e40af',
            padding: '2px 6px',
            'border-radius': '3px',
            'font-weight': '500',
        },
    },
    {
        id: 'highlight-green',
        label: 'Evidenziato verde',
        declarations: {
            'background-color': '#d1fae5',
            color: '#065f46',
            padding: '2px 6px',
            'border-radius': '3px',
            'font-weight': '500',
        },
    },
    {
        id: 'highlight-red',
        label: 'Evidenziato rosso',
        declarations: {
            'background-color': '#fee2e2',
            color: '#991b1b',
            padding: '2px 6px',
            'border-radius': '3px',
            'font-weight': '500',
        },
    },
    {
        id: 'code-inline',
        label: 'Codice inline',
        declarations: {
            'background-color': '#1f2937',
            color: '#10b981',
            padding: '2px 6px',
            'border-radius': '4px',
            'font-family': '"Courier New", monospace',
            'font-size': '0.9em',
            border: '1px solid #374151',
        },
    },
    {
        id: 'quote',
        label: 'Citazione',
        declarations: {
            'border-left': '4px solid #6366f1',
            'padding-left': '12px',
            'font-style': 'italic',
            'margin-left': '8px',
            display: 'block',
        },
    },
    {
        id: 'warning',
        label: 'Avviso',
        declarations: {
            'background-color': '#fef3c7',
            color: '#92400e',
            padding: '8px 12px',
            'border-radius': '6px',
            'border-left': '4px solid #f59e0b',
            'font-weight': '500',
            display: 'block',
        },
    },
    {
        id: 'success',
        label: 'Successo',
        declarations: {
            'background-color': '#d1fae5',
            color: '#065f46',
            padding: '8px 12px',
            'border-radius': '6px',
            'border-left': '4px solid #10b981',
            'font-weight': '500',
            display: 'block',
        },
    },
];

/** Emoji per wiki e messaggi di gioco, raggruppate per tema. */
export const EMOJI_GROUPS = [
    {
        id: 'enfasi',
        label: 'Enfasi',
        emojis: [
            '📌', '📍', '🔖', '⚠️', '❗', '❕', '‼️', '⁉️', '❓', '❔',
            '💡', '🔆', '💫', '✨', '⭐', '🌟', '💥', '💢', '🔥', '⚡',
            '✅', '❌', '⭕', '🚫', '💯', '♾️', '🆕', '🆙', '🔞', '⛔',
        ],
    },
    {
        id: 'combattimento',
        label: 'Armi e magia',
        emojis: [
            '⚔️', '🗡️', '🔪', '🏹', '🛡️', '🪓', '⚒️', '🔨', '⛏️', '🪃',
            '🎯', '💣', '🧨', '🔮', '🪄', '💎', '💠', '🔷', '🔶', '🔱',
            '⚗️', '🧪', '🧬', '🧫', '🩸', '💉', '🧿', '📿', '🔗', '⛓️',
        ],
    },
    {
        id: 'creature',
        label: 'Creature',
        emojis: [
            '🐉', '🐲', '🦎', '🐍', '🦂', '🕷️', '🦇', '🦅', '🦉', '🦌',
            '🐺', '🦊', '🐗', '🐻', '🦁', '🐯', '🦈', '🐙', '🦑', '🐘',
            '🐾', '🦴', '☠️', '💀', '👹', '👺', '👻', '👽', '🤖', '🤡',
        ],
    },
    {
        id: 'luoghi',
        label: 'Luoghi',
        emojis: [
            '🏰', '🏯', '🗼', '🗿', '🏛️', '⛪', '🕌', '🛕', '🗻', '⛰️',
            '🏔️', '🌋', '🏕️', '⛺', '🏞️', '🏜️', '🏝️', '🌌', '🕳️', '🌠',
            '🗺️', '🧭', '🚩', '🏴', '🏳️', '🏁', '⛳', '🌍', '🌎', '🌏',
        ],
    },
    {
        id: 'potere',
        label: 'Potere e tesori',
        emojis: [
            '👑', '💍', '💰', '🪙', '🏆', '🥇', '🥈', '🥉', '🎖️', '🏅',
            '🎗️', '⚜️', '🔰', '🗝️', '📜', '📋', '📚', '📖', '📕', '📗',
            '✍️', '✒️', '🖋️', '🖌️', '📝', '🗂️', '📂', '🗃️', '🗄️', '💼',
        ],
    },
    {
        id: 'tempo',
        label: 'Tempo e meteo',
        emojis: [
            '⏰', '⏱️', '⏲️', '⌛', '⏳', '🌅', '🌄', '🌃', '🌆', '🌇',
            '☀️', '🌙', '☄️', '❄️', '☃️', '🌊', '🌈', '☁️', '⛈️', '🌩️',
            '💧', '💦', '💨', '🌪️', '🕯️', '⚰️', '🪦', '🔄', '🔁', '⏳',
        ],
    },
    {
        id: 'espressioni',
        label: 'Espressioni',
        emojis: [
            '😀', '😃', '😄', '😊', '😎', '🤔', '😮', '😱', '😡', '😈',
            '👿', '🙏', '👍', '👎', '👋', '🤝', '💪', '🫡', '🤫', '🫥',
            '⬆️', '⬇️', '⬅️', '➡️', '↗️', '↘️', '↩️', '↪️', '▶️', '◀️',
        ],
    },
];

export const TABLE_PRESETS = [
    {
        id: 'grid',
        label: 'Griglia con intestazione',
        html: '<table data-table-style="grid"><thead><tr><th>Intestazione 1</th><th>Intestazione 2</th><th>Intestazione 3</th></tr></thead><tbody><tr><td>Cella 1</td><td>Cella 2</td><td>Cella 3</td></tr><tr><td>Cella 4</td><td>Cella 5</td><td>Cella 6</td></tr></tbody></table><p><br></p>',
    },
    {
        id: 'duo',
        label: 'Due colonne Testo/Descrizione',
        html: '<table data-table-style="duo"><thead><tr><th>Testo</th><th>Descrizione</th></tr></thead><tbody><tr><td>Voce</td><td>Descrizione della voce</td></tr><tr><td>Voce</td><td>Descrizione della voce</td></tr></tbody></table><p><br></p>',
    },
];

/**
 * Sezione collapsible: nessuno stile inline, l'aspetto arriva dal CSS condiviso
 * (`.wiki-collapsible` in richTextSharedStyles) cosi editor e viewer restano allineati.
 */
export const COLLAPSIBLE_TEMPLATE = '<details class="wiki-collapsible"><summary>Titolo sezione (clic per espandere)</summary><div><p>Contenuto della sezione. Modifica qui.</p></div></details><p><br></p>';
