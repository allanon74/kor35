import React, { useEffect, useState } from 'react';
import { Calendar, MapPin, Clock, AlertCircle } from 'lucide-react';
import { getEventiPubblici } from '../../api';

/**
 * Widget Eventi - Mostra gli eventi pubblici futuri e recenti
 * Non richiede un ID, recupera automaticamente gli eventi dal backend
 */
export default function WidgetEventi() {
  const [eventi, setEventi] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getEventiPubblici()
      .then(res => {
        setEventi(res);
        setLoading(false);
      })
      .catch(err => {
        console.error('Errore caricamento eventi:', err);
        setError(true);
        setLoading(false);
      });
  }, []);

  // Formatta la data in formato leggibile
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('it-IT', {
      day: '2-digit',
      month: 'long',
      year: 'numeric'
    });
  };

  // Determina se l'evento è nel futuro
  const isFuturo = (dataInizio) => {
    return new Date(dataInizio) > new Date();
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            <div className="h-20 bg-gray-100 rounded"></div>
            <div className="h-20 bg-gray-100 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-red-200">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle size={24} />
          <p>Errore nel caricamento degli eventi</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-gray-200">
        <Calendar className="text-red-700" size={28} />
        <h3 className="text-xl font-bold text-gray-800">Eventi</h3>
      </div>
      
      {eventi.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Calendar size={48} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Nessun evento in programma al momento</p>
          <p className="text-sm mt-1">Controlla più tardi per aggiornamenti</p>
        </div>
      ) : (
        <div className="space-y-4">
          {eventi.map((evento) => (
            <div 
              key={evento.id} 
              className={`p-4 rounded-lg border-l-4 transition-all hover:shadow-md ${
                isFuturo(evento.data_inizio) 
                  ? 'bg-green-50 border-green-500' 
                  : 'bg-gray-50 border-gray-400'
              }`}
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex-1">
                  <h4 className="font-bold text-gray-800 mb-2 flex items-center gap-2">
                    {evento.titolo}
                    {isFuturo(evento.data_inizio) && (
                      <span className="text-xs bg-green-500 text-white px-2 py-0.5 rounded-full font-normal">
                        Prossimo
                      </span>
                    )}
                  </h4>
                  
                  {evento.sinossi && (
                    <p className="text-sm text-gray-600 mb-3 leading-relaxed">
                      {evento.sinossi}
                    </p>
                  )}
                  
                  <div className="flex flex-wrap gap-3 text-xs text-gray-500">
                    <div className="flex items-center gap-1.5">
                      <Clock size={14} className="text-red-700" />
                      <span>
                        {formatDate(evento.data_inizio)}
                        {evento.data_fine && evento.data_fine !== evento.data_inizio && (
                          <> - {formatDate(evento.data_fine)}</>
                        )}
                      </span>
                    </div>
                    
                    {evento.luogo && (
                      <div className="flex items-center gap-1.5">
                        <MapPin size={14} className="text-red-700" />
                        <span>{evento.luogo}</span>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))}
          
          {eventi.length > 0 && (
            <div className="mt-4 text-center">
              <p className="text-xs text-gray-500 italic">
                Vengono mostrati gli eventi degli ultimi 30 giorni e quelli futuri
              </p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
