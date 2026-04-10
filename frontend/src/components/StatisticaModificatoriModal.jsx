import React, { useState, useEffect } from 'react';
import { fetchAuthenticated } from '../api';
import { X, Plus, Percent, TrendingUp } from 'lucide-react';

const StatisticaModificatoriModal = ({ punteggio, personaggioId, onClose, onLogout }) => {
  const [dettagli, setDettagli] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchDettagli = async () => {
      try {
        setLoading(true);
        setError(null);
        
        const url = `/api/personaggi/api/personaggi/${personaggioId}/modificatori-dettagliati/?parametro=${punteggio.parametro}`;
        const response = await fetchAuthenticated(url, { method: 'GET' }, onLogout);
        
        // La risposta è un oggetto con una chiave uguale al parametro
        const datiParametro = response[punteggio.parametro];
        
        if (datiParametro) {
          setDettagli(datiParametro);
        } else {
          setError('Nessun dato trovato per questa statistica');
        }
      } catch (err) {
        console.error('Errore nel caricamento dei modificatori:', err);
        setError(err.message || 'Errore nel caricamento dei dettagli');
      } finally {
        setLoading(false);
      }
    };

    if (punteggio?.parametro && personaggioId) {
      fetchDettagli();
    }
  }, [punteggio, personaggioId, onLogout]);

  if (!punteggio) return null;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4"
      onClick={onClose}
    >
      <div 
        className="flex flex-col w-full max-w-2xl max-h-[90vh] bg-gray-800 rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gradient-to-r from-indigo-900 to-gray-800">
          <div className="flex items-center gap-3">
            <div 
              className="w-10 h-10 rounded-full flex items-center justify-center text-lg font-bold shadow-lg"
              style={{ backgroundColor: punteggio.colore || '#6366f1' }}
            >
              {punteggio.nome?.charAt(0) || '?'}
            </div>
            <div>
              <h2 className="text-xl font-bold text-white">{punteggio.nome}</h2>
              <p className="text-sm text-gray-300">Dettaglio Calcolo</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Chiudi"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 p-6 overflow-y-auto bg-gray-900">
          {loading && (
            <div className="text-center py-8">
              <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-500"></div>
              <p className="mt-4 text-gray-400">Caricamento dettagli...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-900/50 border border-red-500 rounded-lg p-4 text-red-200">
              <strong>Errore:</strong> {error}
            </div>
          )}

          {!loading && !error && dettagli && (
            <div className="space-y-6">
              {/* Valore Base */}
              <div className="bg-gray-800 rounded-lg p-4 border border-gray-700">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5 text-blue-400" />
                    <span className="text-gray-300 font-semibold">Valore Base</span>
                  </div>
                  <span className="text-2xl font-bold text-white">
                    {dettagli.valore_base}
                  </span>
                </div>
              </div>

              {/* Modificatori */}
              {dettagli.modificatori && dettagli.modificatori.length > 0 ? (
                <div className="space-y-3">
                  <h3 className="text-lg font-semibold text-gray-200 flex items-center gap-2">
                    <div className="w-1 h-6 bg-indigo-500 rounded"></div>
                    Modificatori Applicati
                  </h3>
                  
                  {dettagli.modificatori.map((mod, index) => (
                    <div 
                      key={index}
                      className="bg-gray-800 rounded-lg p-4 border border-gray-700 hover:border-indigo-500 transition-colors"
                    >
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="flex items-center gap-2 mb-1">
                            {mod.tipo === 'add' ? (
                              <Plus className="w-4 h-4 text-green-400" />
                            ) : (
                              <Percent className="w-4 h-4 text-purple-400" />
                            )}
                            <span className="text-gray-300 font-medium">{mod.fonte}</span>
                          </div>
                          <span className="text-xs text-gray-500 uppercase tracking-wider">
                            {mod.tipo === 'add' ? 'Modificatore Additivo' : 'Modificatore Moltiplicativo'}
                          </span>
                        </div>
                        <div className="text-right">
                          <div className={`text-xl font-bold ${
                            mod.tipo === 'add' 
                              ? mod.valore >= 0 ? 'text-green-400' : 'text-red-400'
                              : 'text-purple-400'
                          }`}>
                            {mod.tipo === 'add' 
                              ? (mod.valore >= 0 ? `+${mod.valore}` : mod.valore)
                              : `×${mod.valore}`
                            }
                          </div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="bg-gray-800 rounded-lg p-6 border border-gray-700 text-center">
                  <p className="text-gray-400">Nessun modificatore attivo per questa statistica</p>
                </div>
              )}

              {/* Calcolo Finale */}
              <div className="bg-gradient-to-r from-indigo-900 to-gray-800 rounded-lg p-4 border border-indigo-600">
                <div className="flex justify-between items-center mb-2">
                  <span className="text-gray-300 font-semibold text-lg">Formula di Calcolo</span>
                </div>
                <div className="text-sm text-gray-400 font-mono mb-3">
                  ({dettagli.valore_base} + {dettagli.add_totale || 0}) × {dettagli.mol_totale || 1}
                </div>
                <div className="flex justify-between items-center pt-3 border-t border-indigo-700">
                  <span className="text-xl font-bold text-white">Valore Finale</span>
                  <span className="text-3xl font-bold text-indigo-400">
                    {dettagli.valore_finale}
                  </span>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 bg-gray-800 text-center">
          <button
            onClick={onClose}
            className="px-6 py-2 font-bold text-white bg-indigo-600 rounded-md shadow-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500 transition-colors"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};

export default StatisticaModificatoriModal;
