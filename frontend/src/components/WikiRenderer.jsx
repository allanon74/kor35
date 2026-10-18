import React, { useCallback, useContext, useLayoutEffect, useMemo, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { createRoot } from 'react-dom/client';
import { ensureDetailsClosed } from '../utils/htmlSanitizer';
import { applyWikiGlossaryToContainer } from '../utils/wikiGlossaryDom';
import { ensureRichTextStyles } from '../styles/richTextStyleSheet';
import { CharacterContext } from './CharacterContext';
import WidgetTier from './wg/WidgetTier';
import WidgetAura from './wg/WidgetAura';
import WidgetTabellaAbilita from './wg/WidgetTabellaAbilita';
import WidgetImmagine from './wg/WidgetImmagine';
import WidgetChiSiamo from './wg/WidgetChiSiamo';
import WidgetEventi from './wg/WidgetEventi';
import WidgetSocial from './wg/WidgetSocial';
import { WidgetButtonsSlot } from './wg/WidgetButtons';
import WidgetMattoni from './wg/WidgetMattoni';
import WidgetTierCollection from './wg/WidgetTierCollection';
import WidgetEra from './wg/WidgetEra';

const WIDGET_REGEX = /{{WIDGET_([A-Z_]+):([A-Za-z0-9-]+)}}/g;

/** Riferimento stabile: evita useLayoutEffect a ogni render se il glossario non è passato. */
const EMPTY_GLOSSARY = [];

function renderWidgetByType(type, id, characterValue, navigate) {
  const widget = (() => {
    switch (type) {
      case 'TIER': return <WidgetTier id={id} />;
      case 'AURA': return <WidgetAura id={id} />;
      case 'TABELLA': return <WidgetTabellaAbilita id={id} />;
      case 'IMAGE':
      case 'IMMAGINE': return <WidgetImmagine id={id} />;
      case 'CHI_SIAMO': return <WidgetChiSiamo />;
      case 'EVENTI': return <WidgetEventi />;
      case 'SOCIAL': return <WidgetSocial />;
      case 'BUTTONS':
      case 'PULSANTI': return <WidgetButtonsSlot id={id} navigate={navigate} />;
      case 'MATTONI': return <WidgetMattoni id={id} />;
      case 'TIER_COLLECTION': return <WidgetTierCollection id={id} />;
      case 'ERA':
      case 'ERE': return <WidgetEra id={id} />;
      default: return <div className="text-red-500 text-xs p-2 border border-red-300 bg-red-50 font-mono">[WIDGET IGNOTO: {type}]</div>;
    }
  })();
  // I widget sono montati con createRoot in un albero separato: serve il Provider per useCharacter
  return (
    <CharacterContext.Provider value={characterValue}>
      {widget}
    </CharacterContext.Provider>
  );
}

function cleanContent(html) {
  let currentHtml = html;
  let hasChanged = true;
  const wrapperRegex = /<([a-z][a-z0-9]*)[^>]*>(?:[\s\u00A0]|&nbsp;|<br\/?>)*({{WIDGET_[A-Z_]+:[A-Za-z0-9-]+}})(?:[\s\u00A0]|&nbsp;|<br\/?>)*<\/\1>/gi;
  while (hasChanged) {
    const newHtml = currentHtml.replace(wrapperRegex, '$2');
    if (newHtml !== currentHtml) currentHtml = newHtml;
    else hasChanged = false;
  }
  return currentHtml;
}

function getFinalHtml(content) {
  const processedContent = cleanContent(content);
  let slotIndex = 0;
  const htmlWithSlots = processedContent.replace(WIDGET_REGEX, (_, type, id) => {
    const key = slotIndex++;
    return `<div class="wiki-widget-slot" data-widget-type="${type}" data-widget-id="${id}" data-widget-key="${key}"></div>`;
  });
  return ensureDetailsClosed(htmlWithSlots);
}

/** Firma stabile: un array nuovo con gli stessi termini non ricostruisce la pagina. */
function glossarySignature(entries) {
  if (!entries || entries.length === 0) return '';
  return entries.map((entry) => [
    entry?.sync_id ?? '',
    entry?.nome ?? '',
    entry?.dichiarazione ?? '',
    entry?.descrizione ?? '',
  ].join('\u0001')).join('\u0002');
}

export default function WikiRenderer({ content, glossaryEntries = EMPTY_GLOSSARY }) {
  ensureRichTextStyles();

  const containerRef = useRef(null);
  const rootsRef = useRef([]);
  const characterValue = useContext(CharacterContext);
  const navigate = useNavigate();
  const characterValueRef = useRef(characterValue);
  const navigateRef = useRef(navigate);
  const glossaryRef = useRef(glossaryEntries);
  characterValueRef.current = characterValue;
  navigateRef.current = navigate;
  glossaryRef.current = glossaryEntries;

  // Render container whenever we have content (string); empty string still gets a div so effect can run
  const contentStr = content != null ? String(content) : '';
  const glossaryKey = useMemo(
    () => glossarySignature(glossaryEntries),
    [glossaryEntries],
  );

  const paintWidgets = useCallback(() => {
    const value = characterValueRef.current;
    const nav = navigateRef.current;
    rootsRef.current.forEach(({ root, type, id }) => {
      root.render(renderWidgetByType(type, id, value, nav));
    });
  }, []);

  // Il contesto personaggio (poll stato evento ~60s, messaggi, timer) NON deve
  // riscrivere l'HTML. innerHTML azzera i widget: la pagina Professioni si accorcia,
  // lo scroll del <main> torna in cima e i tier vengono richiesti da capo.
  useLayoutEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    rootsRef.current.forEach(({ root }) => root.unmount());
    rootsRef.current = [];

    // Set HTML imperatively so React never overwrites it on re-render (fix: widgets no longer disappear)
    const finalHtml = getFinalHtml(contentStr);
    container.innerHTML = finalHtml;

    const entries = glossaryRef.current;
    if (entries && entries.length > 0) {
      applyWikiGlossaryToContainer(container, entries);
    }

    const openGlossaryTarget = (e) => {
      const a = e.target?.closest?.('a.wiki-glossary-term');
      if (!a || !container.contains(a)) return;
      const href = a.getAttribute('href');
      if (!href || href.charAt(0) !== '#') return;
      const id = href.slice(1);
      if (!id.startsWith('wiki-glossario-')) return;
      const el = document.getElementById(id);
      if (!el) return;
      const panel = el.closest('details.wiki-glossary-section');
      if (panel) panel.open = true;
    };
    container.addEventListener('click', openGlossaryTarget);

    const slots = container.querySelectorAll('.wiki-widget-slot');
    slots.forEach((slot) => {
      const type = slot.getAttribute('data-widget-type');
      const id = slot.getAttribute('data-widget-id');
      const root = createRoot(slot);
      rootsRef.current.push({ root, type, id });
    });
    paintWidgets();

    return () => {
      container.removeEventListener('click', openGlossaryTarget);
      rootsRef.current.forEach(({ root }) => root.unmount());
      rootsRef.current = [];
    };
  }, [contentStr, glossaryKey, paintWidgets]);

  // Aggiorna il Provider dei widget già montati (es. costi in PunteggioDisplay)
  // senza smontarli: lo stato locale (filtri, sezioni aperte) resta.
  useLayoutEffect(() => {
    if (rootsRef.current.length === 0) return;
    paintWidgets();
  }, [characterValue, navigate, paintWidgets]);

  // Senza contenuto non si monta il contenitore: l'effect sopra si limita a non fare nulla
  // (l'uscita anticipata prima degli hook violava le regole dei hook di React).
  if (content == null) return null;

  return (
    <div
      ref={containerRef}
      className="wiki-content prose prose-red max-w-none text-gray-800"
    />
  );
}