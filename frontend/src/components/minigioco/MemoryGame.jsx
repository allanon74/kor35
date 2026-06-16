import React, { useState, useMemo } from 'react';

const GLYPHS = ['◆', '◇', '●', '○', '▲', '△', '■', '□', '★', '☆', '✦', '✧', '⬡', '⬢', '✸', '✹'];

const MemoryGame = ({ cols, rows, cards, matched, imageUrl, onChange }) => {
  const [flipped, setFlipped] = useState([]);
  const [lock, setLock] = useState(false);

  const matchedSet = useMemo(() => new Set(matched || []), [matched]);
  const total = cols * rows;

  const reveal = (idx) => {
    if (lock || matchedSet.has(idx) || flipped.includes(idx)) return;
    const nextFlipped = [...flipped, idx];
    setFlipped(nextFlipped);
    if (nextFlipped.length < 2) return;

    setLock(true);
    const [a, b] = nextFlipped;
    const deck = cards || [];
    if (deck[a] === deck[b]) {
      const nextMatched = [...(matched || []), a, b];
      onChange({ cards: deck, matched: nextMatched });
      setFlipped([]);
      setLock(false);
    } else {
      setTimeout(() => {
        setFlipped([]);
        setLock(false);
      }, 700);
    }
  };

  const pctW = 100 / cols;
  const pctH = 100 / rows;

  const cardFace = (idx) => {
    const sym = (cards || [])[idx];
    if (imageUrl) {
      const pairCount = total / 2;
      const col = sym % Math.max(2, Math.ceil(Math.sqrt(pairCount)));
      const row = Math.floor(sym / Math.max(2, Math.ceil(Math.sqrt(pairCount))));
      const grid = Math.ceil(Math.sqrt(pairCount));
      return {
        backgroundImage: `url(${imageUrl})`,
        backgroundSize: `${grid * 100}%`,
        backgroundPosition: `${col * (100 / (grid - 1 || 1))}% ${row * (100 / (grid - 1 || 1))}%`,
      };
    }
    return { label: GLYPHS[sym % GLYPHS.length] };
  };

  return (
    <div
      className="relative w-full max-w-sm mx-auto aspect-[4/5] bg-gray-950 rounded-lg overflow-hidden border border-purple-500/50"
      style={{ touchAction: 'manipulation' }}
    >
      {Array.from({ length: total }, (_, idx) => {
        const isOpen = matchedSet.has(idx) || flipped.includes(idx);
        const face = cardFace(idx);
        return (
          <button
            key={idx}
            type="button"
            className={`absolute box-border border border-white/10 text-2xl font-bold flex items-center justify-center transition-colors ${
              isOpen ? 'bg-indigo-900/40' : 'bg-gray-800 hover:bg-gray-700'
            }`}
            style={{
              width: `${pctW}%`,
              height: `${pctH}%`,
              left: `${(idx % cols) * pctW}%`,
              top: `${Math.floor(idx / cols) * pctH}%`,
              ...(isOpen && face.backgroundImage
                ? { backgroundImage: face.backgroundImage, backgroundSize: face.backgroundSize, backgroundPosition: face.backgroundPosition }
                : {}),
            }}
            onClick={() => reveal(idx)}
            aria-label={isOpen ? 'Carta scoperta' : 'Carta coperta'}
          >
            {!isOpen ? '?' : face.label || null}
          </button>
        );
      })}
    </div>
  );
};

export default MemoryGame;
