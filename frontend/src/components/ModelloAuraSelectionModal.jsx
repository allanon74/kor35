import React, { useState, useEffect } from 'react';
import { X, Lock, AlertTriangle, CheckCircle, Info } from 'lucide-react';
import { getModelliAura, selezionaModelloAura } from '../api';
import { useCharacter } from './CharacterContext';
import IconaPunteggio from './IconaPunteggio';

const ModelloAuraSelectionModal = ({ aura, onClose }) => {
  const { selectedCharacterId, refreshCharacterData, onLogout } = useCharacter();
  const [modelli, setModelli] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selecting, setSelecting] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        const data = await getModelliAura(aura.id);
        setModelli(data);
      } catch (err) {
        console.error(err);
        alert("Errore nel caricamento dei modelli");
        onClose();
      } finally {
        setLoading(false);
      }
    };
    if (aura?.id) {
        fetchModels();
    }
  }, [aura, onClose]);

  const handleSelect = async (modello) => {
    if (!window.confirm(`Sei sicuro di voler scegliere il modello "${modello.nome}"? Questa scelta NON può essere cambiata.`)) return;

    setSelecting(modello.id);
    try {
      await selezionaModelloAura(selectedCharacterId, modello.id, onLogout);
      await refreshCharacterData(); // Ricarica il PG per aggiornare la UI
      onClose();
    } catch (err) {
      alert("Errore durante la selezione: " + err.message);
      setSelecting(null);
    }
  };

  // Componente helper per renderizzare le liste di mattoni (proibiti o obbligatori)
  const RenderMattoniList = ({ title, items, icon: Icon, colorClass, titleClass }) => {
    if (!items || items.length === 0) return null;
    return (
      <div className="mb-2">
        <span className={`text-xs uppercase font-bold mb-1 flex items-center gap-1 ${titleClass}`}>
           <Icon size={10} /> {title}:
        </span>
        <div className="flex flex-wrap gap-2">
            {items.map(m => (
                <div key={m.id} title={m.nome} className={`flex items-center gap-1 bg-black/40 px-2 py-1 rounded border ${colorClass}`}>
                    {/* Assicurati che il serializer backend invii 'icona_url' o gestisci il path qui */}
                    <IconaPunteggio url={m.icona_url || m.icona} color={m.colore || 'white'} size="xs" mode="mask" />
                    <span className="text-xs text-gray-300">{m.nome}</span>
                </div>
            ))}
        </div>
      </div>
    );
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-80 p-4 backdrop-blur-sm">
      <div className="bg-gray-800 rounded-xl shadow-2xl border border-gray-700 w-full max-w-2xl max-h-[90vh] flex flex-col">
        
        {/* HEADER */}
        <div className="p-6 border-b border-gray-700 flex justify-between items-center shrink-0">
          <div>
              <h2 className="text-xl font-bold text-white flex items-center gap-2">
                  <div className="w-6 h-6" style={{ backgroundColor: aura.colore, maskImage: `url(${aura.icona_url})`, WebkitMaskImage: `url(${aura.icona_url})` }} />
                  Scegli Modello per {aura.nome}
              </h2>
              <p className="text-xs text-yellow-400 mt-1 flex items-center gap-1">
                  <AlertTriangle size={12} /> Attenzione: La scelta è definitiva!
              </p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24} /></button>
        </div>

        {/* CONTENT */}
        <div className="p-6 overflow-y-auto custom-scrollbar">
          {loading ? (
             <p className="text-center text-gray-400">Caricamento modelli...</p>
          ) : (
             <>
             {modelli.length === 0 ? (
                <p className="text-center text-gray-400 py-4">Nessun modello disponibile per questa Aura.</p>
             ) : (
                 <div className="grid grid-cols-1 gap-4">
                    {modelli.map(mod => {
                        const hasObbligatori = mod.mattoni_obbligatori && mod.mattoni_obbligatori.length > 0;
                        const hasProibiti = mod.mattoni_proibiti && mod.mattoni_proibiti.length > 0;

                        return (
                            <div 
                                key={mod.id} 
                                onClick={() => !selecting && handleSelect(mod)}
                                className={`border border-gray-700 bg-gray-900 rounded-lg p-4 hover:border-kor-accent hover:bg-gray-800 cursor-pointer transition-all relative group ${selecting === mod.id ? 'opacity-50' : ''}`}
                            >
                                <div className="flex justify-between items-start mb-2">
                                    <h3 className="font-bold text-lg text-white group-hover:text-kor-accent transition-colors">{mod.nome}</h3>
                                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                                        <span className="bg-kor-main text-white text-xs px-2 py-1 rounded shadow font-bold">Seleziona</span>
                                    </div>
                                </div>
                                
                                {/* DESCRIZIONE */}
                                {mod.descrizione && (
                                    <div className="text-sm text-gray-400 italic mb-4 border-l-2 border-gray-600 pl-2">
                                        {mod.descrizione}
                                    </div>
                                )}

                                {/* MATTONI OBBLIGATORI */}
                                <RenderMattoniList 
                                    title="Mattoni Obbligatori" 
                                    items={mod.mattoni_obbligatori} 
                                    icon={CheckCircle} 
                                    colorClass="border-green-800/50"
                                    titleClass="text-green-400"
                                />

                                {/* MATTONI PROIBITI */}
                                <RenderMattoniList 
                                    title="Mattoni Bloccati" 
                                    items={mod.mattoni_proibiti} 
                                    icon={Lock} 
                                    colorClass="border-red-800/50"
                                    titleClass="text-red-400"
                                />

                                {/* NESSUNA RESTRIZIONE */}
                                {!hasObbligatori && !hasProibiti && (
                                    <p className="text-xs text-green-400 italic mt-2 flex items-center gap-1">
                                        <CheckCircle size={10} /> Nessuna restrizione sui mattoni.
                                    </p>
                                )}
                            </div>
                        );
                    })}
                 </div>
             )}
             </>
          )}
        </div>
      </div>
    </div>
  );
};

export default ModelloAuraSelectionModal;