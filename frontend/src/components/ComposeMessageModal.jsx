import React, { useState, useEffect } from 'react';
import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react';
import { searchPersonaggi, fetchAuthenticated } from '../api';
import RichTextEditor from './RichTextEditor';
import { Shield, User, X } from 'lucide-react';

const ComposeMessageModal = ({
  isOpen,
  onClose,
  currentCharacterId,
  onMessageSent,
  onLogout,
  replyToRecipient,
  availableTransferItems = [],
  currentCredits = 0,
}) => {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [selectedRecipient, setSelectedRecipient] = useState(null);
  
  // NUOVO: Toggle per invio staff
  const [isStaffMessage, setIsStaffMessage] = useState(false);
  
  const [titolo, setTitolo] = useState('');
  const [testo, setTesto] = useState(''); // HTML content
  const [includeTransfer, setIncludeTransfer] = useState(false);
  const [creditiToSend, setCreditiToSend] = useState('');
  const [selectedItemIds, setSelectedItemIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(''); 

  // Reset stato all'apertura
  useEffect(() => {
    if (isOpen) {
        setQuery('');
        setResults([]);
        setTitolo('');
        setTesto('');
        setIncludeTransfer(false);
        setCreditiToSend('');
        setSelectedItemIds([]);
        setError('');
        
        // Se c'è un destinatario pre-impostato (risposta)
        if (replyToRecipient) {
            if (replyToRecipient.isStaff) {
                setIsStaffMessage(true);
                setSelectedRecipient(null);
            } else {
                setIsStaffMessage(false);
                setSelectedRecipient(replyToRecipient);
                setQuery(replyToRecipient.nome || '');
            }
        } else {
            setSelectedRecipient(null);
            setIsStaffMessage(false);
        }
    }
  }, [isOpen, replyToRecipient]);

  // Logica di ricerca (Disabilitata se è messaggio staff)
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (!isStaffMessage && query.length >= 2 && !selectedRecipient) {
        try {
          const data = await searchPersonaggi(query, currentCharacterId);
          setResults(data);
        } catch (err) {
          console.error("Errore ricerca", err);
        }
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [query, currentCharacterId, selectedRecipient, isStaffMessage]);

  const handleSelect = (pg) => {
    setSelectedRecipient(pg);
    setQuery(pg.nome);
    setResults([]);
  };

  const handleSendMessage = async (e) => {
    e.preventDefault();
    
    // Validazione
    if (!isStaffMessage && !selectedRecipient) {
        setError("Devi selezionare un destinatario o spuntare 'Scrivi allo Staff'.");
        return;
    }

    // Pulizia HTML vuoto
    const cleanText = testo.replace(/<[^>]+>/g, '').trim();
    if (!cleanText && !testo.includes('<img')) {
        setError("Il messaggio non può essere vuoto.");
        return;
    }

    const parsedCrediti = includeTransfer ? Math.max(0, Number(creditiToSend || 0)) : 0;
    if (includeTransfer && !Number.isFinite(parsedCrediti)) {
      setError("Importo crediti non valido.");
      return;
    }
    if (parsedCrediti > Number(currentCredits || 0)) {
      setError("Crediti insufficienti per questo invio.");
      return;
    }
    if (isStaffMessage && (parsedCrediti > 0 || selectedItemIds.length > 0)) {
      setError("Non puoi allegare crediti/oggetti nei messaggi allo staff.");
      return;
    }

    setLoading(true);
    setError('');

    try {
        const payload = {
            // Se Staff Message è true, destinatario è NULL
            destinatario_id: isStaffMessage ? null : selectedRecipient.id,
            mittente_personaggio_id: currentCharacterId ? Number(currentCharacterId) : null,
            titolo: titolo,
            testo: testo,
            is_staff_message: isStaffMessage, // Flag per il backend
            crediti_da_inviare: parsedCrediti,
            oggetti_ids: includeTransfer ? selectedItemIds : [],
        };

        await fetchAuthenticated('/api/personaggi/api/messaggi/send/', {
            method: 'POST',
            body: JSON.stringify(payload)
        }, onLogout);

        if (onMessageSent) onMessageSent();
        onClose();
    } catch (err) {
        setError('Errore invio: ' + err.message);
    } finally {
        setLoading(false);
    }
  };

  const toggleItemSelection = (itemId) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  };

  return (
    <Dialog open={isOpen} onClose={onClose} className="relative z-50">
      {/* Backdrop */}
      <DialogBackdrop className="fixed inset-0 bg-black/80" />

      {/* Container per centrare il panel */}
      <div className="fixed inset-0 flex items-center justify-center p-4">
        <DialogPanel className="mx-auto max-w-2xl w-full rounded-lg bg-gray-800 text-white p-6 shadow-2xl border border-gray-600">
          <div className="flex justify-between items-center mb-4">
             <DialogTitle className="text-xl font-bold">Nuovo Messaggio</DialogTitle>
             <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={24}/></button>
          </div>

          {error && <div className="bg-red-900 text-red-200 p-2 rounded mb-4 text-sm">{error}</div>}

          <form onSubmit={handleSendMessage} className="space-y-4">
            
            {/* OPZIONE STAFF */}
            <div className="flex items-center gap-3 p-3 bg-gray-700/50 rounded border border-gray-600">
                <input 
                    type="checkbox" 
                    id="chk_staff"
                    checked={isStaffMessage}
                    onChange={(e) => {
                        setIsStaffMessage(e.target.checked);
                        if(e.target.checked) {
                            setSelectedRecipient(null);
                            setQuery('');
                            setIncludeTransfer(false);
                            setCreditiToSend('');
                            setSelectedItemIds([]);
                        }
                    }}
                    disabled={replyToRecipient?.isStaff} // Disabilita se stiamo rispondendo allo staff
                    className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                />
                <label htmlFor="chk_staff" className="cursor-pointer flex items-center gap-2 font-bold text-indigo-300">
                    <Shield size={18} />
                    Invia messaggio allo Staff
                </label>
            </div>

            {/* RICERCA DESTINATARIO (Nascosta se Staff è attivo) */}
            {!isStaffMessage && (
                <div className="relative">
                    <label className="block text-sm font-medium text-gray-400 mb-1">Destinatario</label>
                    <div className="flex gap-2">
                        <div className="relative w-full">
                            <input
                                type="text"
                                className="w-full bg-gray-900 border border-gray-700 rounded p-2 pl-9 focus:ring-2 focus:ring-indigo-500 outline-none"
                                placeholder="Cerca personaggio..."
                                value={query}
                                onChange={(e) => setQuery(e.target.value)}
                                disabled={!!selectedRecipient}
                            />
                            <User size={16} className="absolute left-3 top-3 text-gray-500"/>
                        </div>
                        
                        {selectedRecipient && !replyToRecipient && (
                            <button 
                                type="button" 
                                onClick={() => { setSelectedRecipient(null); setQuery(''); }}
                                className="text-red-400 hover:text-red-300 px-3 border border-red-900/50 rounded bg-red-900/10"
                            >
                                Cambia
                            </button>
                        )}
                    </div>
                    
                    {/* Lista Risultati */}
                    {results.length > 0 && !selectedRecipient && (
                        <ul className="absolute z-50 w-full bg-gray-700 border border-gray-600 rounded mt-1 max-h-40 overflow-auto shadow-lg">
                            {results.map(pg => (
                                <li 
                                    key={pg.id} 
                                    onClick={() => handleSelect(pg)}
                                    className="p-2 hover:bg-indigo-600 cursor-pointer text-sm border-b border-gray-600 flex justify-between"
                                >
                                    <span>{pg.nome}</span>
                                    {pg.user_username && <span className="text-gray-400 text-xs">@{pg.user_username}</span>}
                                </li>
                            ))}
                        </ul>
                    )}
                </div>
            )}

            {/* Titolo */}
            <div>
              <label className="block text-sm font-medium text-gray-400 mb-1">Oggetto</label>
              <input
                type="text"
                className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                value={titolo}
                onChange={(e) => setTitolo(e.target.value)}
                maxLength={100}
                required
              />
            </div>

            {!isStaffMessage && (
              <div className="rounded border border-gray-700 bg-gray-900/40 p-3 space-y-3">
                <label className="inline-flex items-center gap-2 text-sm font-medium text-gray-200 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeTransfer}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setIncludeTransfer(enabled);
                      if (!enabled) {
                        setCreditiToSend('');
                        setSelectedItemIds([]);
                      }
                    }}
                    className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                  />
                  Allega crediti e/o oggetti
                </label>

                {includeTransfer && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">
                        Crediti (disponibili: {Number(currentCredits || 0)})
                      </label>
                      <input
                        type="number"
                        min="0"
                        step="1"
                        value={creditiToSend}
                        onChange={(e) => setCreditiToSend(e.target.value)}
                        className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                        placeholder="0"
                      />
                    </div>

                    <div>
                      <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">
                        Oggetti da inviare
                      </label>
                      <div className="max-h-32 overflow-y-auto border border-gray-700 rounded bg-gray-900">
                        {availableTransferItems.length === 0 ? (
                          <div className="p-2 text-xs text-gray-500">Nessun oggetto trasferibile.</div>
                        ) : (
                          availableTransferItems.map((item) => (
                            <label
                              key={item.id}
                              className="flex items-center gap-2 p-2 border-b border-gray-800 last:border-b-0 cursor-pointer hover:bg-gray-800/60"
                            >
                              <input
                                type="checkbox"
                                checked={selectedItemIds.includes(item.id)}
                                onChange={() => toggleItemSelection(item.id)}
                                className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500"
                              />
                              <span className="text-sm text-gray-200">{item.nome || `Oggetto ${item.id}`}</span>
                            </label>
                          ))
                        )}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Editor */}
            <div className="h-64 sm:h-80 text-black rounded overflow-hidden">
                <RichTextEditor 
                    label="Testo"
                    value={testo} 
                    onChange={setTesto} 
                    placeholder="Scrivi qui..."
                />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-gray-700 mt-4">
              <button type="button" onClick={onClose} className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors">Annulla</button>
              <button 
                type="submit" 
                disabled={loading}
                className={`px-6 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-colors ${loading ? 'opacity-50' : ''}`}
              >
                {loading ? 'Invio...' : 'Invia'}
              </button>
            </div>

          </form>
        </DialogPanel>
      </div>
    </Dialog>
  );
};

export default ComposeMessageModal;