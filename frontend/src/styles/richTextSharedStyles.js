/**
 * Stili condivisi per la visualizzazione di contenuto HTML ricco
 * (liste, hr, link wiki, sezioni collapsible).
 * Usato da RichTextDisplay (.ql-editor-view), WikiRenderer (.wiki-content)
 * e dall'area editabile del RichTextEditor, che porta la classe `.ql-editor-view`
 * proprio per garantire che quello che si scrive sia identico a quello che si vede.
 * Un solo posto per evitare duplicazione e mantenere coerenza.
 */
export const RICH_TEXT_SHARED_STYLES = `
  /* Testo su sfondo chiaro (es. pagina informazioni logistiche evento) */
  .ql-editor-view--light,
  .ql-editor-view--light p,
  .ql-editor-view--light li,
  .ql-editor-view--light span,
  .ql-editor-view--light div {
    color: inherit;
  }
  .ql-editor-view--light a.wiki-link {
    color: #6366f1;
  }
  .ql-editor-view--light a.wiki-link:hover {
    color: #4f46e5;
  }

  /* Tipografia viewer (allineata all'editor; Tailwind preflight azzera margini p/h) */
  .ql-editor-view p {
    margin: 0.5em 0;
  }
  .ql-editor-view strong,
  .ql-editor-view b {
    font-weight: 700;
    color: inherit;
  }
  .ql-editor-view em,
  .ql-editor-view i {
    font-style: italic;
  }
  .ql-editor-view u {
    text-decoration: underline;
  }
  .ql-editor-view h1 { font-size: 2em; font-weight: 700; margin: 0.67em 0; }
  .ql-editor-view h2 { font-size: 1.5em; font-weight: 700; margin: 0.75em 0; }
  .ql-editor-view h3 { font-size: 1.17em; font-weight: 700; margin: 0.83em 0; }
  .ql-editor-view h4 { font-size: 1em; font-weight: 700; margin: 1em 0; }
  .ql-editor-view h5 { font-size: 0.83em; font-weight: 700; margin: 1.5em 0; }
  .ql-editor-view h6 { font-size: 0.67em; font-weight: 700; margin: 2em 0; }
  .ql-editor-view pre {
    white-space: pre-wrap;
    font-family: ui-monospace, monospace;
    margin: 0.5em 0;
    padding: 0.5em 0.75em;
    border-radius: 0.375rem;
    background: rgba(0, 0, 0, 0.25);
  }

  .ql-editor-view ul, .wiki-content ul {
    list-style-type: disc;
    margin: 0.5em 0;
    padding-left: 2em;
  }
  .ql-editor-view ol, .wiki-content ol {
    list-style-type: decimal;
    margin: 0.5em 0;
    padding-left: 2em;
  }
  .ql-editor-view li, .wiki-content li {
    margin: 0.25em 0;
    display: list-item;
  }
  .ql-editor-view ul ul, .wiki-content ul ul {
    list-style-type: circle;
    margin: 0.25em 0;
  }
  .ql-editor-view ul ul ul, .wiki-content ul ul ul {
    list-style-type: square;
  }
  .ql-editor-view hr, .wiki-content hr {
    border: none;
    border-top: 2px solid #9ca3af;
    margin: 1em 0;
  }
  .ql-editor-view a.wiki-link {
    color: #818cf8;
    text-decoration: underline;
    cursor: pointer;
    transition: color 0.2s;
  }
  .ql-editor-view a.wiki-link:hover {
    color: #a5b4fc;
  }
  .wiki-content a.wiki-link {
    color: #6366f1;
    text-decoration: underline;
    cursor: pointer;
    transition: color 0.2s;
  }
  .wiki-content a.wiki-link:hover {
    color: #818cf8;
  }

  .wiki-content a.wiki-glossary-term {
    color: #b91c1c;
    text-decoration: underline dotted;
    text-underline-offset: 2px;
    cursor: help;
  }
  .wiki-content a.wiki-glossary-term:hover {
    color: #991b1b;
  }
  .wiki-content details.wiki-glossary-panel {
    width: 100%;
    max-width: 100%;
    margin-top: 1.5rem;
  }
  .wiki-content .wiki-glossary-panel-body {
    display: flex;
    flex-direction: column;
    gap: 0.75rem;
  }
  .wiki-content .wiki-glossary-def {
    scroll-margin-top: 0.75rem;
  }

  /* Sezioni collapsible: riquadro grigio chiaro, 90% larghezza, centrato, chiuso di default */
  .ql-editor-view details, .wiki-content details {
    margin: 0.75em auto;
    width: 90%;
    max-width: 100%;
    border: 1px solid #9ca3af;
    border-radius: 6px;
    overflow: hidden;
    background: #e5e7eb;
  }
  .ql-editor-view details summary, .wiki-content details summary {
    padding: 10px 14px;
    cursor: pointer;
    font-weight: 600;
    background: #d1d5db;
    color: #111827;
  }
  .ql-editor-view details summary::-webkit-details-marker,
  .wiki-content details summary::-webkit-details-marker {
    display: none;
  }
  .ql-editor-view details summary:hover, .wiki-content details summary:hover {
    background: #b8bcc4;
  }
  .ql-editor-view details > div, .wiki-content details > div {
    padding: 14px;
    background: #e5e7eb;
    color: #111827;
  }
  .ql-editor-view details > div, .ql-editor-view details > div p, .ql-editor-view details > div *,
  .wiki-content details > div, .wiki-content details > div p, .wiki-content details > div * {
    color: inherit;
  }

  /* Tabelle: preset griglia (header + celle + righe alternate) */
  .wiki-content .wiki-table-scroll {
    overflow-x: auto;
    margin: 1em 0;
    -webkit-overflow-scrolling: touch;
  }
  .wiki-content .wiki-table-scroll table[data-table-style="grid"] {
    margin: 0;
  }
  .ql-editor-view table[data-table-style="grid"],
  .wiki-content table[data-table-style="grid"] {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
  }
  .ql-editor-view table[data-table-style="grid"] th,
  .ql-editor-view table[data-table-style="grid"] td,
  .wiki-content table[data-table-style="grid"] th,
  .wiki-content table[data-table-style="grid"] td {
    border: 1px solid #9ca3af;
    padding: 8px 10px;
    text-align: left;
  }
  .ql-editor-view table[data-table-style="grid"] th {
    background: #374151;
    color: #f3f4f6;
    font-weight: 600;
  }
  .wiki-content table[data-table-style="grid"] th {
    background: #e5e7eb;
    color: #111827;
    font-weight: 600;
  }
  .ql-editor-view table[data-table-style="grid"] tbody tr:nth-child(even) {
    background: #1f2937;
  }
  .ql-editor-view table[data-table-style="grid"] tbody tr:nth-child(odd) {
    background: #111827;
  }
  .wiki-content table[data-table-style="grid"] tbody tr:nth-child(even) {
    background: #f9fafb;
  }
  .wiki-content table[data-table-style="grid"] tbody tr:nth-child(odd) {
    background: #ffffff;
  }

  /* Tabelle: preset 2 colonne (solo separatori orizzontali) */
  .ql-editor-view table[data-table-style="duo"],
  .wiki-content table[data-table-style="duo"] {
    width: 100%;
    border-collapse: collapse;
    margin: 1em 0;
  }
  .ql-editor-view table[data-table-style="duo"] th,
  .ql-editor-view table[data-table-style="duo"] td,
  .wiki-content table[data-table-style="duo"] th,
  .wiki-content table[data-table-style="duo"] td {
    border: 0;
    border-bottom: 1px solid #9ca3af;
    padding: 8px 10px;
    text-align: left;
    vertical-align: top;
  }
  .ql-editor-view table[data-table-style="duo"] th {
    color: #f3f4f6;
    font-weight: 600;
  }
  .wiki-content table[data-table-style="duo"] th {
    color: #111827;
    font-weight: 600;
  }

  /* Collapsible dentro i widget Tier: larghezza 100%, niente riquadro grigio, rispettano lo stile cromatico del plugin */
  .wiki-content .wiki-widget-tier details,
  .wiki-content .wiki-widget-slot .wiki-widget-tier details {
    margin: 0;
    width: 100%;
    max-width: 100%;
    border: none;
    border-radius: 0;
    background: transparent;
    overflow: visible;
  }
  .wiki-content .wiki-widget-tier details summary,
  .wiki-content .wiki-widget-slot .wiki-widget-tier details summary {
    padding: 0.5rem 0.75rem;
    background: transparent;
    color: inherit;
    border: none;
  }
  .wiki-content .wiki-widget-tier details summary:hover,
  .wiki-content .wiki-widget-slot .wiki-widget-tier details summary:hover {
    background: transparent;
  }
  .wiki-content .wiki-widget-tier details > div,
  .wiki-content .wiki-widget-slot .wiki-widget-tier details > div {
    padding: 0;
    background: transparent;
  }

  /* --- Blocchi vuoti = a capo voluti dall'autore: devono conservare altezza --- */
  .ql-editor-view p:empty,
  .ql-editor-view div:empty,
  .wiki-content p:empty,
  .wiki-content div:empty {
    min-height: 1em;
  }

  /* --- Elementi tipografici aggiuntivi --- */
  .ql-editor-view blockquote,
  .wiki-content blockquote {
    margin: 0.75em 0;
    padding: 0.25em 0 0.25em 1em;
    border-left: 3px solid #6366f1;
    font-style: italic;
  }
  .ql-editor-view code,
  .wiki-content code {
    font-family: ui-monospace, monospace;
    font-size: 0.92em;
    padding: 0.1em 0.35em;
    border-radius: 0.25rem;
    background: rgba(0, 0, 0, 0.25);
  }
  .wiki-content code {
    background: rgba(0, 0, 0, 0.07);
  }
  .ql-editor-view pre code,
  .wiki-content pre code {
    padding: 0;
    background: transparent;
  }
  .ql-editor-view mark,
  .wiki-content mark {
    background: #fef08a;
    color: #111827;
    padding: 0 0.15em;
    border-radius: 2px;
  }
  .ql-editor-view s, .ql-editor-view del,
  .wiki-content s, .wiki-content del {
    text-decoration: line-through;
  }
  .ql-editor-view sub, .ql-editor-view sup,
  .wiki-content sub, .wiki-content sup {
    font-size: 0.75em;
    line-height: 0;
  }
  .ql-editor-view img,
  .wiki-content img {
    max-width: 100%;
    height: auto;
    border-radius: 0.375rem;
  }
  .ql-editor-view figure,
  .wiki-content figure {
    margin: 0.75em 0;
  }
  .ql-editor-view figcaption,
  .wiki-content figcaption {
    font-size: 0.8em;
    opacity: 0.8;
    margin-top: 0.25em;
  }

  /* --- Tabelle: contenitore scrollabile (su smartphone sfonderebbero il layout) --- */
  .rich-table-scroll {
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin: 1em 0;
    max-width: 100%;
  }
  .rich-table-scroll > table {
    margin: 0;
    min-width: 20rem;
  }

  /* --- Area editabile del RichTextEditor --- */
  .kor-rich-editor {
    position: relative;
    outline: none;
    caret-color: #a5b4fc;
    /*
     * Stessa gestione degli spazi del viewer: gli a capo arrivano come <br>/blocchi
     * (normalizzati al caricamento e in fase di incolla), non come newline nel testo.
     * Con pre-wrap l'indentazione scritta in modalita codice si vedeva come righe extra.
     */
    white-space: normal;
    overflow-wrap: anywhere;
  }
  /*
   * Placeholder pilotato da data-empty e non da :empty: dopo aver scritto e cancellato,
   * i browser lasciano un <br> residuo e con :empty il testo guida non ricompariva.
   */
  .kor-rich-editor[data-empty="true"]:before {
    content: attr(data-placeholder);
    position: absolute;
    top: 0;
    left: 0;
    color: #9ca3af;
    font-style: italic;
    pointer-events: none;
    max-width: 100%;
  }

  /* Toolbar: barra di scorrimento discreta su mobile, invisibile a riposo */
  .kor-rich-toolbar-scroll {
    scrollbar-width: thin;
    scrollbar-color: rgba(156, 163, 175, 0.45) transparent;
  }
  .kor-rich-toolbar-scroll::-webkit-scrollbar {
    height: 3px;
  }
  .kor-rich-toolbar-scroll::-webkit-scrollbar-track {
    background: transparent;
  }
  .kor-rich-toolbar-scroll::-webkit-scrollbar-thumb {
    background: rgba(156, 163, 175, 0.45);
    border-radius: 3px;
  }
  .kor-rich-editor [data-kor-rt-marker] {
    display: none;
  }
  .kor-rich-editor > *:first-child {
    margin-top: 0;
  }
  .kor-rich-editor > *:last-child {
    margin-bottom: 0;
  }
  /* Celle sempre cliccabili anche se vuote, e tabelle ridimensionabili in scrittura */
  .kor-rich-editor th,
  .kor-rich-editor td {
    min-width: 2.5rem;
  }
  .kor-rich-editor details {
    /* In scrittura i collapsible restano aperti: servono modificabili. */
    width: 100%;
  }
  .kor-rich-editor summary {
    list-style: none;
  }
`;
