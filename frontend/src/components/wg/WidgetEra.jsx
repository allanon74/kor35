import React, { useEffect, useMemo, useState } from 'react';
import { getWikiEraDisplay } from '../../api';
import { sanitizeHtml } from '../../utils/htmlSanitizer';

function HtmlContent({ html, className }) {
  if (!html) return null;
  return <div className={className} dangerouslySetInnerHTML={{ __html: sanitizeHtml(html) }} />;
}

export default function WidgetEra({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);
    getWikiEraDisplay(id)
      .then((res) => setData(res))
      .catch((err) => {
        console.error(`Errore caricamento Era widget #${id}:`, err);
        setError(true);
      });
  }, [id]);

  const abilitaAutomatiche = useMemo(
    () => (Array.isArray(data?.abilita_automatiche) ? data.abilita_automatiche : []),
    [data]
  );

  if (error) {
    return <div className="text-red-500 text-xs border border-red-300 p-2 rounded bg-red-50">Widget Era #{id} non disponibile.</div>;
  }
  if (!data) {
    return <div className="animate-pulse h-20 bg-gray-200 rounded my-4"></div>;
  }

  const hasDifetto = Boolean(data.difetto_interpretativo_titolo || data.difetto_interpretativo_testo);

  return (
    <div className="wiki-widget-era my-6 w-full max-w-full border border-amber-300 rounded-lg bg-white shadow-sm break-inside-avoid overflow-hidden">
      <div className="p-3 md:p-4 bg-gradient-to-r from-amber-700 to-orange-700 text-white">
        <h3 className="text-base md:text-xl font-bold uppercase tracking-wider leading-tight">{data.nome}</h3>
      </div>

      {data.descrizione_breve && (
        <div className="p-3 md:p-4 border-b border-gray-200 italic bg-amber-50/50">
          <HtmlContent
            html={data.descrizione_breve}
            className="prose prose-sm max-w-none text-xs md:text-sm text-gray-800"
          />
        </div>
      )}

      {hasDifetto && (
        <div className="p-3 md:p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="text-xs md:text-sm font-semibold text-gray-900 mb-1">
            {data.difetto_interpretativo_titolo || 'Difetto comportamentale'}
          </h4>
          {data.difetto_interpretativo_testo ? (
            <HtmlContent
              html={data.difetto_interpretativo_testo}
              className="prose prose-sm max-w-none text-xs md:text-sm text-gray-700"
            />
          ) : (
            <p className="text-xs text-gray-500">Nessuna descrizione disponibile.</p>
          )}
        </div>
      )}

      {abilitaAutomatiche.length === 0 ? (
        <div className="p-3 md:p-4">
          <p className="text-xs text-gray-500">Nessuna abilita automatica configurata.</p>
        </div>
      ) : (
        abilitaAutomatiche.map((a) => (
          <div key={a.id} className="p-3 md:p-4 border-t border-gray-200 bg-gray-50">
            <h4 className="text-xs md:text-sm font-semibold text-gray-900 mb-1">{a.nome}</h4>
            {a.descrizione ? (
              <HtmlContent
                html={a.descrizione}
                className="prose prose-sm max-w-none text-xs md:text-sm text-gray-700"
              />
            ) : (
              <p className="text-xs text-gray-500">Nessuna descrizione disponibile.</p>
            )}
          </div>
        ))
      )}
    </div>
  );
}
