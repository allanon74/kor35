import React, { useState, useMemo, useCallback, memo } from 'react'; 
import { Calendar, Clock, Edit2, Trash, ChevronDown, ChevronUp, BookOpen, Plus } from 'lucide-react';
import QuestItem from './QuestItem';
import RichTextDisplay from './RichTextDisplay';

const GiornoSection = ({ giorno, gIdx, isMaster, risorse, onEdit, onDelete, onAddQuest, questHandlers }) => {
    const [showDettagli, setShowDettagli] = useState(false);

    // LOGICA DI ORDINAMENTO AGGIUNTA (Memoized)
    // Crea una copia dell'array e ordina per orario_indicativo
    const sortedQuests = useMemo(() => {
        return [...(giorno.quests || [])].sort((a, b) => {
            // Se manca l'orario, considera come fine giornata ("23:59:59") per metterlo in fondo
            const timeA = a.orario_indicativo || "23:59:59";
            const timeB = b.orario_indicativo || "23:59:59";
            return timeA.localeCompare(timeB);
        });
    }, [giorno.quests]);
    
    const formatTime = useCallback((iso) => iso ? new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "--:--", []);
    const formatDate = useCallback((iso) => iso ? new Date(iso).toLocaleDateString([], { day: '2-digit', month: 'long', year: 'numeric' }) : "", []);

    return (
        <div className="space-y-6 w-full max-w-full">
            <div className="flex justify-between items-start border-b border-emerald-500/30 pb-3 gap-2">
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <span className="bg-emerald-600 text-white px-2 py-0.5 rounded text-[10px] font-black uppercase whitespace-nowrap">Giorno {gIdx + 1}</span>
                        <span className="text-[10px] font-bold text-gray-400 uppercase flex items-center gap-1 truncate">
                            <Calendar size={12}/> {formatDate(giorno.data_ora_inizio)}
                        </span>
                    </div>
                    
                    {/* Titolo Principale */}
                    <h2 className="text-2xl font-black italic text-white uppercase tracking-tight truncate">
                        {giorno.titolo || `Giorno ${gIdx + 1}`}
                    </h2>
                    
                    {/* Sinossi Breve */}
                    {giorno.sinossi_breve && (
                        <div className="text-sm text-indigo-300 italic font-medium bg-indigo-900/10 p-2 rounded-lg border border-indigo-500/20 mt-2">
                            <RichTextDisplay content={giorno.sinossi_breve} />
                        </div>
                    )}

                    <div className="flex flex-wrap items-center gap-3 text-[10px] text-emerald-400 font-bold uppercase italic mt-2">
                        <span className="flex items-center gap-1 whitespace-nowrap"><Clock size={12}/> {formatTime(giorno.data_ora_inizio)} - {formatTime(giorno.data_ora_fine)}</span>
                        
                        {/* Bottone per espandere i dettagli completi */}
                        {giorno.descrizione_completa && (
                            <button 
                                onClick={() => setShowDettagli(!showDettagli)}
                                className="flex items-center gap-1 text-white bg-emerald-900/40 px-2 py-1 rounded hover:bg-emerald-800 transition-colors"
                            >
                                <BookOpen size={10}/> 
                                {showDettagli ? "Nascondi Plot" : "Leggi Plot Completo"}
                                {showDettagli ? <ChevronUp size={10}/> : <ChevronDown size={10}/>}
                            </button>
                        )}
                    </div>
                </div>

                {isMaster && (
                    <div className="flex gap-2 shrink-0">
                        <button onClick={() => onEdit('giorno', giorno)} className="text-gray-500 hover:text-white p-1"><Edit2 size={16}/></button>
                        <button onClick={() => onDelete(giorno.id)} className="text-red-900 hover:text-red-500 p-1"><Trash size={16}/></button>
                        <button onClick={() => onAddQuest(giorno.id)} className="bg-emerald-600 px-3 py-1.5 rounded text-[10px] font-black uppercase whitespace-nowrap flex items-center gap-1">
                            <Plus size={12}/> Quest
                        </button>
                    </div>
                )}
            </div>

            {/* Sezione Collassata della Descrizione Completa */}
            {showDettagli && giorno.descrizione_completa && (
                <div className="bg-emerald-950/20 border-l-2 border-emerald-500 p-4 rounded-r-lg animate-in fade-in w-full">
                    <h4 className="text-[10px] font-black text-emerald-500 uppercase mb-2">Dettagli Plot / Note Master</h4>
                    <div className="text-xs text-gray-400 bg-black/20 p-2 rounded">
                        <RichTextDisplay content={giorno.descrizione_completa} />
                    </div>
                </div>
            )}

            <div className="grid gap-8 w-full">
                {/* QUI è la correzione: mappiamo 'sortedQuests' invece di 'giorno.quests' */}
                {sortedQuests.map(quest => (
                    <QuestItem 
                        key={quest.id} 
                        quest={quest} 
                        isMaster={isMaster} 
                        risorse={risorse} 
                        onEdit={onEdit} 
                        // Espando i questHandlers (onAddSub, onRemoveSub, ecc.)
                        onAddSub={questHandlers.onAddSub}
                        onRemoveSub={questHandlers.onRemoveSub}
                        onStatChange={questHandlers.onStatChange}
                        onSaveNotes={questHandlers.onSaveNotes}
                        onScanQr={questHandlers.onScanQr}
                    />
                ))}
            </div>
        </div>
    );
};

export default memo(GiornoSection);