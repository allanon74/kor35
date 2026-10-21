import React, { useEffect, useMemo, useState } from 'react';
import { getWikiMattoniWidgetDisplay } from '../../api';
import MattoneWikiCard from './MattoneWikiCard';

function safeText(v) {
  return v == null ? '' : String(v);
}

function sortKeyAuraOrdine(m) {
  const auraOrd = m?.aura?.ordine ?? 0;
  const ordine = m?.ordine ?? 0;
  const nome = safeText(m?.nome).toLowerCase();
  return `${String(auraOrd).padStart(5, '0')}-${String(ordine).padStart(5, '0')}-${nome}`;
}

export default function WidgetMattoni({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    setError(false);
    setData(null);
    getWikiMattoniWidgetDisplay(id)
      .then(res => setData(res))
      .catch(err => {
        console.error(`Errore caricamento Mattoni widget #${id}:`, err);
        setError(true);
      });
  }, [id]);

  const mattoni = useMemo(() => {
    const list = Array.isArray(data?.mattoni) ? data.mattoni : [];
    return [...list].sort((a, b) => sortKeyAuraOrdine(a).localeCompare(sortKeyAuraOrdine(b)));
  }, [data]);

  if (error) {
    return <div className="text-red-500 text-xs border border-red-300 p-2 rounded bg-red-50">Widget Mattoni #{id} non disponibile.</div>;
  }
  if (!data) {
    return <div className="animate-pulse h-20 bg-gray-200 rounded my-4"></div>;
  }

  return (
    <div className="wiki-widget-mattoni my-6 w-full max-w-full break-inside-avoid">
      {data.title && (
        <div className="mb-3">
          <h3 className="text-base md:text-lg font-bold text-gray-800">{data.title}</h3>
        </div>
      )}

      {mattoni.length === 0 ? (
        <div className="text-xs text-gray-600 border border-gray-200 bg-gray-50 rounded p-3">
          Nessun mattone da mostrare.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3 p-2">
          {mattoni.map((m) => (
            <MattoneWikiCard key={m.id} mattone={m} />
          ))}
        </div>
      )}
    </div>
  );
}

