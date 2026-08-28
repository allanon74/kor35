import React, { useMemo } from 'react';
import { sanitizeHtml } from '../utils/htmlSanitizer';
import { ensureRichTextStyles } from '../styles/richTextStyleSheet';

/**
 * Viewer per HTML ricco (descrizioni catalogo, testi formattati dal backend, note staff).
 *
 * Sostituisce gli usi diretti di `dangerouslySetInnerHTML`, che iniettavano l'HTML
 * grezzo: cosi ogni contenuto passa dalla stessa sanitizzazione dell'editor
 * (via niente script/iframe/on*, stili inline filtrati) e riceve la tipografia
 * condivisa `.ql-editor-view`, che rende visibili a capo, elenchi e tabelle.
 *
 * Per i messaggi con macroazioni staff ([ACTIVATE_USER:1], ...) serve invece
 * `RichTextDisplay`, che ne fa il parsing e monta i pulsanti.
 *
 * @param {object} props
 * @param {string} props.content HTML (o testo semplice) da mostrare
 * @param {string} [props.className] Classi aggiuntive del contenitore
 * @param {object} [props.style] Stili inline del contenitore (es. colore di contrasto del widget)
 * @param {'div'|'span'} [props.as='div'] Tag del contenitore (span per testi in linea)
 * @param {'onDark'|'onLight'} [props.tone='onDark'] Su fondo chiaro neutralizza i
 *        colori di testo pensati per il tema scuro (i chip con sfondo proprio restano).
 *
 * Gli altri attributi (onClick, title, ...) finiscono sul contenitore: serve dove il
 * troncamento `line-clamp` e il click di espansione devono stare sullo stesso elemento
 * del testo.
 */
const RichHtml = ({ content, className = '', style, as = 'div', tone = 'onDark', ...rest }) => {
    ensureRichTextStyles();

    const Tag = as;

    const isOnLight = tone === 'onLight';
    const html = useMemo(
        () => sanitizeHtml(content, { dropTextColors: isOnLight }),
        [content, isOnLight]
    );

    if (!html) return null;

    const classes = [
        'ql-editor-view',
        isOnLight ? 'ql-editor-view--light' : '',
        className,
    ].filter(Boolean).join(' ');

    return (
        <Tag
            {...rest}
            className={classes}
            style={style}
            dangerouslySetInnerHTML={{ __html: html }}
        />
    );
};

export default RichHtml;
