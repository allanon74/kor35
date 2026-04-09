import React, { useState, useEffect, useMemo } from 'react';
import { Loader2, Save, Send, Trash2, AlertTriangle, Plus, Minus, Info, Box, Activity, Settings, Zap, Users, Scroll } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { 
    createProposta, 
    updateProposta, 
    sendProposta, 
    deleteProposta, 
    getAllPunteggi, 
    getMattoniAura, 
    getClassiOggetto 
} from '../api';
import IconaPunteggio from './IconaPunteggio';

// Costanti Slot Corporei (Invariate)
const BODY_SLOTS = [
    { id: 'HD1', label: 'Testa (Cervello/Sensi)' },
    { id: 'HD2', label: 'Testa (Volto/Esterno)' },
    { id: 'TR1', label: 'Tronco (Organi Vitali)' },
    { id: 'TR2', label: 'Tronco (Struttura/Pelle)' },
    { id: 'RA', label: 'Braccio Destro' },
    { id: 'LA', label: 'Braccio Sinistro' },
    { id: 'RL', label: 'Gamba Destra' },
    { id: 'LL', label: 'Gamba Sinistra' },
];

// Mappa Tipi Oggetto per UI
const ITEM_TYPES = {
    'MOD': { label: 'Mod (Tecnologico)', icon: Settings, isBound: false },
    'MAT': { label: 'Materia (Soprannaturale)', icon: Zap, isBound: false },
    'INNESTO': { label: 'Innesto (Chirurgico)', icon: Activity, isBound: true },
    'MUTAZIONE': { label: 'Mutazione (Biologico)', icon: Activity, isBound: true }
};

const ProposalEditorModal = ({ proposal, type, onClose, onRefresh }) => {
    const { selectedCharacterData: char, selectedCharacterId } = useCharacter();
    
    // --- STATI DATI PROPOSTA ---
    const [name, setName] = useState(proposal?.nome || '');
    const [description, setDescription] = useState(proposal?.descrizione || '');
    
    // Campi specifici Cerimoniale
    const [prerequisiti, setPrerequisiti] = useState(proposal?.prerequisiti || '');
    const [svolgimento, setSvolgimento] = useState(proposal?.svolgimento || '');
    const [effetto, setEffetto] = useState(proposal?.effetto || '');
    const [livelloCerimoniale, setLivelloCerimoniale] = useState(proposal?.livello || 1);

    const [selectedAuraId, setSelectedAuraId] = useState(proposal?.aura || '');
    const [selectedInfusionAuraId, setSelectedInfusionAuraId] = useState(proposal?.aura_infusione || '');
    
    // --- STATI LOGICA TIPO OGGETTO (Infusioni) ---
    const [selectedItemType, setSelectedItemType] = useState('');
    const [availableItemOptions, setAvailableItemOptions] = useState([]); 
    
    // --- STATI FILTRI E CONFIGURAZIONE ---
    const [selectedClasseId, setSelectedClasseId] = useState(''); 
    const [selectedSlots, setSelectedSlots] = useState([]);
    
    // Init componenti (Mattoni)
    const initialComponents = {};
    if (proposal?.componenti) {
        proposal.componenti.forEach(c => {
            const id = c.caratteristica?.id || c.caratteristica_id || c.caratteristica; 
            if(id) initialComponents[id] = c.valore;
        });
    }
    const [componentsMap, setComponentsMap] = useState(initialComponents);

    // Cache Dati
    const [allPunteggiCache, setAllPunteggiCache] = useState([]);
    const [availableAuras, setAvailableAuras] = useState([]);        
    const [availableInfusionAuras, setAvailableInfusionAuras] = useState([]); 
    const [availableCharacteristics, setAvailableCharacteristics] = useState([]);
    const [availableBricks, setAvailableBricks] = useState([]); 
    const [availableClassi, setAvailableClassi] = useState([]);   
    
    const [isLoadingData, setIsLoadingData] = useState(true);
    const [isSaving, setIsSaving] = useState(false);
    const [error, setError] = useState('');

    const isDraft = !proposal || proposal.stato === 'BOZZA';
    const isEditing = !!proposal;
    const isInfusion = type === 'Infusione';
    const isCerimoniale = type === 'Cerimoniale';

    // Determina l'Aura da cui pescare i nomi dei mattoni
    const auraIdForBricks = useMemo(() => {
        if (isInfusion) return selectedInfusionAuraId || selectedAuraId;
        return selectedAuraId;
    }, [isInfusion, selectedAuraId, selectedInfusionAuraId]);

    // Init Slot se edit
    useEffect(() => {
        if (proposal?.slot_corpo_permessi) {
            setSelectedSlots(proposal.slot_corpo_permessi.split(','));
        }
    }, [proposal]);

    // 1. CARICAMENTO DATI INIZIALI
    useEffect(() => {
        const initData = async () => {
            setIsLoadingData(true);
            try {
                const allData = await getAllPunteggi();
                setAllPunteggiCache(allData);

                if (char && char.punteggi_base) {
                    const validAuras = allData.filter(p => {
                        if (p.tipo !== 'AU') return false;
                        const val = char.punteggi_base[p.nome];
                        if (!val || val < 1) return false;
                        if (isInfusion && !p.permette_infusioni) return false;
                        if (isCerimoniale && p.permette_cerimoniali === false) return false;
                        if (!isInfusion && !isCerimoniale && !p.permette_tessiture) return false;
                        return true;
                    });
                    setAvailableAuras(validAuras);

                    // Filtriamo rigorosamente per tipo 'CA' (Caratteristiche)
                    const validChars = allData.filter(p => p.tipo === 'CA');
                    setAvailableCharacteristics(validChars);
                }

                if (isInfusion) {
                    const classiData = await getClassiOggetto();
                    setAvailableClassi(classiData || []);
                }
            } catch (e) {
                console.error(e);
                setError("Errore caricamento dati dal server.");
            } finally {
                setIsLoadingData(false);
            }
        };
        initData();
    }, [char, type, isInfusion, isCerimoniale]);

    // 2. CARICAMENTO MATTONI SPECIFICI DELL'AURA SELEZIONATA
    useEffect(() => {
        if (!auraIdForBricks) {
            setAvailableBricks([]);
            return;
        }
        getMattoniAura(auraIdForBricks)
            .then(data => setAvailableBricks(data || []))
            .catch(err => console.error("Errore recupero mattoni:", err));
    }, [auraIdForBricks]);

    // 3. LOGICA INFUSIONI (Tipi e Aure Secondarie)
    useEffect(() => {
        if (!selectedAuraId || !isInfusion) return;
        const auraObj = allPunteggiCache.find(p => p.id === parseInt(selectedAuraId));
        if (auraObj) {
            const options = [];
            if (auraObj.produce_mod) options.push('MOD');
            if (auraObj.produce_materia) options.push('MAT');
            if (auraObj.produce_innesti) options.push('INNESTO');
            if (auraObj.produce_mutazioni) options.push('MUTAZIONE');
            setAvailableItemOptions(options);
            if (options.length > 0 && !options.includes(selectedItemType)) setSelectedItemType(options[0]);

            const allowedIds = auraObj.aure_infusione_consentite || [auraObj.id];
            setAvailableInfusionAuras(allPunteggiCache.filter(p => allowedIds.includes(p.id)));
        }
    }, [selectedAuraId, allPunteggiCache, isInfusion, selectedItemType]);

    // --- CALCOLI LIMITI ---
    const currentTotalCount = Object.values(componentsMap).reduce((a, b) => a + b, 0);

    const auraLimit = useMemo(() => {
        if (!selectedAuraId || !char) return 0;
        const auraObj = availableAuras.find(a => a.id == selectedAuraId);
        return auraObj ? (char.punteggi_base[auraObj.nome] || 0) : 0;
    }, [selectedAuraId, char, availableAuras]);

    const maxLivelloCerimoniale = useMemo(() => {
        if (!isCerimoniale || !char) return 0;
        const ccoStat = char.statistiche_primarie?.find(s => s.sigla === 'CCO');
        const ccoVal = ccoStat ? ccoStat.valore_corrente : 0;
        return Math.min(auraLimit, ccoVal);
    }, [isCerimoniale, auraLimit, char]);

    const estimatedCost = currentTotalCount * (isCerimoniale ? 100 : 10);

    // --- HANDLERS ---
    const handleIncrement = (charId, charName) => {
        if (!isDraft) return;
        const currentVal = componentsMap[charId] || 0;

        if (!isCerimoniale) {
            // Vincolo 1: Non superare il punteggio del PG nella Caratteristica
            const pgCharScore = char.punteggi_base[charName] || 0;
            if (currentVal + 1 > pgCharScore) return;

            // Vincolo 2: Non superare il totale permesso dall'Aura
            if (currentTotalCount + 1 > auraLimit) return;
        }

        setComponentsMap(prev => ({ ...prev, [charId]: currentVal + 1 }));
    };

    const handleDecrement = (charId) => {
        if (!isDraft) return;
        const currentVal = componentsMap[charId] || 0;
        if (currentVal <= 1) {
            const newMap = { ...componentsMap };
            delete newMap[charId];
            setComponentsMap(newMap);
        } else {
            setComponentsMap({ ...componentsMap, [charId]: currentVal - 1 });
        }
    };

    const handleTypeChange = (newType) => {
        setSelectedItemType(newType);
        const typeInfo = ITEM_TYPES[newType];
        if (typeInfo?.isBound) setSelectedClasseId('');
        else setSelectedSlots([]);
    };

    const toggleSlot = (slotCode) => {
        if (!isDraft) return;
        setSelectedSlots(prev => prev.includes(slotCode) ? prev.filter(s => s !== slotCode) : [...prev, slotCode]);
    };

    const isCharCompatible = (charId) => {
        if (!isInfusion || isCerimoniale || !selectedClasseId) return true;
        const classeObj = availableClassi.find(c => c.id == selectedClasseId);
        if (!classeObj) return true;
        return selectedItemType === 'MOD' 
            ? (classeObj.mod_allowed_ids || []).includes(parseInt(charId)) 
            : (classeObj.materia_allowed_ids || []).includes(parseInt(charId));
    };

    const getPayload = () => {
        const componentsArray = Object.entries(componentsMap).map(([id, val]) => ({
            caratteristica_id: parseInt(id), 
            valore: val
        }));
        
        let dbType = isInfusion ? 'INF' : isCerimoniale ? 'CER' : 'TES';
        const tipoRisultato = isInfusion ? (['INNESTO', 'MUTAZIONE'].includes(selectedItemType) ? 'AUM' : 'POT') : null;

        return {
            personaggio_id: selectedCharacterId,
            tipo: dbType,
            nome: name,
            descrizione: isCerimoniale ? "Rito Narrativo" : description,
            aura: selectedAuraId,
            aura_infusione: isInfusion ? selectedInfusionAuraId : null,
            tipo_risultato_atteso: tipoRisultato,
            componenti_data: componentsArray, 
            slot_corpo_permessi: isInfusion && ITEM_TYPES[selectedItemType]?.isBound ? selectedSlots.join(',') : '',
            prerequisiti: isCerimoniale ? prerequisiti : null,
            svolgimento: isCerimoniale ? svolgimento : null,
            effetto: isCerimoniale ? effetto : null,
            livello_proposto: isCerimoniale ? livelloCerimoniale : 1,
        };
    };

    const handleSaveAction = async (send = false) => {
        setError(''); 
        if (!name) return setError("Nome della tecnica obbligatorio.");
        if (!selectedAuraId) return setError("Seleziona un'Aura di riferimento.");
        
        if (isCerimoniale) {
            if (!prerequisiti || !svolgimento || !effetto) {
                return setError("Per i cerimoniali, tutti i campi descrittivi sono obbligatori.");
            }
            if (livelloCerimoniale < 1) return setError("Il rito deve avere almeno livello 1.");
        }

        setIsSaving(true);
        try {
            if (send && !window.confirm("Attenzione: l'invio alla valutazione dello staff è definitivo. Confermi?")) {
                setIsSaving(false); return;
            }
            let targetId = proposal?.id;
            const payload = getPayload();
            
            if (!targetId) {
                const newP = await createProposta(payload);
                targetId = newP.id;
            } else {
                await updateProposta(targetId, payload);
            }

            if (send) await sendProposta(targetId);
            onRefresh(); onClose();
        } catch (e) { 
            setError(e.message || "Errore durante il salvataggio."); 
        } finally { 
            setIsSaving(false); 
        }
    };

    const handleDelete = async () => {
        if (!window.confirm("Vuoi davvero eliminare questa bozza? L'azione è irreversibile.")) return;
        try {
            await deleteProposta(proposal.id);
            onRefresh(); onClose();
        } catch (e) { setError(e.message); }
    };

    if (!char) return null;

    // DETERMINA COSA MOSTRARE NELLA GRIGLIA
    const displayItems = availableBricks.length > 0 
        ? availableBricks 
        : availableCharacteristics.filter(c => isCerimoniale || (char.punteggi_base[c.nome] > 0));

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-in fade-in duration-200">
            <div className="bg-gray-900 border border-gray-700 rounded-xl w-full max-w-5xl max-h-[90vh] flex flex-col shadow-2xl animate-fadeIn overflow-hidden">
                
                {/* Header */}
                <div className="p-4 border-b border-gray-700 flex justify-between items-center bg-gray-800 rounded-t-xl shrink-0">
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-gray-900 rounded-lg border border-gray-700">
                            {isInfusion ? <Box className="text-amber-500" size={20}/> : 
                             isCerimoniale ? <Users className="text-purple-400" size={20}/> :
                             <Scroll className="text-indigo-400" size={20}/>}
                        </div>
                        <div>
                            <h2 className="text-lg font-bold text-white">
                                {isEditing ? `Modifica ${type}` : `Crea Nuova Proposta ${type}`}
                            </h2>
                            <p className="text-[10px] text-gray-500 uppercase font-black">
                                {isEditing ? `ID: ${proposal.id} • ${proposal.stato}` : 'Creazione Bozza Personale'}
                            </p>
                        </div>
                    </div>
                    <button onClick={onClose} className="text-gray-400 hover:text-white p-2 hover:bg-gray-700 rounded-full transition-colors">✕</button>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-y-auto p-6 space-y-8 scrollbar-thin scrollbar-thumb-gray-700">
                    {error && <div className="p-3 bg-red-900/30 text-red-200 rounded-lg border border-red-800 flex items-center gap-2 animate-pulse"><AlertTriangle size={16}/> {error}</div>}

                    {/* Identità e Aura */}
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <div className="md:col-span-2">
                            <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest block mb-1">Nome della Tecnica</label>
                            <input 
                                type="text" 
                                value={name} 
                                onChange={e => setName(e.target.value)} 
                                disabled={!isDraft} 
                                className="w-full bg-gray-800 border border-gray-600 rounded-lg p-3 text-white focus:border-indigo-500 outline-none transition-all shadow-inner" 
                                placeholder="Esempio: Dardo del Crepuscolo, Scudo di Naniti..." 
                            />
                        </div>
                        <div>
                            <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest block mb-1">Aura Principale</label>
                            <select 
                                value={selectedAuraId} 
                                onChange={e => {setComponentsMap({}); setSelectedAuraId(e.target.value); setLivelloCerimoniale(1);}} 
                                disabled={!isDraft} 
                                className="w-full bg-gray-800 border border-gray-600 rounded-lg p-3 text-white focus:border-indigo-500 outline-none transition-all cursor-pointer"
                            >
                                <option value="">-- Seleziona Aura --</option>
                                {availableAuras.map(a => (
                                    <option key={a.id} value={a.id}>
                                        {a.nome} (Grado {char.punteggi_base[a.nome] || 0})
                                    </option>
                                ))}
                            </select>
                        </div>
                    </div>

                    {/* LOGICA CERIMONIALE */}
                    {isCerimoniale && selectedAuraId && (
                        <div className="space-y-6 animate-in slide-in-from-top-4 duration-500 bg-purple-900/5 p-6 rounded-2xl border border-purple-500/10">
                            <div className="bg-purple-900/10 p-4 rounded-xl border border-purple-500/20">
                                <label className="text-[10px] font-black text-purple-400 uppercase flex justify-between items-center mb-2">
                                    Livello del Rituale
                                    <span className="text-gray-500 italic lowercase tracking-tight font-normal">Limite Min(Aura, CCO): {maxLivelloCerimoniale}</span>
                                </label>
                                <select 
                                    value={livelloCerimoniale} 
                                    onChange={e => setLivelloCerimoniale(parseInt(e.target.value))}
                                    className="w-full bg-gray-800 border border-purple-500/40 rounded-lg p-3 text-white font-bold outline-none shadow-lg shadow-purple-900/10"
                                >
                                    {[...Array(maxLivelloCerimoniale + 1).keys()].slice(1).map(n => (
                                        <option key={n} value={n}>Livello {n}</option>
                                    ))}
                                    {maxLivelloCerimoniale === 0 && <option value="0">Coralità Insufficiente</option>}
                                </select>
                            </div>

                            <div className="grid grid-cols-1 gap-5">
                                <div>
                                    <label className="text-[10px] font-black text-purple-400 uppercase block mb-1.5 ml-1">Prerequisiti Narrativi</label>
                                    <textarea 
                                        value={prerequisiti} 
                                        onChange={e => setPrerequisiti(e.target.value)} 
                                        className="w-full bg-gray-800 border border-gray-600 rounded-xl p-3 text-white text-sm h-24 focus:border-purple-500 outline-none transition-all placeholder:text-gray-600" 
                                        placeholder="Cosa occorre? (es: partecipanti, fase lunare, incenso raro...)" 
                                        disabled={!isDraft} 
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-gray-400 uppercase block mb-1.5 ml-1">Svolgimento del Rito</label>
                                    <textarea 
                                        value={svolgimento} 
                                        onChange={e => setSvolgimento(e.target.value)} 
                                        className="w-full bg-gray-800 border border-gray-600 rounded-xl p-3 text-white text-sm h-40 focus:border-purple-500 outline-none transition-all placeholder:text-gray-600" 
                                        placeholder="Descrivi dettagliatamente le fasi del cerimoniale..." 
                                        disabled={!isDraft} 
                                    />
                                </div>
                                <div>
                                    <label className="text-[10px] font-black text-purple-400 uppercase block mb-1.5 ml-1">Effetto Finale</label>
                                    <textarea 
                                        value={effetto} 
                                        onChange={e => setEffetto(e.target.value)} 
                                        className="w-full bg-gray-800 border border-gray-600 rounded-xl p-3 text-white text-sm h-24 focus:border-purple-500 outline-none transition-all placeholder:text-gray-600" 
                                        placeholder="Qual è il risultato meccanico o narrativo?" 
                                        disabled={!isDraft} 
                                    />
                                </div>
                            </div>
                        </div>
                    )}

                    {/* LOGICA INFUSIONI/TESSITURE */}
                    {!isCerimoniale && (
                        <div className="space-y-6">
                            <div>
                                <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest block mb-1.5">Descrizione e Meccaniche</label>
                                <textarea 
                                    value={description} 
                                    onChange={e => setDescription(e.target.value)} 
                                    disabled={!isDraft} 
                                    className="w-full bg-gray-800 border border-gray-600 rounded-xl p-4 text-white focus:border-indigo-500 outline-none transition-all min-h-[120px] shadow-inner" 
                                    rows={4}
                                    placeholder="Dettaglia gli effetti meccanici, i bonus numerici e le condizioni di attivazione..."
                                />
                            </div>

                            {isInfusion && selectedAuraId && (
                                <div className="p-6 bg-gray-800/40 rounded-2xl border border-gray-700/50 space-y-6 shadow-xl">
                                    <h3 className="text-sm font-bold text-amber-500 flex items-center gap-2 mb-2"><Settings size={18}/> Configurazione Tecnica Oggetto</h3>
                                    <div className="flex flex-wrap gap-2">
                                        {availableItemOptions.map(optKey => (
                                            <button 
                                                key={optKey} 
                                                onClick={() => handleTypeChange(optKey)} 
                                                className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 transition-all transform active:scale-95 ${selectedItemType === optKey ? 'bg-amber-500 text-black shadow-lg shadow-amber-900/20' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
                                            >
                                                {ITEM_TYPES[optKey].label}
                                            </button>
                                        ))}
                                    </div>
                                    {selectedItemType && (
                                        <div className="animate-in fade-in duration-300">
                                            {ITEM_TYPES[selectedItemType].isBound ? (
                                                <div className="bg-gray-900/50 p-4 rounded-xl border border-pink-500/20">
                                                    <label className="text-[10px] font-black text-pink-400 uppercase block mb-3 ml-1 tracking-widest">Slot Corporei Necessari</label>
                                                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                                                        {BODY_SLOTS.map(slot => (
                                                            <button key={slot.id} onClick={() => toggleSlot(slot.id)} className={`p-2.5 text-[10px] uppercase font-black rounded-lg border transition-all ${selectedSlots.includes(slot.id) ? 'bg-pink-900/40 border-pink-500 text-pink-200' : 'bg-gray-900 border-gray-700 text-gray-500 hover:border-gray-500'}`}>{slot.label}</button>
                                                        ))}
                                                    </div>
                                                </div>
                                            ) : (
                                                <div className="space-y-4">
                                                    <div className="bg-gray-900/50 p-4 rounded-xl border border-indigo-500/20">
                                                        <label className="text-[10px] font-black text-amber-500 uppercase block mb-2 tracking-widest">Aura Sorgente Mattoni (Infusione)</label>
                                                        <select value={selectedInfusionAuraId} onChange={e => {setComponentsMap({}); setSelectedInfusionAuraId(e.target.value);}} className="w-full bg-gray-800 border border-gray-600 rounded-lg p-2.5 text-white text-sm">
                                                            {availableInfusionAuras.map(a => <option key={a.id} value={a.id}>{a.nome}</option>)}
                                                        </select>
                                                    </div>
                                                    <div className="bg-gray-900/50 p-4 rounded-xl border border-indigo-500/20">
                                                        <label className="text-[10px] font-black text-indigo-300 uppercase flex items-center gap-2 mb-2 ml-1 tracking-widest"><Box size={14}/> Compatibilità Classe Oggetto</label>
                                                        <select className="w-full bg-gray-900 border border-indigo-500/30 rounded-xl p-2.5 text-white text-sm" value={selectedClasseId} onChange={e => setSelectedClasseId(e.target.value)}>
                                                            <option value="">-- Mostra Tutte le Caratteristiche --</option>
                                                            {availableClassi.map(c => <option key={c.id} value={c.id}>{c.nome}</option>)}
                                                        </select>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>
                    )}

                    {/* SEZIONE MATTONI / CARATTERISTICHE (COMUNE) */}
                    {selectedAuraId && (
                        <div className="space-y-4 pt-4 border-t border-gray-800">
                            <div className="flex justify-between items-end px-1">
                                <div>
                                    <label className="text-[10px] font-black text-gray-500 uppercase tracking-widest block">
                                        {availableBricks.length > 0 ? `Mattoni dell'Aura Selezionata` : 'Caratteristiche Base'}
                                    </label>
                                    <p className="text-[10px] text-gray-600 mt-0.5">Componi la struttura del potere selezionando i componenti.</p>
                                </div>
                                <div className="text-right">
                                    {!isCerimoniale && (
                                        <span className={`text-[10px] font-bold block uppercase mb-1 ${currentTotalCount >= auraLimit ? 'text-red-500' : 'text-gray-400'}`}>
                                            Totale: {currentTotalCount} / {auraLimit}
                                        </span>
                                    )}
                                    <span className="text-sm font-black text-yellow-500 font-mono tracking-tighter italic">Costo Invio: {estimatedCost} CR</span>
                                </div>
                            </div>

                            <div className="bg-gray-800/20 p-4 rounded-2xl border border-gray-700/50 max-h-[500px] overflow-y-auto shadow-inner grid grid-cols-1 md:grid-cols-3 gap-3">
                                {displayItems.map(item => {
                                    // Gestione polimorfica: Mattone vs Caratteristica
                                    const characteristic = item.caratteristica_associata || item;
                                    const charId = characteristic.id;
                                    const charSigla = characteristic.sigla; // Sigla Caratteristica (es: MIR, FOR)
                                    const charName = characteristic.nome;
                                    const brickName = item.nome; // Nome Mattone (es: "Dardo")

                                    const count = componentsMap[charId] || 0;
                                    const isCompatible = isCharCompatible(charId);
                                    const pgMaxScore = char.punteggi_base[charName] || 0;

                                    return (
                                        <div key={item.id} className={`flex items-center justify-between bg-gray-900 p-3 rounded-xl border transition-all duration-300 ${count > 0 ? 'border-indigo-500/60 bg-indigo-500/5 shadow-lg shadow-indigo-900/10' : 'border-gray-700'} ${!isCompatible ? 'opacity-20 pointer-events-none grayscale' : ''}`}>
                                            <div className="flex items-center gap-3 overflow-hidden">
                                                <IconaPunteggio punteggio={characteristic} size="32px" />
                                                <div className="flex flex-col overflow-hidden">
                                                    {/* NOME MATTONE IN EVIDENZA */}
                                                    <span className="text-[11px] font-bold truncate text-gray-200" title={brickName}>{brickName}</span>
                                                    {/* SIGLA CARATTERISTICA ASSOCIATA SOTTO */}
                                                    <div className="flex items-center gap-1">
                                                        <span className="text-[8px] uppercase text-gray-500 font-black tracking-tighter">{charSigla}</span>
                                                        {!isCerimoniale && <span className="text-[8px] text-gray-600 font-bold">• Max {pgMaxScore}</span>}
                                                    </div>
                                                </div>
                                            </div>
                                            
                                            {isDraft && (
                                                <div className="flex items-center gap-1.5 bg-gray-800 p-1 rounded-lg border border-gray-700 shadow-inner">
                                                    {count > 0 && (
                                                        <button 
                                                            onClick={() => handleDecrement(charId)} 
                                                            className="w-7 h-7 flex items-center justify-center bg-gray-700 hover:bg-red-900/40 rounded-md text-red-400 transition-colors"
                                                        >
                                                            <Minus size={14}/>
                                                        </button>
                                                    )}
                                                    {count > 0 && <span className="text-xs font-mono w-5 text-center text-white font-bold">{count}</span>}
                                                    <button 
                                                        onClick={() => handleIncrement(charId, charName)} 
                                                        disabled={!isCerimoniale && (count >= pgMaxScore || currentTotalCount >= auraLimit)}
                                                        className="w-7 h-7 flex items-center justify-center bg-gray-700 hover:bg-green-900/40 disabled:bg-gray-800 disabled:text-gray-600 rounded-md text-green-400 transition-colors"
                                                    >
                                                        <Plus size={14}/>
                                                    </button>
                                                </div>
                                            )}
                                        </div>
                                    );
                                })}
                            </div>
                        </div>
                    )}
                </div>

                {/* Footer Chiamate API */}
                <div className="p-4 border-t border-gray-700 bg-gray-800 rounded-b-xl flex justify-between items-center shrink-0">
                    <div className="flex items-center gap-4">
                        {isDraft && isEditing ? (
                            <button onClick={handleDelete} className="text-red-400 text-xs font-bold flex items-center gap-1.5 hover:text-red-300 px-3 py-2 rounded-lg hover:bg-red-900/10"><Trash2 size={15}/> Elimina Bozza</button>
                        ) : <div/>}
                    </div>

                    <div className="flex gap-3">
                        {isDraft && (
                            <>
                                <button onClick={() => handleSaveAction(false)} disabled={isSaving} className="px-5 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-xs font-black uppercase flex gap-2 items-center transition-all disabled:opacity-50">{isSaving ? <Loader2 className="animate-spin" size={14}/> : <Save size={15}/>} Salva Bozza</button>
                                <button onClick={() => handleSaveAction(true)} disabled={isSaving || (currentTotalCount === 0 && !isCerimoniale)} className="px-6 py-2.5 bg-green-600 hover:bg-green-500 text-white rounded-xl text-xs font-black uppercase flex gap-2 items-center shadow-lg shadow-green-900/30 transform hover:scale-105">{isSaving ? <Loader2 className="animate-spin" size={14}/> : <Send size={15}/>} Invia allo Staff</button>
                            </>
                        )}
                        {!isDraft && (
                            <button onClick={onClose} className="px-8 py-2.5 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-xs font-black uppercase">Chiudi</button>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default ProposalEditorModal;