import React, { useMemo } from 'react';
import RichHtml from '../RichHtml';
import {
  extractRubricaImgIds,
  layoutFigureClass,
  splitCorpoByMarkers,
} from '../../utils/rubricheMarkers';

function RubricaFigure({ img, titolo, compact = false }) {
  if (!img?.url) return null;
  const layout = img.layout || 'full';
  return (
    <figure className={`${layoutFigureClass(layout)} ${compact ? 'my-2' : 'my-4'}`}>
      <img
        src={img.url}
        alt={img.didascalia || titolo || ''}
        className="w-full object-cover rounded-xl border border-white/10"
      />
      {img.didascalia ? (
        <figcaption className="px-1 pt-1.5 text-[11px] text-gray-400 italic">{img.didascalia}</figcaption>
      ) : null}
    </figure>
  );
}

/**
 * Corpo articolo con marker [[rubrica-img:uuid]] espansi in figure; immagini senza marker in appendice.
 */
export default function ArticoloCorpoConImmagini({
  corpo = '',
  immagini = [],
  titolo = '',
  className = '',
}) {
  const byId = useMemo(() => {
    const map = new Map();
    (Array.isArray(immagini) ? immagini : []).forEach((img) => {
      if (img?.id) map.set(String(img.id).toLowerCase(), img);
    });
    return map;
  }, [immagini]);

  const segments = useMemo(() => splitCorpoByMarkers(corpo), [corpo]);
  const referenziate = useMemo(() => new Set(extractRubricaImgIds(corpo)), [corpo]);
  const appendice = useMemo(
    () => (Array.isArray(immagini) ? immagini : []).filter((img) => !referenziate.has(String(img.id).toLowerCase())),
    [immagini, referenziate]
  );

  /** Accoppia figure consecutive con layout grid_pair. */
  const rendered = [];
  for (let i = 0; i < segments.length; i += 1) {
    const seg = segments[i];
    if (seg.type === 'html') {
      if ((seg.html || '').trim()) {
        rendered.push(
          <RichHtml
            key={`h-${i}`}
            content={seg.html}
            className="text-sm md:text-base leading-7 text-gray-200"
          />
        );
      }
      continue;
    }
    const img = byId.get(seg.id);
    if (!img) continue;
    const next = segments[i + 1];
    const nextImg = next?.type === 'image' ? byId.get(next.id) : null;
    if (img.layout === 'grid_pair' && nextImg?.layout === 'grid_pair') {
      rendered.push(
        <div key={`pair-${i}`} className="grid grid-cols-1 sm:grid-cols-2 gap-3 my-4">
          <RubricaFigure img={img} titolo={titolo} compact />
          <RubricaFigure img={nextImg} titolo={titolo} compact />
        </div>
      );
      i += 1;
      continue;
    }
    rendered.push(<RubricaFigure key={`img-${i}-${seg.id}`} img={img} titolo={titolo} />);
  }

  return (
    <div className={`rubrica-corpo-con-immagini ${className}`}>
      <style>{`
        .rubrica-corpo-con-immagini .rubrica-img--wide {
          width: 100vw;
          max-width: 100vw;
          margin-left: calc(50% - 50vw);
          margin-right: calc(50% - 50vw);
          padding-left: 0.75rem;
          padding-right: 0.75rem;
        }
        @media (min-width: 768px) {
          .rubrica-corpo-con-immagini .rubrica-img--wide {
            width: auto;
            max-width: none;
            margin-left: -1.5rem;
            margin-right: -1.5rem;
            padding-left: 0;
            padding-right: 0;
          }
        }
        .rubrica-corpo-con-immagini .rubrica-img--float-left {
          float: left;
          width: min(100%, 16rem);
          max-width: 48%;
          margin: 0.25rem 1rem 0.75rem 0;
        }
        .rubrica-corpo-con-immagini .rubrica-img--float-right {
          float: right;
          width: min(100%, 16rem);
          max-width: 48%;
          margin: 0.25rem 0 0.75rem 1rem;
        }
        @media (max-width: 639px) {
          .rubrica-corpo-con-immagini .rubrica-img--float-left,
          .rubrica-corpo-con-immagini .rubrica-img--float-right {
            float: none;
            width: 100%;
            max-width: 100%;
            margin: 1rem 0;
          }
        }
        .rubrica-corpo-con-immagini::after {
          content: '';
          display: table;
          clear: both;
        }
      `}</style>

      {rendered}

      {appendice.length > 0 && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5 clear-both">
          {appendice.map((img) => (
            <RubricaFigure key={`app-${img.id}`} img={img} titolo={titolo} compact />
          ))}
        </div>
      )}
    </div>
  );
}
