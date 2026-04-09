// src/components/QuestItem.jsx
import React, { useState, useMemo, useCallback, memo } from 'react';
import { Edit2, Trash, Plus, Package, List, User as UserIcon, QrCode as QrIcon, X } from 'lucide-react';
import RichTextDisplay from './RichTextDisplay';
import QuestFaseSection from './QuestFaseSection';
import SearchableSelect from './editors/SearchableSelect';

// Mappatura tipi a_vista con codici e labels
const TIPO_A_VISTA_OPTIONS = [
    { value: 'PG', label: 'Personaggio (PG)' },
    { value: 'PNG', label: 'Personaggio Non Giocante (PNG)' },
    { value: 'INV', label: 'Inventario' },
    { value: 'OGG', label: 'Oggetto' },
    { value: 'TES', label: 'Tessitura' },
    { value: 'INF', label: 'Infusione' },
    { value: 'CER', label: 'Cerimoniale' },
    { value: 'MAN', label: 'Manifesto' }
];

const QuestItem = ({ quest, isMaster, risorse, onAddSub, onRemoveSub, onStatChange, onEdit, onScanQr }) => {
    const [viewMode, setViewMode] = useState('FASI'); // 'FASI' o 'STAFF'
    const [newVista, setNewVista] = useState({ tipo: 'MAN', a_vista_id: '' });

    // Filtra gli a_vista disponibili in base al tipo selezionato
    const availableOptions = useMemo(() => {
        if (!risorse?.a_vista) return [];
        return risorse.a_vista.filter(av => av.tipo === newVista.tipo);
    }, [newVista.tipo, risorse]);

    const tasksByStaff = useMemo(() => {
        const map = {};
        quest.fasi?.forEach(fase => {
            fase.tasks?.forEach(task => {
                if (!map[task.staffer]) map[task.staffer] = { details: task.staffer_details, items: [] };
                map[task.staffer].items.push({ ...task, fase_titolo: fase.titolo });
            });
        });
        return Object.values(map);
    }, [quest.fasi]);

    return (
        <div className="bg-gray-800/40 border border-gray-700/50 rounded-2xl overflow-hidden shadow-2xl border-l-4 border-l-indigo-500 w-full mb-8">
            {/* 1. Header (Titolo/Orario) */}
            <div className="bg-gray-800/80 px-5 py-3 flex justify-between items-center border-b border-gray-700">
                <div className="flex items-center gap-4">
                    <div className="bg-indigo-600 text-white px-3 py-1 rounded-lg font-black text-xs shadow-lg">{quest.orario_indicativo?.slice(0, 5)}</div>
                    <h3 className="font-black text-lg text-white uppercase tracking-tight truncate">{quest.titolo}</h3>
                </div>
                <div className="flex items-center gap-4">
                    <div className="flex bg-black/40 rounded-lg p-1 border border-gray-700">
                        <button onClick={() => setViewMode('FASI')} className={`p-1.5 rounded transition-colors ${viewMode === 'FASI' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}><List size={18}/></button>
                        <button onClick={() => setViewMode('STAFF')} className={`p-1.5 rounded transition-colors ${viewMode === 'STAFF' ? 'bg-indigo-600 text-white' : 'text-gray-500 hover:text-gray-300'}`}><UserIcon size={18}/></button>
                    </div>
                    {isMaster && (
                        <div className="flex gap-2 border-l border-gray-700 pl-4">
                            <button onClick={() => onEdit('quest', quest)} className="text-gray-400 hover:text-white"><Edit2 size={18}/></button>
                            <button onClick={() => onRemoveSub('quest', quest.id)} className="text-red-900 hover:text-red-500"><Trash size={18}/></button>
                        </div>
                    )}
                </div>
            </div>

            <div className="p-6 space-y-8">
                {/* 2. Info Quest (Descrizione e Props) */}
                <div className="space-y-4">
                    {quest.descrizione_ampia && <div className="bg-black/20 p-4 rounded-xl border border-gray-800 italic text-gray-300 leading-relaxed"><RichTextDisplay content={quest.descrizione_ampia} /></div>}
                    {quest.props && (
                        <div className="flex items-start gap-3 bg-amber-900/10 border border-amber-900/20 p-4 rounded-xl">
                            <Package size={20} className="text-amber-500 shrink-0 mt-0.5" />
                            <div><span className="text-[10px] font-black text-amber-500 uppercase block mb-1 tracking-widest">Materiale di Scena:</span><div className="text-amber-100/80 text-sm"><RichTextDisplay content={quest.props} /></div></div>
                        </div>
                    )}
                </div>

                {/* 3. Gestione Fasi o Staff */}
                <div className="min-h-[200px]">
                    {viewMode === 'FASI' ? (
                        <div className="space-y-4">
                            {quest.fasi?.map(fase => (
                                <QuestFaseSection 
                                    key={fase.id} 
                                    fase={fase} 
                                    isMaster={isMaster} 
                                    risorse={risorse}
                                    onAddTask={(p) => onAddSub('task', p)} 
                                    onRemoveTask={(id) => onRemoveSub('task', id)}
                                    onStatChange={onStatChange} 
                                    onEdit={() => onEdit('fase', fase)}
                                    onDelete={() => onRemoveSub('fase', fase.id)}
                                />
                            ))}
                            {isMaster && (
                                <button onClick={() => onAddSub('fase', { quest: quest.id, titolo: 'Nuova Fase', ordine: (quest.fasi?.length || 0) + 1 })}
                                    className="w-full py-3 border-2 border-dashed border-gray-700 rounded-xl text-gray-500 hover:border-indigo-500 hover:text-indigo-400 transition-all font-black text-xs uppercase tracking-widest">
                                    + Aggiungi Fase Operativa
                                </button>
                            )}
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                            {tasksByStaff.map(staff => (
                                <div key={staff.details.id} className="bg-gray-900/40 p-4 rounded-xl border border-gray-800 shadow-inner">
                                    <div className="text-xs font-black text-indigo-400 uppercase mb-3 flex items-center gap-2">
                                        <div className="w-6 h-6 rounded-full bg-indigo-900/50 flex items-center justify-center text-[10px]">{staff.details.username[0]}</div>
                                        {staff.details.username}
                                    </div>
                                    <div className="space-y-2">
                                        {staff.items.map(t => (
                                            <div key={t.id} className="text-[10px] text-gray-400 border-t border-gray-800/50 pt-2 flex justify-between">
                                                <span><span className="text-white font-bold">{t.fase_titolo}:</span> {t.personaggio_details?.nome || t.mostro_details?.nome || t.compito_offgame}</span>
                                                <span className="text-[8px] font-black uppercase text-gray-600">{t.ruolo}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>

                {/* 4. Viste & QR (Spostato in fondo e reso più visibile) */}
                <div className="pt-6 border-t border-gray-700/50">
                    <span className="text-[10px] font-black text-emerald-500 uppercase flex items-center gap-2 mb-4 tracking-widest"><QrIcon size={14}/> Elementi di Gioco & QR Code</span>
                    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                        {quest.viste_previste.map(v => {
                            // Determina nome e tipo display
                            let nomeElemento = 'Elemento';
                            let tipoLabel = v.tipo;
                            
                            if (v.manifesto_details) nomeElemento = v.manifesto_details.nome || v.manifesto_details.titolo;
                            else if (v.inventario_details) nomeElemento = v.inventario_details.nome;
                            else if (v.oggetto_details) nomeElemento = v.oggetto_details.nome;
                            else if (v.tessitura_details) nomeElemento = v.tessitura_details.nome;
                            else if (v.infusione_details) nomeElemento = v.infusione_details.nome;
                            else if (v.cerimoniale_details) nomeElemento = v.cerimoniale_details.nome;
                            else if (v.personaggio_details) nomeElemento = v.personaggio_details.nome;
                            
                            const tipoOpt = TIPO_A_VISTA_OPTIONS.find(t => t.value === v.tipo);
                            if (tipoOpt) tipoLabel = tipoOpt.label;
                            
                            return (
                                <div key={v.id} className="flex items-center gap-3 bg-gray-950 border border-gray-800 p-2.5 rounded-xl shadow-sm">
                                    <div className={`p-2 rounded-lg ${v.qr_code ? 'bg-emerald-500/10 text-emerald-500' : 'bg-gray-800 text-gray-600'}`}>
                                        <QrIcon size={18} />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-[11px] font-bold text-gray-200 truncate">{nomeElemento}</div>
                                        <div className="text-[8px] text-gray-500 uppercase font-black">{tipoLabel}</div>
                                    </div>
                                    <div className="flex gap-1 shrink-0">
                                        <button 
                                            onClick={() => onScanQr(v.id)} 
                                            className="text-indigo-400 p-1.5 hover:bg-gray-800 rounded transition-colors" 
                                            title="Associa QR"
                                        >
                                            <QrIcon size={14}/>
                                        </button>
                                        {isMaster && (
                                            <button 
                                                onClick={() => onRemoveSub('vista', v.id)} 
                                                className="text-red-900 hover:text-red-500 p-1.5 hover:bg-gray-800 rounded transition-colors"
                                            >
                                                <X size={14}/>
                                            </button>
                                        )}
                                    </div>
                                </div>
                            );
                        })}
                        {isMaster && (
                            <div className="flex flex-col gap-2 bg-emerald-950/20 border border-dashed border-emerald-900/50 p-3 rounded-xl">
                                <div className="flex items-center gap-2">
                                    <span className="text-[9px] font-black text-emerald-500 uppercase tracking-wider whitespace-nowrap">Tipo:</span>
                                    <select 
                                        className="bg-gray-950 border border-gray-700 rounded px-2 py-1 text-[10px] font-bold text-emerald-400 outline-none flex-1"
                                        value={newVista.tipo} 
                                        onChange={(e) => setNewVista({tipo: e.target.value, a_vista_id: ''})}
                                    >
                                        {TIPO_A_VISTA_OPTIONS.map(opt => (
                                            <option key={opt.value} value={opt.value}>{opt.label}</option>
                                        ))}
                                    </select>
                                </div>
                                <div className="flex items-center gap-2">
                                    <span className="text-[9px] font-black text-emerald-500 uppercase tracking-wider whitespace-nowrap">Elemento:</span>
                                    <div className="flex-1">
                                        <SearchableSelect
                                            options={availableOptions}
                                            value={newVista.a_vista_id}
                                            onChange={(val) => setNewVista({...newVista, a_vista_id: val})}
                                            placeholder="Seleziona elemento..."
                                            labelKey="nome"
                                            valueKey="id"
                                        />
                                    </div>
                                    <button 
                                        onClick={() => { 
                                            if(!newVista.a_vista_id) return alert("Seleziona un elemento"); 
                                            onAddSub('vista', { quest: quest.id, tipo: newVista.tipo, a_vista_id: newVista.a_vista_id }); 
                                            setNewVista({tipo: newVista.tipo, a_vista_id: ''}); 
                                        }} 
                                        className="text-emerald-500 hover:bg-emerald-900/30 p-1.5 rounded transition-all"
                                    >
                                        <Plus size={18}/>
                                    </button>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default memo(QuestItem);