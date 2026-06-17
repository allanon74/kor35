import React, { useEffect, useMemo, useState } from 'react';
import { resolveMediaUrl } from '../api';

/**
 * Carosello foto stile Instagram: tap sinistra/destra per scorrere.
 */
const InstafameMediaCarousel = ({ images = [], alt = '', className = '', fullWidth = false }) => {
  const slides = useMemo(
    () =>
      (Array.isArray(images) ? images.filter(Boolean) : []).map((src) => resolveMediaUrl(src) || src),
    [images]
  );
  const [index, setIndex] = useState(0);

  useEffect(() => {
    setIndex(0);
  }, [slides]);

  if (slides.length === 0) return null;

  const count = slides.length;
  const safeIndex = Math.min(index, count - 1);

  const handleClick = (event) => {
    if (count <= 1) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const x = event.clientX - rect.left;
    if (x < rect.width / 2) {
      setIndex((prev) => (prev - 1 + count) % count);
    } else {
      setIndex((prev) => (prev + 1) % count);
    }
  };

  return (
    <div
      className={`relative overflow-hidden bg-black/40 ${
        fullWidth
          ? 'w-full aspect-4/5 border-y border-gray-700/60 lg:aspect-auto lg:h-full lg:min-h-[280px] lg:max-h-[640px] lg:border-y-0'
          : 'w-full max-w-md mx-auto aspect-4/5 rounded-lg border border-gray-700'
      } ${className}`}
    >
      <button
        type="button"
        onClick={handleClick}
        className="h-full w-full cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300/60"
        aria-label={count > 1 ? `Foto ${safeIndex + 1} di ${count}. Tocca ai lati per scorrere.` : 'Foto del post'}
      >
        <img
          src={slides[safeIndex]}
          alt={alt}
          className="h-full w-full object-cover select-none pointer-events-none lg:object-contain"
          draggable={false}
        />
      </button>
      {count > 1 && (
        <>
          <div className="absolute top-2 right-2 px-2 py-0.5 rounded-full bg-black/60 text-white text-xs font-semibold pointer-events-none">
            {safeIndex + 1}/{count}
          </div>
          <div className="absolute bottom-2 left-0 right-0 flex justify-center gap-1.5 pointer-events-none">
            {slides.map((slide, i) => (
              <span
                key={`${slide}-${i}`}
                className={`h-1.5 w-1.5 rounded-full ${i === safeIndex ? 'bg-white' : 'bg-white/40'}`}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default InstafameMediaCarousel;
