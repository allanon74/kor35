import React, { useState, useEffect } from 'react';
import { Activity, Battery, Clock, RefreshCw } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { useOptimisticUseItem, useOptimisticRecharge } from '../hooks/useGameData';

const ActiveItemWidget = ({ item, onUpdate }) => {
    const useItemMutation = useOptimisticUseItem();
    const rechargeMutation = useOptimisticRecharge();
    const { selectedCharacterData } = useCharacter(); 

    const [timeLeft, setTimeLeft] = useState(0);

    // Gestione Timer Intelligente
    useEffect(() => {
        if (!item.data_fine_attivazione) {
            setTimeLeft(0);
            return;
        }

        const calculateTimeLeft = () => {
            const now = new Date().getTime();
            const end = new Date(item.data_fine_attivazione).getTime();
            const diff = Math.floor((end - now) / 1000);
            return diff > 0 ? diff : 0;
        };

        setTimeLeft(calculateTimeLeft());

        const interval = setInterval(() => {
            const remaining = calculateTimeLeft();
            setTimeLeft(remaining);
            if (remaining <= 0) clearInterval(interval);
        }, 1000);

        return () => clearInterval(interval);
    }, [item.data_fine_attivazione]);

    const formatTimer = (totalSeconds) => {
        if (!totalSeconds) return "Scaduto";
        const h = Math.floor(totalSeconds / 3600);
        const m = Math.floor((totalSeconds % 3600) / 60);
        const s = totalSeconds % 60;
        
        if (h > 0) return `${h}h ${m}m ${s}s`;
        return `${m}:${s.toString().padStart(2, '0')}`;
    };

    const handleUseCharge = () => {
        useItemMutation.mutate({ 
            oggetto_id: item.id, 
            charId: selectedCharacterData.id,
            durata_totale: item.durata_totale || 0,
            is_aura_zero_off: item.spegne_a_zero_cariche || false
        }, {
            // CORREZIONE QUI: Chiamiamo onUpdate se l'operazione ha successo
            onSuccess: () => {
                if (onUpdate) onUpdate();
            }
        });
    };

    const handleRecharge = () => {
        if (window.confirm(`Ricaricare ${item.nome}?\nCosto: ${item.costo_ricarica} CR\nMetodo: ${item.testo_ricarica}`)) {
            rechargeMutation.mutate({ 
                oggetto_id: item.id, 
                charId: selectedCharacterData.id 
            }, {
                // CORREZIONE QUI: Chiamiamo onUpdate anche per la ricarica
                onSuccess: () => {
                    if (onUpdate) onUpdate();
                }
            });
        }
    };

    // Logica di stato visuale
    const isWorking = timeLeft > 0;
    const hasCharges = item.cariche_attuali > 0;
    const maxCharges = item.cariche_massime || 0;
    const isDepleted = !hasCharges && !isWorking;

    return (
        <div className={`p-3 rounded-lg border shadow-sm w-full sm:w-[calc(50%-0.5rem)] flex flex-col gap-2 transition-all duration-300 ${isWorking ? 'bg-emerald-900/20 border-emerald-500/50 shadow-[0_0_15px_rgba(16,185,129,0.15)]' : 'bg-gray-800 border-gray-700'}`}>
            
            {/* Header */}
            <div className="flex justify-between items-start">
                <span className={`font-bold text-sm leading-tight ${isWorking ? 'text-emerald-400' : 'text-gray-300'}`}>
                    {item.nome}
                </span>
                {isWorking && <span className="animate-pulse text-emerald-500 shrink-0 ml-2"><Activity size={16}/></span>}
            </div>

            {/* Barra Cariche */}
            {maxCharges > 0 && (
                <div className={`rounded p-1.5 flex justify-between items-center transition-colors ${isDepleted ? 'bg-red-900/20 border border-red-900/30' : 'bg-black/30'}`}>
                    <div className="flex items-center gap-1.5 text-xs font-mono">
                         <Battery size={14} className={hasCharges ? "text-yellow-400" : "text-red-500"} />
                         <span className={hasCharges ? "text-white" : "text-red-400 font-bold"}>
                            {item.cariche_attuali} <span className="text-gray-500">/</span> {maxCharges}
                         </span>
                    </div>
                    
                    <button 
                        onClick={handleUseCharge}
                        disabled={!hasCharges || isWorking}
                        className={`text-[10px] font-bold px-2 py-0.5 rounded border uppercase tracking-wider transition-all active:scale-95 ${
                            isWorking
                            ? 'bg-emerald-600/20 text-emerald-400 border-emerald-600/50 cursor-default'
                            : hasCharges
                                ? 'bg-emerald-600 hover:bg-emerald-500 text-white border-emerald-500 shadow-sm hover:shadow-md'
                                : 'bg-gray-700 text-gray-500 border-gray-600 cursor-not-allowed'
                        }`}
                    >
                        {isWorking ? 'ON' : 'USA'}
                    </button>
                </div>
            )}

            {/* Footer: Timer e Ricarica */}
            <div className="flex justify-between items-end mt-1 h-6">
                <div className="flex flex-col justify-end">
                    {(item.durata_totale > 0 || isWorking) && (
                        <div className={`text-xs font-mono flex items-center gap-1 transition-colors ${isWorking ? 'text-blue-300 font-bold' : 'text-gray-500'}`}>
                            <Clock size={12} />
                            {isWorking 
                                ? <span>{formatTimer(timeLeft)}</span> 
                                : <span className="text-[10px]">Durata: {formatTimer(item.durata_totale)}</span>
                            }
                        </div>
                    )}
                </div>

                {item.costo_ricarica > 0 && item.cariche_attuali < maxCharges && (
                    <button 
                        onClick={handleRecharge}
                        className="flex items-center gap-1 bg-yellow-900/10 hover:bg-yellow-900/30 text-yellow-500 hover:text-yellow-200 px-2 py-0.5 rounded border border-transparent hover:border-yellow-700/50 transition-all text-[10px]"
                        title={item.testo_ricarica}
                    >
                        <RefreshCw size={10} /> {item.costo_ricarica} CR
                    </button>
                )}
            </div>
        </div>
    );
};

export default ActiveItemWidget;