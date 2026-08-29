import React, { useState, useEffect, useMemo, useCallback } from 'react';
import { Dialog, DialogPanel, DialogTitle, DialogBackdrop } from '@headlessui/react';
import { searchPersonaggi, fetchAuthenticated, getPersonaggioDetail } from '../api';
import RichTextEditor from './RichTextEditor';
import { Shield, User, X, UserCircle, Eye, EyeOff, ChevronDown } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { useDirtyModalClose } from '../hooks/useDirtyModalClose';
import { richTextHasContent } from '../utils/htmlSanitizer';

const filterTransferableItems = (oggetti = []) =>
  (oggetti || []).filter(
    (item) => item && item.id && item.tipo_oggetto === 'FIS' && !item.is_equipaggiato
  );

const hasMeaningfulText = (html) => richTextHasContent(html);

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
  const [isStaffMessage, setIsStaffMessage] = useState(false);
  const [titolo, setTitolo] = useState('');
  const [testo, setTesto] = useState('');
  const [includeTransfer, setIncludeTransfer] = useState(false);
  const [creditiToSend, setCreditiToSend] = useState('');
  const [contoCrediti, setContoCrediti] = useState('CORRENTE');
  const [selectedItemIds, setSelectedItemIds] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [selectedSenderId, setSelectedSenderId] = useState('');
  const [senderCredits, setSenderCredits] = useState(0);
  const [senderCorrente, setSenderCorrente] = useState(0);
  const [senderDeposito, setSenderDeposito] = useState(0);
  const [senderDuale, setSenderDuale] = useState(false);
  const [senderTransferItems, setSenderTransferItems] = useState([]);
  const [showOwnerToRecipient, setShowOwnerToRecipient] = useState(true);
  const [ownerLabel, setOwnerLabel] = useState('');
  // Il pannello mittente parte chiuso: su smartphone occupava tutto lo spazio
  // lasciando l'editor del messaggio fuori schermo.
  const [senderPanelOpen, setSenderPanelOpen] = useState(false);

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

  const isDirty = useMemo(() => {
    if (titolo.trim()) return true;
    if (hasMeaningfulText(testo)) return true;
    if (includeTransfer && (Number(creditiToSend) > 0 || selectedItemIds.length > 0)) return true;
    if (isStaffMessage && !replyToRecipient?.isStaff) return true;
    if (selectedRecipient && !replyToRecipient) return true;
    if (query.trim().length >= 2 && !selectedRecipient) return true;
    return false;
  }, [
    titolo,
    testo,
    includeTransfer,
    creditiToSend,
    selectedItemIds,
    isStaffMessage,
    replyToRecipient,
    selectedRecipient,
    query,
  ]);

  const requestClose = useDirtyModalClose(
    isDirty && !loading,
    onClose,
    'Il messaggio non è stato inviato. Se chiudi perderai testo, destinatario e allegati.\n\nChiudere comunque?'
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
      setContoCrediti('CORRENTE');
      setSelectedItemIds([]);
      setError('');
      setSelectedSenderId(currentCharacterId ? String(currentCharacterId) : '');
      setShowOwnerToRecipient(defaultShowOwnerToRecipient);
      setSenderPanelOpen(false);

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

  useEffect(() => {
    if (!isOpen || !selectedSenderId) {
      setSenderCredits(0);
      setSenderCorrente(0);
      setSenderDeposito(0);
      setSenderDuale(false);
      setSenderTransferItems([]);
      return;
    }

    let cancelled = false;

    const applyBalances = (detail, fallbackCredits) => {
      const duale = !!(detail?.economia?.modulo_attivo);
      const corr = Number(detail?.crediti_corrente ?? detail?.crediti ?? fallbackCredits ?? 0);
      const dep = Number(detail?.crediti_deposito ?? 0);
      setSenderDuale(duale);
      setSenderCorrente(corr);
      setSenderDeposito(dep);
      setSenderCredits(
        duale ? (contoCrediti === 'DEPOSITO' ? dep : corr) : Number(detail?.crediti ?? fallbackCredits ?? 0)
      );
    };

    const loadSenderInventory = async () => {
      if (String(selectedSenderId) === String(currentCharacterId)) {
        if (!cancelled) {
          setSenderCredits(Number(currentCredits || 0));
          setSenderCorrente(Number(currentCredits || 0));
          setSenderDeposito(0);
          setSenderDuale(false);
          setSenderTransferItems(filterTransferableItems(availableTransferItems));
          try {
            const detail = await getPersonaggioDetail(selectedSenderId, onLogout);
            if (!cancelled && detail) applyBalances(detail, currentCredits);
          } catch {
            /* keep fallback */
          }
        }
        return;
      }

      const fromList = ownCharacters.find((pg) => String(pg.id) === String(selectedSenderId));
      try {
        const detail = await getPersonaggioDetail(selectedSenderId, onLogout);
        if (cancelled) return;
        applyBalances(detail, fromList?.crediti);
        setSenderTransferItems(filterTransferableItems(detail?.oggetti || []));
      } catch {
        if (!cancelled) {
          setSenderCredits(Number(fromList?.crediti || 0));
          setSenderCorrente(Number(fromList?.crediti || 0));
          setSenderDeposito(0);
          setSenderDuale(false);
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
    ownCharacters,
    onLogout,
    contoCrediti,
  ]);

  useEffect(() => {
    setCreditiToSend('');
    setSelectedItemIds([]);
  }, [selectedSenderId]);

  useEffect(() => {
    const delayDebounceFn = setTimeout(async () => {
      if (!isStaffMessage && query.length >= 2 && !selectedRecipient) {
        try {
          const data = await searchPersonaggi(query, selectedSenderId || currentCharacterId);
          setResults(data);
        } catch (err) {
          console.error('Errore ricerca', err);
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

    if (!isStaffMessage && !selectedRecipient) {
      setError("Devi selezionare un destinatario o spuntare 'Scrivi allo Staff'.");
      return;
    }

    if (!hasMeaningfulText(testo)) {
      setError('Il messaggio non può essere vuoto.');
      return;
    }

    if (includeTransfer && !transferConsentito) {
      setError('Allegati crediti/oggetti disponibili solo durante un evento aperto.');
      return;
    }

    const parsedCrediti = includeTransfer ? Math.max(0, Number(creditiToSend || 0)) : 0;
    if (includeTransfer && !Number.isFinite(parsedCrediti)) {
      setError('Importo crediti non valido.');
      return;
    }
    if (!selectedSenderId) {
      setError('Seleziona il personaggio mittente.');
      return;
    }

    const availableForSend = senderDuale
      ? contoCrediti === 'DEPOSITO'
        ? senderDeposito
        : senderCorrente
      : Number(senderCredits || 0);
    if (parsedCrediti > availableForSend) {
      setError('Crediti insufficienti per questo invio.');
      return;
    }
    if (isStaffMessage && (parsedCrediti > 0 || selectedItemIds.length > 0)) {
      setError('Non puoi allegare crediti/oggetti nei messaggi allo staff.');
      return;
    }
    if (typeof navigator !== 'undefined' && !navigator.onLine) {
      setError(
        'Sei offline: l’invio messaggi (e trasferimenti) è bloccato finché non torna la connessione al server.'
      );
      return;
    }

    setLoading(true);
    setError('');

    try {
      const payload = {
        destinatario_id: isStaffMessage ? null : selectedRecipient.id,
        mittente_personaggio_id: Number(selectedSenderId),
        titolo: titolo,
        testo: testo,
        is_staff_message: isStaffMessage,
        mostra_proprietario_giocatore: showOwnerToRecipient,
        crediti_da_inviare: parsedCrediti,
        conto_crediti: includeTransfer ? contoCrediti : 'CORRENTE',
        oggetti_ids: includeTransfer ? selectedItemIds : [],
      };

      await fetchAuthenticated(
        '/api/personaggi/api/messaggi/send/',
        {
          method: 'POST',
          body: JSON.stringify(payload),
        },
        onLogout
      );

      if (onMessageSent) onMessageSent();
      onClose();
    } catch (err) {
      setError('Errore invio: ' + err.message);
    } finally {
      setLoading(false);
    }
  };

  const toggleItemSelection = useCallback((itemId) => {
    setSelectedItemIds((prev) =>
      prev.includes(itemId) ? prev.filter((id) => id !== itemId) : [...prev, itemId]
    );
  }, []);

  return (
    <Dialog open={isOpen} onClose={requestClose} className="relative z-50">
      <DialogBackdrop className="fixed inset-0 bg-black/80" />

      <div className="fixed inset-0 flex items-center justify-center p-3 sm:p-4">
        {/* Altezza definita su mobile: serve perché l'area di scrittura possa espandersi */}
        <DialogPanel className="mx-auto max-w-2xl w-full h-full sm:h-auto sm:max-h-[min(92vh,900px)] flex flex-col rounded-xl bg-gray-800 text-white shadow-2xl border border-gray-600 overflow-hidden">
          <div className="flex justify-between items-center gap-3 px-4 sm:px-6 py-4 border-b border-gray-700 shrink-0">
            <DialogTitle className="text-xl font-bold">Nuovo Messaggio</DialogTitle>
            <button
              type="button"
              onClick={requestClose}
              className="text-gray-400 hover:text-white p-1 rounded-lg hover:bg-white/10"
              aria-label="Chiudi"
            >
              <X size={24} />
            </button>
          </div>

          {error && (
            <div className="mx-4 sm:mx-6 mt-3 bg-red-900 text-red-200 p-2 rounded text-sm shrink-0">
              {error}
            </div>
          )}

          <form onSubmit={handleSendMessage} className="flex flex-col min-h-0 flex-1">
            {/*
              Intestazione scorrevole con altezza limitata: l'editor sotto conserva
              sempre spazio utile, anche su schermi piccoli.
            */}
            <div className="shrink-0 max-h-[40vh] overflow-y-auto px-4 sm:px-6 py-3 space-y-3 custom-scrollbar border-b border-gray-700/70">
              {ownCharacters.length > 0 && (
                <div className="rounded-xl border border-indigo-500/40 bg-indigo-950/30 overflow-hidden">
                  <button
                    type="button"
                    onClick={() => setSenderPanelOpen((open) => !open)}
                    aria-expanded={senderPanelOpen}
                    className="w-full flex items-center gap-3 p-3 text-left hover:bg-indigo-900/20 transition-colors"
                  >
                    <div className="shrink-0 w-9 h-9 rounded-full bg-indigo-800 border border-indigo-400/40 flex items-center justify-center">
                      <UserCircle size={22} className="text-indigo-200" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[10px] font-bold uppercase tracking-widest text-indigo-300/90">
                        Scrivi come
                      </div>
                      <div className="text-sm font-bold text-white truncate">
                        {selectedSender?.nome || 'Personaggio'}
                        <span className="ml-2 text-[11px] font-normal text-indigo-200/70">
                          {showOwnerToRecipient
                            ? `giocatore visibile${ownerLabel ? `: ${ownerLabel}` : ''}`
                            : 'giocatore nascosto'}
                        </span>
                      </div>
                    </div>
                    <ChevronDown
                      size={18}
                      className={`shrink-0 text-indigo-300 transition-transform ${senderPanelOpen ? 'rotate-180' : ''}`}
                    />
                  </button>

                  {senderPanelOpen && (
                    <div className="px-3 pb-3 space-y-3 border-t border-indigo-500/25">
                      {ownCharacters.length > 1 && (
                        <select
                          className="mt-3 w-full bg-gray-900 border border-indigo-500/40 rounded-lg p-2.5 text-base font-bold text-white focus:ring-2 focus:ring-indigo-400 outline-none"
                          value={selectedSenderId}
                          onChange={(e) => setSelectedSenderId(e.target.value)}
                          aria-label="Personaggio mittente"
                        >
                          {ownCharacters.map((pg) => (
                            <option key={pg.id} value={pg.id}>
                              {pg.nome}
                              {pg.campagna_nome ? ` · ${pg.campagna_nome}` : ''}
                            </option>
                          ))}
                        </select>
                      )}

                      <label className="flex items-start gap-3 cursor-pointer">
                        <input
                          type="checkbox"
                          checked={showOwnerToRecipient}
                          onChange={(e) => setShowOwnerToRecipient(e.target.checked)}
                          className="mt-0.5 w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500"
                        />
                        <span className="text-sm text-gray-100">
                          <span className="font-semibold block mb-0.5">
                            Mostra anche il giocatore proprietario
                          </span>
                          <span className="text-gray-400 text-xs">
                            Se disattivato, il destinatario vede solo il personaggio mittente.
                          </span>
                        </span>
                      </label>

                      <div
                        className={`flex items-center gap-2 rounded-lg px-3 py-2 text-xs border ${
                          showOwnerToRecipient
                            ? 'bg-emerald-950/40 border-emerald-600/40 text-emerald-100'
                            : 'bg-gray-800/80 border-gray-600/50 text-gray-300'
                        }`}
                      >
                        {showOwnerToRecipient ? (
                          <Eye size={15} className="shrink-0" />
                        ) : (
                          <EyeOff size={15} className="shrink-0" />
                        )}
                        <span>
                          Il destinatario vedrà: <strong>{selectedSender?.nome || 'personaggio'}</strong>
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
                  )}
                </div>
              )}

              <div className="flex items-center gap-3 p-2.5 bg-gray-700/50 rounded border border-gray-600">
                <input
                  type="checkbox"
                  id="chk_staff"
                  checked={isStaffMessage}
                  onChange={(e) => {
                    setIsStaffMessage(e.target.checked);
                    if (e.target.checked) {
                      setSelectedRecipient(null);
                      setQuery('');
                      setIncludeTransfer(false);
                      setCreditiToSend('');
                      setSelectedItemIds([]);
                    }
                  }}
                  disabled={replyToRecipient?.isStaff}
                  className="w-5 h-5 text-indigo-600 rounded focus:ring-indigo-500 cursor-pointer disabled:opacity-50"
                />
                <label
                  htmlFor="chk_staff"
                  className="cursor-pointer flex items-center gap-2 font-bold text-indigo-300"
                >
                  <Shield size={18} />
                  Invia messaggio allo Staff
                </label>
              </div>

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
                      <User size={16} className="absolute left-3 top-3 text-gray-500" />
                    </div>

                    {selectedRecipient && !replyToRecipient && (
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedRecipient(null);
                          setQuery('');
                        }}
                        className="text-red-400 hover:text-red-300 px-3 border border-red-900/50 rounded bg-red-900/10"
                      >
                        Cambia
                      </button>
                    )}
                  </div>

                  {results.length > 0 && !selectedRecipient && (
                    <ul className="absolute z-50 w-full bg-gray-700 border border-gray-600 rounded mt-1 max-h-40 overflow-auto shadow-lg">
                      {results.map((pg) => (
                        <li
                          key={pg.id}
                          onClick={() => handleSelect(pg)}
                          className="p-2 hover:bg-indigo-600 cursor-pointer text-sm border-b border-gray-600 flex justify-between"
                        >
                          <span>{pg.nome}</span>
                          {pg.user_username && (
                            <span className="text-gray-400 text-xs">@{pg.user_username}</span>
                          )}
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}

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
                  <label
                    className={`inline-flex items-center gap-2 text-sm font-medium text-gray-200 ${
                      transferConsentito ? 'cursor-pointer' : 'cursor-not-allowed opacity-60'
                    }`}
                  >
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
                          Crediti (disponibili:{' '}
                          {senderDuale
                            ? contoCrediti === 'DEPOSITO'
                              ? Number(senderDeposito || 0).toFixed(2)
                              : Number(senderCorrente || 0).toFixed(2)
                            : Number(senderCredits || 0)}
                          )
                        </label>
                        {senderDuale && (
                          <select
                            className="w-full mb-2 bg-gray-900 border border-gray-700 rounded p-2 text-sm"
                            value={contoCrediti}
                            onChange={(e) => setContoCrediti(e.target.value)}
                          >
                            <option value="CORRENTE">Da conto corrente</option>
                            <option value="DEPOSITO">Da conto deposito</option>
                          </select>
                        )}
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={creditiToSend}
                          onChange={(e) => setCreditiToSend(e.target.value)}
                          className="w-full bg-gray-900 border border-gray-700 rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none"
                          placeholder="0"
                        />
                        {senderDuale && (
                          <p className="text-xs text-gray-500 mt-1">
                            Il destinatario riceve sullo stesso conto.
                          </p>
                        )}
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
                                <span className="text-sm text-gray-200">
                                  {item.nome || `Oggetto ${item.id}`}
                                </span>
                              </label>
                            ))
                          )}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              )}

            </div>

            {/* Area di scrittura: occupa tutta l'altezza rimasta nel modal */}
            <div className="flex-1 min-h-0 flex flex-col px-4 sm:px-6 py-3">
              <RichTextEditor
                label="Testo del messaggio"
                value={testo}
                onChange={setTesto}
                placeholder="Scrivi qui il tuo messaggio…"
                fillHeight
              />
            </div>

            <div className="flex justify-end gap-3 px-4 sm:px-6 py-3 border-t border-gray-700 bg-gray-900/90 shrink-0">
              <button
                type="button"
                onClick={requestClose}
                className="px-4 py-2 rounded bg-gray-700 hover:bg-gray-600 transition-colors"
              >
                Annulla
              </button>
              <button
                type="submit"
                disabled={loading}
                className={`px-6 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-white font-bold transition-colors ${
                  loading ? 'opacity-50' : ''
                }`}
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
