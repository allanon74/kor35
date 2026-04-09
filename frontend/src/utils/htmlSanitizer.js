/** Rimuove l'attributo open da tutti i <details> nell'HTML (per avere collapsible chiusi di default). */
export const ensureDetailsClosed = (html) => {
    if (!html || typeof html !== 'string') return html || '';
    return html.replace(/<details(\s[^>]*)>/gi, (_, attrs) => {
        const cleaned = attrs.replace(/\s+open(?:\s*=\s*["'][^"']*["'])?/gi, '').replace(/\s+/g, ' ').trim();
        return '<details' + (cleaned ? ' ' + cleaned : '') + '>';
    }).replace(/<details>/gi, '<details>');
};

export const sanitizeHtml = (htmlContent) => {
    if (!htmlContent) return "";

    // 1. FASE PRELIMINARE (Stringa): 
    // Sostituisce TUTTI i &nbsp; (e il carattere unicode corrispondente) con uno spazio normale.
    // Questo è il passaggio chiave per far funzionare il "word-wrap".
    let cleanString = htmlContent
        .replace(/&nbsp;/g, ' ')   // Sostituisce l'entità HTML
        .replace(/\u00a0/g, ' ');  // Sostituisce il carattere Unicode invisibile

    try {
        const parser = new DOMParser();
        const doc = parser.parseFromString(cleanString, 'text/html');
        
        // 2. PULIZIA ELEMENTI
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