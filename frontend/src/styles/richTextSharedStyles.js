/**
 * Stili condivisi per la visualizzazione di contenuto HTML ricco
 * (liste, hr, link wiki, sezioni collapsible).
 * Usato da RichTextDisplay (.ql-editor-view) e WikiRenderer (.wiki-content).
 * Un solo posto per evitare duplicazione e mantenere coerenza.
 */
export const RICH_TEXT_SHARED_STYLES = `
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
`;
