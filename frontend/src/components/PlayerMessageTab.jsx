import React, { useMemo, useState, useEffect, useRef } from 'react';
import { useCharacter } from './CharacterContext';
import { Trash2, Mail, Reply, Eye, EyeOff } from 'lucide-react';
import ComposeMessageModal from './ComposeMessageModal';
import RichTextDisplay from './RichTextDisplay';
import { fetchAuthenticated } from '../api';

const PlayerMessageTab = ({ onLogout, composeTarget, onComposeTargetConsumed, scrollToFirstUnreadNonce = 0 }) => {
    const { 
        selectedCharacterData: char, 
        userMessages, 
        fetchUserMessages, 
        selectedCharacterId,
        handleToggleRead,
        handleDeleteMessage: contextDeleteMessage
    } = useCharacter();

    const [isComposeOpen, setIsComposeOpen] = useState(false);
    const [replyToRecipient, setReplyToRecipient] = useState(null); // Per pre-compilare destinatario
    const [expandedMessages, setExpandedMessages] = useState({}); // Gestione espansione
    const messagesEndRef = useRef(null);
    const firstUnreadRef = useRef(null);
    const transferableItems = (char?.oggetti || []).filter(
        (item) => item && item.id && item.tipo_oggetto === 'FIS' && !item.is_equipaggiato
    );

    const firstUnreadId = useMemo(() => {
        const m = (userMessages || []).find((x) => x && x.letto === false);
        return m ? m.id : null;
    }, [userMessages]);

    // Scroll: se ci sono non-letti e richiesto, vai al primo non-letto; altrimenti in fondo.
    useEffect(() => {
        if (firstUnreadRef.current) {
            firstUnreadRef.current.scrollIntoView({ behavior: 'smooth', block: 'start' });
            return;
        }
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [scrollToFirstUnreadNonce, firstUnreadId]);

    useEffect(() => {
        if (!composeTarget) return;
        setReplyToRecipient(composeTarget);
        setIsComposeOpen(true);
        if (onComposeTargetConsumed) onComposeTargetConsumed();
    }, [composeTarget, onComposeTargetConsumed]);

    const toggleMessageExpansion = (msgId) => {
        setExpandedMessages(prev => ({
            ...prev,
            [msgId]: !prev[msgId]
        }));
    };

    const handleReply = (msg) => {
        console.log('Reply to message:', msg); // Debug
        
        // Se il messaggio è dallo staff, rispondi allo staff
        if (msg.mittente_is_staff) {
            setReplyToRecipient({ isStaff: true });
        } else if (msg.mittente_personaggio_id) {
            // Altrimenti rispondi al mittente (usa mittente_personaggio_id dal serializer)
            setReplyToRecipient({ 
                id: msg.mittente_personaggio_id, 
                nome: msg.mittente_nome,
                isStaff: false 
            });
        } else {
            console.error('Impossibile rispondere: mittente non valido', msg);
            alert('Impossibile rispondere a questo messaggio');
            return;
        }
        setIsComposeOpen(true);
    };

    if (!char) return <div className="text-gray-400 text-center mt-4">Seleziona un personaggio</div>;

    return (
        <div className="flex flex-col h-[calc(100vh-200px)] relative">
            
            {/* --- LISTA MESSAGGI --- */}
            <div className="flex-1 overflow-y-auto p-2 space-y-4 custom-scrollbar mb-16">
                {userMessages && userMessages.length > 0 ? (
                    userMessages.map((msg) => {
                        const isStaff = msg.mittente_is_staff;
                        const isExpanded = expandedMessages[msg.id];
                        const isRead = msg.letto;
                        const isOutgoing = Number(msg.mittente_personaggio_id) === Number(selectedCharacterId);
                        const transferCounterpartName = isOutgoing
                            ? (msg.destinatario_personaggio || 'destinatario sconosciuto')
                            : (msg.mittente_personaggio_nome || msg.mittente_nome || 'mittente sconosciuto');

                        return (
                            <div 
                                key={msg.id} 
                                ref={firstUnreadId && msg.id === firstUnreadId ? firstUnreadRef : null}
                                className={`flex w-full ${isStaff ? 'justify-start' : 'justify-end'}`}
                            >
                                <div 
                                    className={`
                                        relative max-w-[90%] sm:max-w-[80%] rounded-xl p-3 shadow-md transition-all duration-200
                                        ${isStaff 
                                            ? `${isRead ? 'bg-gray-800 opacity-80' : 'bg-gray-700'} text-gray-100 rounded-tl-none border-l-4 border-red-500 hover:bg-gray-600` 
                                            : `${isRead ? 'bg-indigo-950 opacity-80' : 'bg-indigo-900'} text-white rounded-tr-none border-r-4 border-indigo-400 hover:bg-indigo-800`
                                        }
                                    `}
                                >
                                    {/* Header Messaggio */}
                                    <div className="flex justify-between items-start mb-2 border-b border-white/10 pb-1 gap-4">
                                        <div className="flex items-center gap-2">
                                            {isRead ? <Mail size={14} className="opacity-50"/> : <Mail size={14} className="text-yellow-400 animate-pulse"/>}
                                            <span className={`text-xs font-bold uppercase tracking-wider ${isStaff ? 'text-red-300' : 'text-indigo-200'}`}>
                                                {msg.mittente_nome || 'Sistema'}
                                            </span>
                                            {!isRead && (
                                                <span className="text-[9px] bg-yellow-600 text-white px-1.5 py-0.5 rounded-full font-bold uppercase">
                                                    Nuovo
                                                </span>
                                            )}
                                        </div>
                                        
                                        <div className="flex items-center gap-2">
                                            <span className="text-[10px] text-gray-400">
                                                {new Date(msg.data_creazione || msg.data_invio).toLocaleString()}
                                            </span>
                                            
                                            {/* Pulsante Rispondi */}
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); handleReply(msg); }}
                                                className="text-gray-400 hover:text-green-400 transition-colors p-0.5 rounded"
                                                title="Rispondi"
                                            >
                                                <Reply size={14} />
                                            </button>
                                            
                                            {/* Pulsante Segna come letto/non letto */}
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); handleToggleRead(msg.id); }}
                                                className={`transition-colors p-0.5 rounded ${isRead ? 'text-gray-500 hover:text-blue-400' : 'text-blue-400 hover:text-blue-300'}`}
                                                title={isRead ? 'Segna come non letto' : 'Segna come letto'}
                                            >
                                                {isRead ? <EyeOff size={14} /> : <Eye size={14} />}
                                            </button>
                                            
                                            {/* Pulsante Elimina */}
                                            <button 
                                                onClick={(e) => { e.stopPropagation(); contextDeleteMessage(msg.id); }}
                                                className="text-gray-400 hover:text-red-400 transition-colors p-0.5 rounded"
                                                title="Cancella"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>

                                    {/* Titolo */}
                                    {msg.titolo && (
                                        <div 
                                            className="font-bold text-sm mb-1 cursor-pointer"
                                            onClick={() => toggleMessageExpansion(msg.id)}
                                        >
                                            {msg.titolo}
                                        </div>
                                    )}

                                    {/* Allegati transazionali */}
                                    {(Number(msg.crediti_allegati || 0) > 0 || (msg.oggetti_allegati_snapshot || []).length > 0) && (
                                        <div className="mb-2 flex flex-wrap items-center gap-2 text-[11px]">
                                            <span className="px-2 py-0.5 rounded-full bg-slate-700/80 text-slate-100 border border-slate-500/30">
                                                {isOutgoing ? `Inviato a ${transferCounterpartName}` : `Ricevuto da ${transferCounterpartName}`}
                                            </span>
                                            {Number(msg.crediti_allegati || 0) > 0 && (
                                                <span className="px-2 py-0.5 rounded-full bg-emerald-700/80 text-emerald-100 border border-emerald-500/30">
                                                    +{Number(msg.crediti_allegati)} crediti
                                                </span>
                                            )}
                                            {(msg.oggetti_allegati_snapshot || []).length > 0 && (
                                                <span className="px-2 py-0.5 rounded-full bg-amber-700/80 text-amber-100 border border-amber-500/30">
                                                    {(msg.oggetti_allegati_snapshot || []).length} oggetti allegati
                                                </span>
                                            )}
                                        </div>
                                    )}

                                    {/* Contenuto Rich Text con Logica "Leggi tutto" via CSS */}
                                    <div 
                                        className={`text-sm prose prose-invert max-w-none wrap-break-words relative transition-all duration-300 cursor-pointer ${!isExpanded ? 'max-h-24 overflow-hidden' : ''}`}
                                        onClick={() => toggleMessageExpansion(msg.id)}
                                    >
                                        <RichTextDisplay content={msg.testo} />
                                        
                                        {/* Sfumatura se non espanso */}
                                        {!isExpanded && (
                                            <div className="absolute bottom-0 left-0 w-full h-8 bg-linear-to-t from-gray-700/90 to-transparent pointer-events-none" />
                                        )}
                                    </div>
                                    
                                    {!isExpanded && (
                                        <div className="text-xs text-center text-gray-400 mt-1 italic">
                                            Clicca per espandere
                                        </div>
                                    )}

                                    {isExpanded && (msg.oggetti_allegati_snapshot || []).length > 0 && (
                                        <div className="mt-2 p-2 rounded border border-gray-600/60 bg-black/20">
                                            <div className="text-[11px] uppercase tracking-wide text-gray-400 mb-1">Oggetti allegati</div>
                                            <ul className="space-y-1">
                                                {msg.oggetti_allegati_snapshot.map((item, idx) => (
                                                    <li key={`${msg.id}-item-${item?.id || idx}`} className="text-xs text-gray-200">
                                                        {item?.nome || `Oggetto ${item?.id || idx + 1}`}
                                                    </li>
                                                ))}
                                            </ul>
                                        </div>
                                    )}
                                </div>
                            </div>
                        );
                    })
                ) : (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 opacity-60">
                         <p>Nessun messaggio.</p>
                    </div>
                )}
                <div ref={messagesEndRef} />
            </div>

            {/* --- FAB / BUTTON PER NUOVO MESSAGGIO --- */}
            <div className="absolute bottom-4 right-4 z-10">
                <button
                    onClick={() => {
                        setReplyToRecipient(null);
                        setIsComposeOpen(true);
                    }}
                    className="bg-indigo-600 hover:bg-indigo-500 text-white rounded-full p-4 shadow-xl flex items-center gap-2 transition-transform hover:scale-105"
                >
                    <Mail size={24} />
                    <span className="font-bold hidden sm:inline">Nuovo Messaggio</span>
                </button>
            </div>

            {/* --- MODALE COMPOSIZIONE --- */}
            <ComposeMessageModal 
                isOpen={isComposeOpen} 
                onClose={() => {
                    setIsComposeOpen(false);
                    setReplyToRecipient(null);
                }}
                currentCharacterId={selectedCharacterId}
                replyToRecipient={replyToRecipient}
                onMessageSent={() => {
                    fetchUserMessages(selectedCharacterId);
                }}
                onLogout={onLogout}
                availableTransferItems={transferableItems}
                currentCredits={char?.crediti || 0}
            />
        </div>
    );
};

export default PlayerMessageTab;