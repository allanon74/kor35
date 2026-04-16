import React, { useState, useEffect, useCallback, memo } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { 
    createPersonaggio, 
    updatePersonaggio, 
    getTipologiePersonaggio,
    getEre,
    staffAddResources,
    getPersonaggioDetail,
    staffIncrementaRisorsaPool,
    resetPersonaggio,
    staffKillPersonaggio,
    staffRevivePersonaggio,
    resolveMediaUrl,
} from '../api';
import { useCharacter } from './CharacterContext';
import { 
    User, Users, Plus, Edit, X, ShieldAlert, Coins, Zap, Gem, RotateCcw, Skull, Heart
} from 'lucide-react';
import RichTextEditor from './RichTextEditor';
import BuildVersions from './BuildVersions';

const PersonaggiTab = ({ onLogout, onSelectChar }) => {
    const navigate = useNavigate();
    // Rimosso setPersonaggiList dal destructuring perché non esposto dal context
    const { 
        personaggiList, 
        fetchPersonaggi, 
        refreshCharacterData, 
        isCampaignMaster,
        isAdmin, 
        viewAll, 
        toggleViewAll, 
        selectCharacter,
        selectedCharacterId,
        campaigns,
    } = useCharacter();

    const queryClient = useQueryClient();

    // Stati Modale Edit/Create
    const [showModal, setShowModal] = useState(false);
    const [editMode, setEditMode] = useState(false);
    const [formData, setFormData] = useState({});
    const [tipologie, setTipologie] = useState([]);
    const [ere, setEre] = useState([]);
    
    // Stati Modale Staff Risorse
    const [showResourceModal, setShowResourceModal] = useState(false);
    const [resourceModalTab, setResourceModalTab] = useState('valute');
    const [poolDetailLoading, setPoolDetailLoading] = useState(false);
    const [poolDetail, setPoolDetail] = useState(null);
    /** { [sigla]: { delta: string, motivo: string } } */
    const [poolInputs, setPoolInputs] = useState({});
    const [resourceData, setResourceData] = useState({
        charId: null,
        charName: '',
        creditiSnapshot: null,
        pcSnapshot: null,
        tipo: 'crediti',
        amount: 0,
        reason: 'Intervento staff',
    });

    /** Conferme azioni staff in modale React (window.confirm è soppresso in alcuni browser di test / automazione). */
    const [staffConfirm, setStaffConfirm] = useState(null);
    const [staffFeedback, setStaffFeedback] = useState(null);

    useEffect(() => {
        // Carica tipologie, gestendo eventuali errori silenziosamente
        getTipologiePersonaggio(onLogout).then(data => {
            if (Array.isArray(data)) setTipologie(data);
        });
        getEre(onLogout).then(data => {
            if (Array.isArray(data)) setEre(data);
        });
        fetchPersonaggi();
    }, []);

    useEffect(() => {
        if (!staffFeedback) return undefined;
        const id = setTimeout(() => setStaffFeedback(null), 7000);
        return () => clearTimeout(id);
    }, [staffFeedback]);

    const handleStaffConfirmExecute = async () => {
        if (!staffConfirm) return;
        const { kind, char } = staffConfirm;
        setStaffConfirm(null);
        try {
            if (kind === 'reset') {
                await resetPersonaggio(char.id, 'Reset manuale da interfaccia staff', onLogout);
                await fetchPersonaggi();
                if (String(char.id) === String(selectedCharacterId)) {
                    refreshCharacterData();
                }
                setStaffFeedback({ type: 'success', message: 'Reset personaggio completato.' });
            } else if (kind === 'kill') {
                await staffKillPersonaggio(char.id, onLogout);
                await fetchPersonaggi();
                if (String(char.id) === String(selectedCharacterId)) {
                    refreshCharacterData();
                }
                setStaffFeedback({ type: 'success', message: 'Personaggio segnato come morto.' });
            } else if (kind === 'revive') {
                await staffRevivePersonaggio(char.id, onLogout);
                await fetchPersonaggi();
                if (String(char.id) === String(selectedCharacterId)) {
                    refreshCharacterData();
                }
                setStaffFeedback({ type: 'success', message: 'Personaggio rivissuto.' });
            }
        } catch (error) {
            setStaffFeedback({
                type: 'error',
                message: error?.message || String(error),
            });
        }
    };

    // --- GESTIONE MODALE CREATE/EDIT ---

    const handleOpenEdit = (char, e) => {
        e.stopPropagation(); 
        setEditMode(true);
        
        // Logica robusta per estrarre l'ID della tipologia
        let tipoId = 1;
        if (char.tipologia) {
            if (typeof char.tipologia === 'number') {
                tipoId = char.tipologia;
            } else if (typeof char.tipologia === 'object' && char.tipologia.id) {
                tipoId = char.tipologia.id;
            } else if (typeof char.tipologia === 'string') {
                // Tenta di trovare l'ID dal nome o parse
                const found = tipologie.find(t => t.nome === char.tipologia);
                tipoId = found ? found.id : (parseInt(char.tipologia) || 1);
            }
        }

        setFormData({
            id: char.id,
            nome: char.nome,
            tipologia: tipoId,
            testo: char.testo || '',
            costume: char.costume || '',
            campagna: char.campagna || '',
            era: typeof char.era === 'object' ? (char.era?.id || '') : (char.era || ''),
            prefettura: typeof char.prefettura === 'object' ? (char.prefettura?.id || '') : (char.prefettura || ''),
            prefettura_esterna: !!char.prefettura_esterna,
        });
        setShowModal(true);
    };

    const handleSaveOptimistic = async () => {
        const payload = { ...formData };
        if (payload.era === '') payload.era = null;
        if (payload.prefettura === '') payload.prefettura = null;
        payload.prefettura_esterna = !!payload.prefettura_esterna;
        
        // Pulizia e validazione ID Tipologia per il backend
        if (payload.tipologia !== undefined) {
            const parsed = parseInt(payload.tipologia, 10);
            if (!isNaN(parsed)) {
                payload.tipologia = parsed;
            } else {
                delete payload.tipologia; // Evita errore 400 se invalido
            }
        }

        if (
            payload.prefettura &&
            payload.era &&
            !payload.prefettura_esterna &&
            !ere.some((era) => {
                if (String(era.id) !== String(payload.era)) return false;
                return (era.prefetture || []).some((p) => String(p.id) === String(payload.prefettura));
            })
        ) {
            payload.prefettura = null;
        }

        const queryKey = ['personaggi_list', viewAll];
        const previousData = queryClient.getQueryData(queryKey);

        // Update Ottimistico
        queryClient.setQueryData(queryKey, (oldList = []) => {
            // Assicuriamoci che oldList sia un array (fix per il bug della paginazione)
            const list = Array.isArray(oldList) ? oldList : []; 
            
            if (editMode) {
                return list.map(p => p.id === payload.id ? { ...p, ...payload } : p);
            } else {
                const tempId = 'temp-' + Date.now();
                return [...list, { 
                    ...payload, 
                    id: tempId, 
                    rango_label: '...', 
                    crediti: 0,
                    punti_caratteristica: 0,
                    tipologia: tipologie.find(t => t.id === payload.tipologia)?.nome || payload.tipologia 
                }];
            }
        });

        setShowModal(false);

        try {
            if (editMode) {
                await updatePersonaggio(payload.id, payload, onLogout);
                // Aggiorna dettagli se è il PG selezionato
                if (String(payload.id) === String(selectedCharacterId)) {
                    refreshCharacterData();
                }
            } else {
                await createPersonaggio(payload, onLogout);
            }
            // Sincronizzazione reale
            await fetchPersonaggi();

        } catch (error) {
            console.error("Errore salvataggio:", error);
            alert("Errore salvataggio: " + error.message);
            // Rollback
            if (previousData) queryClient.setQueryData(queryKey, previousData);
        }
    };

    // --- GESTIONE RISORSE STAFF ---

    const handleOpenResourceModal = (char, e) => {
        e.stopPropagation();
        setResourceModalTab('valute');
        setPoolDetail(null);
        setResourceData({
            charId: char.id,
            charName: char.nome,
            creditiSnapshot: char.crediti,
            pcSnapshot: char.punti_caratteristica,
            tipo: 'crediti',
            amount: 0,
            reason: 'Intervento staff',
        });
        setShowResourceModal(true);
    };

    const handleCloseResourceModal = () => {
        setShowResourceModal(false);
        setPoolDetail(null);
        setResourceModalTab('valute');
        setPoolInputs({});
    };

    const updatePoolInput = useCallback((sigla, field, value) => {
        setPoolInputs((prev) => ({
            ...prev,
            [sigla]: { ...(prev[sigla] || { delta: '', motivo: '' }), [field]: value },
        }));
    }, []);

    const handleGiveResources = async () => {
        try {
            const amt = parseInt(resourceData.amount, 10);
            if (Number.isNaN(amt) || amt === 0) {
                alert('Inserisci una quantità diversa da zero (positiva o negativa).');
                return;
            }
            const resp = await staffAddResources(
                resourceData.charId,
                resourceData.tipo,
                amt,
                resourceData.reason,
                onLogout
            );
            alert(
                resp.msg ||
                    `Aggiornato. Nuovo valore: ${resourceData.tipo === 'crediti' ? 'CR' : 'PC'} ${resp.new_val ?? ''}`
            );
            handleCloseResourceModal();
            fetchPersonaggi();
            if (String(resourceData.charId) === String(selectedCharacterId)) {
                refreshCharacterData();
            }
        } catch (error) {
            alert('Errore: ' + error.message);
        }
    };

    useEffect(() => {
        if (!showResourceModal || resourceModalTab !== 'risorse' || !resourceData.charId) {
            return undefined;
        }
        let cancelled = false;
        (async () => {
            setPoolDetailLoading(true);
            try {
                const d = await getPersonaggioDetail(resourceData.charId, onLogout);
                if (!cancelled) setPoolDetail(d);
            } catch (err) {
                if (!cancelled) {
                    setPoolDetail(null);
                    alert('Impossibile caricare le risorse pool: ' + (err.message || err));
                }
            } finally {
                if (!cancelled) setPoolDetailLoading(false);
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [showResourceModal, resourceModalTab, resourceData.charId, onLogout]);

    const handlePoolAdjust = async (sigla, deltaRaw, motivoRiga) => {
        try {
            const delta = parseInt(deltaRaw, 10);
            if (Number.isNaN(delta) || delta === 0) {
                alert('Variazione non valida (usa un intero diverso da zero).');
                return;
            }
            const motivo = (motivoRiga || resourceData.reason || '').trim() || 'Regolazione risorsa pool';
            await staffIncrementaRisorsaPool(resourceData.charId, sigla, motivo, onLogout, delta);
            const d = await getPersonaggioDetail(resourceData.charId, onLogout);
            setPoolDetail(d);
            await fetchPersonaggi();
            if (String(resourceData.charId) === String(selectedCharacterId)) {
                refreshCharacterData();
            }
            alert('Risorsa pool aggiornata.');
        } catch (error) {
            alert('Errore: ' + error.message);
        }
    };

    const handleSelect = (char) => {
        const charId = char?.id;
        if (String(charId).startsWith('temp-')) return;
        if (char?.data_morte && !(isCampaignMaster || isAdmin)) {
            alert('Questo personaggio e morto e non e utilizzabile. Contatta lo staff.');
            return;
        }
        selectCharacter(charId);
        if (onSelectChar) onSelectChar();
    };

    const selectedEra = ere.find((e) => String(e.id) === String(formData.era));
    const allPrefetture = ere.flatMap((era) => (era.prefetture || []).map((p) => ({ ...p, era_ref: era })));
    const prefettureDisponibili = formData.prefettura_esterna ? allPrefetture : (selectedEra?.prefetture || []);
    const selectedPrefettura = allPrefetture.find((p) => String(p.id) === String(formData.prefettura));
    const formatPrefetturaLabel = (pref) => {
        const prefEraId = pref.era ?? pref.era_ref?.id;
        const prefRegSigla = pref.regione_sigla || '';
        const baseName = prefRegSigla ? `${prefRegSigla} ${pref.nome}` : pref.nome;
        const isExternal = selectedEra && String(prefEraId) !== String(selectedEra.id);
        if (!isExternal) return baseName;
        const miaEraBreve = selectedEra?.abbreviazione || selectedEra?.nome || '';
        return miaEraBreve ? `${baseName} (${miaEraBreve})` : baseName;
    };

    return (
        <div className="h-full flex flex-col bg-gray-900 text-white p-4 overflow-hidden">
            <div className="flex justify-between items-center mb-6 shrink-0">
                <div className="min-w-0">
                    <h2 className="text-2xl font-black uppercase italic tracking-wider text-indigo-500">
                        Seleziona Personaggio
                    </h2>
                    <BuildVersions className="mt-1" />
                </div>
                
                <div className="flex gap-2">
                    <button
                        onClick={() => navigate('/app/social')}
                        className="flex items-center gap-2 px-4 py-2 bg-fuchsia-700 rounded-lg font-bold uppercase text-xs tracking-widest hover:bg-fuchsia-600 transition-colors shadow-lg"
                        title="Apri InstaFame"
                    >
                        ✨ InstaFame
                    </button>
                    {(isAdmin || isCampaignMaster) && (
                        <button 
                            onClick={toggleViewAll} 
                            className={`p-2 rounded-lg border ${viewAll ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-transparent border-gray-600 text-gray-400'}`}
                            title="Filtro Staff"
                        >
                            {viewAll ? <Users size={20}/> : <User size={20}/>}
                        </button>
                    )}
                    
                    <button
                        onClick={() => navigate('/app/start')}
                        className="flex items-center gap-2 px-4 py-2 bg-indigo-700 rounded-lg font-bold uppercase text-xs tracking-widest hover:bg-indigo-600 transition-colors shadow-lg"
                    >
                        <Plus size={16}/> Nuovo PG
                    </button>
                </div>
            </div>

            {staffFeedback && (
                <div
                    className={`mb-4 flex shrink-0 items-start justify-between gap-3 rounded-lg border px-4 py-3 text-sm ${
                        staffFeedback.type === 'success'
                            ? 'border-emerald-600 bg-emerald-950/80 text-emerald-100'
                            : 'border-red-600 bg-red-950/80 text-red-100'
                    }`}
                    role="status"
                >
                    <span className="min-w-0 pt-0.5">{staffFeedback.message}</span>
                    <button
                        type="button"
                        onClick={() => setStaffFeedback(null)}
                        className="shrink-0 rounded p-1 text-current opacity-80 hover:opacity-100"
                        aria-label="Chiudi messaggio"
                    >
                        <X size={18} />
                    </button>
                </div>
            )}

            <div className="flex-1 overflow-y-auto space-y-4 pb-20 custom-scrollbar">
                {/* Controllo di sicurezza: mappa solo se è un array */}
                {Array.isArray(personaggiList) && personaggiList.map(char => {
                    const isSelected = selectedCharacterId === String(char.id);
                    const staffToolbar = (isCampaignMaster || isAdmin);
                    /* Grid + overflow-hidden a sinistra: evita che testo lungo copra la toolbar (hit-testing / paint sopra i pulsanti). */
                    const rowBase = `relative isolate group grid grid-cols-[minmax(0,1fr)_auto] gap-3 items-center p-4 rounded-xl border transition-all duration-200 hover:shadow-md active:opacity-95 ${
                        isSelected
                            ? 'bg-indigo-900/30 border-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.3)] ring-2 ring-indigo-500/20'
                            : 'bg-gray-800 border-gray-700 hover:border-gray-500 hover:bg-gray-750'
                    }`;

                    return (
                    <div key={char.id} className={rowBase}>
                        <div
                            role="button"
                            tabIndex={0}
                            onClick={() => handleSelect(char)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' || e.key === ' ') {
                                    e.preventDefault();
                                    handleSelect(char);
                                }
                            }}
                            className="flex min-h-[3rem] min-w-0 cursor-pointer items-center gap-4 overflow-hidden rounded-lg outline-none focus-visible:ring-2 focus-visible:ring-indigo-500/60"
                        >
                            <div className={`flex h-12 w-12 shrink-0 items-center justify-center rounded-full text-xl font-bold uppercase transition-all overflow-hidden ${isSelected ? 'scale-110 bg-indigo-600 text-white shadow-lg shadow-indigo-500/30' : 'bg-gray-700 text-gray-300 group-hover:bg-gray-600'}`}>
                                {char.avatar_url ? (
                                    <img src={resolveMediaUrl(char.avatar_url)} alt="" className="h-full w-full object-cover" />
                                ) : (
                                    char.nome ? char.nome.charAt(0) : '?'
                                )}
                            </div>

                            <div className="min-w-0">
                                <h3 className="truncate text-lg font-bold leading-none">
                                    {char.nome}
                                    {char.data_morte ? (
                                        <span className="ml-2 rounded-full border border-red-700 bg-red-900/70 px-2 py-0.5 text-[10px] uppercase tracking-wide text-red-200">
                                            Morto
                                        </span>
                                    ) : null}
                                </h3>
                                {(char.era_nome || char.prefettura_nome) && (
                                    <div className="mt-1 text-[11px] text-indigo-300">
                                        {char.era_nome || 'Era non selezionata'}
                                        {char.prefettura_nome ? ` - ${
                                            (char.prefettura_era_nome && char.era_nome && String(char.prefettura_era_nome) !== String(char.era_nome))
                                                ? `${char.prefettura_nome} (${char.prefettura_regione_sigla ? `${char.prefettura_regione_sigla} - ` : ''}${char.prefettura_era_nome})`
                                                : char.prefettura_nome
                                        }` : ''}
                                    </div>
                                )}
                                {isCampaignMaster && (
                                    <div className="mt-1 font-mono text-[10px] text-gray-400">
                                        CR: {char.crediti} | PC: {char.punti_caratteristica}
                                    </div>
                                )}
                            </div>
                        </div>

                        {staffToolbar && (
                        <div className="relative z-20 flex shrink-0 flex-wrap touch-manipulation items-center justify-end gap-2">
                            <button
                                type="button"
                                onClick={(e) => handleOpenResourceModal(char, e)}
                                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-amber-700 bg-amber-900/50 text-amber-400 transition-colors hover:bg-amber-800"
                                title="Gestione risorse"
                            >
                                <Coins size={18} aria-hidden />
                            </button>
                            <button
                                type="button"
                                onClick={(e) => handleOpenEdit(char, e)}
                                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-gray-900 text-gray-400 transition-colors hover:bg-indigo-600 hover:text-white"
                                title="Modifica personaggio"
                            >
                                <Edit size={18} aria-hidden />
                            </button>
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    setStaffConfirm({ kind: 'reset', char });
                                }}
                                className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-red-800 bg-red-950/60 text-red-300 transition-colors hover:bg-red-800 hover:text-white"
                                title="Reset personaggio"
                            >
                                <RotateCcw size={18} aria-hidden />
                            </button>
                            {char.data_morte ? (
                                <button
                                    type="button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setStaffConfirm({ kind: 'revive', char });
                                    }}
                                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-emerald-700 bg-emerald-900/50 text-emerald-300 transition-colors hover:bg-emerald-700 hover:text-white"
                                    title="Rivivi personaggio"
                                >
                                    <Heart size={18} aria-hidden />
                                </button>
                            ) : (
                                <button
                                    type="button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setStaffConfirm({ kind: 'kill', char });
                                    }}
                                    className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg border border-red-800 bg-red-950/60 text-red-300 transition-colors hover:bg-red-800 hover:text-white"
                                    title="Uccidi personaggio"
                                >
                                    <Skull size={18} aria-hidden />
                                </button>
                            )}
                        </div>
                        )}
                    </div>
                    );
                })}
            </div>

            {/* Conferma azioni staff (reset / morte / rivivere) */}
            {staffConfirm && (
                <div
                    className="fixed inset-0 z-[60] flex items-center justify-center bg-black/75 p-4 backdrop-blur-sm"
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="staff-confirm-title"
                    onClick={(e) => {
                        if (e.target === e.currentTarget) setStaffConfirm(null);
                    }}
                >
                    <div className="w-full max-w-md rounded-2xl border border-gray-600 bg-gray-800 p-6 shadow-2xl">
                        <h3 id="staff-confirm-title" className="text-lg font-bold text-white">
                            {staffConfirm.kind === 'reset' && 'Reset personaggio'}
                            {staffConfirm.kind === 'kill' && 'Segnare come morto'}
                            {staffConfirm.kind === 'revive' && 'Rivivere personaggio'}
                        </h3>
                        <p className="mt-3 text-sm leading-relaxed text-gray-300">
                            {staffConfirm.kind === 'reset' && (
                                <>
                                    Confermi il reset completo di <strong className="text-white">«{staffConfirm.char.nome}»</strong>?
                                    Verranno rimosse abilità, infusioni, tessiture e cerimoniali, con rimborso costi.
                                </>
                            )}
                            {staffConfirm.kind === 'kill' && (
                                <>
                                    Segnare <strong className="text-white">«{staffConfirm.char.nome}»</strong> come morto?
                                </>
                            )}
                            {staffConfirm.kind === 'revive' && (
                                <>
                                    Rivivere il personaggio <strong className="text-white">«{staffConfirm.char.nome}»</strong>?
                                </>
                            )}
                        </p>
                        <div className="mt-6 flex flex-wrap justify-end gap-2">
                            <button
                                type="button"
                                onClick={() => setStaffConfirm(null)}
                                className="rounded-lg border border-gray-600 bg-gray-700 px-4 py-2.5 text-sm font-bold text-gray-200 hover:bg-gray-600"
                            >
                                Annulla
                            </button>
                            <button
                                type="button"
                                onClick={() => void handleStaffConfirmExecute()}
                                className={`rounded-lg px-4 py-2.5 text-sm font-bold text-white ${
                                    staffConfirm.kind === 'revive'
                                        ? 'bg-emerald-600 hover:bg-emerald-500'
                                        : 'bg-red-600 hover:bg-red-500'
                                }`}
                            >
                                Conferma
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODALE CREATE/EDIT */}
            {showModal && (
                <div className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-gray-800 w-full max-w-3xl rounded-2xl border border-gray-700 shadow-2xl flex flex-col max-h-[95vh]">
                        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
                            <h3 className="font-black text-xl italic uppercase text-indigo-400">
                                {editMode ? 'Modifica Personaggio' : 'Nuovo Personaggio'}
                            </h3>
                            <button onClick={() => setShowModal(false)}><X className="text-gray-400 hover:text-white"/></button>
                        </div>
                        <div className="p-6 overflow-y-auto space-y-4">
                            <input 
                                className="w-full bg-gray-900 border border-gray-700 rounded p-3 text-xl font-bold text-white placeholder-gray-600"
                                value={formData.nome}
                                onChange={e => setFormData({...formData, nome: e.target.value})}
                                placeholder="Nome Personaggio"
                            />
                            
                            <RichTextEditor 
                                label="Background" 
                                value={formData.testo} 
                                onChange={val => setFormData({...formData, testo: val})}
                            />

                            <div className="p-4 bg-gray-900/50 rounded-xl border border-gray-700 space-y-3">
                                <label className="block text-xs text-gray-400 uppercase tracking-widest">Era di provenienza</label>
                                <select
                                    className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-white"
                                    value={formData.era ?? ''}
                                    onChange={e => setFormData({...formData, era: e.target.value || '', prefettura: ''})}
                                >
                                    <option value="">Seleziona un'era</option>
                                    {ere.map(era => <option key={era.id} value={era.id}>{era.nome}</option>)}
                                </select>
                                {selectedEra?.descrizione_breve && (
                                    <p className="text-xs text-gray-300">{selectedEra.descrizione_breve}</p>
                                )}
                                {selectedEra?.descrizione && (
                                    <p className="text-xs text-gray-400">{selectedEra.descrizione}</p>
                                )}
                                <label className="flex items-center gap-2 text-xs text-gray-300">
                                    <input
                                        type="checkbox"
                                        checked={!!formData.prefettura_esterna}
                                        onChange={(e) => setFormData({ ...formData, prefettura_esterna: e.target.checked, prefettura: '' })}
                                    />
                                    Provengo da una prefettura esterna alle usuali per questa Era
                                </label>
                                {prefettureDisponibili.length > 0 && (
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">Prefettura di origine</label>
                                        <select
                                            className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-white"
                                            value={formData.prefettura ?? ''}
                                            onChange={e => setFormData({...formData, prefettura: e.target.value || ''})}
                                        >
                                            <option value="">Seleziona prefettura</option>
                                            {prefettureDisponibili.map(pref => (
                                                <option key={pref.id} value={pref.id}>{formatPrefetturaLabel(pref)}</option>
                                            ))}
                                        </select>
                                        {formData.prefettura && (
                                            <p className="text-xs text-gray-400 mt-1">
                                                {selectedPrefettura?.descrizione || ''}
                                            </p>
                                        )}
                                    </div>
                                )}
                            </div>

                            {(isCampaignMaster || isAdmin) && (
                                <div className="p-4 bg-gray-900/50 rounded-xl border border-gray-700 space-y-4 mt-4">
                                    <div className="flex items-center gap-2 text-amber-500 font-bold text-xs uppercase tracking-widest">
                                        <ShieldAlert size={14}/> Area Staff
                                    </div>
                                    <div>
                                        <label className="block text-xs text-gray-500 mb-1">Tipologia</label>
                                        <select 
                                            className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-white"
                                            value={formData.tipologia}
                                            onChange={e => setFormData({...formData, tipologia: parseInt(e.target.value)})}
                                        >
                                            {tipologie.map(t => <option key={t.id} value={t.id}>{t.nome}</option>)}
                                        </select>
                                    </div>
                                    <RichTextEditor 
                                        label="Note Costume" 
                                        value={formData.costume} 
                                        onChange={val => setFormData({...formData, costume: val})}
                                    />
                                    {(isCampaignMaster || isAdmin) && editMode && (
                                        <div>
                                            <label className="block text-xs text-gray-500 mb-1">Campagna personaggio</label>
                                            <select
                                                className="w-full bg-gray-800 border border-gray-600 rounded p-2 text-white"
                                                value={formData.campagna || ''}
                                                onChange={e => setFormData({ ...formData, campagna: e.target.value || '' })}
                                            >
                                                <option value="">Seleziona campagna</option>
                                                {(campaigns || [])
                                                    .filter(c => c.ruolo === 'MASTER' || isAdmin)
                                                    .map(c => <option key={c.id || c.slug} value={c.id}>{c.nome}</option>)}
                                            </select>
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                        <div className="p-4 border-t border-gray-700">
                            <button 
                                onClick={handleSaveOptimistic}
                                className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-bold uppercase transition-colors"
                            >
                                Salva
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* MODALE STAFF RISORSE */}
            {showResourceModal && (
                <div className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center p-4">
                    <div className="bg-gray-800 w-full max-w-lg rounded-2xl border border-amber-600 shadow-2xl flex flex-col max-h-[90vh]">
                        <div className="p-5 border-b border-gray-700 shrink-0">
                            <h3 className="text-amber-500 font-bold text-lg uppercase flex items-center gap-2">
                                <ShieldAlert size={20} /> Gestione risorse: {resourceData.charName}
                            </h3>
                            <p className="text-[11px] text-gray-500 mt-1">
                                Solo utenti con permessi adeguati. Le modifiche restano tracciate su movimenti e log.
                            </p>
                            <div className="flex gap-2 mt-4">
                                <button
                                    type="button"
                                    onClick={() => setResourceModalTab('valute')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm font-bold transition-all ${
                                        resourceModalTab === 'valute'
                                            ? 'bg-amber-600 border-amber-500 text-white'
                                            : 'border-gray-600 text-gray-400 hover:bg-gray-750'
                                    }`}
                                >
                                    <Coins size={18} /> Crediti / PC
                                </button>
                                <button
                                    type="button"
                                    onClick={() => setResourceModalTab('risorse')}
                                    className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg border text-sm font-bold transition-all ${
                                        resourceModalTab === 'risorse'
                                            ? 'bg-violet-600 border-violet-500 text-white'
                                            : 'border-gray-600 text-gray-400 hover:bg-gray-750'
                                    }`}
                                >
                                    <Gem size={18} /> Risorse pool
                                </button>
                            </div>
                        </div>

                        <div className="p-5 overflow-y-auto flex-1 min-h-0 space-y-4">
                            {resourceModalTab === 'valute' && (
                                <>
                                    <div className="grid grid-cols-2 gap-2 text-center text-xs font-mono text-gray-400">
                                        <div className="bg-gray-900/80 rounded-lg py-2 border border-gray-700">
                                            CR attuali:{' '}
                                            <span className="text-amber-300">{resourceData.creditiSnapshot ?? '—'}</span>
                                        </div>
                                        <div className="bg-gray-900/80 rounded-lg py-2 border border-gray-700">
                                            PC attuali:{' '}
                                            <span className="text-cyan-300">{resourceData.pcSnapshot ?? '—'}</span>
                                        </div>
                                    </div>
                                    <p className="text-xs text-gray-500">
                                        Quantità <strong className="text-gray-300">positiva</strong> aggiunge,{' '}
                                        <strong className="text-gray-300">negativa</strong> sottrae (crediti e punti
                                        caratteristica seguono le regole di fondo scala già usate dal backend).
                                    </p>
                                    <div className="grid grid-cols-2 gap-2">
                                        <button
                                            type="button"
                                            onClick={() =>
                                                setResourceData({ ...resourceData, tipo: 'crediti' })
                                            }
                                            className={`p-3 rounded-lg border font-bold transition-all ${
                                                resourceData.tipo === 'crediti'
                                                    ? 'bg-amber-600 border-amber-500 text-white'
                                                    : 'border-gray-600 text-gray-400 hover:bg-gray-700'
                                            }`}
                                        >
                                            <div className="flex flex-col items-center justify-center gap-1">
                                                <Coins size={20} /> Crediti (CR)
                                            </div>
                                        </button>
                                        <button
                                            type="button"
                                            onClick={() => setResourceData({ ...resourceData, tipo: 'pc' })}
                                            className={`p-3 rounded-lg border font-bold transition-all ${
                                                resourceData.tipo === 'pc'
                                                    ? 'bg-cyan-600 border-cyan-500 text-white'
                                                    : 'border-gray-600 text-gray-400 hover:bg-gray-700'
                                            }`}
                                        >
                                            <div className="flex flex-col items-center justify-center gap-1">
                                                <Zap size={20} /> Punti caratteristica
                                            </div>
                                        </button>
                                    </div>
                                    <div>
                                        <label className="block text-xs uppercase text-gray-500 mb-1">
                                            Variazione (+ / −)
                                        </label>
                                        <input
                                            type="number"
                                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white font-mono text-lg text-center"
                                            value={resourceData.amount}
                                            onChange={(e) =>
                                                setResourceData({ ...resourceData, amount: e.target.value })
                                            }
                                        />
                                    </div>
                                    <div>
                                        <label className="block text-xs uppercase text-gray-500 mb-1">
                                            Motivazione (compare nei movimenti / log)
                                        </label>
                                        <input
                                            type="text"
                                            className="w-full bg-gray-900 border border-gray-700 rounded p-2 text-white"
                                            placeholder="Es. Ricompensa quest, Correzione referto, …"
                                            value={resourceData.reason}
                                            onChange={(e) =>
                                                setResourceData({ ...resourceData, reason: e.target.value })
                                            }
                                        />
                                    </div>
                                </>
                            )}

                            {resourceModalTab === 'risorse' && (
                                <>
                                    <p className="text-xs text-gray-500">
                                        Statistiche contrassegnate come <strong className="text-gray-300">risorsa a pool</strong>{' '}
                                        (es. Fortuna). Variazione positiva = più punti disponibili nel pool; negativa = meno,
                                        senza scendere sotto 0 o superare il massimo di scheda.
                                    </p>
                                    {poolDetailLoading && (
                                        <p className="text-sm text-gray-400 animate-pulse">Caricamento dati personaggio…</p>
                                    )}
                                    {!poolDetailLoading &&
                                        poolDetail &&
                                        (!poolDetail.risorse_pool_ui || poolDetail.risorse_pool_ui.length === 0) && (
                                            <p className="text-sm text-amber-200/80 bg-amber-950/30 border border-amber-900/50 rounded-lg p-3">
                                                Nessuna risorsa pool con massimo &gt; 0 per questo personaggio. Configura le
                                                statistiche nel backend o aumenta il massimo in scheda.
                                            </p>
                                        )}
                                    {!poolDetailLoading &&
                                        poolDetail?.risorse_pool_ui?.map((pool) => {
                                            const row = poolInputs[pool.sigla] || { delta: '', motivo: '' };
                                            return (
                                                <div
                                                    key={pool.sigla}
                                                    className="bg-gray-900/60 border border-gray-700 rounded-xl p-4 space-y-2"
                                                >
                                                    <div className="flex justify-between items-baseline gap-2">
                                                        <span className="font-bold text-white">{pool.nome}</span>
                                                        <span className="text-xs font-mono text-gray-500">{pool.sigla}</span>
                                                    </div>
                                                    <div className="text-sm font-mono text-violet-200">
                                                        Attuale: {pool.valore_corrente}{' '}
                                                        <span className="text-gray-500 text-xs">/ max {pool.valore_max}</span>
                                                    </div>
                                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                                                        <div>
                                                            <label className="block text-[10px] uppercase text-gray-500 mb-0.5">
                                                                Variazione pt.
                                                            </label>
                                                            <input
                                                                type="number"
                                                                className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white font-mono"
                                                                value={row.delta}
                                                                onChange={(e) =>
                                                                    updatePoolInput(pool.sigla, 'delta', e.target.value)
                                                                }
                                                                placeholder="es. 1 o -1"
                                                            />
                                                        </div>
                                                        <div>
                                                            <label className="block text-[10px] uppercase text-gray-500 mb-0.5">
                                                                Motivo (opz.)
                                                            </label>
                                                            <input
                                                                type="text"
                                                                className="w-full bg-gray-950 border border-gray-700 rounded p-2 text-white text-sm"
                                                                value={row.motivo}
                                                                onChange={(e) =>
                                                                    updatePoolInput(pool.sigla, 'motivo', e.target.value)
                                                                }
                                                                placeholder="Lascia vuoto per usare quello globale"
                                                            />
                                                        </div>
                                                    </div>
                                                    <button
                                                        type="button"
                                                        onClick={() =>
                                                            handlePoolAdjust(
                                                                pool.sigla,
                                                                row.delta,
                                                                row.motivo || resourceData.reason
                                                            )
                                                        }
                                                        className="w-full py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-sm font-bold"
                                                    >
                                                        Applica per {pool.nome}
                                                    </button>
                                                </div>
                                            );
                                        })}
                                </>
                            )}
                        </div>

                        <div className="p-4 border-t border-gray-700 flex gap-2 shrink-0 bg-gray-900/40">
                            <button
                                type="button"
                                onClick={handleCloseResourceModal}
                                className="flex-1 py-2.5 bg-gray-700 rounded-lg hover:bg-gray-600 font-bold text-sm"
                            >
                                Chiudi
                            </button>
                            {resourceModalTab === 'valute' && (
                                <button
                                    type="button"
                                    onClick={handleGiveResources}
                                    className="flex-1 py-2.5 bg-emerald-600 rounded-lg font-bold hover:bg-emerald-500 text-sm"
                                >
                                    Conferma CR / PC
                                </button>
                            )}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default memo(PersonaggiTab);