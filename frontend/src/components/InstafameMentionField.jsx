import React, { useRef, useState } from 'react';
import InstafameTextArea from './InstafameTextArea';
import { searchPersonaggi } from '../api';
import { findActiveMention, replaceActiveMention } from '../utils/instafameMentions';
import { HASHTAG_INLINE_REGEX, normalizeHashtagFilter } from '../utils/hashtags';

function hashtagNelTesto(text) {
  const trovati = new Set();
  const regex = new RegExp(HASHTAG_INLINE_REGEX.source, 'g');
  let match;
  while ((match = regex.exec(String(text || ''))) !== null) {
    const tag = normalizeHashtagFilter(match[2]);
    if (tag.length >= 2 && tag.length <= 40) trovati.add(tag);
  }
  return [...trovati].sort();
}

/**
 * Campo testo InstaFame: emoji, suggerimenti @personaggio e anteprima #hashtag.
 */
export default function InstafameMentionField({
  value,
  onChange,
  personaggioId,
  placeholder,
  rows = 3,
  compact = false,
  className = '',
  showHashtags = false,
}) {
  const [suggerimenti, setSuggerimenti] = useState([]);
  const cursoreRef = useRef(0);
  const selezioneRef = useRef(null);

  const aggiorna = async (testo, cursore) => {
    const pos = cursore ?? String(testo || '').length;
    cursoreRef.current = pos;
    onChange(testo);
    const attivo = findActiveMention(testo, pos);
    if (!attivo || !attivo.query) {
      setSuggerimenti([]);
      return;
    }
    try {
      const risposta = await searchPersonaggi(attivo.query, personaggioId || '', null, 'menzione');
      setSuggerimenti(Array.isArray(risposta) ? risposta : []);
    } catch {
      setSuggerimenti([]);
    }
  };

  const inserisci = (personaggio) => {
    const { text, cursorPos } = replaceActiveMention(
      value || '',
      cursoreRef.current ?? String(value || '').length,
      `@${personaggio.id} `
    );
    selezioneRef.current = cursorPos;
    cursoreRef.current = cursorPos;
    onChange(text);
    setSuggerimenti([]);
  };

  const etichetta = (personaggio) => personaggio.nome || personaggio.nickname || `PG ${personaggio.id}`;

  const hashtag = showHashtags ? hashtagNelTesto(value) : [];

  return (
    <div className={`relative min-w-0 ${className}`}>
      {suggerimenti.length > 0 && (
        <div className="absolute z-30 left-0 right-0 bottom-full mb-1 max-h-40 overflow-auto rounded-lg border border-amber-300/30 bg-gray-950 shadow-xl">
          {suggerimenti.map((personaggio) => (
            <button
              key={personaggio.id}
              type="button"
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => inserisci(personaggio)}
              className="block w-full text-left px-3 py-2 text-sm text-amber-100 hover:bg-white/10"
            >
              @{etichetta(personaggio)}
              <span className="text-gray-500"> · {personaggio.id}</span>
            </button>
          ))}
        </div>
      )}
      <InstafameTextArea
        value={value || ''}
        onChange={aggiorna}
        pendingSelectionRef={selezioneRef}
        placeholder={placeholder}
        rows={rows}
        compact={compact}
      />
      {hashtag.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-1.5">
          {hashtag.map((tag) => (
            <span
              key={tag}
              className="text-[11px] px-2 py-0.5 rounded-full bg-fuchsia-900/40 border border-fuchsia-400/30 text-fuchsia-100"
            >
              #{tag}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
