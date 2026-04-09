import React, { useState, useEffect } from 'react';
import { useCharacter } from './CharacterContext';
import { getProposte } from '../api';
import { FileEdit, Loader2, Plus } from 'lucide-react';
import ProposalEditorModal from './ProposalEditorModal';

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
            const all = await getProposte(selectedCharacterId);
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
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-40 p-4">
            <div className="bg-gray-900 w-full max-w-5xl h-[80vh] rounded-xl flex flex-col border border-gray-700 shadow-2xl relative">
                <div className="absolute top-4 right-4">
                     <button onClick={onClose} className="text-gray-400 hover:text-white bg-gray-800 p-2 rounded-full">✕</button>
                </div>
                
                <div className="p-6 border-b border-gray-700 flex justify-between items-center">
                    <div>
                        <h2 className="text-2xl font-bold text-white">Le tue proposte di {type}</h2>
                        <p className="text-gray-400 text-sm mt-1">Gestisci le tue creazioni. Inviare costa 10 CR per livello.</p>
                    </div>
                    <button 
                        onClick={handleCreateNew}
                        className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-lg flex items-center gap-2 shadow-lg transition-all"
                    >
                        <Plus size={18} /> Nuova Proposta
                    </button>
                </div>

                <div className="flex-1 overflow-y-auto p-6">
                    {isLoading ? (
                        <div className="flex justify-center p-10"><Loader2 className="animate-spin text-indigo-500"/></div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {proposals.map(p => (
                                <div 
                                    key={p.id} 
                                    onClick={() => handleEdit(p)}
                                    className="bg-gray-800 p-4 rounded-lg border border-gray-700 hover:border-indigo-500 cursor-pointer transition-all hover:bg-gray-750 group"
                                >
                                    <div className="flex justify-between items-start mb-2">
                                        <div className={`text-xs font-bold px-2 py-1 rounded uppercase ${
                                            p.stato === 'BOZZA' ? 'bg-gray-600 text-gray-300' :
                                            p.stato === 'VALUTAZIONE' ? 'bg-yellow-600/20 text-yellow-500 border border-yellow-600/50' :
                                            p.stato === 'APPROVATA' ? 'bg-green-600/20 text-green-500 border border-green-600/50' :
                                            'bg-red-600/20 text-red-500 border border-red-600/50'
                                        }`}>
                                            {p.stato}
                                        </div>
                                        {p.stato === 'BOZZA' && <FileEdit size={16} className="text-gray-500 group-hover:text-indigo-400"/>}
                                    </div>
                                    <h3 className="font-bold text-lg text-white mb-1 truncate">{p.personaggio_nome}</h3>
                                    <div className="text-sm text-gray-400 mb-3 flex items-center gap-2">
                                        <div className="w-2 h-2 rounded-full" style={{backgroundColor: p.aura_details?.colore || '#ccc'}}></div>
                                        {p.aura_details?.nome || 'Aura sconosciuta'}
                                        <span className="ml-auto text-xs bg-gray-900 px-2 py-0.5 rounded">Lv. {p.livello}</span>
                                    </div>
                                    {p.note_staff && (
                                        <div className="mt-2 p-2 bg-gray-900/50 rounded text-xs text-gray-300 border-l-2 border-indigo-500">
                                            <span className="font-bold text-indigo-400 block">Staff:</span>
                                            {p.note_staff}
                                        </div>
                                    )}
                                </div>
                            ))}
                            {proposals.length === 0 && (
                                <div className="col-span-full text-center py-10 text-gray-500 border-2 border-dashed border-gray-700 rounded-xl">
                                    Nessuna proposta trovata. Creane una nuova!
                                </div>
                            )}
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