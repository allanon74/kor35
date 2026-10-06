import React, { useState, useEffect, Fragment } from 'react';
import { Tab } from '@headlessui/react';
import { useCharacter } from './CharacterContext';
import { 
    postBroadcastMessage, 
    getAdminSentMessages, 
    fetchStaffMessages, 
    searchPersonaggi,
    markStaffMessageAsRead,
    deleteStaffMessage,
    getStaffMessaggiModelli,
    createStaffMessaggioModello,
    deleteStaffMessaggioModello,
    getStaffPoolPgMeta,
    postMessaggioEventoInvio,
} from '../api';
import RichTextEditor from './RichTextEditor';
import RichTextDisplay from './RichTextDisplay';
import { Mail, Users, Shield, Search, X, RefreshCw, Trash2, Eye, EyeOff, Reply, Send, Calendar, BookmarkPlus } from 'lucide-react';

function classNames(...classes) {
  return classes.filter(Boolean).join(' ');
}

const AdminMessageTab = ({ onLogout }) => {
    const { isCampaignStaffer, isAdmin } = useCharacter();
    const canAccessStaffInbox = isCampaignStaffer || isAdmin;

    // Gestione tab attiva
    const [selectedTab, setSelectedTab] = useState(0);

    // --- STATI TAB INBOX (Posta Staff) ---
    const [inboxMessages, setInboxMessages] = useState([]);
    const [isLoadingInbox, setIsLoadingInbox] = useState(false);
    const [optimisticReadStates, setOptimisticReadStates] = useState({}); // Optimistic UI

    // --- STATI TAB COMPONI ---
    const [targetType, setTargetType] = useState('broadcast'); // 'broadcast', 'group', 'single', 'evento'
    const [selectedGroup, setSelectedGroup] = useState('tutti');
    const [singleRecipient, setSingleRecipient] = useState(null); // Oggetto PG selezionato
    const [searchQuery, setSearchQuery] = useState('');
    const [searchResults, setSearchResults] = useState([]);
    const [eventi, setEventi] = useState([]);
    const [selectedEventoId, setSelectedEventoId] = useState('');
    const [modelli, setModelli] = useState([]);
    const [modelloNome, setModelloNome] = useState('');
    
    const [title, setTitle] = useState('');
    const [text, setText] = useState('');
    const [saveHistory, setSaveHistory] = useState(true);
    const [isSending, setIsSending] = useState(false);
    const [feedback, setFeedback] = useState({ type: '', msg: '' });

    // --- STATI TAB CRONOLOGIA ---
    const [history, setHistory] = useState([]); 
    const [isLoadingHistory, setIsLoadingHistory] = useState(false);

    // --- EFFETTI ---
    useEffect(() => {
        if (canAccessStaffInbox) {
            loadInbox();
            loadHistory();
            loadModelli();
            loadEventi();
        }
    // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [canAccessStaffInbox]);

    // Carica Inbox Staff
    const loadInbox = async () => {
        setIsLoadingInbox(true);
        try {
            const data = await fetchStaffMessages(onLogout);
            setInboxMessages(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Errore caricamento inbox:", err);
        } finally {
            setIsLoadingInbox(false);
        }
    };

    // Marca messaggio come letto/non letto
    const handleToggleRead = async (messageId, currentStatus) => {
        // Optimistic update
        setOptimisticReadStates(prev => ({ ...prev, [messageId]: !currentStatus }));
        
        try {
            if (!currentStatus) {
                // Se non è letto, marcalo come letto
                await markStaffMessageAsRead(messageId, onLogout);
            }
            // Ricarica i messaggi per aggiornare lo stato
            loadInbox();
        } catch (err) {
            console.error("Errore marcatura messaggio:", err);
            alert('Errore nel marcare il messaggio: ' + err.message);
            // Ripristina lo stato precedente in caso di errore
            setOptimisticReadStates(prev => {
                const newState = { ...prev };
                delete newState[messageId];
                return newState;
            });
        }
    };

    // Elimina messaggio
    const handleDeleteMessage = async (messageId) => {
        if (!window.confirm('Sei sicuro di voler eliminare questo messaggio?')) {
            return;
        }
        
        try {
            await deleteStaffMessage(messageId, onLogout);
            // Ricarica i messaggi dopo l'eliminazione
            loadInbox();
        } catch (err) {
            console.error("Errore eliminazione messaggio:", err);
            alert('Errore nell\'eliminazione: ' + err.message);
        }
    };

    // Risponde a un messaggio (prepara invio singolo)
    const handleReplyToPlayer = (msg) => {
        console.log('Reply to player message:', msg); // Debug
        
        // Imposta il destinatario e passa alla tab compose
        if (msg.mittente_personaggio_id) {
            setSingleRecipient({ 
                id: msg.mittente_personaggio_id, 
                nome: msg.mittente_personaggio_nome || msg.mittente_nome 
            });
            setTargetType('single');
            setSearchQuery(msg.mittente_personaggio_nome || msg.mittente_nome || '');
            // Cambia alla tab "Nuovo Msg" (index 1)
            setSelectedTab(1);
        } else {
            console.error('Impossibile rispondere: mittente_personaggio_id non valido', msg);
            alert('Impossibile rispondere a questo messaggio (no mittente)');
        }
    };

    // Carica Cronologia
    const loadHistory = async () => {
        setIsLoadingHistory(true);
        try {
            const data = await getAdminSentMessages(onLogout);
            setHistory(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error("Errore caricamento cronologia:", err);
        } finally {
            setIsLoadingHistory(false);
        }
    };

    const loadModelli = async () => {
        try {
            const data = await getStaffMessaggiModelli(onLogout);
            setModelli(Array.isArray(data) ? data : []);
        } catch (err) {
            console.error('Errore modelli messaggio:', err);
        }
    };

    const loadEventi = async () => {
        try {
            const data = await getStaffPoolPgMeta(onLogout);
            setEventi(Array.isArray(data?.eventi) ? data.eventi : []);
            if (data?.evento_in_corso_id && !selectedEventoId) {
                setSelectedEventoId(String(data.evento_in_corso_id));
            }
        } catch (err) {
            console.error('Errore elenco eventi:', err);
        }
    };

    const handleApplyModello = (mod) => {
        setTitle(mod.titolo || '');
        setText(mod.testo || '');
        setFeedback({ type: 'success', msg: `Modello «${mod.nome}» caricato. Puoi modificarlo prima di inviare.` });
    };

    const handleSaveModello = async () => {
        const nome = modelloNome.trim() || title.trim();
        if (!nome || !text.trim()) {
            setFeedback({ type: 'error', msg: 'Per salvare un modello servono un nome (o oggetto) e un testo.' });
            return;
        }
        try {
            await createStaffMessaggioModello({ nome, titolo: title, testo: text }, onLogout);
            setModelloNome('');
            setFeedback({ type: 'success', msg: `Modello «${nome}» salvato.` });
            loadModelli();
        } catch (err) {
            setFeedback({ type: 'error', msg: err.message || 'Impossibile salvare il modello.' });
        }
    };

    const handleDeleteModello = async (mod) => {
        if (!window.confirm(`Eliminare il modello «${mod.nome}»?`)) return;
        try {
            await deleteStaffMessaggioModello(mod.id, onLogout);
            loadModelli();
        } catch (err) {
            setFeedback({ type: 'error', msg: err.message || 'Eliminazione fallita.' });
        }
    };

    // Gestione Ricerca PG (per invio singolo)
    useEffect(() => {
        const delayDebounceFn = setTimeout(async () => {
            if (targetType === 'single' && searchQuery.length >= 2 && !singleRecipient) {
                try {
                    const results = await searchPersonaggi(searchQuery);
                    setSearchResults(results);
                } catch (error) {
                    console.error("Errore ricerca:", error);
                }
            } else {
                setSearchResults([]);
            }
        }, 300);
        return () => clearTimeout(delayDebounceFn);
    }, [searchQuery, targetType, singleRecipient]);


    // Gestione Invio
    const handleSend = async (e) => {
        e.preventDefault();
        setFeedback({ type: '', msg: '' });

        if (!title.trim() || !text.trim()) {
            setFeedback({ type: 'error', msg: 'Titolo e testo sono obbligatori.' });
            return;
        }

        if (targetType === 'single' && !singleRecipient) {
            setFeedback({ type: 'error', msg: 'Devi selezionare un destinatario per l\'invio singolo.' });
            return;
        }
        if (targetType === 'evento' && !selectedEventoId) {
            setFeedback({ type: 'error', msg: 'Seleziona un evento per l\'invio agli iscritti.' });
            return;
        }

        setIsSending(true);

        try {
            if (targetType === 'single') {
                await postMessaggioEventoInvio({
                    destinatario_id: singleRecipient.id,
                    titolo: title,
                    testo: text,
                }, onLogout);
            } else if (targetType === 'evento') {
                const res = await postMessaggioEventoInvio({
                    evento_id: selectedEventoId,
                    titolo: title,
                    testo: text,
                }, onLogout);
                setFeedback({ type: 'success', msg: `Inviate ${res.inviati} copie individuali agli iscritti.` });
                setTitle('');
                setText('');
                loadHistory();
                setIsSending(false);
                return;
            } else {
                // Invio Broadcast o Gruppo (Usa la tua API postBroadcastMessage esistente)
                const payload = {
                    titolo: title,
                    testo: text,
                    target_type: targetType,
                    target_group: targetType === 'group' ? selectedGroup : null,
                    save_history: saveHistory
                };
                await postBroadcastMessage(payload, onLogout);
            }

            setFeedback({ type: 'success', msg: 'Messaggio inviato con successo!' });
            setTitle('');
            setText('');
            setSingleRecipient(null);
            setSearchQuery('');
            loadHistory(); // Aggiorna la tab cronologia
        } catch (err) {
            setFeedback({ type: 'error', msg: 'Errore invio: ' + err.message });
        } finally {
            setIsSending(false);
        }
    };

    if (!canAccessStaffInbox) {
        return (
            <div className="flex flex-col items-center justify-center h-64 text-red-400 p-4">
                <Shield size={48} className="mb-2" />
                <h3 className="text-xl font-bold">Accesso Negato</h3>
                <p>Area riservata allo Staff.</p>
            </div>
        );
    }

    return (
        <div className="w-full h-full flex flex-col bg-gray-900 rounded-lg shadow-xl overflow-hidden border border-gray-800">
            <Tab.Group selectedIndex={selectedTab} onChange={setSelectedTab}>
                <div className="bg-gray-800 p-2 border-b border-gray-700">
                    <Tab.List className="flex space-x-2 rounded-xl bg-gray-900/50 p-1">
                        
                        {/* TAB 1: INBOX */}
                        <Tab as={Fragment}>
                            {({ selected }) => (
                                <button className={classNames(
                                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all flex items-center justify-center gap-2',
                                    selected ? 'bg-green-700 text-white shadow' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                                )}>
                                    <Mail size={18} />
                                    <span>Posta Staff</span>
                                    {inboxMessages.filter(m => !m.letto).length > 0 && (
                                        <span className="bg-red-500 text-white text-[10px] font-bold px-2 py-0.5 rounded-full animate-pulse shadow-sm">
                                            {inboxMessages.filter(m => !m.letto).length}
                                        </span>
                                    )}
                                </button>
                            )}
                        </Tab>

                        {/* TAB 2: COMPOSE */}
                        <Tab as={Fragment}>
                            {({ selected }) => (
                                <button className={classNames(
                                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all flex items-center justify-center gap-2',
                                    selected ? 'bg-indigo-600 text-white shadow' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                                )}>
                                    <Send size={18} />
                                    <span>Nuovo Msg</span>
                                </button>
                            )}
                        </Tab>

                        {/* TAB 3: HISTORY */}
                        <Tab as={Fragment}>
                            {({ selected }) => (
                                <button className={classNames(
                                    'w-full rounded-lg py-2.5 text-sm font-medium leading-5 transition-all flex items-center justify-center gap-2',
                                    selected ? 'bg-gray-600 text-white shadow' : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                                )}>
                                    <RefreshCw size={18} />
                                    <span>Cronologia</span>
                                </button>
                            )}
                        </Tab>
                    </Tab.List>
                </div>

                <Tab.Panels className="flex-1 overflow-hidden relative">
                    
                    {/* --- PANEL 1: INBOX (Lettura messaggi admin/registrazioni) --- */}
                    <Tab.Panel className="h-full overflow-y-auto custom-scrollbar p-3 space-y-3">
                        <div className="flex justify-between items-center mb-2 px-1">
                            <h3 className="text-green-400 font-bold uppercase text-xs flex items-center gap-2">
                                <Shield size={14}/> Messaggi ricevuti (Admin)
                            </h3>
                            <button onClick={loadInbox} className="text-gray-400 hover:text-white p-1 rounded hover:bg-gray-700 transition-colors" title="Aggiorna">
                                <RefreshCw size={14}/>
                            </button>
                        </div>

                        {isLoadingInbox ? (
                            <div className="flex justify-center p-10"><RefreshCw className="animate-spin text-gray-500"/></div>
                        ) : inboxMessages.length === 0 ? (
                            <div className="flex flex-col items-center justify-center h-40 text-gray-500 border border-gray-700 border-dashed rounded-lg">
                                <Mail size={32} className="mb-2 opacity-50"/>
                                <p className="text-sm">Nessuna nuova richiesta o messaggio.</p>
                            </div>
                        ) : (
                            inboxMessages.map(msg => {
                                // Usa lo stato ottimistico se presente, altrimenti lo stato dal server
                                const isRead = optimisticReadStates[msg.id] !== undefined 
                                    ? optimisticReadStates[msg.id] 
                                    : msg.letto_staff;
                                
                                return (
                                <div key={msg.id} className={`rounded-lg p-4 shadow-md transition-all hover:bg-gray-750 border-l-4 ${isRead ? 'bg-gray-850 opacity-75 border-gray-600' : 'bg-gray-800 border-green-500'}`}>
                                    <div className="flex justify-between items-start mb-2 border-b border-gray-700 pb-2">
                                        <div className="flex-1">
                                            <div className="flex items-center gap-2 mb-1">
                                                <span className="font-bold text-green-300 block text-sm">
                                                    Da: {msg.mittente_personaggio_nome || msg.mittente_nome || 'Utente Sconosciuto / Sistema'}
                                                </span>
                                                {msg.mittente_proprietario_nome && (
                                                    <span className="text-[11px] text-gray-400 block">
                                                        Giocatore: {msg.mittente_proprietario_nome}
                                                        {!msg.mostra_proprietario_giocatore && (
                                                            <span className="ml-1 text-amber-400/90">(nascosto al destinatario)</span>
                                                        )}
                                                    </span>
                                                )}
                                                {!isRead && <span className="bg-green-600 text-white text-[9px] font-bold px-2 py-0.5 rounded shadow-sm uppercase tracking-wide animate-pulse">Nuovo</span>}
                                            </div>
                                            <span className="text-[10px] text-gray-500 uppercase tracking-wider">
                                                {new Date(msg.data_creazione || msg.data_invio).toLocaleString()}
                                            </span>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            
                                            {/* Pulsante Rispondi */}
                                            {msg.mittente_personaggio_id && (
                                                <button
                                                    onClick={() => handleReplyToPlayer(msg)}
                                                    className="p-1.5 bg-blue-900/50 hover:bg-blue-800 text-blue-300 rounded transition-colors"
                                                    title="Rispondi"
                                                >
                                                    <Reply size={14} />
                                                </button>
                                            )}
                                            
                                            {/* Pulsante Marca come Letto */}
                                            <button
                                                onClick={() => handleToggleRead(msg.id, isRead)}
                                                className={`p-1.5 rounded transition-colors ${isRead ? 'bg-gray-700 hover:bg-gray-600 text-gray-400' : 'bg-green-900/50 hover:bg-green-800 text-green-300'}`}
                                                title={isRead ? 'Già letto' : 'Segna come letto'}
                                            >
                                                {isRead ? <EyeOff size={14} /> : <Eye size={14} />}
                                            </button>
                                            
                                            {/* Pulsante Elimina */}
                                            <button
                                                onClick={() => handleDeleteMessage(msg.id)}
                                                className="p-1.5 bg-red-900/50 hover:bg-red-800 text-red-300 rounded transition-colors"
                                                title="Elimina messaggio"
                                            >
                                                <Trash2 size={14} />
                                            </button>
                                        </div>
                                    </div>
                                    
                                    <h4 className="font-bold text-white text-sm mb-2">{msg.titolo}</h4>
                                    
                                    {/* RichTextDisplay gestisce i bottoni di attivazione e eliminazione utente */}
                                    <div className="bg-gray-900/60 p-3 rounded text-sm text-gray-300 border border-gray-700/50">
                                        <RichTextDisplay content={msg.testo} onUpdate={loadInbox} onLogout={onLogout} />
                                    </div>
                                </div>
                                );
                            })
                        )}
                    </Tab.Panel>

                    {/* --- PANEL 2: COMPOSE (Invio Broadcast, Gruppi o Singolo) --- */}
                    <Tab.Panel className="h-full min-h-0 flex flex-col p-0">
                        <form onSubmit={handleSend} className="max-w-3xl mx-auto w-full flex flex-col min-h-0 flex-1 h-full">
                          {/*
                            Intestazione (destinatario + oggetto) con altezza limitata: l'editor
                            sotto riceve tutto lo spazio restante invece di finire in coda allo scroll.
                          */}
                          <div className="shrink-0 max-h-[38vh] overflow-y-auto custom-scrollbar p-4 pb-3 space-y-3">
                            {/* TARGET SELECTOR */}
                            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 bg-gray-800 p-1.5 rounded-lg border border-gray-700">
                                {[
                                    { type: 'broadcast', label: 'Tutti', icon: Send },
                                    { type: 'group', label: 'Gruppo', icon: Users },
                                    { type: 'single', label: 'Singolo', icon: Mail },
                                    { type: 'evento', label: 'Iscritti evento', icon: Calendar },
                                ].map(({ type, label, icon: Icon }) => (
                                    <label 
                                        key={type} 
                                        className={`flex min-h-11 items-center justify-center gap-2 p-2 rounded cursor-pointer transition-colors text-xs sm:text-sm font-bold ${targetType === type ? 'bg-indigo-600 text-white shadow' : 'hover:bg-gray-700 text-gray-400'}`}
                                    >
                                        <input type="radio" name="target" value={type} checked={targetType === type} onChange={() => setTargetType(type)} className="hidden" />
                                        <Icon size={16} />
                                        {label}
                                    </label>
                                ))}
                            </div>

                            {/* LOGICA SELEZIONE DESTINATARIO */}
                            <div className="animate-fadeIn empty:hidden">
                                {targetType === 'group' && (
                                    <div className="bg-gray-800 p-3 rounded-lg border border-gray-700">
                                        <label className="block text-xs font-bold text-gray-400 mb-1 uppercase">Seleziona Gruppo</label>
                                        <select 
                                            value={selectedGroup} 
                                            onChange={(e) => setSelectedGroup(e.target.value)}
                                            className="w-full bg-gray-900 border border-gray-600 text-white rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                        >
                                            <option value="tutti">Tutti i Personaggi</option>
                                            <option value="staff">Solo Staff</option>
                                            <option value="master">Solo Master</option>
                                            <option value="png">Solo PNG</option>
                                            <option value="pg">Solo PG Giocanti</option>
                                        </select>
                                    </div>
                                )}

                                {targetType === 'single' && (
                                    <div className="bg-gray-800 p-3 rounded-lg border border-gray-700 relative">
                                        <label className="block text-xs font-bold text-gray-400 mb-1 uppercase">Cerca Personaggio</label>
                                        <div className="flex gap-2">
                                            <div className="relative w-full">
                                                <input 
                                                    type="text" 
                                                    placeholder="Inizia a scrivere il nome..."
                                                    value={singleRecipient ? singleRecipient.nome : searchQuery}
                                                    onChange={(e) => setSearchQuery(e.target.value)}
                                                    className="w-full bg-gray-900 border border-gray-600 text-white rounded p-2 pl-9 focus:ring-2 focus:ring-indigo-500 outline-none text-sm disabled:opacity-50"
                                                    disabled={!!singleRecipient}
                                                />
                                                <Search size={16} className="absolute left-3 top-2.5 text-gray-500"/>
                                            </div>
                                            {singleRecipient && (
                                                <button 
                                                    type="button"
                                                    onClick={() => { setSingleRecipient(null); setSearchQuery(''); }}
                                                    className="bg-red-900/50 hover:bg-red-900 text-red-200 px-3 rounded border border-red-800 transition-colors"
                                                >
                                                    <X size={16} />
                                                </button>
                                            )}
                                        </div>

                                        {/* Dropdown Risultati */}
                                        {searchResults.length > 0 && !singleRecipient && (
                                            <ul className="absolute z-50 w-full left-0 bg-gray-700 border border-gray-600 mt-1 rounded shadow-xl max-h-40 overflow-y-auto">
                                                {searchResults.map(pg => (
                                                    <li 
                                                        key={pg.id} 
                                                        onClick={() => { setSingleRecipient(pg); setSearchQuery(''); setSearchResults([]); }}
                                                        className="p-2 hover:bg-indigo-600 cursor-pointer text-sm border-b border-gray-600 last:border-0 text-white"
                                                    >
                                                        {pg.nome}
                                                    </li>
                                                ))}
                                            </ul>
                                        )}
                                    </div>
                                )}
                                {targetType === 'evento' && (
                                    <div className="bg-gray-800 p-3 rounded-lg border border-gray-700">
                                        <label className="block text-xs font-bold text-gray-400 mb-1 uppercase">Evento (iscritti)</label>
                                        <select
                                            value={selectedEventoId}
                                            onChange={(e) => setSelectedEventoId(e.target.value)}
                                            className="w-full min-h-11 bg-gray-900 border border-gray-600 text-white rounded p-2 focus:ring-2 focus:ring-indigo-500 outline-none text-sm"
                                        >
                                            <option value="">— Seleziona evento —</option>
                                            {eventi.map((ev) => (
                                                <option key={ev.id} value={ev.id}>
                                                    {ev.in_corso ? '● ' : ''}{ev.titolo}
                                                    {ev.data_inizio ? ` (${new Date(ev.data_inizio).toLocaleDateString()})` : ''}
                                                </option>
                                            ))}
                                        </select>
                                        <p className="text-[11px] text-gray-500 mt-1">
                                            Ogni iscritto riceve una copia individuale in inbox, con notifica.
                                        </p>
                                    </div>
                                )}
                            </div>

                            <div className="bg-gray-800/80 p-3 rounded-lg border border-gray-700 space-y-2">
                                <div className="flex items-center justify-between gap-2">
                                    <span className="text-xs font-bold text-gray-400 uppercase">Modelli</span>
                                    <span className="text-[10px] text-gray-500">Clicca per compilare titolo e testo</span>
                                </div>
                                <div className="flex flex-wrap gap-1.5">
                                    {modelli.length === 0 && (
                                        <span className="text-[11px] text-gray-500">Nessun modello salvato.</span>
                                    )}
                                    {modelli.map((mod) => (
                                        <span key={mod.id} className="inline-flex items-center max-w-full">
                                            <button
                                                type="button"
                                                onClick={() => handleApplyModello(mod)}
                                                className="min-h-11 truncate max-w-[11rem] rounded-l-lg bg-emerald-900/70 hover:bg-emerald-800 px-3 text-xs font-bold text-emerald-100"
                                                title={mod.titolo}
                                            >
                                                {mod.nome}
                                            </button>
                                            <button
                                                type="button"
                                                onClick={() => handleDeleteModello(mod)}
                                                className="min-h-11 rounded-r-lg bg-red-950/80 hover:bg-red-900 px-2 text-red-300"
                                                aria-label={`Elimina modello ${mod.nome}`}
                                            >
                                                <Trash2 size={12} />
                                            </button>
                                        </span>
                                    ))}
                                </div>
                                <div className="flex flex-col sm:flex-row gap-2">
                                    <input
                                        type="text"
                                        value={modelloNome}
                                        onChange={(e) => setModelloNome(e.target.value)}
                                        placeholder="Nome modello (opzionale, usa l'oggetto)"
                                        className="min-h-11 flex-1 bg-gray-900 border border-gray-600 text-white rounded px-2 text-sm"
                                    />
                                    <button
                                        type="button"
                                        onClick={handleSaveModello}
                                        className="min-h-11 inline-flex items-center justify-center gap-1 rounded-lg bg-gray-700 hover:bg-gray-600 px-3 text-xs font-bold text-white"
                                    >
                                        <BookmarkPlus size={14} /> Salva modello
                                    </button>
                                </div>
                            </div>
                            <div>
                                <input
                                    type="text"
                                    placeholder="Oggetto del messaggio"
                                    className="w-full bg-gray-800 border border-gray-700 rounded p-3 text-white focus:ring-2 focus:ring-indigo-500 outline-none font-bold text-sm"
                                    value={title}
                                    onChange={(e) => setTitle(e.target.value)}
                                />
                            </div>

                            {feedback.msg && (
                                <div className={`p-3 rounded text-center text-sm font-bold ${feedback.type === 'error' ? 'bg-red-900/50 text-red-200 border border-red-800' : 'bg-green-900/50 text-green-200 border border-green-800'}`}>
                                    {feedback.msg}
                                </div>
                            )}
                          </div>

                          {/* Area di scrittura: prende tutta l'altezza rimasta nel pannello */}
                          <div className="flex-1 min-h-0 flex flex-col px-4 pb-3">
                                <RichTextEditor
                                    label="Contenuto del messaggio"
                                    value={text}
                                    onChange={setText}
                                    placeholder="Scrivi qui il contenuto del messaggio…"
                                    fillHeight
                                />
                          </div>

                            {/* FOOTER AZIONI sticky */}
                            <div className="flex justify-between items-center gap-3 p-4 border-t border-gray-800 bg-gray-900 shrink-0">
                                <label className="flex items-center gap-2 text-sm text-gray-400 cursor-pointer hover:text-white">
                                    <input 
                                        type="checkbox" 
                                        checked={saveHistory} 
                                        onChange={(e) => setSaveHistory(e.target.checked)}
                                        className="rounded bg-gray-700 border-gray-600 text-indigo-500 focus:ring-indigo-500 w-4 h-4"
                                    />
                                    Salva in cronologia
                                </label>

                                <button
                                    type="submit"
                                    disabled={isSending}
                                    className={`px-6 py-2 rounded font-bold text-white transition-all shadow-lg text-sm uppercase tracking-wide ${isSending ? 'bg-gray-600 cursor-not-allowed' : 'bg-indigo-600 hover:bg-indigo-500 hover:-translate-y-px'}`}
                                >
                                    {isSending ? 'Invio in corso...' : 'Invia Messaggio'}
                                </button>
                            </div>
                        </form>
                    </Tab.Panel>

                    {/* --- PANEL 3: HISTORY (Cronologia) --- */}
                    <Tab.Panel className="h-full overflow-y-auto custom-scrollbar p-3 space-y-3">
                        <div className="flex justify-between items-center mb-2 px-1">
                            <h3 className="text-gray-400 font-bold uppercase text-xs">Messaggi Inviati dallo Staff</h3>
                            <button onClick={loadHistory} className="text-indigo-400 hover:text-white text-xs underline">Aggiorna lista</button>
                        </div>

                        {isLoadingHistory ? (
                            <div className="flex justify-center p-10"><RefreshCw className="animate-spin text-gray-500"/></div>
                        ) : history.length > 0 ? (
                            history.map((msg) => (
                                <div key={msg.id} className="bg-gray-800 border border-gray-700 p-4 rounded-lg shadow-sm hover:border-gray-600 transition-colors">
                                    <div className="flex justify-between items-center mb-2">
                                        <h4 className="font-bold text-indigo-300 text-sm truncate pr-2">{msg.titolo}</h4>
                                        <span className="text-[10px] bg-gray-700 px-2 py-1 rounded text-gray-300 uppercase tracking-wider whitespace-nowrap">
                                            {msg.tipo_target || (msg.destinatario_personaggio ? 'Singolo' : 'Broadcast')}
                                        </span>
                                    </div>
                                    
                                    <div className="text-xs text-gray-400 mb-2 line-clamp-3 bg-gray-900/30 p-2 rounded">
                                        <RichTextDisplay content={msg.testo} />
                                    </div>

                                    <div className="flex justify-between items-center border-t border-gray-700 pt-2 mt-2">
                                        <span className="text-[10px] text-gray-600">ID: {msg.id}</span>
                                        <p className="text-[10px] text-gray-500">
                                            Inviato il: {new Date(msg.data_invio || msg.data_creazione).toLocaleString()}
                                        </p>
                                    </div>
                                </div>
                            ))
                        ) : (
                            <div className="text-center text-gray-500 py-10 border border-gray-800 rounded-lg bg-gray-800/30">
                                Nessun messaggio trovato nella cronologia.
                            </div>
                        )}
                    </Tab.Panel>

                </Tab.Panels>
            </Tab.Group>
        </div>
    );
};

export default AdminMessageTab;