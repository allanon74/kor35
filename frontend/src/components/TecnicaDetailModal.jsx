import React from 'react';
import { X } from 'lucide-react';
import PunteggioDisplay from './PunteggioDisplay.jsx';
import RichHtml from './RichHtml';
import ActivationCostPreview from './ActivationCostPreview';
import { evaluateActivationCosts } from '../lib/activationCostUtils';

const ACTIVATION_COST_LABELS = {
  Infusione: "Costi all'uso dell'oggetto (per attivazione)",
  Tessitura: 'Costi attivazione effetto runtime',
};

const TecnicaDetailModal = ({ tecnica, onClose, type = 'tecnica', char = null }) => {
  if (!tecnica) return null;

  const testoDescrizione = tecnica.testo_formattato_personaggio || tecnica.TestoFormattato || tecnica.testo;

  // LOGICA COSTI:
  // costo_pieno e costo_effettivo arrivano dal serializer backend.
  // Se mancano, usiamo il fallback standard (livello * 100).
  const costoPieno = tecnica.costo_pieno ?? (tecnica.costo_crediti || tecnica.livello * 100);
  const costoEffettivo = tecnica.costo_effettivo ?? costoPieno;
  const hasDiscount = costoEffettivo < costoPieno;
  const activationCosts = tecnica.costi_attivazione || [];
  const activationEval = char ? evaluateActivationCosts(char, activationCosts) : null;
  const activationLabel = ACTIVATION_COST_LABELS[type] || 'Costi attivazione';
  const componentiRows = Array.isArray(tecnica.componenti) && tecnica.componenti.length > 0
    ? tecnica.componenti
    : (Array.isArray(tecnica.mattoni) ? tecnica.mattoni.map((m) => ({ caratteristica: m.mattone, valore: m.valore })) : []);

  return (
    <div 
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black bg-opacity-75 p-0 sm:p-4 backdrop-blur-sm animate-fadeIn"
      onClick={onClose}
    >
      <div 
        className="relative w-full sm:max-w-lg p-5 sm:p-6 bg-gray-800 rounded-t-2xl sm:rounded-xl shadow-2xl border border-gray-700 max-h-[92vh] sm:max-h-[90vh] overflow-y-auto transform transition-all animate-slideIn"
        onClick={(e) => e.stopPropagation()} 
      >
        <button 
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors p-1 min-h-10 min-w-10 flex items-center justify-center"
          aria-label="Chiudi"
        >
          <X size={24} />
        </button>
        
        {/* Header con Aura */}
        <div className="pr-12 mb-4 sm:mb-6">
            <div>
                <div className="flex items-center gap-2 mb-1 min-w-0">
                  {tecnica.aura_richiesta && (
                    <PunteggioDisplay
                      punteggio={tecnica.aura_richiesta}
                      displayText="none"
                      iconType="inv_circle"
                      size="s"
                    />
                  )}
                  <h2 className="text-2xl font-bold text-indigo-400 leading-tight break-words">
                    {tecnica.nome}
                  </h2>
                </div>
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-sm font-bold text-gray-400 uppercase tracking-wider border border-gray-600 px-2.5 py-1 rounded">
                      {type} · Livello {tecnica.livello}
                  </span>
                  {tecnica.non_acquistabile && (
                    <span className="text-xs font-bold uppercase tracking-wider border border-sky-500/70 bg-sky-900/30 text-sky-100 px-2 py-1 rounded">
                      Solo QR/Master
                    </span>
                  )}
                </div>
            </div>
        </div>
        
        {/* Corpo del testo formattato — tipografia leggibile su cellulare */}
        <div className="bg-gray-900/60 p-4 rounded-lg border border-gray-700/50 mb-6 shadow-inner space-y-4">
            {componentiRows.length > 0 && (
              <div className="rounded-md border border-cyan-800/40 bg-cyan-950/20 p-3">
                <div className="text-xs font-bold text-cyan-300 uppercase tracking-wider mb-2">
                  Mattoni componenti
                </div>
                <div className="flex flex-wrap gap-2">
                  {componentiRows.map((row, idx) => {
                    const caratteristica = row.caratteristica || row.mattone;
                    const mattoneNome = row.mattone_nome || caratteristica?.nome || '?';
                    const badgePunteggio = caratteristica
                      ? { ...caratteristica, nome: mattoneNome }
                      : { nome: mattoneNome, colore: '#6b7280' };
                    return (
                      <PunteggioDisplay
                        key={`${caratteristica?.id || idx}-${idx}`}
                        punteggio={badgePunteggio}
                        value={row.valore > 1 ? row.valore : null}
                        displayText="name"
                        iconType="glyph"
                        size="s"
                        readOnly
                        className="max-w-full shrink-0"
                      />
                    );
                  })}
                </div>
              </div>
            )}
            {testoDescrizione ? (
            <RichHtml
                content={testoDescrizione}
                className="text-gray-200 text-base leading-relaxed prose prose-invert prose-base max-w-none break-words prose-p:my-2 prose-li:my-1"
            />
            ) : (
            <p className="text-gray-500 italic text-base">Nessuna descrizione disponibile.</p>
            )}
        </div>

        {activationCosts.length > 0 && (
          <div className="mb-6 rounded-lg border border-amber-800/40 bg-amber-950/20 p-4">
            <h3 className="text-sm font-bold text-amber-400 uppercase mb-2 tracking-wider">
              {activationLabel}
            </h3>
            {char ? (
              <>
                <ActivationCostPreview char={char} costi={activationCosts} />
                {activationEval && !activationEval.affordable && (
                  <p className="mt-2 text-sm text-red-400 font-medium">
                    Risorse insufficienti con il personaggio attuale.
                  </p>
                )}
              </>
            ) : (
              <p className="text-sm text-amber-200/80 font-mono">
                {activationCosts.map((r) => `-${r.costo} ${r.statistica?.sigla || '?'}`).join(', ')}
              </p>
            )}
          </div>
        )}

        {/* Footer: Info Costo e Aura Secondaria */}
        <div className="mt-2 pt-4 border-t border-gray-700 flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3 text-sm text-gray-400 font-mono">
            
            {/* VISUALIZZAZIONE PREZZO BARRATO */}
            <div className="bg-gray-900 px-3 py-2 rounded flex items-center gap-2 w-full sm:w-auto">
                <span className="text-gray-500">Costo:</span>
                {hasDiscount && (
                    <span className="text-red-400 line-through decoration-red-500 opacity-70 mr-1">
                        {costoPieno}
                    </span>
                )}
                <span className={`font-bold text-base ${hasDiscount ? 'text-green-400' : 'text-yellow-500'}`}>
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
