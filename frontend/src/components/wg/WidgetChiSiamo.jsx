import React, { useEffect, useState } from 'react';
import { Users, MapPin, Calendar, Mail, AlertCircle } from 'lucide-react';
import { getConfigurazioneSito } from '../../api';

/**
 * Widget Chi Siamo - Mostra informazioni sull'associazione dal database
 * I dati sono modificabili tramite l'admin Django in "Configurazione Sito"
 */
export default function WidgetChiSiamo() {
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getConfigurazioneSito()
      .then(res => {
        setConfig(res);
        setLoading(false);
      })
      .catch(err => {
        console.error('Errore caricamento configurazione sito:', err);
        setError(true);
        setLoading(false);
      });
  }, []);

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            <div className="h-4 bg-gray-100 rounded"></div>
            <div className="h-4 bg-gray-100 rounded w-5/6"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error || !config) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-red-200">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle size={24} />
          <p>Errore nel caricamento delle informazioni</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-gray-200">
        <Users className="text-red-700" size={28} />
        <h3 className="text-xl font-bold text-gray-800">Chi Siamo</h3>
      </div>
      
      <div className="space-y-4 text-gray-700">
        <p className="leading-relaxed">
          <strong>{config.nome_associazione}</strong> {config.descrizione_breve}
        </p>
        
        <div className="grid md:grid-cols-2 gap-4 mt-4">
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <MapPin className="text-red-700 flex-shrink-0 mt-1" size={20} />
            <div>
              <h4 className="font-semibold text-sm text-gray-800 mb-1">Sede</h4>
              <p className="text-sm text-gray-600">
                {config.indirizzo}<br />
                {config.cap} {config.citta} ({config.provincia})<br />
                {config.nazione}
              </p>
            </div>
          </div>
          
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
            <Calendar className="text-red-700 flex-shrink-0 mt-1" size={20} />
            <div>
              <h4 className="font-semibold text-sm text-gray-800 mb-1">Fondata nel</h4>
              <p className="text-sm text-gray-600">{config.anno_fondazione}</p>
            </div>
          </div>
          
          <div className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg md:col-span-2">
            <Mail className="text-red-700 flex-shrink-0 mt-1" size={20} />
            <div>
              <h4 className="font-semibold text-sm text-gray-800 mb-1">Contatti</h4>
              <p className="text-sm text-gray-600">
                Email: <a href={`mailto:${config.email}`} className="text-red-700 hover:underline">{config.email}</a>
                {config.pec && (
                  <>
                    <br />
                    PEC: <a href={`mailto:${config.pec}`} className="text-red-700 hover:underline">{config.pec}</a>
                  </>
                )}
                {config.telefono && (
                  <>
                    <br />
                    Tel: <a href={`tel:${config.telefono}`} className="text-red-700 hover:underline">{config.telefono}</a>
                  </>
                )}
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
