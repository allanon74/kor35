import React, { useEffect, useRef, useState } from 'react';
import { Smile } from 'lucide-react';
import { countGraphemes, NICKNAME_MAX_GRAPHEMES, truncateToGraphemes } from '../utils/graphemeLength';
import { INSTAFAME_EMOJIS, insertEmojiAtCursor } from './InstafameTextArea';

/**
 * Campo nickname InstaFame: testo + emoji con conteggio per grafemi (non UTF-16).
 */
export default function InstafameNicknameInput({ value, onChange, className = '', inputClassName = '' }) {
  const containerRef = useRef(null);
  const inputRef = useRef(null);
  const [open, setOpen] = useState(false);
  const graphemeCount = countGraphemes(value);

  useEffect(() => {
    if (!open) return undefined;
    const onPointerDown = (event) => {
      if (containerRef.current?.contains(event.target)) return;
      setOpen(false);
    };
    document.addEventListener('mousedown', onPointerDown);
    document.addEventListener('touchstart', onPointerDown);
    return () => {
      document.removeEventListener('mousedown', onPointerDown);
      document.removeEventListener('touchstart', onPointerDown);
    };
  }, [open]);

  const handleChange = (next) => {
    onChange(truncateToGraphemes(next, NICKNAME_MAX_GRAPHEMES));
  };

  const handleInsert = (emoji) => {
    insertEmojiAtCursor(inputRef.current, emoji, value, handleChange);
  };

  return (
    <div ref={containerRef} className={`rounded-lg border border-gray-700 bg-gray-800 ${className}`}>
      <div className="flex items-center gap-1">
        <input
          ref={inputRef}
          type="text"
          className={`flex-1 min-w-0 bg-transparent border-0 px-3 py-2 text-white placeholder:text-gray-500 focus:outline-none focus:ring-0 ${inputClassName}`}
          placeholder="Nome mostrato ad altri giocatori"
          value={value}
          onChange={(e) => handleChange(e.target.value)}
        />
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          className={`mr-1 rounded-full p-1.5 transition-colors ${
            open ? 'bg-fuchsia-900/40 text-fuchsia-200' : 'text-gray-400 hover:text-amber-200 hover:bg-white/5'
          }`}
          aria-label="Inserisci emoji"
          aria-expanded={open}
          title="Emoji"
        >
          <Smile size={20} strokeWidth={1.75} />
        </button>
      </div>
      <div className="flex items-center justify-between border-t border-gray-700/70 px-3 py-1 text-[11px] text-gray-500">
        <span>Lettere e emoji consentite</span>
        <span className={graphemeCount >= NICKNAME_MAX_GRAPHEMES ? 'text-amber-300' : ''}>
          {graphemeCount}/{NICKNAME_MAX_GRAPHEMES}
        </span>
      </div>
      <div
        className={`grid transition-[grid-template-rows] duration-200 ease-out ${
          open ? 'grid-rows-[1fr]' : 'grid-rows-[0fr]'
        }`}
        aria-hidden={!open}
      >
        <div className="overflow-hidden">
          <div
            className="border-t border-gray-700/70 bg-gray-900/95 rounded-b-lg p-2.5 max-h-44 overflow-y-auto grid grid-cols-8 gap-0.5"
            role="region"
            aria-label="Scegli un emoji"
          >
            {INSTAFAME_EMOJIS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                className="text-[1.35rem] leading-none p-1.5 rounded-lg hover:bg-gray-700 active:scale-95 transition-transform"
                onClick={() => handleInsert(emoji)}
                title={emoji}
                tabIndex={open ? 0 : -1}
              >
                {emoji}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
