import React, { useState, useEffect } from 'react';
import { X, Loader2, Zap, Swords, Lock, Battery, Clock } from 'lucide-react';
import { getOggettoDetail } from '../api';
import PunteggioDisplay from './PunteggioDisplay';

const formatDuration = (seconds) => {
    if (!seconds) return "";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    
    const parts = [];
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    if (s > 0 || parts.length === 0) parts.push(`${s}s`);
    
    return parts.join(' ');
};

const ModuloDetailModal = ({ moduloId, onClose, onLogout }) => {
  const [modulo, setModulo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!moduloId) return;

    const fetchDetails = async () => {
      try {
        setLoading(true);
        const data = await getOggettoDetail(moduloId, onLogout);
        setModulo(data);
        setError(null);
      } catch (err) {
        console.error('Errore caricamento dettagli modulo:', err);
        setError('Impossibile caricare i dettagli del modulo.');
      } finally {
        setLoading(false);
      }
    };

    fetchDetails();
  }, [moduloId, onLogout]);

  if (!moduloId) return null;

  // Render Componenti (Mattoni)
  const renderComponents = (componenti) => {
    if (!componenti || componenti.length === 0) return null;
    return (
      <div className="flex flex-wrap gap-1 items-center">
        {componenti.map((comp, idx) => {
          if (!comp.caratteristica) return null;
          return (
            <PunteggioDisplay
              key={idx}
              punteggio={comp.caratteristica}
              value={comp.valore || 1}
              displayText="abbr"
              iconType="inv_circle"
              size="badge"
              readOnly={true}
              className="shrink-0"
            />
          );
        })}
      </div>
    );
  };

  // Render Statistiche
  const renderStats = (statistiche) => {
    if (!statistiche || statistiche.length === 0) return null;
    const activeStats = statistiche.filter(s => s.valore !== 0);
    if (activeStats.length === 0) return null;

    return (
      <div className="flex flex-wrap gap-2 mt-2">
        {activeStats.map((stat, idx) => {
          const hasCondition = stat.usa_limitazione_aura || stat.usa_limitazione_elemento || stat.usa_condizione_text;
          const conditionTitle = stat.condizione_text || "Condizionale";
          
          return (
            <div key={idx} className="flex items-center bg-gray-900 border border-gray-600 rounded px-2 py-1 text-xs shadow-sm">
              <span className="font-bold text-gray-300 mr-1">{stat.statistica.nome}</span>
              <span className={`font-mono font-bold ${stat.valore > 0 ? 'text-green-400' : 'text-red-400'}`}>
                {stat.valore > 0 ? '+' : ''}{stat.valore}
              </span>
              {hasCondition && (
                <div className="ml-1 text-amber-500" title={conditionTitle}>
                  <Lock size={10} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-2xl bg-gray-800 rounded-lg shadow-2xl overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-indigo-400 flex items-center gap-2">
            <Zap size={20} /> Dettagli Modulo
          </h2>
          <button 
            onClick={onClose}
            className="text-gray-400 hover:text-white transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="p-4 max-h-[70vh] overflow-y-auto">
          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="animate-spin text-indigo-400" size={32} />
            </div>
          )}

          {error && (
            <div className="bg-red-900/20 border border-red-500 text-red-400 p-4 rounded-lg">
              {error}
            </div>
          )}

          {modulo && !loading && (
            <div className="space-y-4">
              {/* Header con Aura e Nome */}
              <div className="flex items-start gap-4">
                {modulo.aura ? (
                  <div className="shrink-0">
                    <PunteggioDisplay
                      punteggio={modulo.aura}
                      value={null}
                      displayText="none"
                      iconType="inv_circle"
                      size="m"
                      readOnly={true}
                    />
                  </div>
                ) : null}
                
                <div className="flex-1">
                  <h3 className="text-2xl font-bold text-white mb-1">{modulo.nome}</h3>
                  <div className="flex items-center gap-2 text-xs text-gray-400 uppercase">
                    <span>{modulo.tipo_oggetto_display}</span>
                    {modulo.classe_oggetto_nome && (
                      <>
                        <span>•</span>
                        <span>{modulo.classe_oggetto_nome}</span>
                      </>
                    )}
                    {modulo.livello > 0 && (
                      <>
                        <span>•</span>
                        <span className="text-gray-300 font-mono">Lv.{modulo.livello}</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Componenti (Mattoni) */}
                <div className="shrink-0">
                  {renderComponents(modulo.componenti)}
                </div>
              </div>

              {/* Attacco */}
              {modulo.attacco_formattato && (
                <div className="bg-red-900/20 border border-red-900/40 p-3 rounded-lg flex items-center gap-2 text-red-300 text-sm font-bold shadow-inner">
                  <Swords size={16} />
                  <span>ATTACCO: {modulo.attacco_formattato}</span>
                </div>
              )}

              {/* Statistiche */}
              {modulo.statistiche && modulo.statistiche.length > 0 && (
                <div>
                  <h4 className="text-xs font-bold text-gray-400 uppercase mb-2">Modificatori</h4>
                  {renderStats(modulo.statistiche)}
                </div>
              )}

              {/* Descrizione */}
              <div className="bg-black/20 border border-gray-700/50 p-3 rounded-lg">
                <h4 className="text-xs font-bold text-gray-400 uppercase mb-2">Descrizione</h4>
                <div 
                  className="text-sm text-gray-300 prose prose-invert prose-sm max-w-none leading-relaxed"
                  dangerouslySetInnerHTML={{ 
                    __html: modulo.testo_formattato_personaggio || modulo.testo || modulo.descrizione || "Nessuna descrizione disponibile." 
                  }} 
                />
              </div>

              {/* Info Cariche e Durata */}
              {(modulo.cariche_massime > 0 || modulo.durata_totale > 0) && (
                <div className="bg-black/30 border border-gray-600/50 p-3 rounded-lg">
                  <h4 className="text-xs font-bold text-gray-400 uppercase mb-2">Energia</h4>
                  
                  {modulo.cariche_massime > 0 && (
                    <div className="flex items-center gap-2 text-sm mb-2">
                      <Battery size={14} className={modulo.cariche_attuali === 0 ? 'text-red-500' : 'text-yellow-500'} />
                      <span className="text-gray-300">
                        Cariche: <span className="font-bold font-mono">{modulo.cariche_attuali} / {modulo.cariche_massime}</span>
                      </span>
                    </div>
                  )}

                  {modulo.durata_totale > 0 && (
                    <div className="flex items-center gap-2 text-sm">
                      <Clock size={14} className="text-blue-400" />
                      <span className="text-gray-300">
                        Durata: <span className="font-bold">{formatDuration(modulo.durata_totale)}</span>
                      </span>
                    </div>
                  )}

                  {modulo.data_fine_attivazione && (
                    <div className="mt-2 pt-2 border-t border-gray-700 text-xs text-orange-400 font-mono">
                      Scade: {new Date(modulo.data_fine_attivazione).toLocaleString()}
                    </div>
                  )}

                  {modulo.costo_ricarica > 0 && (
                    <div className="mt-2 text-xs text-gray-500">
                      Costo ricarica: <span className="font-bold text-yellow-300">{modulo.costo_ricarica} CR</span>
                    </div>
                  )}
                </div>
              )}

              {/* Potenziamenti Installati (se il modulo ne ha) */}
              {modulo.potenziamenti_installati && modulo.potenziamenti_installati.length > 0 && (
                <div className="bg-indigo-900/10 border border-indigo-500/30 p-3 rounded-lg">
                  <h4 className="text-xs font-bold text-indigo-400 uppercase mb-2 flex items-center gap-2">
                    <Zap size={12} /> Sub-Moduli
                  </h4>
                  <div className="space-y-2">
                    {modulo.potenziamenti_installati.map(submod => (
                      <div key={submod.id} className="bg-black/30 border border-gray-700/50 p-2 rounded text-xs">
                        <div className="flex justify-between items-start mb-1">
                          <div>
                            <span className="font-bold text-indigo-200">{submod.nome}</span>
                            <span className="text-gray-500 text-[10px] ml-2">{submod.tipo_oggetto_display}</span>
                          </div>
                          {renderComponents(submod.componenti)}
                        </div>
                        {renderStats(submod.statistiche)}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t border-gray-700 text-center">
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

export default ModuloDetailModal;
