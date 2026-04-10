import React from 'react';
import { X } from 'lucide-react';
import PunteggioDisplay from './PunteggioDisplay.jsx';

const TecnicaDetailModal = ({ tecnica, onClose, type = 'tecnica' }) => {
  if (!tecnica) return null;

  const testoDescrizione = tecnica.testo_formattato_personaggio || tecnica.TestoFormattato || tecnica.testo;

  // LOGICA COSTI:
  // costo_pieno e costo_effettivo arrivano dal serializer backend.
  // Se mancano, usiamo il fallback standard (livello * 100).
  const costoPieno = tecnica.costo_pieno ?? (tecnica.costo_crediti || tecnica.livello * 100);
  const costoEffettivo = tecnica.costo_effettivo ?? costoPieno;
  const hasDiscount = costoEffettivo < costoPieno;

  return (
    <div 
      className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="relative w-full max-w-lg p-6 bg-gray-800 rounded-xl shadow-2xl border border-gray-700 max-h-[90vh] overflow-y-auto transform transition-all animate-slideIn"
        onClick={(e) => e.stopPropagation()} 
      >
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors"
        >
          <X size={24} />
        </button>
        
        {/* Header con Aura */}
        <div className="flex items-start justify-between pr-10 mb-6">
            <div>
                <h2 className="text-2xl font-bold text-indigo-400 leading-tight mb-1">
                {tecnica.nome}
                </h2>
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider border border-gray-600 px-2 py-0.5 rounded">
                    {type} - Livello {tecnica.livello}
                </span>
            </div>
            {tecnica.aura_richiesta && (
                <div className="shrink-0 ml-3">
                    <PunteggioDisplay
                        punteggio={tecnica.aura_richiesta}
                        displayText="none"
                        iconType="inv_circle"
                        size="m"
                    />
                </div>
            )}
        </div>
        
        {/* Corpo del testo formattato */}
        <div className="bg-gray-900/60 p-4 rounded-lg border border-gray-700/50 mb-6 shadow-inner">
            {testoDescrizione ? (
            <div
                className="text-gray-300 prose prose-invert prose-sm max-w-none leading-relaxed" 
                dangerouslySetInnerHTML={{ __html: testoDescrizione }}
            />
            ) : (
            <p className="text-gray-500 italic text-sm">Nessuna descrizione disponibile.</p>
            )}
        </div>

        {/* Mattoni Componenti */}
        {tecnica.mattoni && tecnica.mattoni.length > 0 && (
          <div className="mb-6">
            <h3 className="text-xs font-bold text-gray-400 uppercase mb-3 tracking-wider">Mattoni Componenti</h3>
            <div className="flex flex-wrap gap-3">
              {tecnica.mattoni.map((m, idx) => (
                <div key={idx} className="scale-90 origin-top-left">
                    <PunteggioDisplay
                        punteggio={m.mattone}
                        displayText="name"
                        iconType="inv_circle"
                        size="s"
                    />
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Footer: Info Costo e Aura Secondaria */}
        <div className="mt-2 pt-4 border-t border-gray-700 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-2 text-xs text-gray-400 font-mono">
            
            {/* VISUALIZZAZIONE PREZZO BARRATO */}
            <div className="bg-gray-900 px-3 py-1.5 rounded flex items-center gap-2">
                <span className="text-gray-500">Costo:</span>
                {hasDiscount && (
                    <span className="text-red-400 line-through decoration-red-500 opacity-70 mr-1">
                        {costoPieno}
                    </span>
                )}
                <span className={`font-bold ${hasDiscount ? 'text-green-400' : 'text-yellow-500'}`}>
                    {costoEffettivo} CR
                </span>
            </div>
            
            {tecnica.aura_infusione && (
                <span className="flex items-center gap-2">
                    Aura Secondaria: 
                    <span className="text-indigo-300 font-bold">{tecnica.aura_infusione.nome}</span>
                </span>
            )}
        </div>

      </div>
    </div>
  );
};

export default TecnicaDetailModal;