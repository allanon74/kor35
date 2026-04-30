import React, { useEffect, useMemo, useState } from 'react';
import { getWikiEraDisplay } from '../../api';

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
        <div className="p-3 md:p-4 text-xs md:text-sm text-gray-800 border-b border-gray-200 italic bg-amber-50/50">
          {data.descrizione_breve}
        </div>
      )}

      {hasDifetto && (
        <div className="p-3 md:p-4 border-b border-gray-200 bg-gray-50">
          <h4 className="text-xs md:text-sm font-semibold text-gray-900 mb-1">
            {data.difetto_interpretativo_titolo || 'Difetto comportamentale'}
          </h4>
          {data.difetto_interpretativo_testo ? (
            <p className="text-xs md:text-sm text-gray-700 whitespace-pre-wrap">{data.difetto_interpretativo_testo}</p>
          ) : (
            <p className="text-xs text-gray-500">Nessuna descrizione disponibile.</p>
          )}
        </div>
      )}

      <div className="p-3 md:p-4">
        <h4 className="text-xs md:text-sm font-semibold text-gray-900 mb-2">Abilita assegnate automaticamente</h4>
        {abilitaAutomatiche.length === 0 ? (
          <p className="text-xs text-gray-500">Nessuna abilita automatica configurata.</p>
        ) : (
          <ul className="space-y-2">
            {abilitaAutomatiche.map((a) => (
              <li key={a.id} className="text-xs md:text-sm text-gray-800">
                <span className="font-semibold">{a.nome}</span>
                {a.descrizione && <span className="text-gray-600"> - {a.descrizione}</span>}
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
