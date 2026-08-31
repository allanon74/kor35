import React from 'react';
import { BookOpen, Clock, Heart, MessageCircle } from 'lucide-react';
import { formatCount } from '../../utils/formatCount';

const dataLeggibile = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'short', year: 'numeric' });
};

/**
 * Anteprima "da testata" di un articolo: usata nella lista rubriche e,
 * in versione compatta, dentro i post InstaFame che linkano l'articolo.
 */
export default function ArticoloRubricaCard({ articolo, onOpen, compatta = false }) {
  if (!articolo) return null;

  const colore = articolo.rubrica_colore || '#b91c1c';
  const occhiello = articolo.occhiello || articolo.rubrica_nome || '';
  const sommario = articolo.sommario_effettivo || articolo.sommario || '';

  return (
    <button
      type="button"
      onClick={() => onOpen?.(articolo)}
      className={`group w-full text-left rounded-2xl border border-amber-200/25 bg-[#17111c]/90 overflow-hidden transition hover:border-amber-200/60 hover:bg-[#1f1626]/90 ${
        compatta ? '' : 'shadow-[0_10px_28px_rgba(0,0,0,0.35)]'
      }`}
    >
      <div className={compatta ? 'flex gap-3 p-2.5' : 'flex flex-col sm:flex-row gap-3 p-3'}>
        {articolo.hero_url ? (
          <img
            src={articolo.hero_url}
            alt={articolo.titolo}
            loading="lazy"
            decoding="async"
            className={`rounded-xl object-cover border border-white/10 ${
              compatta ? 'w-20 h-20 shrink-0' : 'w-full sm:w-44 h-32 sm:h-28 shrink-0'
            }`}
          />
        ) : (
          <div
            className={`rounded-xl border border-white/10 flex items-center justify-center text-amber-200/70 ${
              compatta ? 'w-20 h-20 shrink-0' : 'w-full sm:w-44 h-32 sm:h-28 shrink-0'
            }`}
            style={{ background: `linear-gradient(140deg, ${colore}33, #0d0910)` }}
          >
            <BookOpen size={compatta ? 20 : 26} />
          </div>
        )}

        <div className="min-w-0 flex-1">
          <p
            className="text-[10px] font-bold uppercase tracking-[0.14em] truncate"
            style={{ color: colore }}
          >
            {occhiello}
          </p>
          <h3
            className={`font-serif font-bold text-amber-50 leading-snug group-hover:text-white ${
              compatta ? 'text-sm line-clamp-2' : 'text-base md:text-lg line-clamp-3'
            }`}
          >
            {articolo.titolo}
          </h3>
          {!compatta && articolo.sottotitolo && (
            <p className="text-xs text-amber-100/70 italic line-clamp-2 mt-0.5">{articolo.sottotitolo}</p>
          )}
          {!compatta && sommario && (
            <p className="text-xs text-gray-300/85 line-clamp-2 mt-1">{sommario}</p>
          )}

          <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-[11px] text-gray-400">
            <span className="truncate max-w-[45%]">di {articolo.firma}</span>
            {articolo.data_pubblicazione && <span>{dataLeggibile(articolo.data_pubblicazione)}</span>}
            <span className="inline-flex items-center gap-1">
              <Clock size={11} /> {articolo.tempo_lettura_min} min
            </span>
            {!compatta && (
              <>
                <span className="inline-flex items-center gap-1">
                  <Heart size={11} fill={articolo.liked_by_me ? 'currentColor' : 'none'} />
                  {formatCount(articolo.likes_count)}
                </span>
                <span className="inline-flex items-center gap-1">
                  <MessageCircle size={11} /> {formatCount(articolo.comments_count)}
                </span>
              </>
            )}
            {articolo.stato && articolo.stato !== 'PUBBLICATO' && (
              <span className="px-1.5 py-0.5 rounded-full bg-amber-900/50 border border-amber-400/40 text-amber-200">
                {articolo.stato === 'BOZZA' ? 'Bozza' : 'Archiviato'}
              </span>
            )}
          </div>
        </div>
      </div>
    </button>
  );
}
