import React, { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { Clock, MapPin, Navigation, ArrowLeft } from 'lucide-react';
import { getEventoPubblicoDettaglio } from '../api';
import { RichTextViewer } from '../components/RichTextDisplay';
import { RICH_TEXT_SHARED_STYLES } from '../styles/richTextSharedStyles';

function formatDate(dateString) {
  const date = new Date(dateString);
  return date.toLocaleDateString('it-IT', {
    day: '2-digit',
    month: 'long',
    year: 'numeric',
  });
}

export default function EventoLogisticaPage() {
  const { id } = useParams();
  const [evento, setEvento] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await getEventoPubblicoDettaglio(id);
        if (mounted) setEvento(data);
      } catch {
        if (mounted) setError('Informazioni logistiche non disponibili per questo evento.');
      } finally {
        if (mounted) setLoading(false);
      }
    };
    load();
    return () => {
      mounted = false;
    };
  }, [id]);

  if (loading) {
    return <div className="p-8 text-center text-gray-500">Caricamento informazioni evento…</div>;
  }

  if (error) {
    return (
      <div className="max-w-3xl mx-auto p-8 text-center">
        <p className="text-red-600 mb-4">{error}</p>
        <Link to="/" className="text-red-800 font-bold hover:underline inline-flex items-center gap-2">
          <ArrowLeft size={16} />
          Torna alla home
        </Link>
      </div>
    );
  }

  if (!evento) return null;

  const links = evento.link_navigatore;
  const hasCoords = !!links;

  return (
    <div className="max-w-3xl mx-auto px-4 py-8">
      <style>{RICH_TEXT_SHARED_STYLES}</style>

      <Link
        to="/"
        className="inline-flex items-center gap-2 text-sm text-gray-500 hover:text-red-800 mb-6 font-medium"
      >
        <ArrowLeft size={16} />
        Torna alla home
      </Link>

      <article className="bg-white rounded-xl shadow-md border border-gray-200 overflow-hidden">
        <header className="bg-gradient-to-r from-red-800 to-red-900 text-white p-6 md:p-8">
          <p className="text-xs font-bold uppercase tracking-widest text-white/70 mb-2">Informazioni evento</p>
          <h1 className="text-2xl md:text-3xl font-black leading-tight">{evento.titolo}</h1>
          <div className="mt-4 flex flex-wrap gap-4 text-sm text-white/90">
            <span className="inline-flex items-center gap-1.5">
              <Clock size={15} />
              {formatDate(evento.data_inizio)}
              {evento.data_fine && evento.data_fine !== evento.data_inizio && (
                <> – {formatDate(evento.data_fine)}</>
              )}
            </span>
            {evento.luogo && (
              <span className="inline-flex items-center gap-1.5">
                <MapPin size={15} />
                {evento.luogo}
              </span>
            )}
          </div>
        </header>

        <div className="p-6 md:p-8 space-y-8">
          {evento.logistiche_pubbliche && (
            <section>
              <h2 className="text-sm font-black uppercase tracking-widest text-gray-500 mb-3">
                Indicazioni logistiche
              </h2>
              <div className="wiki-content prose prose-sm max-w-none text-gray-700 leading-relaxed">
                <RichTextViewer content={evento.logistiche_pubbliche} textTone="onLight" />
              </div>
            </section>
          )}

          {hasCoords && (
            <section className="rounded-xl border border-emerald-200 bg-emerald-50 p-5">
              <h2 className="text-sm font-black uppercase tracking-widest text-emerald-800 mb-3 flex items-center gap-2">
                <Navigation size={16} />
                Raggiungere il luogo
              </h2>
              {(evento.latitudine != null && evento.longitudine != null) && (
                <p className="text-sm text-emerald-900/80 mb-4 font-mono">
                  {evento.latitudine}, {evento.longitudine}
                </p>
              )}
              <div className="flex flex-wrap gap-3">
                <a
                  href={links.geo}
                  className="inline-flex items-center gap-2 rounded-lg bg-emerald-700 px-4 py-2.5 text-sm font-bold text-white hover:bg-emerald-800 shadow"
                >
                  <Navigation size={16} />
                  Apri nel navigatore
                </a>
                <a
                  href={links.google_maps}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100"
                >
                  Google Maps
                </a>
                <a
                  href={links.apple_maps}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100"
                >
                  Apple Maps
                </a>
                <a
                  href={links.waze}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 rounded-lg border border-emerald-300 bg-white px-4 py-2.5 text-sm font-bold text-emerald-800 hover:bg-emerald-100"
                >
                  Waze
                </a>
              </div>
            </section>
          )}

          {evento.sinossi && (
            <section>
              <h2 className="text-sm font-black uppercase tracking-widest text-gray-500 mb-3">
                Sinossi
              </h2>
              <div className="wiki-content prose prose-sm max-w-none text-gray-600">
                <RichTextViewer content={evento.sinossi} textTone="onLight" />
              </div>
            </section>
          )}
        </div>
      </article>
    </div>
  );
}
