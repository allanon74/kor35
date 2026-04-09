import React, { useMemo } from 'react';
import { sanitizeHtml } from '../utils/htmlSanitizer';
import { activateUser, deleteUser, staffKillPersonaggio, staffRevivePersonaggio } from '../api';
import { RICH_TEXT_SHARED_STYLES } from '../styles/richTextSharedStyles';

const RichTextDisplay = ({ content, onUpdate, onLogout }) => {
    // 1. Sanitizzazione base dell'HTML
    const cleanContent = useMemo(() => sanitizeHtml(content), [content]);

    if (!cleanContent) return null;

    // 2. Funzione per gestire il click sul pulsante di attivazione
    const handleActivate = async (userId) => {
        if(window.confirm(`Sei sicuro di voler attivare l'utente #${userId}?`)) {
            try {
                await activateUser(userId);
                alert('Utente attivato con successo!');
                if (onUpdate) onUpdate();
            } catch (err) {
                alert('Errore attivazione: ' + err.message);
            }
        }
    };

    // 3. Funzione per gestire l'eliminazione di un utente
    const handleDelete = async (userId) => {
        if(window.confirm(`ATTENZIONE: Sei sicuro di voler ELIMINARE l'utente #${userId}? Questa azione è irreversibile e rimuoverà l'account e tutti i dati associati.`)) {
            try {
                await deleteUser(userId);
                alert('Utente eliminato con successo!');
                if (onUpdate) onUpdate();
            } catch (err) {
                alert('Errore eliminazione: ' + err.message);
            }
        }
    };

    const handleConfirmDeath = async (personaggioId) => {
        if (window.confirm(`Confermi lo stato "morto" per il personaggio #${personaggioId}?`)) {
            try {
                await staffKillPersonaggio(personaggioId, onLogout);
                alert('Morte confermata.');
                if (onUpdate) onUpdate();
            } catch (err) {
                alert('Errore conferma morte: ' + err.message);
            }
        }
    };

    const handleRevokeDeath = async (personaggioId) => {
        if (window.confirm(`Rivivere il personaggio #${personaggioId}?`)) {
            try {
                await staffRevivePersonaggio(personaggioId, onLogout);
                alert('Personaggio rivissuto.');
                if (onUpdate) onUpdate();
            } catch (err) {
                alert('Errore revive: ' + err.message);
            }
        }
    };

    // 4. Parser Custom per trovare i tag [ACTIVATE_USER:ID] e [DELETE_USER:ID]
    // Dividiamo la stringa in parti basate sulla Regex
    const parts = cleanContent.split(/(\[(?:ACTIVATE|DELETE)_USER:\d+\]|\[(?:CONFIRM_DEATH|REVOKE_DEATH):\d+\])/g);

    return (
        <>
            <style>{RICH_TEXT_SHARED_STYLES}</style>
            <div 
                className="ql-editor-view w-full"
                style={{
                    fontSize: '0.875rem',
                    lineHeight: '1.6',
                    color: '#d1d5db', 
                    whiteSpace: 'normal',       
                    overflowWrap: 'anywhere',   
                    wordBreak: 'normal',        
                    maxWidth: '100%',
                    minWidth: '0'
                }}
            >
                {parts.map((part, index) => {
                // Controllo se questa parte è il tag ACTIVATE_USER
                const activateMatch = part.match(/\[ACTIVATE_USER:(\d+)\]/);
                
                if (activateMatch) {
                    const userId = activateMatch[1];
                    return (
                        <span key={index} className="inline-block my-1 mx-1">
                            <button
                                onClick={() => handleActivate(userId)}
                                className="bg-green-600 hover:bg-green-500 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors flex items-center gap-1"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                                </svg>
                                Attiva Utente #{userId}
                            </button>
                        </span>
                    );
                }

                // Controllo se questa parte è il tag DELETE_USER
                const deleteMatch = part.match(/\[DELETE_USER:(\d+)\]/);
                
                if (deleteMatch) {
                    const userId = deleteMatch[1];
                    return (
                        <span key={index} className="inline-block my-1 mx-1">
                            <button
                                onClick={() => handleDelete(userId)}
                                className="bg-red-600 hover:bg-red-500 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors flex items-center gap-1"
                            >
                                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                                </svg>
                                Elimina Utente #{userId}
                            </button>
                        </span>
                    );
                }

                const confirmDeathMatch = part.match(/\[CONFIRM_DEATH:(\d+)\]/);
                if (confirmDeathMatch) {
                    const personaggioId = confirmDeathMatch[1];
                    return (
                        <span key={index} className="inline-block my-1 mx-1">
                            <button
                                onClick={() => handleConfirmDeath(personaggioId)}
                                className="bg-red-700 hover:bg-red-600 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors"
                            >
                                Conferma morte #{personaggioId}
                            </button>
                        </span>
                    );
                }

                const revokeDeathMatch = part.match(/\[REVOKE_DEATH:(\d+)\]/);
                if (revokeDeathMatch) {
                    const personaggioId = revokeDeathMatch[1];
                    return (
                        <span key={index} className="inline-block my-1 mx-1">
                            <button
                                onClick={() => handleRevokeDeath(personaggioId)}
                                className="bg-emerald-700 hover:bg-emerald-600 text-white text-xs font-bold py-1 px-3 rounded shadow transition-colors"
                            >
                                Revoca morte #{personaggioId}
                            </button>
                        </span>
                    );
                }

                // Se non è un tag, renderizziamo l'HTML normale (sicuro perché già sanitizzato)
                return (
                    <span 
                        key={index} 
                        dangerouslySetInnerHTML={{ __html: part }} 
                    />
                );
            })}
            </div>
        </>
    );
};

export default RichTextDisplay;