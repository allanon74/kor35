import React, { useMemo, useState } from 'react';
import { canShowInlineReminder, tokenizeCardRulesText } from './parseCardRulesText';

function KeywordInline({ kw, matched, text, matchIndex, matchLen, maxLineLength }) {
  const [open, setOpen] = useState(false);
  const testoRegola = kw.testo_regola || '';
  const reminder = kw.reminder_breve || '';
  const showReminder = canShowInlineReminder(
    text,
    matchIndex,
    matchLen,
    reminder,
    maxLineLength,
  );

  if (showReminder && reminder) {
    return (
      <>
        <strong className="font-bold text-white">{matched}</strong>
        <em className="text-gray-400 not-italic"> (*{reminder}*)</em>
      </>
    );
  }

  return (
    <span className="relative inline">
      <button
        type="button"
        className="font-bold text-white underline decoration-dotted decoration-gray-500"
        onClick={(e) => {
          e.stopPropagation();
          setOpen((v) => !v);
        }}
      >
        {matched}
      </button>
      {open && (
        <span
          role="tooltip"
          className="absolute bottom-full left-0 z-50 mb-1 max-w-[220px] rounded border border-gray-600 bg-gray-950 px-2 py-1 text-left text-[10px] font-normal normal-case text-gray-200 shadow-lg"
          onClick={(e) => e.stopPropagation()}
        >
          <span className="block font-bold text-violet-300">{matched}</span>
          {testoRegola}
        </span>
      )}
    </span>
  );
}

export default function CardRulesText({
  text,
  keywords = [],
  className = '',
  maxLineLength = 90,
}) {
  const segments = useMemo(
    () => tokenizeCardRulesText(text || '', keywords),
    [text, keywords],
  );

  return (
    <span className={className}>
      {segments.map((seg, idx) => {
        if (seg.kind === 'text') {
          return <React.Fragment key={`t-${idx}`}>{seg.value}</React.Fragment>;
        }
        return (
          <KeywordInline
            key={`k-${idx}-${seg.index}`}
            kw={seg.kw}
            matched={seg.matched}
            text={text || ''}
            matchIndex={seg.index}
            matchLen={seg.len}
            maxLineLength={maxLineLength}
          />
        );
      })}
    </span>
  );
}
