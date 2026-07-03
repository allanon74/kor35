import React, { useState, useEffect, useMemo } from 'react';
import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react';
import { searchPersonaggi, fetchAuthenticated, getPersonaggioDetail } from '../api';
import RichTextEditor from './RichTextEditor';
import { Shield, User, X, UserCircle, Eye, EyeOff } from 'lucide-react';
import { useCharacter } from './CharacterContext';

const filterTransferableItems = (oggetti = []) =>
  (oggetti || []).filter(
    (item) => item && item.id && item.tipo_oggetto === 'FIS' && !item.is_equipaggiato
  );

const ComposeMessageModal = ({
  isOpen,
  onClose,
  currentCharacterId,
  availableCharacters = [],
  onMessageSent,
  onLogout,
  replyToRecipient,
  availableTransferItems = [],
  currentCredits = 0,
  isCampaignStaffer = false,
}) => {
  const { transazioniGiocatoreAbilitate, bypassEventoGate } = useCharacter();
  const transferConsentito = transazioniGiocatoreAbilitate;
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
  const [selectedSenderId, setSelectedSenderId] = useState('');
  const [senderCredits, setSenderCredits] = useState(0);
  const [senderTransferItems, setSenderTransferItems] = useState([]);
  const [showOwnerToRecipient, setShowOwnerToRecipient] = useState(true);
  const [ownerLabel, setOwnerLabel] = useState('');

  const defaultShowOwnerToRecipient = !isCampaignStaffer;

  const ownCharacters = useMemo(
    () =>
      (availableCharacters || []).filter(
        (pg) => pg && pg.id && (pg.is_own === undefined || pg.is_own === true)
      ),
    [availableCharacters]
  );

  const selectedSender = useMemo(
    () => ownCharacters.find((pg) => String(pg.id) === String(selectedSenderId)) || null,
    [ownCharacters, selectedSenderId]
  );

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
        setSelectedSenderId(currentCharacterId ? String(currentCharacterId) : '');
        setShowOwnerToRecipient(defaultShowOwnerToRecipient);
        
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
  }, [isOpen, replyToRecipient, currentCharacterId, defaultShowOwnerToRecipient]);

  useEffect(() => {
    if (!isOpen) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await fetchAuthenticated('/api/personaggi/api/user/me/', { method: 'GET' }, onLogout);
        if (cancelled || !me) return;
        const label = `${me.first_name || ''} ${me.last_name || ''}`.trim() || me.username || 'Giocatore';
        setOwnerLabel(label);
      } catch {
        if (!cancelled) setOwnerLabel('Giocatore');
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [isOpen, onLogout]);

  // Inventario del personaggio mittente selezionato (crediti/oggetti per allegati).
  useEffect(() => {
    if (!isOpen || !selectedSenderId) {
      setSenderCredits(0);
      setSenderTransferItems([]);
      return;
    }

    let cancelled = false;

    const loadSenderInventory = async () => {
      if (String(selectedSenderId) === String(currentCharacterId)) {
        if (!cancelled) {
          setSenderCredits(Number(currentCredits || 0));
          setSenderTransferItems(filterTransferableItems(availableTransferItems));
        }
        return;
      }

      const fromList = ownCharacters.find((pg) => String(pg.id) === String(selectedSenderId));
      try {
        const detail = await getPersonaggioDetail(selectedSenderId, onLogout);
        if (cancelled) return;
        setSenderCredits(Number(detail?.crediti ?? fromList?.crediti ?? 0));
        setSenderTransferItems(filterTransferableItems(detail?.oggetti));
      } catch (err) {
        console.error('Errore caricamento inventario mittente', err);
        if (!cancelled) {
          setSenderCredits(Number(fromList?.crediti || 0));
          setSenderTransferItems([]);
        }
      }
    };

    loadSenderInventory();
    return () => {
      cancelled = true;
    };
  }, [
    isOpen,
    selectedSenderId,
    currentCharacterId,
    currentCredits,
    availableTransferItems,
    onLogout,
    ownCharacters,
  ]);

  useEffect(() => {
    setCreditiToSend('');
    setSelectedItemIds([]);
  }, [selectedSenderId]);

  // Logica di ricerca (Disabilitata se è messaggio staff)
  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (!isStaffMessage && query.length >= 2 && !selectedRecipient) {
        try {
          const data = await searchPersonaggi(query, selectedSenderId || currentCharacterId);
          setResults(data);
        } catch (err) {
          console.error("Errore ricerca", err);
        }
      } else {
        setResults([]);
      }
    }, 300);

    return () => clearTimeout(delayDebounceFn);
  }, [query, currentCharacterId, selectedSenderId, selectedRecipient, isStaffMessage]);

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

    if (includeTransfer && !transferConsentito) {
      setError('Allegati crediti/oggetti disponibili solo durante un evento aperto.');
      return;
    }

    const parsedCrediti = includeTransfer ? Math.max(0, Number(creditiToSend || 0)) : 0;
    if (includeTransfer && !Number.isFinite(parsedCrediti)) {
      setError("Importo crediti non valido.");
      return;
    }
    if (!selectedSenderId) {
      setError("Seleziona il personaggio mittente.");
      return;
    }

    if (parsedCrediti > Number(senderCredits || 0)) {
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
            mittente_personaggio_id: Number(selectedSenderId),
            titolo: titolo,
            testo: testo,
            is_staff_message: isStaffMessage, // Flag per il backend
            mostra_proprietario_giocatore: showOwnerToRecipient,
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

            {/* RIQUADRO MITTENTE — ben visibile */}
            {ownCharacters.length > 0 && (
              <div className="rounded-xl border-2 border-indigo-500/50 bg-indigo-950/40 p-4 space-y-3 shadow-lg shadow-indigo-900/20">
                <div className="flex items-start gap-3">
                  <div className="shrink-0 w-11 h-11 rounded-full bg-indigo-800 border border-indigo-400/40 flex items-center justify-center">
                    <UserCircle size={28} className="text-indigo-200" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[11px] font-bold uppercase tracking-widest text-indigo-300/90">
                      Stai scrivendo come
                    </div>
                    {ownCharacters.length > 1 ? (
                      <select
                        className="mt-1 w-full bg-gray-900 border border-indigo-500/40 rounded-lg p-2.5 text-lg font-bold text-white focus:ring-2 focus:ring-indigo-400 outline-none"
                        value={selectedSenderId}
                        onChange={(e) => setSelectedSenderId(e.target.value)}
                      >
                        {ownCharacters.map((pg) => (
                          <option key={pg.id} value={pg.id}>
                            {pg.nome}
                            {pg.campagna_nome ? ` · ${pg.campagna_nome}` : ''}
                          </option>
                        ))}
                      </select>
                    ) : (
                      <div className="mt-1 text-xl font-bold text-white truncate">
                        {selectedSender?.nome || 'Personaggio'}
                        {selectedSender?.campagna_nome ? (
                          <span className="text-sm font-normal text-indigo-200/80 ml-2">
                            {selectedSender.campagna_nome}
                          </span>
                        ) : null}
                      </div>
                    )}
                  </div>
                </div>

                <div className="rounded-lg border border-gray-600/80 bg-gray-900/60 p-3 space-y-2">
                  <label className="flex items-start gap-3 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={showOwnerToRecipient}
                      onChange={(e) => setShowOwnerToRecipient(e.target.checked)}
                      className="mt-1 w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500"
                    />
                    <span className="text-sm text-gray-100">
                      <span className="font-semibold block mb-0.5">
                        Mostra anche il giocatore proprietario nel messaggio
                      </span>
                      <span className="text-gray-400 text-xs">
                        Se disattivato, il destinatario vede solo il personaggio mittente.
                      </span>
                    </span>
                  </label>

                  <div
                    className={`flex items-center gap-2 rounded-lg px-3 py-2 text-sm border ${
                      showOwnerToRecipient
                        ? 'bg-emerald-950/40 border-emerald-600/40 text-emerald-100'
                        : 'bg-gray-800/80 border-gray-600/50 text-gray-300'
                    }`}
                  >
                    {showOwnerToRecipient ? <Eye size={16} className="shrink-0" /> : <EyeOff size={16} className="shrink-0" />}
                    <span>
                      Il destinatario vedrà:{' '}
                      <strong>{selectedSender?.nome || 'personaggio'}</strong>
                      {showOwnerToRecipient ? (
                        <>
                          {' '}
                          <span className="text-gray-400">(giocatore:</span>{' '}
                          <strong>{ownerLabel || '…'}</strong>
                          <span className="text-gray-400">)</span>
                        </>
                      ) : (
                        <span className="text-gray-400"> — identità giocatore nascosta</span>
                      )}
                    </span>
                  </div>
                </div>
              </div>
            )}
            
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
                {!transferConsentito && !bypassEventoGate && (
                  <p className="text-xs text-amber-300/90">
                    Crediti e oggetti via messaggio sono disponibili solo durante un evento aperto.
                  </p>
                )}
                <label className={`inline-flex items-center gap-2 text-sm font-medium text-gray-200 ${transferConsentito ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'}`}>
                  <input
                    type="checkbox"
                    checked={includeTransfer}
                    disabled={!transferConsentito}
                    onChange={(e) => {
                      const enabled = e.target.checked;
                      setIncludeTransfer(enabled);
                      if (!enabled) {
                        setCreditiToSend('');
                        setSelectedItemIds([]);
                      }
                    }}
                    className="w-4 h-4 text-indigo-600 rounded focus:ring-indigo-500 disabled:opacity-50"
                  />
                  Allega crediti e/o oggetti
                </label>

                {includeTransfer && (
                  <div className="space-y-3">
                    <div>
                      <label className="block text-xs uppercase tracking-wide text-gray-400 mb-1">
                        Crediti (disponibili: {Number(senderCredits || 0)})
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
                        {senderTransferItems.length === 0 ? (
                          <div className="p-2 text-xs text-gray-500">Nessun oggetto trasferibile.</div>
                        ) : (
                          senderTransferItems.map((item) => (
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