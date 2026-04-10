import React, { useEffect, useState } from 'react';
import { getWikiTable } from '../../api'; 
import AbilitaTable from '../wiki/AbilitaTable'; 

export default function WidgetTabellaAbilita({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getWikiTable(id)
       .then(responseData => setData(responseData))
       .catch(err => {
         console.error(`Errore caricamento tabella Wiki #${id}:`, err);
         setError(true);
       });
  }, [id]);

  if (error) return (
    <div className="p-3 border-l-4 border-red-500 bg-red-50 text-red-700 text-sm my-4 rounded">
      <strong>Errore:</strong> Tabella #{id} non trovata.
    </div>
  );

  if (!data) return (
    <div className="animate-pulse flex space-x-4 my-4 p-4 border rounded">
       <div className="h-4 bg-gray-200 rounded w-3/4"></div>
    </div>
  );

  const listaAbilita = data.abilita_selezionate || data.abilita || [];

  return (
    <div className="my-6 w-full max-w-full bg-white rounded-lg shadow-sm border border-gray-200">
      <div className="p-3 md:p-4 border-b border-gray-100 bg-gray-50 rounded-t-lg">
          <h3 className="text-lg md:text-xl font-bold text-red-900 leading-tight">
            {data.titolo}
          </h3>
          {data.descrizione && (
            <div className="mt-2 text-xs md:text-sm text-gray-600 italic break-words" dangerouslySetInnerHTML={{__html: data.descrizione}} />
          )}
      </div>

      <div className="bg-white">
        <AbilitaTable list={listaAbilita} />
      </div>
    </div>
  );
}