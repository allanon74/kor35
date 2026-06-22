import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import { resolveMediaUrl } from '../api';

/** Frazione larghezza per zone tap sinistra/destra (il centro apre il lightbox). */
const EDGE_ZONE_RATIO = 0.33;

const getTapZone = (event) => {
  const rect = event.currentTarget.getBoundingClientRect();
  const ratio = (event.clientX - rect.left) / rect.width;
  if (ratio < EDGE_ZONE_RATIO) return 'left';
  if (ratio > 1 - EDGE_ZONE_RATIO) return 'right';
  return 'center';
};

/**
 * Carosello foto stile Instagram: tap sinistra/destra per scorrere, centro per ingrandire.
 */
const InstafameMediaCarousel = ({ images = [], alt = '', className = '', fullWidth = false }) => {
  const slides = useMemo(
    () =>
      (Array.isArray(images) ? images.filter(Boolean) : []).map((src) => resolveMediaUrl(src) || src),
    [images]
  );
  const [index, setIndex] = useState(0);
  const [lightboxOpen, setLightboxOpen] = useState(false);

  useEffect(() => {
    setIndex(0);
    setLightboxOpen(false);
  }, [slides]);

  const count = slides.length;
  const safeIndex = Math.min(index, count - 1);

  const goPrev = useCallback(() => {
    setIndex((prev) => (prev - 1 + count) % count);
  }, [count]);

  const goNext = useCallback(() => {
    setIndex((prev) => (prev + 1) % count);
  }, [count]);

  const handleCarouselClick = (event) => {
    const zone = getTapZone(event);
    if (count <= 1) {
      setLightboxOpen(true);
      return;
    }
    if (zone === 'left') goPrev();
    else if (zone === 'right') goNext();
    else setLightboxOpen(true);
  };

  const handleLightboxSurfaceClick = (event) => {
    if (count <= 1) {
      setLightboxOpen(false);
      return;
    }
    const zone = getTapZone(event);
    if (zone === 'left') goPrev();
    else if (zone === 'right') goNext();
    else setLightboxOpen(false);
  };

  useEffect(() => {
    if (!lightboxOpen) return undefined;
    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        setLightboxOpen(false);
        return;
      }
      if (count <= 1) return;
      if (event.key === 'ArrowLeft') goPrev();
      if (event.key === 'ArrowRight') goNext();
    };
    const prevOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    window.addEventListener('keydown', onKeyDown);
    return () => {
      document.body.style.overflow = prevOverflow;
      window.removeEventListener('keydown', onKeyDown);
    };
  }, [lightboxOpen, count, goPrev, goNext]);

  if (slides.length === 0) return null;

  const carouselLabel =
    count > 1
      ? `Foto ${safeIndex + 1} di ${count}. Tocca ai lati per scorrere, al centro per ingrandire.`
      : 'Foto del post. Tocca per ingrandire.';

  const lightbox = lightboxOpen
    ? createPortal(
        <div
          className="fixed inset-0 z-[120] flex items-center justify-center bg-black/95 p-3 sm:p-6"
          role="dialog"
          aria-modal="true"
          aria-label={alt || 'Anteprima foto'}
        >
          <button
            type="button"
            onClick={() => setLightboxOpen(false)}
            className="absolute top-3 right-3 z-10 rounded-full bg-black/60 p-2 text-white hover:bg-black/80 focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300/60"
            aria-label="Chiudi anteprima"
          >
            <X className="h-6 w-6" />
          </button>

          <button
            type="button"
            onClick={handleLightboxSurfaceClick}
            className="relative flex h-full w-full max-h-[92vh] max-w-[96vw] cursor-default items-center justify-center focus:outline-none"
            aria-label={
              count > 1
                ? `Foto ${safeIndex + 1} di ${count}. Tocca ai lati per scorrere, al centro per chiudere.`
                : 'Foto ingrandita. Tocca per chiudere.'
            }
          >
            <img
              src={slides[safeIndex]}
              alt={alt}
              className="max-h-[92vh] max-w-full object-contain select-none"
              draggable={false}
            />
          </button>

          {count > 1 && (
            <>
              <div className="pointer-events-none absolute top-3 left-1/2 -translate-x-1/2 rounded-full bg-black/60 px-2.5 py-0.5 text-xs font-semibold text-white">
                {safeIndex + 1}/{count}
              </div>
              <div className="pointer-events-none absolute bottom-4 left-0 right-0 flex justify-center gap-1.5">
                {slides.map((slide, i) => (
                  <span
                    key={`lb-${slide}-${i}`}
                    className={`h-1.5 w-1.5 rounded-full ${i === safeIndex ? 'bg-white' : 'bg-white/40'}`}
                  />
                ))}
              </div>
            </>
          )}
        </div>,
        document.body
      )
    : null;

  return (
    <>
      <div
        className={`relative overflow-hidden bg-black/40 ${
          fullWidth
            ? 'w-full aspect-4/5 border-y border-gray-700/60 lg:aspect-auto lg:border-y-0'
            : 'w-full max-w-md mx-auto aspect-4/5 rounded-lg border border-gray-700'
        } ${className}`}
      >
        <button
          type="button"
          onClick={handleCarouselClick}
          className="h-full w-full cursor-pointer focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-300/60 lg:h-auto"
          aria-label={carouselLabel}
        >
          <img
            src={slides[safeIndex]}
            alt={alt}
            className="h-full w-full object-cover select-none pointer-events-none lg:object-contain lg:h-auto lg:max-h-none"
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
      {lightbox}
    </>
  );
};

export default InstafameMediaCarousel;
