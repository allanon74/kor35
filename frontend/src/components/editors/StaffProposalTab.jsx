import React, { useState, useEffect, useCallback, memo } from 'react';
import { staffGetProposteInValutazione, staffRifiutaProposta, staffApprovaProposta } from '../../api';
import GenericHeader from '../GenericHeader';
import { Eye, X, Check, ClipboardCheck, AlertCircle } from 'lucide-react';
import RichTextEditor from '../RichTextEditor';

// Importazione degli Editor per la fase di approvazione/creazione finale
import InfusioneEditor from './InfusioneEditor';
import TessituraEditor from './TessituraEditor';
import CerimonialeEditor from './CerimonialeEditor';

const StaffProposalTab = ({ onLogout }) => {
    const [proposals, setProposals] = useState([]);
    const [selectedProposal, setSelectedProposal] = useState(null);
    const [viewMode, setViewMode] = useState('list'); // 'list', 'detail', 'approve_edit'
    const [staffNotes, setStaffNotes] = useState("");
    const [loading, setLoading] = useState(false);

    const loadProposals = useCallback(async () => {
        setLoading(true);
        try {
            const data = await staffGetProposteInValutazione(onLogout);
            setProposals(Array.isArray(data) ? data : data.results || []);
        } catch (error) {
            console.error("Errore caricamento proposte", error);
        } finally {
            setLoading(false);
        }
    }, [onLogout]);

    useEffect(() => {
        loadProposals();
    }, [loadProposals]);

    const handleOpenDetail = useCallback((prop) => {
        setSelectedProposal(prop);
        setStaffNotes(prop.note_staff || "");
        setViewMode('detail');
    }, []);

    const handleBack = useCallback(() => {
        setSelectedProposal(null);
        setViewMode('list');
    }, []);

    const handleRifiuta = async () => {
        if (!confirm("Confermi il rifiuto? La proposta tornerà in Bozza al giocatore.")) return;
        try {
            await staffRifiutaProposta(selectedProposal.id, staffNotes, onLogout);
            alert("Proposta rifiutata e rimandata al giocatore.");
            handleBack();
            loadProposals();
        } catch (err) {
            alert("Errore: " + err.message);
        }
    };

    const handleStartApproval = () => {
        setViewMode('approve_edit');
    };

    // Prepara i dati per l'editor.
    // FIX: Mappiamo correttamente i dati per evitare errori 'undefined map'
    const getInitialEditorData = () => {
        if (!selectedProposal) return {};
        const p = selectedProposal;
        
        // Normalizziamo i componenti: l'editor si aspetta un array.
        // Inoltre, convertiamo l'oggetto 'caratteristica' nel suo ID, perché i select degli editor lavorano con gli ID.
        const cleanComponenti = (p.componenti || []).map(c => ({
            caratteristica: (c.caratteristica && typeof c.caratteristica === 'object') ? c.caratteristica.id : c.caratteristica,
            valore: c.valore
        }));

        return {
            nome: p.nome,
            descrizione: p.descrizione,
            testo: p.descrizione, // ridondanza utile per alcuni editor
            aura_richiesta: (p.aura && typeof p.aura === 'object') ? p.aura.id : p.aura,
            
            // Livello e Liv (per compatibilità cerimoniali)
            livello: p.livello,
            liv: p.livello_proposto || 1, 
            
            // FIX CRITICO: Passiamo 'componenti' con la chiave standard, non 'override'
            componenti: cleanComponenti,
            
            // Altri campi testuali
            prerequisiti: p.prerequisiti || "",
            svolgimento: p.svolgimento || "",
            effetto: p.effetto || "",
            
            note_staff: staffNotes
        };
    };

    const handleFinalizeApproval = async (finalData) => {
        try {
            // Assicuriamoci che le note staff siano aggiornate
            finalData.note_staff = staffNotes;
            
            // Chiamata API
            await staffApprovaProposta(selectedProposal.id, finalData, onLogout);
            
            // Feedback Utente
            alert("Tecnica approvata e creata con successo!");
            
            // Chiudi e Aggiorna
            // IMPORTANTE: Eseguiamo queste azioni in ordine sicuro
            handleBack(); // Chiude il modale
            setTimeout(() => {
                loadProposals(); // Ricarica la lista dopo un attimo per dare tempo al DB di aggiornarsi
            }, 300);

        } catch (err) {
            console.error("Errore Approvazione:", err);
            // Gestione sicura dell'errore (evita variabili non definite come 't')
            const errorMsg = err.response?.data?.error || err.message || "Errore sconosciuto";
            alert("Errore durante l'approvazione: " + errorMsg);
        }
    };

    // Helper per visualizzare nomi
    const getCharName = (componente) => {
        if (componente.caratteristica_nome) return componente.caratteristica_nome;
        if (componente.caratteristica && typeof componente.caratteristica === 'object') {
            return componente.caratteristica.nome || componente.caratteristica.sigla || "Caratteristica";
        }
        return "ID: " + componente.caratteristica;
    };

    const getPgName = (p) => {
        // Gestione robusta del nome personaggio
        if (p.personaggio_nome) return p.personaggio_nome;
        if (p.personaggio && typeof p.personaggio === 'object') return p.personaggio.nome;
        // Se è solo ID, proviamo a vedere se abbiamo info extra, altrimenti fallback
        return "Personaggio (ID " + p.personaggio + ")";
    };

    // --- RENDER: LISTA ---
    if (viewMode === 'list') {
        return (
            <div className="h-full flex flex-col bg-gray-900 text-white p-6 overflow-hidden">
                <div className="flex justify-between items-center mb-6">
                    <h2 className="text-2xl font-black uppercase tracking-wider text-orange-500 flex items-center gap-3">
                        <ClipboardCheck size={32}/> Valutazione Proposte
                    </h2>
                    <button onClick={loadProposals} className="text-sm underline text-gray-400 hover:text-white">Aggiorna</button>
                </div>
                
                <div className="flex-1 overflow-auto rounded-xl border border-gray-700 bg-gray-800/50 shadow-inner">
                    <table className="w-full text-left text-gray-300">
                        <thead className="bg-gray-800 text-xs uppercase font-bold text-gray-400 sticky top-0 z-10 shadow-md">
                            <tr>
                                <th className="px-6 py-4">Personaggio</th>
                                <th className="px-6 py-4">Tipo</th>
                                <th className="px-6 py-4">Nome Tecnica</th>
                                {/* Rimossa colonna data come richiesto */}
                                <th className="px-6 py-4 text-right">Azioni</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-gray-700">
                            {proposals.length === 0 ? (
                                <tr>
                                    <td colSpan="4" className="p-10 text-center text-gray-500 italic flex flex-col items-center gap-2">
                                        <AlertCircle size={24}/>
                                        Nessuna proposta in attesa di valutazione.
                                    </td>
                                </tr>
                            ) : (
                                proposals.map(p => (
                                    <tr key={p.id} className="hover:bg-gray-700/50 transition-colors">
                                        <td className="px-6 py-4 font-bold text-white">
                                            {getPgName(p)}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className={`px-2 py-1 rounded text-[10px] font-black tracking-wider uppercase border ${
                                                p.tipo==='INF' ? 'bg-indigo-900/30 text-indigo-300 border-indigo-700' :
                                                p.tipo==='TES' ? 'bg-cyan-900/30 text-cyan-300 border-cyan-700' : 
                                                'bg-purple-900/30 text-purple-300 border-purple-700'
                                            }`}>
                                                {p.tipo === 'INF' ? 'Infusione' : p.tipo === 'TES' ? 'Tessitura' : 'Cerimoniale'}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-white font-medium">{p.nome}</td>
                                        <td className="px-6 py-4 text-right">
                                            <button 
                                                onClick={() => handleOpenDetail(p)} 
                                                className="bg-orange-600 hover:bg-orange-500 text-white px-4 py-1.5 rounded-lg text-xs font-bold uppercase shadow-lg transition-all flex items-center gap-2 ml-auto"
                                            >
                                                <Eye size={14} /> Valuta
                                            </button>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        );
    }

    // --- RENDER: EDITOR DI APPROVAZIONE ---
    if (viewMode === 'approve_edit') {
        const commonProps = {
            initialData: getInitialEditorData(),
            onSave: handleFinalizeApproval,
            onCancel: () => setViewMode('detail'),
            onLogout: onLogout, 
            isApprovalMode: true 
        };

        return (
            <div className="fixed inset-0 bg-black z-60 overflow-y-auto">
                <div className="p-6 max-w-7xl mx-auto">
                    <div className="flex justify-between items-center mb-6 bg-gray-800 p-4 rounded-xl border border-gray-700">
                        <div className="flex items-center gap-3">
                            <div className="bg-green-600/20 p-2 rounded-lg border border-green-500/50">
                                <Check className="text-green-500" size={24}/>
                            </div>
                            <div>
                                <h2 className="text-xl font-bold text-white">Finalizzazione {selectedProposal.tipo}</h2>
                                <p className="text-sm text-gray-400">Modifica se necessario e salva per creare la tecnica effettiva.</p>
                            </div>
                        </div>
                        <button onClick={() => setViewMode('detail')} className="bg-gray-700 hover:bg-gray-600 text-white px-4 py-2 rounded-lg font-bold text-sm">Annulla</button>
                    </div>
                    
                    <div className="bg-gray-900 rounded-xl border border-gray-700 overflow-hidden min-h-[80vh]">
                        {selectedProposal.tipo === 'INF' && <InfusioneEditor {...commonProps} />}
                        {selectedProposal.tipo === 'TES' && <TessituraEditor {...commonProps} />}
                        {selectedProposal.tipo === 'CER' && <CerimonialeEditor {...commonProps} />}
                    </div>
                </div>
            </div>
        );
    }

    // --- RENDER: DETTAGLIO (MODALE VALUTAZIONE) ---
    return (
        <div className="fixed inset-0 bg-black/90 flex items-center justify-center p-4 z-50 overflow-y-auto backdrop-blur-md">
            <div className="bg-gray-900 border border-gray-600 rounded-2xl w-full max-w-6xl max-h-[95vh] flex flex-col shadow-2xl">
                
                {/* Header Modale */}
                <div className="p-5 border-b border-gray-700 flex justify-between items-center bg-gray-800 rounded-t-2xl">
                    <div>
                        <h2 className="text-2xl font-bold text-white flex items-center gap-2">
                            <span className="text-orange-500">Valutazione:</span> {selectedProposal.nome}
                        </h2>
                        <div className="flex gap-2 mt-1">
                            <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300 font-mono">ID: {selectedProposal.id}</span>
                            <span className="text-xs bg-gray-700 px-2 py-0.5 rounded text-gray-300">Livello: {selectedProposal.livello}</span>
                        </div>
                    </div>
                    <button onClick={handleBack} className="text-gray-400 hover:text-white bg-gray-700/50 p-2 rounded-full hover:bg-gray-700"><X size={24}/></button>
                </div>

                {/* Contenuto Scrollabile */}
                <div className="p-6 overflow-y-auto flex-1 space-y-6">
                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 h-full">
                        
                        {/* Colonna SX: Dati della Proposta */}
                        <div className="space-y-6 overflow-y-auto pr-2">
                            {/* Card Dati Tecnici */}
                            <div className="bg-gray-800/50 p-5 rounded-xl border border-gray-700">
                                <h3 className="text-cyan-500 font-black uppercase text-xs tracking-widest mb-4 border-b border-gray-700 pb-2">Specifiche Tecniche</h3>
                                <div className="space-y-2 text-sm">
                                    <p><strong className="text-gray-400">Tipo:</strong> {selectedProposal.tipo}</p>
                                    <p><strong className="text-gray-400">Aura Richiesta:</strong> {selectedProposal.aura_nome || (typeof selectedProposal.aura === 'object' ? selectedProposal.aura.nome : selectedProposal.aura)}</p>
                                    {selectedProposal.tipo === 'CER' && (
                                        <p><strong className="text-gray-400">Livello Proposto:</strong> {selectedProposal.livello_proposto}</p>
                                    )}
                                    <div className="mt-3 bg-gray-900 p-3 rounded-lg">
                                        <strong className="text-gray-400 block mb-2 text-xs uppercase">Componenti / Mattoni:</strong>
                                        <ul className="list-disc pl-5 text-gray-300 space-y-1">
                                            {selectedProposal.componenti && selectedProposal.componenti.map((c, i) => (
                                                <li key={i}>
                                                    <span className="text-cyan-400 font-bold">{getCharName(c)}</span> 
                                                    <span className="text-gray-500 text-xs ml-2">x{c.valore}</span>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                </div>
                            </div>

                            {/* Card Descrizione */}
                            <div className="bg-gray-800/50 p-5 rounded-xl border border-gray-700">
                                <h3 className="text-cyan-500 font-black uppercase text-xs tracking-widest mb-4 border-b border-gray-700 pb-2">Descrizione Giocatore</h3>
                                <div className="prose prose-invert text-sm max-w-none text-gray-300 leading-relaxed whitespace-pre-wrap"
                                     dangerouslySetInnerHTML={{ __html: selectedProposal.descrizione }} 
                                />
                                
                                {selectedProposal.tipo === 'CER' && (
                                    <div className="mt-6 space-y-4 pt-4 border-t border-gray-700/50">
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Prerequisiti</strong>
                                            <p className="text-sm text-gray-300">{selectedProposal.prerequisiti}</p>
                                        </div>
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Svolgimento</strong>
                                            <p className="text-sm text-gray-300">{selectedProposal.svolgimento}</p>
                                        </div>
                                        <div>
                                            <strong className="text-yellow-500 block text-xs uppercase mb-1">Effetto</strong>
                                            <p className="text-sm text-gray-300">{selectedProposal.effetto}</p>
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Colonna DX: Note Staff e Azioni */}
                        <div className="flex flex-col h-full bg-gray-800 p-1 rounded-xl border border-gray-700">
                            <div className="bg-gray-900 rounded-t-lg p-3 border-b border-gray-700">
                                <label className="text-xs font-black text-gray-400 uppercase tracking-widest flex items-center gap-2">
                                    <ClipboardCheck size={14}/> Note Staff (Visibili al giocatore)
                                </label>
                            </div>
                            <div className="flex-1 overflow-hidden relative">
                                <RichTextEditor 
                                    value={staffNotes} 
                                    onChange={setStaffNotes}
                                    placeholder="Scrivi qui le motivazioni del rifiuto o eventuali note di approvazione..."
                                    className="h-full border-none rounded-none focus:ring-0"
                                />
                            </div>
                        </div>
                    </div>
                </div>

                {/* Footer Azioni */}
                <div className="p-5 border-t border-gray-700 bg-gray-800 rounded-b-2xl flex justify-end gap-4 shadow-lg z-20">
                    <button 
                        onClick={handleRifiuta}
                        className="bg-red-900/30 border border-red-700 text-red-300 hover:bg-red-900/50 px-6 py-3 rounded-xl flex items-center gap-2 text-sm font-bold uppercase transition-all"
                    >
                        <X size={18} /> Rifiuta (Torna in Bozza)
                    </button>
                    
                    <button 
                        onClick={handleStartApproval}
                        className="bg-green-600 hover:bg-green-500 text-white px-8 py-3 rounded-xl flex items-center gap-2 font-black uppercase shadow-lg shadow-green-900/30 hover:scale-105 transition-all"
                    >
                        <Check size={18} /> Approva & Crea Tecnica
                    </button>
                </div>
            </div>
        </div>
    );
};

export default memo(StaffProposalTab);