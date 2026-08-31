import React, { useCallback, useEffect, useState } from 'react';
import { ArrowLeft, Clock, Heart, MessageCircle, Send, Trash2 } from 'lucide-react';
import RichHtml from '../RichHtml';
import { formatCount } from '../../utils/formatCount';
import {
  creaCommentoArticolo,
  eliminaCommentoArticolo,
  getArticolo,
  getCommentiArticolo,
  toggleLikeArticolo,
  toggleLikeCommentoArticolo,
} from '../../api/rubriche';

const dataEstesa = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('it-IT', { day: '2-digit', month: 'long', year: 'numeric' });
};

/**
 * Lettore giornalistico in-game: impaginazione da testata + interazioni InstaFame
 * (like e commenti). La versione Wiki resta di sola lettura.
 */
export default function ArticoloRubricaReader({
  articoloId,
  personaggioId,
  onLogout,
  onChiudi,
  onModifica,
}) {
  const [articolo, setArticolo] = useState(null);
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState('');
  const [commenti, setCommenti] = useState([]);
  const [nuovoCommento, setNuovoCommento] = useState('');
  const [inviando, setInviando] = useState(false);

  const caricaArticolo = useCallback(async () => {
    if (!articoloId) return;
    setCaricamento(true);
    setErrore('');
    try {
      const dati = await getArticolo(articoloId, personaggioId, onLogout);
      setArticolo(dati);
    } catch (e) {
      setErrore(e?.message || "Impossibile caricare l'articolo.");
    } finally {
      setCaricamento(false);
    }
  }, [articoloId, personaggioId, onLogout]);

  const caricaCommenti = useCallback(async () => {
    if (!articoloId) return;
    try {
      const risposta = await getCommentiArticolo(articoloId, personaggioId, onLogout, 1, 30);
      setCommenti(Array.isArray(risposta?.results) ? risposta.results : []);
    } catch {
      setCommenti([]);
    }
  }, [articoloId, personaggioId, onLogout]);

  useEffect(() => {
    caricaArticolo();
    caricaCommenti();
  }, [caricaArticolo, caricaCommenti]);

  const gestisciLike = async () => {
    if (!articolo) return;
    try {
      const esito = await toggleLikeArticolo(articolo.id, personaggioId, onLogout);
      setArticolo((prec) => ({
        ...prec,
        liked_by_me: !!esito?.liked,
        likes_count: Math.max(
          0,
          Number(prec.likes_count || 0) + (esito?.liked ? Number(esito.peso_like || 1) : -1)
        ),
      }));
    } catch (e) {
      setErrore(e?.message || 'Like non riuscito.');
    }
  };

  const inviaCommento = async (evento) => {
    evento.preventDefault();
    const testo = nuovoCommento.trim();
    if (!testo || !articolo) return;
    setInviando(true);
    try {
      await creaCommentoArticolo(articolo.id, testo, personaggioId, onLogout);
      setNuovoCommento('');
      await caricaCommenti();
      setArticolo((prec) => ({ ...prec, comments_count: Number(prec.comments_count || 0) + 1 }));
    } catch (e) {
      setErrore(e?.message || 'Commento non inviato.');
    } finally {
      setInviando(false);
    }
  };

  const rimuoviCommento = async (commentoId) => {
    if (!window.confirm('Eliminare il commento?')) return;
    try {
      await eliminaCommentoArticolo(articolo.id, commentoId, personaggioId, onLogout);
      await caricaCommenti();
      setArticolo((prec) => ({
        ...prec,
        comments_count: Math.max(0, Number(prec.comments_count || 0) - 1),
      }));
    } catch (e) {
      setErrore(e?.message || 'Eliminazione non riuscita.');
    }
  };

  const likeCommento = async (commentoId) => {
    try {
      await toggleLikeCommentoArticolo(articolo.id, commentoId, personaggioId, onLogout);
      await caricaCommenti();
    } catch (e) {
      setErrore(e?.message || 'Like al commento non riuscito.');
    }
  };

  if (caricamento) {
    return <div className="rounded-2xl border border-gray-700 bg-gray-900/70 p-6 animate-pulse h-64" />;
  }
  if (!articolo) {
    return (
      <div className="rounded-2xl border border-red-500/40 bg-red-950/30 p-4 text-sm text-red-200">
        {errore || 'Articolo non disponibile.'}
      </div>
    );
  }

  const colore = articolo.rubrica_colore || '#b91c1c';

  return (
    <article className="rounded-3xl border border-amber-200/30 bg-[#15101a]/95 overflow-hidden shadow-[0_16px_40px_rgba(0,0,0,0.45)]">
      <div className="flex items-center justify-between gap-2 px-3 py-2 border-b border-white/10 bg-black/30">
        <button
          type="button"
          onClick={onChiudi}
          className="inline-flex items-center gap-1 text-xs text-amber-100/80 hover:text-white"
        >
          <ArrowLeft size={14} /> Torna alla rubrica
        </button>
        <div className="flex items-center gap-2">
          {articolo.can_edit && onModifica && (
            <button
              type="button"
              onClick={() => onModifica(articolo)}
              className="text-xs px-2 py-1 rounded-lg bg-indigo-700/70 border border-indigo-400/40 hover:bg-indigo-600"
            >
              Modifica
            </button>
          )}
          <span className="text-[11px] uppercase tracking-widest" style={{ color: colore }}>
            {articolo.rubrica_nome}
          </span>
        </div>
      </div>

      <header className="px-4 md:px-8 pt-5 pb-3 max-w-3xl mx-auto">
        {articolo.occhiello && (
          <p className="text-[11px] font-bold uppercase tracking-[0.2em]" style={{ color: colore }}>
            {articolo.occhiello}
          </p>
        )}
        <h1 className="font-serif text-2xl md:text-4xl font-black text-amber-50 leading-tight mt-1">
          {articolo.titolo}
        </h1>
        {articolo.sottotitolo && (
          <p className="font-serif text-base md:text-xl text-amber-100/75 italic mt-2 leading-snug">
            {articolo.sottotitolo}
          </p>
        )}
        <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-3 pt-3 border-t border-white/10 text-[11px] text-gray-400">
          {articolo.autore_avatar && (
            <img src={articolo.autore_avatar} alt="" className="w-6 h-6 rounded-full object-cover" />
          )}
          <span className="text-amber-100/90 font-semibold">di {articolo.firma}</span>
          {articolo.data_pubblicazione && <span>{dataEstesa(articolo.data_pubblicazione)}</span>}
          <span className="inline-flex items-center gap-1">
            <Clock size={12} /> {articolo.tempo_lettura_min} min di lettura
          </span>
        </div>
      </header>

      {articolo.hero_url && (
        <figure className="max-w-4xl mx-auto px-0 md:px-8">
          <img src={articolo.hero_url} alt={articolo.titolo} className="w-full object-cover max-h-[460px]" />
          {articolo.hero_didascalia && (
            <figcaption className="px-4 md:px-0 py-2 text-[11px] text-gray-400 italic">
              {articolo.hero_didascalia}
            </figcaption>
          )}
        </figure>
      )}

      <div className="px-4 md:px-8 py-4 max-w-3xl mx-auto">
        {(articolo.sommario_effettivo || articolo.sommario) && (
          <p
            className="text-sm md:text-base text-amber-50/90 font-medium leading-relaxed pl-3 mb-4"
            style={{ borderLeft: `3px solid ${colore}` }}
          >
            {articolo.sommario_effettivo || articolo.sommario}
          </p>
        )}

        {articolo.corpo && (
          <RichHtml content={articolo.corpo} className="text-sm md:text-base leading-7 text-gray-200" />
        )}

        {Array.isArray(articolo.immagini) && articolo.immagini.length > 0 && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mt-5">
            {articolo.immagini.map((img) => (
              <figure key={img.id} className="rounded-xl overflow-hidden border border-white/10">
                <img src={img.url} alt={img.didascalia || articolo.titolo} className="w-full object-cover" />
                {img.didascalia && (
                  <figcaption className="px-2 py-1 text-[11px] text-gray-400 italic bg-black/40">
                    {img.didascalia}
                  </figcaption>
                )}
              </figure>
            ))}
          </div>
        )}

        {articolo.video_url && (
          <video controls src={articolo.video_url} className="w-full rounded-xl mt-5 border border-white/10" />
        )}
      </div>

      <div className="px-4 md:px-8 py-3 border-t border-white/10 flex flex-wrap items-center gap-2 max-w-3xl mx-auto w-full">
        <button
          type="button"
          onClick={gestisciLike}
          className="inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full bg-[#3a1d2a] border border-rose-300/30 text-rose-200 hover:bg-[#4a2333]"
        >
          <Heart size={16} fill={articolo.liked_by_me ? 'currentColor' : 'none'} />
          {formatCount(articolo.likes_count)}
        </button>
        <span className="inline-flex items-center gap-1 text-sm px-3 py-1.5 rounded-full bg-[#1f253d] border border-sky-300/30 text-sky-200">
          <MessageCircle size={16} /> {formatCount(articolo.comments_count)}
        </span>
      </div>

      <section className="px-4 md:px-8 pb-6 max-w-3xl mx-auto w-full space-y-3">
        {errore && <p className="text-xs text-red-300">{errore}</p>}

        <form onSubmit={inviaCommento} className="flex gap-2">
          <input
            value={nuovoCommento}
            onChange={(e) => setNuovoCommento(e.target.value)}
            placeholder="Scrivi un commento…"
            className="flex-1 bg-gray-900/80 border border-gray-700 rounded-xl px-3 py-2 text-sm"
          />
          <button
            type="submit"
            disabled={inviando || !nuovoCommento.trim()}
            className="inline-flex items-center gap-1 px-3 py-2 rounded-xl bg-fuchsia-700 hover:bg-fuchsia-600 disabled:opacity-50 text-sm font-semibold"
          >
            <Send size={15} /> Invia
          </button>
        </form>

        {commenti.length === 0 && <p className="text-xs text-gray-500">Nessun commento.</p>}
        {commenti.map((commento) => (
          <div key={commento.id} className="rounded-xl border border-white/10 bg-black/25 p-2.5">
            <div className="flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 min-w-0">
                {commento.autore_avatar && (
                  <img src={commento.autore_avatar} alt="" className="w-6 h-6 rounded-full object-cover" />
                )}
                <span className="text-xs font-semibold text-amber-100 truncate">{commento.autore_nome}</span>
                <span className="text-[10px] text-gray-500">
                  {new Date(commento.created_at).toLocaleString('it-IT')}
                </span>
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <button
                  type="button"
                  onClick={() => likeCommento(commento.id)}
                  className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-full bg-[#3a1d2a] border border-rose-300/25 text-rose-200"
                >
                  <Heart size={12} fill={commento.liked_by_me ? 'currentColor' : 'none'} />
                  {formatCount(commento.likes_count)}
                </button>
                {commento.can_delete && (
                  <button
                    type="button"
                    onClick={() => rimuoviCommento(commento.id)}
                    className="text-[11px] px-2 py-1 rounded-full bg-[#3b1a1f] border border-red-300/25 text-red-200"
                    title="Elimina commento"
                  >
                    <Trash2 size={12} />
                  </button>
                )}
              </div>
            </div>
            <p className="text-sm text-gray-200 mt-1 whitespace-pre-wrap">{commento.testo}</p>
          </div>
        ))}
      </section>
    </article>
  );
}
