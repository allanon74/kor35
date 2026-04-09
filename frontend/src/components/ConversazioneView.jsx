import React, { useState, useRef, useEffect } from 'react';
import { Reply, Send, X, Users, MessageCircle } from 'lucide-react';
import RichTextDisplay from './RichTextDisplay';
import RichTextEditor from './RichTextEditor';

const ConversazioneView = ({ conversazione, onRispondi, onClose, currentPersonaggioId }) => {
    const [testoRisposta, setTestoRisposta] = useState('');
    const [isReplying, setIsReplying] = useState(false);
    const [isSending, setIsSending] = useState(false);
    const messagesEndRef = useRef(null);

    useEffect(() => {
        if (messagesEndRef.current) {
            messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
        }
    }, [conversazione.messaggi]);

    const handleRispondi = async () => {
        if (!testoRisposta.trim()) return;
        
        setIsSending(true);
        try {
            await onRispondi(conversazione.messaggi[0].id, testoRisposta);
            setTestoRisposta('');
            setIsReplying(false);
        } catch (error) {
            console.error('Errore invio risposta:', error);
            alert('Errore nell\'invio della risposta');
        } finally {
            setIsSending(false);
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
            <div className="flex flex-col w-full max-w-4xl h-[90vh] bg-gray-900 rounded-lg shadow-2xl overflow-hidden border border-gray-700">
                
                {/* Header */}
                <div className="flex items-center justify-between p-4 border-b border-gray-700 bg-gray-800">
                    <div className="flex items-center gap-3">
                        <MessageCircle className="w-6 h-6 text-indigo-400" />
                        <div>
                            <h2 className="text-xl font-bold text-white">Conversazione</h2>
                            <div className="flex items-center gap-2 mt-1">
                                <Users className="w-4 h-4 text-gray-400" />
                                <span className="text-sm text-gray-400">
                                    {conversazione.partecipanti.map(p => p.nome).join(', ')}
                                </span>
                            </div>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white transition-colors"
                    >
                        <X className="w-6 h-6" />
                    </button>
                </div>

                {/* Messages Area */}
                <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-gray-950">
                    {conversazione.messaggi.map((msg, index) => {
                        const isStaff = msg.mittente_is_staff;
                        const isMine = msg.mittente_personaggio_id === currentPersonaggioId;
                        const showAvatar = index === 0 || conversazione.messaggi[index - 1].mittente_personaggio_id !== msg.mittente_personaggio_id;

                        return (
                            <div 
                                key={msg.id}
                                className={`flex w-full ${isMine ? 'justify-end' : 'justify-start'}`}
                            >
                                <div className={`relative max-w-[75%] ${isMine ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
                                    {/* Nome mittente */}
                                    {showAvatar && (
                                        <span className={`text-xs font-bold ${isStaff ? 'text-red-400' : isMine ? 'text-indigo-400' : 'text-gray-400'} px-2`}>
                                            {msg.mittente_personaggio_nome || msg.mittente_nome || 'Staff'}
                                        </span>
                                    )}
                                    
                                    {/* Bubble messaggio */}
                                    <div
                                        className={`
                                            rounded-2xl p-3 shadow-md
                                            ${isMine 
                                                ? 'bg-indigo-700 text-white rounded-tr-none' 
                                                : isStaff 
                                                    ? 'bg-red-900/50 text-gray-100 rounded-tl-none border border-red-700' 
                                                    : 'bg-gray-800 text-gray-100 rounded-tl-none'
                                            }
                                        `}
                                    >
                                        {msg.titolo && (
                                            <div className="font-bold text-sm mb-1 opacity-90">{msg.titolo}</div>
                                        )}
                                        <div className="text-sm prose prose-invert max-w-none">
                                            <RichTextDisplay content={msg.testo} />
                                        </div>
                                        <div className={`text-[10px] mt-1 ${isMine ? 'text-indigo-200' : 'text-gray-500'}`}>
                                            {new Date(msg.data_creazione).toLocaleString()}
                                        </div>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                    <div ref={messagesEndRef} />
                </div>

                {/* Reply Area */}
                <div className="border-t border-gray-700 bg-gray-800 p-4">
                    {!isReplying ? (
                        <button
                            onClick={() => setIsReplying(true)}
                            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-colors"
                        >
                            <Reply className="w-5 h-5" />
                            Rispondi
                        </button>
                    ) : (
                        <div className="space-y-2">
                            <div className="bg-gray-900 rounded-lg border border-gray-700 overflow-hidden" style={{ minHeight: '120px' }}>
                                <RichTextEditor 
                                    value={testoRisposta}
                                    onChange={setTestoRisposta}
                                    placeholder="Scrivi la tua risposta..."
                                />
                            </div>
                            <div className="flex gap-2">
                                <button
                                    onClick={handleRispondi}
                                    disabled={!testoRisposta.trim() || isSending}
                                    className="flex-1 py-2 bg-green-600 hover:bg-green-500 text-white font-bold rounded-lg flex items-center justify-center gap-2 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                                >
                                    <Send className="w-4 h-4" />
                                    {isSending ? 'Invio...' : 'Invia'}
                                </button>
                                <button
                                    onClick={() => {
                                        setIsReplying(false);
                                        setTestoRisposta('');
                                    }}
                                    className="px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white rounded-lg transition-colors"
                                >
                                    Annulla
                                </button>
                            </div>
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ConversazioneView;
