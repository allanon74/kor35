import React, { useState, useEffect } from 'react';
import { 
    X, Plus, Trash2, Search, Layers, 
    ChevronDown, LayoutList, Type, AlignLeft 
} from 'lucide-react';
import RichTextEditor from '../RichTextEditor'; 
import { getAllAbilitaSimple } from '../../api';
import EditorSaveActions from './EditorSaveActions';

// Mappatura delle tipologie (da allineare con personaggi/models.py)
const TIER_TYPES = [
    { value: 'G0', label: 'Tabelle Generali' },
    { value: 'T1', label: 'Tier 1' },
    { value: 'T2', label: 'Tier 2' },
    { value: 'T3', label: 'Tier 3' },
    { value: 'T4', label: 'Tier 4' },
    // { value: 'SP', label: 'Specializzazione' },
    // { value: 'AL', label: 'Altro' },
];

const TabellaEditor = ({ tier, onSave, onCancel, onLogout, statusMessage = '', statusType = 'success' }) => {
    // Stato form principale
    const [formData, setFormData] = useState({
        nome: tier?.nome || '',
        // Il backend accetta valori come 'G0', 'T1', 'T2', ecc.
        // Usiamo 'G0' (Tabelle Generali) come default quando si crea una nuova tabella.
        tipo: tier?.tipo || 'G0',
        descrizione: tier?.descrizione || '',
    });

    // Stato gestione abilità collegate
    const [connectedSkills, setConnectedSkills] = useState(
        tier?.abilita_collegate?.map(a => ({
            abilita_id: a.abilita_id,
            nome: a.abilita_nome,
            ordine: a.ordine
        })) || []
    );

    // Stato gestione ricerca/aggiunta abilità
    const [allAbilities, setAllAbilities] = useState([]);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedAbilityId, setSelectedAbilityId] = useState('');
    const [newOrder, setNewOrder] = useState(0);

    // Carica lista completa abilità
    useEffect(() => {
        const loadAbilities = async () => {
            try {
                const data = await getAllAbilitaSimple(onLogout);
                setAllAbilities(data);
                const maxOrder = connectedSkills.length > 0 ? Math.max(...connectedSkills.map(s => s.ordine)) : 0;
                setNewOrder(maxOrder + 1);
            } catch (error) {
                console.error("Errore caricamento abilità", error);
            }
        };
        loadAbilities();
    }, []); // eslint-disable-line react-hooks/exhaustive-deps

    // Filtra abilità
    const filteredAbilities = allAbilities.filter(a => 
        a.nome.toLowerCase().includes(searchTerm.toLowerCase()) &&
        !connectedSkills.some(cs => cs.abilita_id === a.id)
    );

    const handleAddSkill = () => {
        if (!selectedAbilityId) return;
        const abilityToAdd = allAbilities.find(a => a.id === parseInt(selectedAbilityId));
        
        setConnectedSkills(prev => [...prev, {
            abilita_id: abilityToAdd.id,
            nome: abilityToAdd.nome,
            ordine: parseInt(newOrder)
        }].sort((a,b) => a.ordine - b.ordine));

        setSelectedAbilityId('');
        setNewOrder(parseInt(newOrder) + 1);
        setSearchTerm('');
    };

    const handleRemoveSkill = (id) => {
        setConnectedSkills(prev => prev.filter(s => s.abilita_id !== id));
    };
    
    const handleSkillOrderEdit = (idx, val) => {
        const newSkills = [...connectedSkills];
        newSkills[idx].ordine = parseInt(val);
        newSkills.sort((a,b) => a.ordine - b.ordine);
        setConnectedSkills(newSkills);
    };

    const handleSubmit = (mode = 'save_close') => {
        onSave(formData, connectedSkills, mode);
    };

    return (
        <div className="bg-gray-900 rounded-xl shadow-2xl border border-gray-800 flex flex-col h-full overflow-hidden animate-in fade-in zoom-in-95 duration-300">
            
            {/* === HEADER === */}
            <div className="p-4 md:p-5 border-b border-gray-800 flex justify-between items-center bg-linear-to-r from-gray-900 to-gray-800 shrink-0 z-10">
                <div className="flex items-center gap-3">
                    <div className="bg-indigo-600/20 p-2 rounded-lg border border-indigo-500/30 text-indigo-400">
                        <Layers size={24} />
                    </div>
                    <div>
                        <h2 className="text-lg md:text-xl font-black text-white uppercase tracking-wide leading-none">
                            {tier ? 'Modifica Tabella' : 'Nuova Tabella'}
                        </h2>
                        <span className="text-[10px] text-gray-400 font-mono uppercase tracking-widest">Editor Configurazione</span>
                    </div>
                </div>
                <button onClick={onCancel} className="bg-gray-800 hover:bg-gray-700 text-gray-400 hover:text-white p-2 rounded-full transition-all border border-gray-700 hover:border-gray-500">
                    <X size={20} />
                </button>
            </div>

            {/* === BODY SCROLLABILE === */}
            <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-6 custom-scrollbar bg-gray-900/50">
                
                {/* SEZIONE 1: Dati Generali */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Nome */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                            <Type size={14}/> Nome Tabella
                        </label>
                        <input 
                            type="text" 
                            value={formData.nome}
                            onChange={e => setFormData({...formData, nome: e.target.value})}
                            className="w-full bg-gray-800 border border-gray-700 rounded-lg p-3 text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-all font-medium text-sm placeholder-gray-600"
                            placeholder="Es. Guerriero, Elfo, Fabbro..."
                            required
                        />
                    </div>

                    {/* Tipo (Select Reale) */}
                    <div className="space-y-2">
                        <label className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                            <LayoutList size={14}/> Tipologia
                        </label>
                        <div className="relative">
                            <select 
                                value={formData.tipo}
                                onChange={e => setFormData({...formData, tipo: e.target.value})}
                                className="w-full appearance-none bg-gray-800 border border-gray-700 rounded-lg p-3 pr-10 text-white focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 focus:outline-none transition-all font-medium text-sm cursor-pointer hover:bg-gray-750"
                            >
                                {TIER_TYPES.map(type => (
                                    <option key={type.value} value={type.value}>{type.label}</option>
                                ))}
                            </select>
                            <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-500 pointer-events-none" size={18} />
                        </div>
                    </div>
                </div>

                {/* Descrizione */}
                <div className="space-y-2">
                    <label className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
                        <AlignLeft size={14}/> Descrizione Formattata
                    </label>
                    <div className="bg-white rounded-lg border border-gray-700 overflow-hidden min-h-[150px] shadow-inner">
                        <RichTextEditor 
                            value={formData.descrizione} 
                            onChange={(val) => setFormData({...formData, descrizione: val})} 
                        />
                    </div>
                </div>

                <div className="border-t border-gray-800 my-2"></div>

                {/* SEZIONE 2: Gestione Abilità */}
                <div className="bg-gray-800/40 rounded-xl border border-gray-800 overflow-hidden">
                    <div className="p-4 bg-gray-800/60 border-b border-gray-800 flex flex-col md:flex-row md:items-center justify-between gap-4">
                        <h3 className="text-sm font-bold text-gray-200 flex items-center gap-2">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            ABILITÀ NEL TIER
                            <span className="bg-gray-700 text-gray-300 text-[10px] px-2 py-0.5 rounded-full">{connectedSkills.length}</span>
                        </h3>
                        
                        {/* Area Aggiunta Rapida */}
                        <div className="flex gap-2 w-full md:w-auto">
                            <div className="relative flex-1 md:w-64 group">
                                <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-indigo-400 transition-colors"/>
                                <input 
                                    type="text"
                                    placeholder="Cerca abilità..."
                                    value={searchTerm}
                                    onChange={e => setSearchTerm(e.target.value)}
                                    className="w-full pl-9 pr-2 py-2 bg-gray-900 border border-gray-700 rounded-lg text-sm focus:border-indigo-500 focus:outline-none transition-colors"
                                />
                                {/* Dropdown Risultati */}
                                {searchTerm && filteredAbilities.length > 0 && (
                                    <div className="absolute top-full left-0 right-0 mt-1 bg-gray-800 border border-gray-700 rounded-lg shadow-xl max-h-48 overflow-y-auto z-50 divide-y divide-gray-700/50">
                                        {filteredAbilities.map(a => (
                                            <button 
                                                key={a.id}
                                                onClick={() => { setSelectedAbilityId(a.id); setSearchTerm(a.nome); }}
                                                className="w-full text-left px-3 py-2 text-sm text-gray-300 hover:bg-indigo-600 hover:text-white transition-colors"
                                            >
                                                {a.nome}
                                            </button>
                                        ))}
                                    </div>
                                )}
                            </div>
                            
                            <div className="flex items-center gap-2 bg-gray-900 rounded-lg border border-gray-700 p-1 px-2">
                                <span className="text-[10px] uppercase text-gray-500 font-bold">Ord.</span>
                                <input 
                                    type="number" 
                                    value={newOrder}
                                    onChange={e => setNewOrder(e.target.value)}
                                    className="w-10 bg-transparent text-center text-sm font-bold text-white focus:outline-none"
                                />
                            </div>

                            <button 
                                type="button"
                                onClick={handleAddSkill}
                                disabled={!selectedAbilityId && !searchTerm}
                                className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:text-gray-500 text-white p-2 rounded-lg shadow-lg transition-all active:scale-95"
                            >
                                <Plus size={20}/>
                            </button>
                        </div>
                    </div>

                    {/* Lista Card Abilità */}
                    <div className="p-2 space-y-2 max-h-[300px] overflow-y-auto custom-scrollbar bg-gray-900/20">
                        {connectedSkills.length === 0 && (
                            <div className="text-center py-8 border-2 border-dashed border-gray-800 rounded-lg m-2">
                                <Layers size={32} className="mx-auto text-gray-700 mb-2"/>
                                <p className="text-gray-500 text-sm">Nessuna abilità collegata.</p>
                            </div>
                        )}
                        
                        {connectedSkills.map((skill, idx) => (
                            <div key={skill.abilita_id} className="flex items-center gap-3 bg-gray-800 p-2 px-3 rounded-lg border border-gray-700/50 hover:border-gray-600 transition-all group animate-in slide-in-from-left-2 duration-300">
                                
                                {/* Badge Ordine */}
                                <div className="flex flex-col items-center justify-center bg-gray-900 w-10 h-10 rounded border border-gray-700 shrink-0">
                                    <span className="text-[9px] text-gray-500 uppercase leading-none">Ord</span>
                                    <input 
                                        type="number" 
                                        value={skill.ordine}
                                        onChange={(e) => handleSkillOrderEdit(idx, e.target.value)}
                                        className="w-full bg-transparent text-center font-bold text-indigo-400 focus:outline-none text-sm leading-none mt-0.5"
                                    />
                                </div>
                                
                                {/* Nome Skill */}
                                <div className="flex-1 min-w-0">
                                    <span className="block font-bold text-gray-200 truncate">{skill.nome}</span>
                                    <span className="text-[10px] text-gray-500 uppercase tracking-wider">ID: {skill.abilita_id}</span>
                                </div>

                                {/* Azioni */}
                                <button 
                                    onClick={() => handleRemoveSkill(skill.abilita_id)}
                                    className="text-gray-500 hover:text-red-500 hover:bg-red-500/10 p-2 rounded-lg transition-all opacity-100 md:opacity-0 md:group-hover:opacity-100"
                                    title="Rimuovi"
                                >
                                    <Trash2 size={18} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            </div>

            {/* === FOOTER === */}
            <div className="p-4 border-t border-gray-800 bg-gray-900 flex justify-end gap-3 shrink-0 z-10">
                <EditorSaveActions
                    onSave={() => handleSubmit('save_close')}
                    onSaveAndContinue={() => handleSubmit('save_continue')}
                    onSaveAsNew={tier?.id ? () => handleSubmit('save_as_new') : null}
                    onSaveAndNew={() => handleSubmit('save_new_blank')}
                    onCancel={onCancel}
                    saveLabel={tier ? 'Salva modifiche' : 'Crea tabella'}
                    statusMessage={statusMessage}
                    statusType={statusType}
                />
            </div>
        </div>
    );
};

export default TabellaEditor;