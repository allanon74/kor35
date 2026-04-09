import React, { useState, useEffect } from 'react';
import { Loader2, Hammer, CheckCircle, Clock, User, Trash2 } from 'lucide-react';
import { completeForging } from '../api';
import { useCharacter } from './CharacterContext';
import GraftInstallationModal from './GraftInstallationModal'; // Assicurati che il percorso sia corretto

const ForgingItem = ({ item, onComplete, onOpenGraftModal, currentCharacterId }) => {
  // ... (tutto il codice timer esistente rimane uguale) ...
  const [timeLeft, setTimeLeft] = useState(item.secondi_rimanenti);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // ... (logica timer identica a prima) ...
    const calculateTimeLeft = () => {
        const now = new Date();
        const end = new Date(item.data_fine);
        const diff = Math.max(0, (end - now) / 1000);
        return diff;
    };
    setTimeLeft(calculateTimeLeft());
    const interval = setInterval(() => {
      const remaining = calculateTimeLeft();
      setTimeLeft(remaining);
      if (remaining <= 0) clearInterval(interval);
    }, 1000);
    return () => clearInterval(interval);
  }, [item.data_fine]);

  // Logica differenziata per il Click
  const handleClick = () => {
      // Se ha slot permessi, è un innesto/mutazione -> APRI MODALE
      if (item.infusione_slot_permessi && item.infusione_slot_permessi.length > 0) {
          onOpenGraftModal(item);
      } else {
          // Altrimenti comportamento standard
          handleCollect();
      }
  };

  const handleCollect = async () => {
    setIsProcessing(true);
    try {
        await onComplete(item.id);
    } catch (e) {
        setIsProcessing(false);
    }
  };

  const isReady = timeLeft <= 0;
  const canCollect = item.can_collect !== undefined ? item.can_collect : true;

  // Format MM:SS
  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-gray-800 border border-gray-700 p-3 rounded-lg flex items-center justify-between shadow-sm animate-fadeIn hover:bg-gray-750 transition-colors">
      <div className="flex items-center gap-3">
         {/* ... (Parte visiva identica a prima) ... */}
         <div className={`p-2 rounded-full ${isReady ? 'bg-green-900/30 text-green-400' : 'bg-amber-900/30 text-amber-500'}`}>
            {isReady ? <CheckCircle size={20} /> : <Hammer size={20} className={timeLeft > 0 ? "animate-pulse" : ""} />}
        </div>
        <div>
            <h4 className="font-bold text-gray-200 text-sm">{item.infusione_nome}</h4>
            {item.info_extra && (
                <div className="text-xs text-indigo-300 flex items-center gap-1 mt-0.5 font-medium">
                    <User size={12}/> {item.info_extra}
                </div>
            )}
            <div className="text-xs text-gray-400 mt-1 flex items-center gap-1">
                <Clock size={12}/>
                {isReady ? (
                    <span className="text-green-400 font-bold">Completato</span>
                ) : (
                    <span>Termina in: <span className="font-mono text-gray-300">{formatTime(timeLeft)}</span></span>
                )}
            </div>
        </div>
      </div>

      {isReady ? (
          canCollect ? (
            <button
                onClick={handleClick} // <--- CAMBIATO QUI
                disabled={isProcessing}
                className="px-4 py-1.5 rounded text-xs font-bold transition-all bg-green-600 hover:bg-green-500 text-white shadow-lg shadow-green-900/20 flex items-center gap-2 active:scale-95 disabled:opacity-50"
            >
                {isProcessing ? <Loader2 className="animate-spin" size={14} /> : "Ritira/Installa"}
            </button>
          ) : (
            <span className="text-xs text-gray-500 italic px-2 bg-gray-900/50 py-1 rounded">
                In attesa ritiro cliente
            </span>
          )
      ) : (
        <div className="text-gray-500 text-xs italic px-2">In lavorazione</div>
      )}
    </div>
  );
};

const ForgingQueue = ({ queue, refetchQueue }) => {
  const { selectedCharacterId, refreshCharacterData } = useCharacter();
  
  // Stato per la modale
  const [selectedGraftTask, setSelectedGraftTask] = useState(null);

  const handleCompleteStandard = async (forgiaturaId) => {
    try {
        await completeForging(forgiaturaId, selectedCharacterId);
        await Promise.all([refetchQueue(), refreshCharacterData()]);
    } catch (error) {
        alert("Errore nel ritiro: " + error.message);
    }
  };

  const handleGraftSuccess = async () => {
      // Chiamato quando la modale finisce con successo
      setSelectedGraftTask(null);
      await Promise.all([refetchQueue(), refreshCharacterData()]);
  };

  if (!queue || queue.length === 0) return null;

  return (
    <>
        <div className="mb-6 bg-gray-800/50 border border-gray-700 rounded-lg p-4 shadow-lg">
            <h3 className="text-sm font-bold text-gray-400 uppercase tracking-wider mb-3 flex items-center gap-2 border-b border-gray-700 pb-2">
                <Hammer size={16} className="text-amber-500"/> 
                Coda di Forgiatura <span className="text-gray-600">({queue.length})</span>
            </h3>
            
            <div className="space-y-2">
                {queue.map(item => (
                    <ForgingItem 
                        key={item.id} 
                        item={item} 
                        onComplete={handleCompleteStandard} 
                        onOpenGraftModal={setSelectedGraftTask} // <--- Passiamo il setter
                        currentCharacterId={selectedCharacterId}
                    />
                ))}
            </div>
        </div>

        {/* MODALE INNESTO */}
        {selectedGraftTask && (
            <GraftInstallationModal 
                task={selectedGraftTask}
                onClose={() => setSelectedGraftTask(null)}
                onSuccess={handleGraftSuccess}
            />
        )}
    </>
  );
};

export default ForgingQueue;