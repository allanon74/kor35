import React, { useState, useEffect, useMemo, useCallback, memo } from 'react';
import { 
    getEventi, associaQrAVista, getRisorseEditor, getAVistaDisponibili,
    createEvento, updateEvento, deleteEvento,
    createGiorno, updateGiorno, deleteGiorno,
    createQuest, updateQuest, deleteQuest,
    addPngToQuest, addMostroToQuest, addVistaToQuest,
    removePngFromQuest, removeMostroFromQuest, removeVistaFromQuest,
    addFaseToQuest, removeFaseFromQuest,updateFase,
    addTaskToFase, removeTaskFromFase,
    // AGGIUNTI GLI IMPORT MANCANTI PER LO STAFF:
    staffCreateOffGame, staffDeleteOffGame,
    fetchAuthenticated 
} from '../api';
import { useCharacter } from './CharacterContext';
import { Plus, X, Save, Printer } from 'lucide-react';
import EventoSection from './EventoSection';
import GiornoSection from './GiornoSection';
import QrTab from './QrTab'; 
import RichTextEditor from './RichTextEditor';

// Cache per le risorse (persiste per la sessione)
const RISORSE_CACHE_KEY = 'plot_risorse_cache';
const RISORSE_CACHE_TIMEOUT = 5 * 60 * 1000; // 5 minuti

const PlotTab = ({ onLogout }) => {
    const { isMaster } = useCharacter();
    const [eventi, setEventi] = useState([]);
    const [selectedEvento, setSelectedEvento] = useState(null);
    const [loading, setLoading] = useState(true);
    const [risorse, setRisorse] = useState(() => {
        // Prova a caricare dalla cache
        try {
            const cached = sessionStorage.getItem(RISORSE_CACHE_KEY);
            if (cached) {
                const { data, timestamp } = JSON.parse(cached);
                if (Date.now() - timestamp < RISORSE_CACHE_TIMEOUT) {
                    console.log("PlotTab: Risorse caricate dalla cache");
                    return data;
                }
            }
        } catch (e) {
            console.warn("PlotTab: Errore lettura cache:", e);
        }
        return { png: [], templates: [], manifesti: [], inventari: [], staff: [], a_vista: [] };
    });
    const [risorseLoaded, setRisorseLoaded] = useState(() => {
        // Verifica se le risorse sono state caricate dalla cache
        try {
            const cached = sessionStorage.getItem(RISORSE_CACHE_KEY);
            if (cached) {
                const { timestamp } = JSON.parse(cached);
                return Date.now() - timestamp < RISORSE_CACHE_TIMEOUT;
            }
        } catch (e) {
            // Ignora errori
        }
        return false;
    });
    
    const [editMode, setEditMode] = useState(null); 
    const [formData, setFormData] = useState({});
    const [scanningForVista, setScanningForVista] = useState(null);

    const loadInitialData = useCallback(async () => {
        try {
            console.log("PlotTab: Inizio caricamento eventi...");
            
            // Carica prima gli eventi (più importante, più veloce)
            const evData = await getEventi(onLogout);
            
            // Verifica che evData sia un array
            if (!Array.isArray(evData)) {
                console.error("PlotTab: evData non è un array:", evData);
                setEventi([]);
                setLoading(false);
                return;
            }
            
            // Ordina eventi per data e trova il primo futuro
            const sortedEvents = evData.sort((a, b) => new Date(a.data_inizio) - new Date(b.data_inizio));
            const today = new Date().setHours(0,0,0,0);
            const nextEvent = sortedEvents.find(ev => new Date(ev.data_inizio) >= today) || sortedEvents[0];
            
            setEventi(sortedEvents);
            if (nextEvent) {
                console.log("PlotTab: Evento selezionato:", nextEvent.id, nextEvent.titolo);
                setSelectedEvento(nextEvent);
            } else {
                console.warn("PlotTab: Nessun evento trovato");
            }
            
            // Ora che gli eventi sono caricati, possiamo mostrare l'interfaccia
            setLoading(false);
            
            // Carica le risorse in background (lazy loading) solo se non in cache
            if (!risorseLoaded) {
                console.log("PlotTab: Caricamento risorse in background...");
                try {
                    // Carica sia risorse che a_vista in parallelo
                    const [risData, aVistaData] = await Promise.all([
                        getRisorseEditor(onLogout),
                        getAVistaDisponibili(onLogout)
                    ]);
                    console.log("PlotTab: Risorse caricate:", risData);
                    console.log("PlotTab: A_vista disponibili:", aVistaData);
                    
                    const risorseData = {
                        ...(risData || {}),
                        a_vista: aVistaData?.a_vista || []
                    };
                    setRisorse(risorseData);
                    setRisorseLoaded(true);
                    
                    // Salva in cache
                    try {
                        sessionStorage.setItem(RISORSE_CACHE_KEY, JSON.stringify({
                            data: risorseData,
                            timestamp: Date.now()
                        }));
                    } catch (e) {
                        console.warn("PlotTab: Errore salvataggio cache:", e);
                    }
                } catch (risError) {
                    console.error("PlotTab: Errore caricamento risorse (non critico):", risError);
                    // Le risorse non sono critiche, possiamo continuare senza
                }
            } else {
                console.log("PlotTab: Risorse già in cache, skip caricamento");
            }
        } catch (e) { 
            console.error("PlotTab: Errore caricamento plot:", e);
            alert(`Errore nel caricamento dei dati plot: ${e.message || e}`);
            setEventi([]);
            setRisorse({ png: [], templates: [], manifesti: [], inventari: [], staff: [], a_vista: [] });
            setLoading(false);
        }
    }, [onLogout, risorseLoaded]);

    useEffect(() => { loadInitialData(); }, [loadInitialData]);

    const refreshData = useCallback(async () => {
        const data = await getEventi(onLogout);
        const sorted = data.sort((a, b) => new Date(a.data_inizio) - new Date(b.data_inizio));
        setEventi(sorted);
        setSelectedEvento(prev => {
            if (!prev) return sorted[0];
            const updated = sorted.find(e => e.id === prev.id);
            return updated || sorted[0];
        });
    }, [onLogout]);

    // Formatters memoized
    const formatDateForInput = useCallback((iso) => iso ? iso.split('T')[0] : '', []);
    const formatDateTimeForInput = useCallback((iso) => iso ? iso.slice(0, 16) : '', []);
    const formatTimeForInput = useCallback((time) => time ? time.slice(0, 5) : '', []);

    const startEdit = useCallback((tipo, oggetto = {}) => {
        setEditMode(tipo);
        setFormData({ ...oggetto });
    }, []);

    const handleSaveMain = useCallback(async () => {
        try {
            if (editMode === 'evento') {
                if (formData.id) await updateEvento(formData.id, formData, onLogout);
                else await createEvento(formData, onLogout);
            } else if (editMode === 'giorno') {
                const data = { ...formData, evento: selectedEvento.id };
                if (formData.id) await updateGiorno(formData.id, data, onLogout);
                else await createGiorno(data, onLogout);
            } else if (editMode === 'quest') {
                if (formData.id) await updateQuest(formData.id, formData, onLogout);
                else await createQuest(formData, onLogout);
            } else if (editMode === 'fase') { // <--- NUOVO BLOCCO
                if (formData.id) {
                    await updateFase(formData.id, formData, onLogout);
                }
             } 
            setEditMode(null);
            refreshData();
        } catch (e) { alert("Errore durante il salvataggio."); console.error(e); }
    }, [editMode, formData, selectedEvento, onLogout, refreshData]);

    const handleDeleteEvento = useCallback(async (id) => { 
        if(window.confirm("Eliminare intero evento?")) { 
            await deleteEvento(id, onLogout); 
            refreshData(); 
        } 
    }, [onLogout, refreshData]);
    
    const handleDeleteGiorno = useCallback(async (id) => { 
        if(window.confirm("Eliminare giorno?")) { 
            await deleteGiorno(id, onLogout); 
            refreshData(); 
        } 
    }, [onLogout, refreshData]);

    const questHandlers = useMemo(() => ({
    onAddSub: async (tipo, payload) => {
        try {
            if (tipo === 'fase') await addFaseToQuest(payload, onLogout);
            if (tipo === 'task') await addTaskToFase(payload, onLogout);
            if (tipo === 'vista') {
                // Passa direttamente tipo e a_vista_id
                const vistaPayload = { 
                    tipo: payload.tipo, 
                    a_vista_id: payload.a_vista_id
                };
                await addVistaToQuest(payload.quest, vistaPayload, onLogout);
            }
            refreshData();
        } catch (error) {
            console.error("Errore aggiunta:", error);
            alert("Errore nell'operazione: " + error.message);
        }
    },
    onRemoveSub: async (tipo, id) => {
        if (tipo === 'fase') await removeFaseFromQuest(id, onLogout);
        if (tipo === 'task') await removeTaskFromFase(id, onLogout);
        if (tipo === 'vista') await removeVistaFromQuest(id, onLogout);
        if (tipo === 'quest') { if (window.confirm("Eliminare quest?")) await deleteQuest(id, onLogout); }
        refreshData();
    },
    onStatChange: async (id, field, delta) => {
        // Cerchiamo il task nell'albero dei dati per avere il valore attuale
        const allTasks = selectedEvento.giorni
            .flatMap(g => g.quests)
            .flatMap(q => q.fasi || [])
            .flatMap(f => f.tasks || []);
        
        const task = allTasks.find(t => t.id === id);
        if (!task) return;

        await fetchAuthenticated(`/api/plot/api/tasks/${id}/`, { 
            method: 'PATCH', 
            body: JSON.stringify({ [field]: (task[field] || 0) + delta }) 
        }, onLogout);
        refreshData();
    },
    onScanQr: (id) => setScanningForVista(id)
}), [selectedEvento, onLogout, refreshData]);

    // Callbacks per EventoSection (spostati fuori dal JSX)
    const handleUpdateEvento = useCallback((id, data) => { 
        updateEvento(id, data, onLogout); 
        refreshData(); 
    }, [onLogout, refreshData]);

    const handleAddGiorno = useCallback(() => startEdit('giorno'), [startEdit]);
    
    // Callback per GiornoSection (spostato fuori dal JSX)
    const handleAddQuest = useCallback((gid) => startEdit('quest', { giorno: gid }), [startEdit]);

    // IMPORTANTE: handlePrintEvent deve essere definito PRIMA del return condizionale
    const handlePrintEvent = useCallback(() => {
        if (!selectedEvento || !selectedEvento.giorni) return;

        const printWindow = window.open('', '_blank');
        
        // --- FUNZIONI DI FORMATTAZIONE PER LA STAMPA ---
        const formatFullDate = (iso) => iso ? new Date(iso).toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) : 'Data da definire';
        const formatTime = (iso) => iso ? new Date(iso).toLocaleTimeString('it-IT', { hour: '2-digit', minute: '2-digit' }) : '--:--';
        const formatTimeSimple = (timeStr) => timeStr ? timeStr.slice(0, 5) : 'N/D';

        // --- STILI CSS AVANZATI PER STAMPA ---
        const styles = `
            <style>
                @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@300;400;700;900&family=Merriweather:ital,wght@0,300;0,700;1,400&display=swap');
                
                @page { margin: 1.5cm; size: A4; }
                
                body { 
                    font-family: 'Roboto', sans-serif; 
                    color: #1a1a1a; 
                    line-height: 1.5; 
                    font-size: 10pt;
                    -webkit-print-color-adjust: exact; 
                }

                h1 { font-size: 26pt; text-transform: uppercase; border-bottom: 4px solid #000; margin-bottom: 5px; padding-bottom: 10px; font-weight: 900; }
                h2 { font-size: 18pt; margin-top: 0; background: #222; color: #fff; padding: 8px 15px; font-weight: 700; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
                h3 { font-size: 14pt; margin: 20px 0 10px 0; border-bottom: 2px solid #666; padding-bottom: 5px; color: #444; font-weight: 800; display: flex; justify-content: space-between; }
                h4 { font-size: 12pt; margin: 15px 0 5px 0; color: #2563eb; font-weight: 700; text-transform: uppercase; border-left: 4px solid #2563eb; padding-left: 10px; }

                .meta { font-size: 11pt; color: #666; margin-bottom: 20px; font-style: italic; border-bottom: 1px solid #ddd; padding-bottom: 10px; }
                
                /* Box Informativi */
                .box-synopsis { background-color: #f3f4f6; padding: 15px; border-left: 5px solid #000; margin-bottom: 30px; font-family: 'Merriweather', serif; text-align: justify; }
                .box-master { background-color: #e0e7ff; padding: 10px; border: 1px solid #c7d2fe; margin-bottom: 15px; font-size: 9pt; }
                .box-props { background-color: #fff7ed; padding: 10px; border: 1px solid #ffedd5; margin: 10px 0; font-size: 9pt; page-break-inside: avoid; }

                /* Struttura Giorni */
                .day-container { margin-bottom: 40px; page-break-before: always; }
                .day-container:first-of-type { page-break-before: auto; }
                .day-meta { font-size: 12pt; font-weight: bold; margin-bottom: 15px; color: #444; }

                /* Struttura Quest */
                .quest-block { margin-bottom: 30px; }
                .quest-desc { font-family: 'Merriweather', serif; margin-bottom: 15px; }

                /* Task Grid */
                .task-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 10px; }
                .task-card { border: 1px solid #ccc; padding: 8px; font-size: 9pt; background: #fff; page-break-inside: avoid; box-shadow: 2px 2px 0px #eee; }
                .task-header { font-weight: 900; border-bottom: 1px solid #eee; padding-bottom: 4px; margin-bottom: 4px; display: flex; justify-content: space-between; align-items: center; }
                .task-role { font-size: 7pt; color: #fff; padding: 2px 5px; border-radius: 3px; font-weight: bold; text-transform: uppercase; }
                .bg-png { background-color: #4f46e5; }
                .bg-mostro { background-color: #dc2626; }
                .bg-off { background-color: #4b5563; }
                .stats { font-family: monospace; font-weight: bold; margin-top: 5px; font-size: 8pt; color: #666; background: #f9f9f9; padding: 2px; text-align: center; }

                /* Rich Text Reset per stampa */
                .rich-text p { margin-bottom: 8px; margin-top: 0; }
                .rich-text ul, .rich-text ol { padding-left: 20px; margin: 5px 0; }
                .rich-text li { margin-bottom: 2px; }
                strong { font-weight: 900; }
            </style>
        `;

        // --- BODY HTML ---
        let content = `
            <html>
            <head><title>Report Plot: ${selectedEvento.titolo}</title>${styles}</head>
            <body>
                <h1>${selectedEvento.titolo}</h1>
                <div class="meta">
                    <strong>Periodo:</strong> ${formatFullDate(selectedEvento.data_inizio)} - ${formatFullDate(selectedEvento.data_fine)} <br/>
                    <strong>Luogo:</strong> ${selectedEvento.luogo || 'Non specificato'} | 
                    <strong>PC Globali:</strong> ${selectedEvento.pc_guadagnati || 0}
                </div>
                
                ${selectedEvento.sinossi ? `
                    <div class="box-synopsis">
                        <div style="font-weight:bold; text-transform:uppercase; font-size:9pt; color:#666; margin-bottom:5px;">Sinossi Evento</div>
                        <div class="rich-text">${selectedEvento.sinossi}</div>
                    </div>
                ` : ''}
        `;

        // Loop Giorni
        selectedEvento.giorni.forEach((giorno, idx) => {
            content += `
                <div class="day-container">
                    <h2>GIORNO ${idx + 1}: ${giorno.titolo || 'Senza Titolo'}</h2>
                    <div class="day-meta">
                        Data: ${formatFullDate(giorno.data_ora_inizio)} | 
                        Orario: ${formatTime(giorno.data_ora_inizio)} - ${formatTime(giorno.data_ora_fine)}
                    </div>

                    ${giorno.sinossi_breve ? `<p class="rich-text"><strong>Sinossi Breve:</strong> ${giorno.sinossi_breve}</p>` : ''}
                    
                    ${giorno.descrizione_completa ? `
                        <div class="box-master">
                            <strong>Note Master / Descrizione Completa:</strong><br/>
                            <div class="rich-text">${giorno.descrizione_completa}</div>
                        </div>
                    ` : ''}
            `;

            // Loop Quest (Ordinate per orario)
            if (giorno.quests && giorno.quests.length > 0) {
                // Ordina quest per orario
                const questsOrdinate = [...giorno.quests].sort((a, b) => 
                    (a.orario_indicativo || '00:00').localeCompare(b.orario_indicativo || '00:00')
                );

                questsOrdinate.forEach(quest => {
                    content += `
                        <div class="quest-block">
                            <h3>
                                <span>${quest.titolo}</span>
                                <span>${formatTimeSimple(quest.orario_indicativo)}</span>
                            </h3>
                            
                            <div class="quest-desc rich-text">
                                ${quest.descrizione_ampia || quest.descrizione || '<em style="color:#999">Nessuna descrizione disponibile.</em>'}
                            </div>

                            ${quest.props ? `
                                <div class="box-props">
                                    <strong>OGGETTI DI SCENA (PROPS):</strong>
                                    <div class="rich-text">${quest.props}</div>
                                </div>
                            ` : ''}
                    `;

                    // Loop Fasi
                    if (quest.fasi && quest.fasi.length > 0) {
                        const fasiOrdinate = [...quest.fasi].sort((a,b) => a.ordine - b.ordine);
                        
                        fasiOrdinate.forEach(fase => {
                            content += `
                                <div>
                                    <h4>FASE ${fase.ordine}: ${fase.titolo}</h4>
                                    ${fase.descrizione ? `<div class="rich-text" style="font-size:9pt; margin-bottom:5px; padding-left:10px; color:#555;">${fase.descrizione}</div>` : ''}
                            `;

                            // Loop Tasks
                            if (fase.tasks && fase.tasks.length > 0) {
                                content += `<div class="task-grid">`;
                                fase.tasks.forEach(task => {
                                    const nomeTarget = task.personaggio_details?.nome 
                                        || task.mostro_details?.nome 
                                        || (task.compito_offgame === 'REG' ? 'Gestione Regole' : task.compito_offgame === 'AIU' ? 'Aiuto Master' : 'Allestimento');
                                    
                                    let ruoloClass = 'bg-off';
                                    if(task.ruolo === 'PNG') ruoloClass = 'bg-png';
                                    if(task.ruolo === 'MOSTRO') ruoloClass = 'bg-mostro';
                                    
                                    content += `
                                        <div class="task-card">
                                            <div class="task-header">
                                                <span>${nomeTarget}</span>
                                                <span class="task-role ${ruoloClass}">${task.ruolo}</span>
                                            </div>
                                            <div style="margin-bottom:4px; font-size:8pt; color:#666;">
                                                <strong>Staff:</strong> @${task.staffer_details?.username || 'N/D'}
                                                ${task.ruolo === 'PNG' ? `(PnG di ${task.personaggio_details?.proprietario || 'N/D'})` : ''}
                                            </div>
                                            
                                            ${task.istruzioni ? `<div class="rich-text">${task.istruzioni}</div>` : ''}
                                            
                                            ${task.ruolo === 'MOSTRO' ? `
                                                <div class="stats">
                                                    PV: ${task.punti_vita} | SC: ${task.schermo || task.guscio || 0} | ARM: ${task.armatura}
                                                </div>
                                                ${task.mostro_details?.costume ? `<div style="margin-top:4px; font-size:8pt;"><strong>Costume:</strong> ${task.mostro_details.costume}</div>` : ''}
                                            ` : ''}
                                        </div>
                                    `;
                                });
                                content += `</div>`; // close grid
                            } else {
                                content += `<div style="font-style:italic; font-size:9pt; color:#aaa; margin-left:10px;">Nessun incarico assegnato.</div>`;
                            }
                            content += `</div>`; // close fase div
                        });
                    } else {
                        content += `<p style="margin-left:10px;">Nessuna fase operativa definita.</p>`;
                    }
                    content += `</div>`; // close quest-block
                });
            } else {
                content += `<p>Nessuna quest pianificata per questo giorno.</p>`;
            }
            content += `</div>`; // close day-container
        });

        content += `
            <script>
                window.onload = function() { window.print(); }
            </script>
            </body></html>
        `;

        printWindow.document.write(content);
        printWindow.document.close();
    }, [selectedEvento]);

    // Check di loading DOPO tutti gli hook
    if (loading) return <div className="h-full flex items-center justify-center bg-gray-900"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-indigo-500"></div></div>;

    return (
        <div className="flex flex-col h-full bg-gray-900 text-white pb-20 overflow-hidden">
            <div className="p-4 bg-gray-950 border-b border-gray-800 flex gap-2 z-40 shadow-xl sticky top-0">
                <select 
                    className="flex-1 bg-gray-900 p-3 rounded-xl border border-gray-800 font-black text-indigo-400 outline-none cursor-pointer transition-all hover:border-indigo-500"
                    value={selectedEvento?.id || ''} 
                    onChange={(e) => {
                        const found = eventi.find(ev => ev.id === parseInt(e.target.value));
                        if (found) setSelectedEvento(found);
                    }}
                    disabled={eventi.length === 0}
                >
                    {eventi.length === 0 ? (
                        <option value="">Nessun evento disponibile</option>
                    ) : (
                        eventi.map(ev => <option key={ev.id} value={ev.id}>{ev.titolo?.toUpperCase() || 'Senza titolo'}</option>)
                    )}
                </select>
                {isMaster && (
                    <button onClick={() => startEdit('evento')} className="p-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 transition-colors shadow-lg"><Plus size={24}/></button>
                )}
                <button 
                    onClick={handlePrintEvent}
                    className="p-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg transition-colors shadow-lg shadow-indigo-900/20 flex items-center gap-2"
                    title="Stampa Report Completo"
                >
                    <Printer size={20} />
                    <span className="hidden md:inline font-bold text-xs uppercase">Stampa Report</span>
                </button>
            </div>

            {editMode && (
                <div className="fixed inset-0 z-100 bg-black/90 flex items-center justify-center p-4 backdrop-blur-sm">
                    <div className="bg-gray-800 p-6 rounded-2xl w-full max-w-3xl border-t-4 border-indigo-500 shadow-2xl overflow-y-auto max-h-[90vh]">
                        <div className="flex justify-between items-center mb-6">
                            <h3 className="text-xl font-black uppercase text-indigo-400 italic tracking-widest">Editor {editMode}</h3>
                            <button onClick={() => setEditMode(null)} className="p-2 hover:bg-gray-700 rounded-full transition-colors"><X/></button>
                        </div>
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {/* ... Codice form invariato ... */}
                            {editMode === 'evento' && (
                                <>
                                    <div className="md:col-span-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Titolo</label>
                                        <input className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700 focus:border-indigo-500 outline-none" value={formData.titolo || ''} onChange={e => setFormData({...formData, titolo: e.target.value})} />
                                    </div>
                                    <div><label className="text-[10px] font-bold text-gray-500 uppercase px-1">Inizio</label><input type="date" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formatDateForInput(formData.data_inizio)} onChange={e => setFormData({...formData, data_inizio: e.target.value})} /></div>
                                    <div><label className="text-[10px] font-bold text-gray-500 uppercase px-1">Fine</label><input type="date" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formatDateForInput(formData.data_fine)} onChange={e => setFormData({...formData, data_fine: e.target.value})} /></div>
                                    <div><label className="text-[10px] font-bold text-gray-500 uppercase px-1">Luogo</label><input className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formData.luogo || ''} onChange={e => setFormData({...formData, luogo: e.target.value})} /></div>
                                    <div><label className="text-[10px] font-bold text-gray-500 uppercase px-1">PC Guadagnati</label><input type="number" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formData.pc_guadagnati || 0} onChange={e => setFormData({...formData, pc_guadagnati: e.target.value})} /></div>
                                    <div className="md:col-span-2">
                                        <RichTextEditor label="Sinossi" value={formData.sinossi} onChange={val => setFormData({...formData, sinossi: val})} />
                                    </div>
                                </>
                            )}
                            {editMode === 'giorno' && (
                                <>
                                    <div className="md:col-span-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Titolo Giorno</label>
                                        <input className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700 focus:border-indigo-500 outline-none" value={formData.titolo || ''} onChange={e => setFormData({...formData, titolo: e.target.value})} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <RichTextEditor label="Sinossi Breve (Sottotitolo)" value={formData.sinossi_breve} onChange={val => setFormData({...formData, sinossi_breve: val})} />
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Inizio (Data/Ora)</label>
                                        <input type="datetime-local" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formatDateTimeForInput(formData.data_ora_inizio)} onChange={e => setFormData({...formData, data_ora_inizio: e.target.value})} />
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Fine (Data/Ora)</label>
                                        <input type="datetime-local" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formatDateTimeForInput(formData.data_ora_fine)} onChange={e => setFormData({...formData, data_ora_fine: e.target.value})} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <RichTextEditor label="Descrizione Plot Completa (Info Master)" value={formData.descrizione_completa} onChange={val => setFormData({...formData, descrizione_completa: val})} />
                                    </div>
                                </>
                            )}
                            {editMode === 'quest' && (
                                <>
                                    <div className="md:col-span-2"><label className="text-[10px] font-bold text-gray-500 uppercase px-1">Titolo Quest</label><input className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formData.titolo || ''} onChange={e => setFormData({...formData, titolo: e.target.value})} /></div>
                                    <div><label className="text-[10px] font-bold text-gray-500 uppercase px-1">Orario</label><input type="time" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" value={formatTimeForInput(formData.orario_indicativo)} onChange={e => setFormData({...formData, orario_indicativo: e.target.value})} /></div>
                                    <div className="md:col-span-2">
                                        <RichTextEditor label="Descrizione Ampia" value={formData.descrizione_ampia} onChange={val => setFormData({...formData, descrizione_ampia: val})} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <RichTextEditor label="Props (Materiale di scena)" value={formData.props} onChange={val => setFormData({...formData, props: val})} />
                                    </div>
                                </>
                            )}
                            {editMode === 'fase' && (
                                <>
                                    <div className="md:col-span-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Titolo Fase</label>
                                        <input className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" 
                                            value={formData.titolo || ''} 
                                            onChange={e => setFormData({...formData, titolo: e.target.value})} />
                                    </div>
                                    <div>
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Ordine</label>
                                        <input type="number" className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700" 
                                            value={formData.ordine || 0} 
                                            onChange={e => setFormData({...formData, ordine: parseInt(e.target.value)})} />
                                    </div>
                                    <div className="md:col-span-2">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase px-1">Descrizione (Opzionale)</label>
                                        <textarea className="w-full bg-gray-900 p-3 rounded-lg border border-gray-700 h-24 resize-none" 
                                            value={formData.descrizione || ''} 
                                            onChange={e => setFormData({...formData, descrizione: e.target.value})} />
                                    </div>
                                </>
                            )}
                        </div>
                        <button onClick={handleSaveMain} className="w-full mt-6 bg-indigo-600 py-4 rounded-xl font-black uppercase tracking-widest hover:bg-indigo-500 transition-all flex items-center justify-center gap-2">
                            <Save size={20}/> Salva {editMode}
                        </button>
                    </div>
                </div>
            )}

            <div className="flex-1 overflow-y-auto custom-scrollbar">
                {eventi.length === 0 ? (
                    <div className="h-full flex flex-col items-center justify-center p-8 text-center">
                        <p className="text-xl font-bold text-gray-400 mb-4">Nessun evento disponibile</p>
                        <p className="text-sm text-gray-500 mb-6">
                            {isMaster 
                                ? "Crea un nuovo evento utilizzando il pulsante + sopra" 
                                : "Non hai eventi assegnati. Contatta un Master per essere assegnato a un evento."}
                        </p>
                        {isMaster && (
                            <button 
                                onClick={() => startEdit('evento')} 
                                className="px-6 py-3 bg-indigo-600 rounded-xl hover:bg-indigo-500 transition-colors shadow-lg font-bold uppercase"
                            >
                                Crea Primo Evento
                            </button>
                        )}
                    </div>
                ) : (
                    <>
                        {selectedEvento && (
                            <EventoSection 
                                evento={selectedEvento} 
                                isMaster={isMaster} 
                                risorse={risorse}
                                onEdit={startEdit} 
                                onDelete={handleDeleteEvento}
                                onUpdateEvento={handleUpdateEvento}
                                onAddGiorno={handleAddGiorno}
                            />
                        )}
                        <div className="p-4 space-y-16">
                            {selectedEvento?.giorni?.map((giorno, gIdx) => (
                                <GiornoSection 
                                    key={giorno.id} 
                                    giorno={giorno} 
                                    gIdx={gIdx} 
                                    isMaster={isMaster} 
                                    risorse={risorse}
                                    onEdit={startEdit} 
                                    onDelete={handleDeleteGiorno} 
                                    onAddQuest={handleAddQuest}
                                    questHandlers={questHandlers} 
                                />
                            ))}
                        </div>
                    </>
                )}
            </div>

            {scanningForVista && (
                <div className="fixed inset-0 z-110 bg-black flex flex-col">
                    <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 shadow-xl">
                        <span className="font-black text-white uppercase italic tracking-widest">Associa QR Fisico</span>
                        <button onClick={() => setScanningForVista(null)} className="px-4 py-2 bg-red-600 rounded-lg text-xs font-black shadow-lg">X ANNULLA</button>
                    </div>
                    <div className="flex-1">
                        <QrTab onScanSuccess={async (qr_id) => {
                            try {
                                await associaQrAVista(scanningForVista, qr_id, onLogout, false);
                                setScanningForVista(null); 
                                refreshData();
                            } catch (error) {
                                // Se il QR è già associato (409 Conflict), chiedi conferma
                                if (error.status === 409 && error.data?.already_associated) {
                                    const conferma = window.confirm(
                                        `⚠️ ATTENZIONE!\n\n${error.data.message}\n\nVuoi procedere comunque e spostare il QR su questo elemento?`
                                    );
                                    if (conferma) {
                                        await associaQrAVista(scanningForVista, qr_id, onLogout, true);
                                        setScanningForVista(null);
                                        refreshData();
                                    }
                                } else {
                                    throw error;
                                }
                            }
                        }} onLogout={onLogout} />
                    </div>
                </div>
            )}
        </div>
    );
};

export default memo(PlotTab);