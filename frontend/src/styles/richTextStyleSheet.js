import { RICH_TEXT_SHARED_STYLES } from './richTextSharedStyles';

const STYLE_ELEMENT_ID = 'kor-rich-text-shared-styles';

/**
 * Inserisce il foglio di stile condiviso del blocco RichText una sola volta in <head>.
 *
 * Prima ogni istanza di editor/viewer stampava il proprio tag <style> inline: nelle
 * liste lunghe (abilita, inventario, tabelle wiki) lo stesso CSS veniva duplicato
 * decine di volte nel DOM. La funzione e idempotente e si puo chiamare in fase di
 * render: serve che le regole esistano prima della prima pittura, altrimenti il
 * contenuto lampeggia senza stili.
 */
export const ensureRichTextStyles = () => {
    if (typeof document === 'undefined') return;
    if (document.getElementById(STYLE_ELEMENT_ID)) return;

    const style = document.createElement('style');
    style.id = STYLE_ELEMENT_ID;
    style.textContent = RICH_TEXT_SHARED_STYLES;
    document.head.appendChild(style);
};
