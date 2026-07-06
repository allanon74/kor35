import React, { useEffect, useMemo, useRef, useState } from 'react';
import CardRulesText from './CardRulesText';

export function LoreTextBlock({ text, className = '', onExpand }) {
  const ref = useRef(null);
  const [overflows, setOverflows] = useState(false);

  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const check = () => setOverflows(el.scrollHeight > el.clientHeight + 2);
    check();
    const ro = typeof ResizeObserver !== 'undefined' ? new ResizeObserver(check) : null;
    ro?.observe(el);
    return () => ro?.disconnect();
  }, [text]);

  if (!text?.trim()) return null;

  return (
    <div className={className}>
      <p
        ref={ref}
        className="mt-2 line-clamp-4 whitespace-pre-wrap italic text-gray-400/95"
      >
        {text.trim()}
      </p>
      {overflows && (
        <button
          type="button"
          className="mt-1 text-[10px] font-semibold text-violet-300 underline"
          onClick={(e) => {
            e.stopPropagation();
            onExpand?.(text.trim());
          }}
        >
          Leggi tutto il testo di lore
        </button>
      )}
    </div>
  );
}

export function CardRulesPreview({ text, keywords, label = 'Anteprima testo gioco (Keywords)' }) {
  return (
    <div className="rounded border border-gray-700 bg-gray-900/50 p-2">
      <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-violet-300">{label}</p>
      <p className="whitespace-pre-wrap text-sm leading-relaxed text-gray-200">
        <CardRulesText text={text || '—'} keywords={keywords} maxLineLength={120} />
      </p>
    </div>
  );
}

export function LoreFullModal({ text, title, onClose }) {
  if (!text) return null;
  return (
    <div
      className="fixed inset-0 z-[120] flex items-center justify-center bg-black/85 p-4"
      onClick={onClose}
    >
      <div
        className="max-h-[85vh] w-full max-w-lg overflow-y-auto rounded-xl border border-gray-600 bg-gray-950 p-4 shadow-2xl"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="mb-3 flex items-start justify-between gap-2">
          <h3 className="text-lg font-bold text-white">{title || 'Testo di lore'}</h3>
          <button type="button" className="text-gray-400 hover:text-white" onClick={onClose}>✕</button>
        </div>
        <p className="whitespace-pre-wrap text-sm leading-relaxed italic text-gray-300">{text}</p>
      </div>
    </div>
  );
}
