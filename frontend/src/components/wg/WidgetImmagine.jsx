import React, { useEffect, useState } from 'react';
import { getWikiImage } from '../../api';
import { getMediaUrl } from '../../api';

export default function WidgetImmagine({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    getWikiImage(id)
       .then(res => setData(res))
       .catch(err => {
         console.error(`Errore caricamento Immagine #${id}:`, err);
         setError(true);
       });
  }, [id]);

  if (error) {
    return (
      <div className="text-red-500 text-xs border border-red-300 p-2 rounded bg-red-50 my-4">
        Immagine #{id} non disponibile.
      </div>
    );
  }

  if (!data) {
    return <div className="animate-pulse h-40 bg-gray-200 rounded my-4"></div>;
  }

  // Determina le classi CSS per l'allineamento con supporto responsive
  const alignmentClasses = {
    // Su mobile (< md), tutte le immagini sono centrate e occupano tutta la larghezza
    // Su desktop, mantengono l'allineamento specificato
    'left': 'md:float-left md:mr-4 mb-4 mx-auto md:mx-0',
    'right': 'md:float-right md:ml-4 mb-4 mx-auto md:mx-0',
    'center': 'mx-auto block mb-4',
    'full': 'w-full block mb-4'
  };

  const alignmentClass = alignmentClasses[data.allineamento] || alignmentClasses['center'];

  // Determina lo stile per la larghezza
  const imageStyle = {};
  if (data.larghezza_max > 0 && data.allineamento !== 'full') {
    imageStyle.maxWidth = `${data.larghezza_max}px`;
    // Assicura che l'immagine si adatti al container su schermi piccoli
    imageStyle.width = '100%';
  }

  return (
    <figure className={`my-6 ${alignmentClass}`} style={imageStyle}>
      <img 
        src={data.immagine_url || getMediaUrl(data.immagine)}
        alt={data.titolo || 'Immagine wiki'}
        className={`rounded-lg shadow-md w-full h-auto ${
          data.allineamento === 'full' ? '' : 'max-w-full'
        }`}
      />
      {(data.titolo || data.descrizione) && (
        <figcaption className="mt-2 text-sm text-gray-600 italic text-center">
          {data.titolo && <strong>{data.titolo}</strong>}
          {data.titolo && data.descrizione && ' — '}
          {data.descrizione && <span dangerouslySetInnerHTML={{ __html: data.descrizione }} />}
        </figcaption>
      )}
    </figure>
  );
}
