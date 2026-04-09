import React, { useEffect, useState } from 'react';
import { getWikiAura } from '../../api';
import MattoneList from '../wiki/MattoneList';

export default function WidgetAura({ id }) {
  const [aura, setAura] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getWikiAura(id)
       .then(data => setAura(data))
       .catch(err => {
         console.error(`Errore caricamento Aura #${id}`, err);
         setError(true);
       });
  }, [id]);

  if (error) return <div className="text-red-500 text-xs">[Aura #{id} non trovata]</div>;
  if (!aura) return <div className="text-xs text-gray-400 p-2">Caricamento dati aura...</div>;

  return (
    <div className="my-6 p-4 md:p-6 bg-blue-50 border border-blue-200 rounded-xl shadow-sm w-full max-w-full">
      {/* Header Flessibile: Colonna su mobile, Riga su desktop */}
      <div className="flex flex-col md:flex-row justify-between items-start border-b border-blue-200 pb-3 mb-3 gap-2">
          <div>
            <h2 className="text-xl md:text-2xl font-bold text-blue-900 leading-tight">{aura.nome}</h2>
            <div className="text-blue-700 text-xs md:text-sm mt-1 flex flex-wrap gap-3">
                <span className="bg-blue-100 px-2 py-0.5 rounded">⚡ Costo: <strong>{aura.costo_attivazione || '-'}</strong></span>
                <span className="bg-blue-100 px-2 py-0.5 rounded">🔄 Mant: <strong>{aura.mantenimento || '-'}</strong></span>
            </div>
          </div>
          <div className="bg-blue-600 text-white px-2 py-1 rounded text-[10px] md:text-xs uppercase font-bold tracking-wider self-start">
            Aura
          </div>
      </div>

      {aura.descrizione && (
        <div className="mb-4 prose prose-blue prose-sm max-w-none text-gray-700 break-words">
           <div dangerouslySetInnerHTML={{ __html: aura.descrizione }} />
        </div>
      )}

      {aura.mattoni && aura.mattoni.length > 0 && (
        <div className="mt-4">
            <h4 className="font-bold text-blue-900 mb-2 uppercase text-[10px] tracking-wider border-b border-blue-200 inline-block pb-1">
                Effetti e Mattoni
            </h4>
            <MattoneList mattoni={aura.mattoni} />
        </div>
      )}
    </div>
  );
}