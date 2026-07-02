/** Rimuove l'attributo open da tutti i <details> nell'HTML (per avere collapsible chiusi di default). */
export const ensureDetailsClosed = (html) => {
    if (!html || typeof html !== 'string') return html || '';
    return html.replace(/<details(\s[^>]*)>/gi, (_, attrs) => {
        const cleaned = attrs.replace(/\s+open(?:\s*=\s*["'][^"']*["'])?/gi, '').replace(/\s+/g, ' ').trim();
        return '<details' + (cleaned ? ' ' + cleaned : '') + '>';
    }).replace(/<details>/gi, '<details>');
};

/** Converte span con stili inline in tag semantici prima della rimozione degli style. */
const preserveSemanticFormatting = (doc) => {
    const spans = [...doc.body.querySelectorAll('span[style]')];
    spans.forEach((span) => {
        const style = (span.getAttribute('style') || '').toLowerCase();
        const weight = (style.match(/font-weight\s*:\s*([^;]+)/) || [])[1]?.trim();
        const isBold = weight && (
            weight === 'bold'
            || weight === 'bolder'
            || (parseInt(weight, 10) >= 600 && !Number.isNaN(parseInt(weight, 10)))
        );
        const isItalic = /font-style\s*:\s*italic/.test(style);
        const isUnderline = /text-decoration(?:-line)?\s*:[^;]*underline/.test(style);

        let node = span;
        const wrap = (tag) => {
            const el = doc.createElement(tag);
            while (node.firstChild) el.appendChild(node.firstChild);
            node.appendChild(el);
            node = el;
        };

        if (isBold) wrap('strong');
        if (isItalic) wrap('em');
        if (isUnderline) wrap('u');

        const parent = span.parentNode;
        if (!parent) return;
        while (span.firstChild) parent.insertBefore(span.firstChild, span);
        parent.removeChild(span);
    });
};

/** Se non c'è markup HTML, preserva gli a capo come <br>. */
export const prepareRichHtmlForView = (content) => {
    if (!content) return '';
    const trimmed = String(content).trim();
    if (!trimmed) return '';
    if (/<[a-z][\s\S]*>/i.test(trimmed)) return trimmed;
    const escaped = trimmed
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    return escaped.replace(/\r\n/g, '\n').replace(/\n/g, '<br>');
};

export const sanitizeHtml = (htmlContent) => {
    if (!htmlContent) return "";

    let cleanString = prepareRichHtmlForView(htmlContent);
    if (!/<[a-z][\s\S]*>/i.test(cleanString)) {
        return cleanString;
    }

    cleanString = cleanString
        .replace(/&nbsp;/g, ' ')
        .replace(/\u00a0/g, ' ');

    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(cleanString, 'text/html');

        preserveSemanticFormatting(doc);
        
        // PULIZIA ELEMENTI
        const allElements = doc.body.querySelectorAll('*');
        allElements.forEach(el => {
            // Rimuove stili inline (es. width fisse, white-space: nowrap copiati da Word)
            el.removeAttribute('style');
            
            // Rimuove classi (spesso portano dietro colori o font strani)
            el.removeAttribute('class'); 
            
            // Opzionale: Rimuove attributi width/height da tabelle o div che rompono il layout
            el.removeAttribute('width');
            el.removeAttribute('height');
            // Sezioni collapsible: chiuso di default (rimuove open)
            if (el.tagName === 'DETAILS') el.removeAttribute('open');
        });

        // 3. RIMOZIONE PARAGRAFI VUOTI ECCESSIVI
        // Elimina i <p> che contengono solo spazi o <br> inutili
        const paragraphs = doc.body.querySelectorAll('p');
        paragraphs.forEach(p => {
            const text = p.textContent.trim();
            const hasMedia = p.querySelector('img, iframe, video');
            
            // Se non c'è testo, non ci sono media, ed è vuoto o ha solo un <br>
            if (!text && !hasMedia) {
                if (p.innerHTML.trim() === '' || p.innerHTML === '<br>') {
                    p.remove();
                }
            }
        });

        return doc.body.innerHTML;
    } catch (e) {
        console.error("Errore sanitizzazione HTML:", e);
        // Se fallisce il parsing, restituisci almeno la stringa con gli spazi sostituiti
        return cleanString; 
    }
};