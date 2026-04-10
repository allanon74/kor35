import React, { useState } from 'react';
import { X, Check, Lock, ChevronRight, Loader2 } from 'lucide-react';
import { acquireAbilita } from '../api'; 

export default function AuraTraitsModal({ aura, personaggio, onClose, onUpdateCharacter, currentValue }) {
  const [selectedStep, setSelectedStep] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // --- LOGICA RECUPERO VALORE SEMPLIFICATA ---
  // Se currentValue è passato (da PunteggioDisplay), usalo.
  // Altrimenti, fallback su 0.
  const currentAuraVal = currentValue !== undefined ? parseInt(currentValue, 10) : 0;
  // --------------------------------------------

  const getPossessedTrait = (level) => {
    if (!personaggio?.abilita_possedute || !aura.tratti_disponibili) return null;
    
    const availableIdsAtLevel = aura.tratti_disponibili
        .filter(t => t.livello_riferimento === level)
        .map(t => t.id);
    
    return personaggio.abilita_possedute.find(ab => availableIdsAtLevel.includes(ab.id));
  };

  const handleStepClick = (config) => {
    if (currentAuraVal < config.livello) return; // Blocco se livello insufficiente
    setSelectedStep(config);
  };

  const handleSelectTrait = async (trait) => {
    setLoading(true);
    setError(null);
    try {
      await acquireAbilita(trait.id, personaggio.id, null); 
      if (onUpdateCharacter) await onUpdateCharacter(); 
      setSelectedStep(null); 
    } catch (err) {
      console.error(err);
      setError(err.message || "Errore durante la selezione.");
    } finally {
      setLoading(false);
    }
  };

  // --- RENDER OPZIONI ---
  if (selectedStep) {
    const options = aura.tratti_disponibili.filter(t => t.livello_riferimento === selectedStep.livello);
    const possessed = getPossessedTrait(selectedStep.livello);

    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
        <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-2xl max-h-[90vh] flex flex-col shadow-2xl">
            <div className="p-4 border-b border-slate-700 flex justify-between items-center bg-slate-800/50 rounded-t-xl">
                <div>
                    <h3 className="text-xl font-bold text-amber-400">Seleziona {selectedStep.nome_step}</h3>
                    <p className="text-sm text-slate-400">Livello Aura richiesto: {selectedStep.livello}</p>
                </div>
                <button onClick={() => setSelectedStep(null)} className="p-2 hover:bg-slate-700 rounded-full text-slate-400 hover:text-white">
                    <X size={24} />
                </button>
            </div>

            <div className="p-4 overflow-y-auto space-y-3 flex-1">
                {error && <div className="p-3 bg-red-900/50 border border-red-500/50 text-red-200 rounded mb-4">{error}</div>}
                
                {options.length === 0 ? (
                    <div className="text-center text-slate-500 py-8">Nessuna opzione disponibile.</div>
                ) : (
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        {options.map(trait => {
                            const isSelected = possessed?.id === trait.id;
                            return (
                                <div key={trait.id} 
                                     className={`relative p-4 rounded-lg border transition-all cursor-pointer group
                                        ${isSelected 
                                            ? 'bg-amber-900/20 border-amber-500 ring-1 ring-amber-500' 
                                            : 'bg-slate-800 border-slate-700 hover:border-slate-500 hover:bg-slate-750'
                                        }`}
                                     onClick={() => !isSelected && handleSelectTrait(trait)}
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <h4 className={`font-bold ${isSelected ? 'text-amber-400' : 'text-slate-200'}`}>{trait.nome}</h4>
                                        {isSelected && <Check size={18} className="text-amber-500" />}
                                    </div>
                                    <div 
                                        className="text-xs text-slate-400 line-clamp-3 mb-2 prose prose-invert prose-p:my-1 prose-strong:text-slate-200"
                                        dangerouslySetInnerHTML={{ __html: trait.descrizione || "Nessuna descrizione." }}
                                    />
                                    
                                    {trait.statistica_modificata && (
                                        <span className="inline-flex items-center px-2 py-1 bg-slate-900 rounded text-[10px] text-cyan-400 border border-slate-700">
                                            {trait.statistica_modificata}
                                        </span>
                                    )}
                                </div>
                            );
                        })}
                    </div>
                )}
            </div>
            {loading && <div className="p-2 text-center text-amber-400 text-sm">Elaborazione in corso...</div>}
        </div>
      </div>
    );
  }

  // --- RENDER TIMELINE ---
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4">
      <div className="bg-slate-900 border border-slate-700 rounded-xl w-full max-w-lg shadow-2xl relative overflow-hidden flex flex-col max-h-[85vh]">
        
        <div className="p-5 border-b border-slate-700 flex justify-between items-center bg-linear-to-r from-slate-900 to-slate-800 shrink-0">
            <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded bg-slate-800 border border-slate-600 flex items-center justify-center text-xl font-bold text-slate-300">
                   {aura.nome.charAt(0)}
                </div>
                <div>
                    <h2 className="text-xl font-bold text-white tracking-wide">Evoluzione {aura.nome}</h2>
                    <p className="text-xs text-slate-400 uppercase tracking-wider">
                        Livello Attuale: <span className="text-amber-400 font-bold ml-1">{currentAuraVal}</span>
                    </p>
                </div>
            </div>
            <button onClick={onClose} className="p-2 hover:bg-slate-700 rounded-full text-slate-400 hover:text-white">
                <X size={24} />
            </button>
        </div>

        <div className="p-6 space-y-6 overflow-y-auto">
            {aura.configurazione_livelli && aura.configurazione_livelli.map((step, index) => {
                const possessedTrait = getPossessedTrait(step.livello);
                
                const isLocked = currentAuraVal < step.livello;
                const isCompleted = !!possessedTrait;

                return (
                    <div key={step.id || index} className="relative pl-8 last:pb-0">
                        {index !== aura.configurazione_livelli.length - 1 && (
                            <div className={`absolute left-[11px] top-8 bottom-6 w-0.5 ${isCompleted ? 'bg-amber-500/50' : 'bg-slate-700'}`} />
                        )}

                        <div className={`absolute left-0 top-1 w-6 h-6 rounded-full flex items-center justify-center border-2 z-10 
                            ${isCompleted ? 'bg-amber-900 border-amber-500 text-amber-500' : 
                              isLocked ? 'bg-slate-800 border-slate-600 text-slate-600' : 
                              'bg-cyan-900 border-cyan-500 text-cyan-400 animate-pulse'}`}>
                            {isLocked ? <Lock size={12} /> : isCompleted ? <Check size={12} /> : <div className="w-2 h-2 bg-cyan-400 rounded-full" />}
                        </div>

                        <div 
                            className={`p-4 rounded-lg border transition-all ${
                                isLocked ? 'bg-slate-900/50 border-slate-800 opacity-60' : 
                                isCompleted ? 'bg-slate-800 border-amber-500/30' : 
                                'bg-slate-800 border-cyan-500/50 cursor-pointer hover:bg-slate-750 hover:shadow-lg'
                            }`}
                            onClick={() => !isLocked && handleStepClick(step)}
                        >
                            <div className="flex justify-between items-start">
                                <div>
                                    <span className="text-[10px] font-mono text-slate-500 mb-1 block uppercase">Livello {step.livello}</span>
                                    <h3 className={`font-bold text-lg leading-tight ${isCompleted ? 'text-amber-400' : 'text-slate-200'}`}>
                                        {step.nome_step}
                                    </h3>
                                </div>
                                {!isLocked && !isCompleted && <ChevronRight size={20} className="text-cyan-500" />}
                            </div>
                            
                            <div className="mt-2 text-sm">
                                {isLocked ? (
                                    <p className="text-slate-600 italic text-xs">Sblocca al livello {step.livello}</p>
                                ) : isCompleted ? (
                                    <div className="flex items-center gap-2 bg-amber-950/30 px-3 py-2 rounded border border-amber-500/20 mt-1">
                                        <span className="text-amber-200 font-medium text-sm">{possessedTrait.nome}</span>
                                    </div>
                                ) : (
                                    <p className="text-slate-400 text-xs">{step.descrizione_fluff || "Clicca per selezionare un tratto."}</p>
                                )}
                            </div>
                        </div>
                    </div>
                );
            })}
        </div>
      </div>
    </div>
  );
}