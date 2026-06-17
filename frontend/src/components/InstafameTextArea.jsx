import React, { useEffect, useRef, useState } from 'react';
import { Smile } from 'lucide-react';

/** Emoji rapide per caption InstaFame (social + fantasy leggero). */
export const INSTAFAME_EMOJIS = [
  '😀', '😂', '🥰', '😍', '😎', '🤩', '🥳', '😭', '🙏', '👀',
  '❤️', '🧡', '💛', '💚', '💙', '💜', '🖤', '💔', '❤️‍🔥', '💕',
  '🔥', '✨', '💫', '⭐', '🌟', '💯', '👏', '🙌', '💪', '🤝',
  '💎', '🎬', '🎥', '📸', '📷', '🎉', '🎊', '🎭', '🎵', '🍿',
  '☕', '🍕', '🌙', '☀️', '🌈', '⚡', '💡', '📍', '🗺️', '🏰',
  '⚔️', '🛡️', '🗡️', '🏹', '🔮', '🐉', '👑', '💍', '🎖️', '🏆',
];

export function insertEmojiAtCursor(textarea, emoji, value, onChange) {
  const current = value ?? '';
  if (!textarea) {
    onChange(current + emoji);
    return;
  }
  const start = textarea.selectionStart ?? current.length;
  const end = textarea.selectionEnd ?? start;
  const next = current.slice(0, start) + emoji + current.slice(end);
  onChange(next);
  requestAnimationFrame(() => {
    textarea.focus();
    const pos = start + emoji.length;
    textarea.setSelectionRange(pos, pos);
  });
}

/**
 * Textarea con pulsante emoji stile Instagram: barra emoji espandibile sotto il campo.
 */
export default function InstafameTextArea({
  value,
  onChange,
  className = '',
  textareaClassName = '',
  placeholder,
  rows = 4,
  minHeightClass = 'min-h-24',
  compact = false,
  ...rest
}) {
  const containerRef = useRef(null);
  const textareaRef = useRef(null);
  const [open, setOpen] = useState(false);

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

  const handleInsert = (emoji) => {
    insertEmojiAtCursor(textareaRef.current, emoji, value, onChange);
  };

  const resolvedRows = compact ? 1 : rows;
  const resolvedMinHeight = compact ? 'min-h-10' : minHeightClass;
  const emojiSize = compact ? 20 : 22;

  return (
    <div
      ref={containerRef}
      className={`rounded-lg border border-gray-700 bg-gray-800 ${compact ? 'text-sm' : ''} ${className}`}
    >
      <textarea
        ref={textareaRef}
        className={`w-full bg-transparent border-0 px-3 py-2 text-white placeholder:text-gray-500 focus:outline-none focus:ring-0 resize-y rounded-t-lg ${resolvedMinHeight} ${textareaClassName}`}
        placeholder={placeholder}
        rows={resolvedRows}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        {...rest}
      />
      <div
        className={`flex items-center border-t border-gray-700/70 bg-gray-800/80 ${
          compact ? 'px-0.5 py-0' : 'px-1 py-0.5'
        } ${open ? '' : 'rounded-b-lg'}`}
      >
        <button
          type="button"
          onClick={() => setOpen((prev) => !prev)}
          className={`rounded-full transition-colors ${
            compact ? 'p-1.5' : 'p-2'
          } ${
            open ? 'bg-fuchsia-900/40 text-fuchsia-200' : 'text-gray-400 hover:text-amber-200 hover:bg-white/5'
          }`}
          aria-label="Inserisci emoji"
          aria-expanded={open}
          title="Emoji"
        >
          <Smile size={emojiSize} strokeWidth={1.75} />
        </button>
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
