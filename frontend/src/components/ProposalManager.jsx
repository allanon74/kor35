import React, { useState, useEffect } from 'react';
import { useCharacter } from './CharacterContext';
import { getProposte } from '../api';
import { FileEdit, Loader2, Plus } from 'lucide-react';
import ProposalEditorModal from './ProposalEditorModal';
import RichHtml from './RichHtml';
import { getAuraName } from '../utils/auraDisplay';
import { etichettaStatoProposta, propostaDaRivedere, sezioneProposta } from '../lib/propostaTecnicaStato';

const SEZIONI = [
    {
        id: 'bozze',
        titolo: 'Bozze',
        descrizione: 'Modificabili. Se lo staff rimanda indietro una proposta, torna qui con le note.',
    },
    {
        id: 'valutazione',
        titolo: 'In valutazione',
        descrizione: 'In attesa dello staff. Un rifiuto le toglie da questo elenco e le riporta in bozza.',
    },
    {
        id: 'approvate',
        titolo: 'Approvate',
        descrizione: 'Create e inserite tra le tecniche apprese.',
    },
];

function righeProposte(payload) {
    if (Array.isArray(payload)) return payload;
    if (Array.isArray(payload?.results)) return payload.results;
    return [];
}

const ProposalManager = ({ type, onClose }) => { // type = 'Infusione' | 'Tessitura'
    const { selectedCharacterId } = useCharacter();
    const [proposals, setProposals] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [editorOpen, setEditorOpen] = useState(false);
    const [selectedProposal, setSelectedProposal] = useState(null);

    const filterType = type === 'Infusione' ? 'INF' : type === 'Cerimoniale' ? 'CER' : 'TES';

    const fetchProposals = async () => {
        setIsLoading(true);
        try {
            const all = righeProposte(await getProposte(selectedCharacterId));
            setProposals(all.filter(p => p.tipo === filterType));
        } catch (e) {
            console.error(e);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        if (selectedCharacterId) fetchProposals();
    }, [selectedCharacterId]);

    const handleCreateNew = () => {
        setSelectedProposal(null);
        setEditorOpen(true);
    };

    const handleEdit = (prop) => {
        setSelectedProposal(prop);
        setEditorOpen(true);
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-end sm:items-center justify-center z-40 p-0 sm:p-4">
            <div className="bg-gray-900 w-full max-w-5xl h-[92vh] sm:h-[80vh] rounded-t-2xl sm:rounded-xl flex flex-col border border-gray-700 shadow-2xl relative">
                <div className="absolute top-3 right-3 z-10">
                     <button onClick={onClose} className="text-gray-400 hover:text-white bg-gray-800 p-2 rounded-full min-h-11 min-w-11 flex items-center justify-center" aria-label="Chiudi">✕</button>
                </div>
                
                <div className="p-4 sm:p-6 pr-14 border-b border-gray-700 flex flex-col sm:flex-row sm:justify-between sm:items-center gap-3">
                    <div>
                        <h2 className="text-xl sm:text-2xl font-bold text-white">Le tue proposte di {type}</h2>
                        <p className="text-gray-400 text-sm mt-1">Le bozze si modificano e si ripresentano. L&apos;invio costa crediti (10 CR per livello, salvo l&apos;aura).</p>
                    </div>
                    <button 
                        onClick={handleCreateNew}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-lg flex items-center justify-center gap-2 shadow-lg transition-all w-full sm:w-auto min-h-11"
                    >
                        <Plus size={18} /> Nuova Proposta
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-4 sm:p-6">
                    {isLoading ? (
                        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-indigo-500"/></div>
                    ) : proposals.length === 0 ? (
                        <div className="text-center py-10 text-gray-500 border-2 border-dashed border-gray-700 rounded-xl">
                            Nessuna proposta trovata. Creane una nuova!
                        </div>
                    ) : (
                        <div className="space-y-8">
                            {SEZIONI.map((sezione) => {
                                const rows = proposals.filter((p) => sezioneProposta(p) === sezione.id);
                                if (rows.length === 0 && sezione.id !== 'bozze') return null;
                                return (
                                    <section key={sezione.id} aria-label={sezione.titolo}>
                                        <h3 className="text-sm font-black uppercase tracking-widest text-gray-300">{sezione.titolo}</h3>
                                        <p className="text-xs text-gray-500 mt-1 mb-3">{sezione.descrizione}</p>
                                        {rows.length === 0 ? (
                                            <div className="text-sm text-gray-500 border border-dashed border-gray-700 rounded-xl px-4 py-6 text-center">
                                                Nessuna bozza. Una proposta rifiutata ricompare qui.
                                            </div>
                                        ) : (
                                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                                                {rows.map((p) => {
                                                    const daRivedere = propostaDaRivedere(p);
                                                    return (
                                                        <div
                                                            key={p.id}
                                                            onClick={() => handleEdit(p)}
                                                            className={`bg-gray-800 p-4 rounded-lg border cursor-pointer transition-all group min-w-0 ${
                                                                daRivedere
                                                                    ? 'border-amber-600/70 hover:border-amber-400'
                                                                    : 'border-gray-700 hover:border-indigo-500'
                                                            }`}
                                                        >
                                                            <div className="flex justify-between items-start mb-2 gap-2">
                                                                <div className={`text-xs font-bold px-2 py-1 rounded ${
                                                                    sezione.id === 'bozze' ? (daRivedere ? 'bg-amber-600/20 text-amber-200 border border-amber-600/50' : 'bg-gray-600 text-gray-300') :
                                                                    sezione.id === 'valutazione' ? 'bg-yellow-600/20 text-yellow-500 border border-yellow-600/50' :
                                                                    'bg-green-600/20 text-green-500 border border-green-600/50'
                                                                }`}>
                                                                    {etichettaStatoProposta(p)}
                                                                </div>
                                                                {sezione.id === 'bozze' && <FileEdit size={16} className="text-gray-500 group-hover:text-indigo-400 shrink-0"/>}
                                                            </div>
                                                            <h3 className="font-bold text-lg text-white mb-1 break-words">{p.nome || 'Senza nome'}</h3>
                                                            <div className="text-sm text-gray-400 mb-3 flex items-center gap-2 min-w-0">
                                                                <div className="w-2 h-2 rounded-full shrink-0" style={{backgroundColor: p.aura_details?.colore || '#ccc'}}></div>
                                                                <span className="truncate">{getAuraName(p)}</span>
                                                                <span className="ml-auto text-xs bg-gray-900 px-2 py-0.5 rounded shrink-0">Lv. {p.livello}</span>
                                                            </div>
                                                            {p.note_staff && (
                                                                <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs text-gray-300 border-l-2 border-amber-500 min-w-0">
                                                                    <span className="font-bold text-amber-300 block">Note dello staff</span>
                                                                    <RichHtml content={p.note_staff} className="text-xs text-gray-200 break-words line-clamp-4" />
                                                                </div>
                                                            )}
                                                        </div>
                                                    );
                                                })}
                                            </div>
                                        )}
                                    </section>
                                );
                            })}
                        </div>
                    )}
                </div>
            </div>

            {editorOpen && (
                <ProposalEditorModal 
                    type={type}
                    proposal={selectedProposal}
                    onClose={() => setEditorOpen(false)}
                    onRefresh={fetchProposals}
                />
            )}
        </div>
    );
};

export default ProposalManager;