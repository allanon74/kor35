import React, { useState, useMemo, useEffect, useCallback, memo } from 'react';
import { Swords, Users, Monitor, Trash, Heart, Shield, Edit2, Plus, ChevronDown, ChevronUp, UserCheck, Shirt, ScrollText, Zap, SquareActivity } from 'lucide-react';
import RichTextEditor from './RichTextEditor';
import RichTextDisplay from './RichTextDisplay';

// --- SOTTO-COMPONENTE PER LA CARD DEL TASK --- (Memoized)
const TaskCard = memo(({ task, isMaster, currentUserId, onRemove, onStatChange }) => {
    
    // 1. LOGICA "IS MINE"
    const isMine = useMemo(() => {
        if (!currentUserId || !task.staffer) return false;
        const taskStafferId = typeof task.staffer === 'object' && 'id' in task.staffer 
            ? task.staffer.id 
            : task.staffer;
        return String(taskStafferId) === String(currentUserId);
    }, [task.staffer, currentUserId]);

    const [expanded, setExpanded] = useState(false);

    useEffect(() => {
        if (isMine) setExpanded(true);
    }, [isMine]);

    // 2. STILI RUOLO
    const getRoleStyles = () => {
        switch (task.ruolo) {
            case 'MOSTRO': return 'bg-gradient-to-br from-red-950/60 to-black border-red-900/50 hover:border-red-500/50';
            case 'PNG': return 'bg-gradient-to-br from-indigo-950/60 to-black border-indigo-900/50 hover:border-indigo-500/50';
            default: return 'bg-gradient-to-br from-slate-800/60 to-black border-slate-600/50 hover:border-slate-400/50';
        }
    };

    const baseClasses = getRoleStyles();
    const highlightClasses = isMine 
        ? "border-amber-500 shadow-[0_0_15px_-3px_rgba(245,158,11,0.3)] ring-1 ring-amber-500/50" 
        : "";

    const nomeTarget = task.personaggio_details?.nome 
        || task.mostro_details?.nome 
        || (task.compito_offgame === 'REG' ? 'Gestione Regole' : task.compito_offgame === 'AIU' ? 'Aiuto Master' : 'Allestimento');

    // Render Attacchi
    const renderAttacchi = (attacchi) => {
        if (!attacchi) return <span className="text-gray-500 italic">Nessun attacco specificato</span>;
        if (Array.isArray(attacchi)) {
            if (attacchi.length === 0) return <span className="text-gray-500 italic">Nessun attacco specificato</span>;
            return (
                <div className="space-y-1.5 mt-1">
                    {attacchi.map((att, idx) => (
                        <div key={att.id || idx} className="flex flex-col sm:flex-row sm:justify-between sm:items-baseline border-b border-white/10 last:border-0 pb-1">
                            <span className="font-bold text-red-300 text-[11px] whitespace-nowrap mr-2">• {att.nome_attacco}</span>
                            <span className="text-gray-400 text-[10px] italic">{att.descrizione_danno}</span>
                        </div>
                    ))}
                </div>
            );
        }
        return <RichTextDisplay content={attacchi} />;
    };

    return (
        <div className={`rounded-xl border p-3 transition-all duration-300 ${baseClasses} ${highlightClasses}`}>
            {/* --- HEADER --- */}
            <div className="flex flex-col gap-2">
                <div className="flex justify-between items-start gap-2 cursor-pointer select-none" onClick={() => setExpanded(!expanded)}>
                    <div className="flex items-center gap-3 overflow-hidden">
                        <div className={`p-2 rounded-lg shrink-0 shadow-inner ${task.ruolo === 'MOSTRO' ? 'bg-red-500/20 text-red-400' : task.ruolo === 'PNG' ? 'bg-indigo-500/20 text-indigo-400' : 'bg-slate-500/20 text-slate-400'}`}>
                            {task.ruolo === 'MOSTRO' ? <Swords size={20}/> : task.ruolo === 'PNG' ? <Users size={20}/> : <Monitor size={20}/>}
                        </div>
                        <div className="flex flex-col min-w-0">
                            <div className="flex items-center gap-2 flex-wrap">
                                <span className={`text-sm font-black uppercase tracking-tight ${isMine ? 'text-amber-100' : 'text-gray-100'}`}>
                                    {nomeTarget}
                                </span>
                                {isMine && (
                                    <span className="text-[9px] bg-amber-500 text-black px-1.5 py-0.5 rounded font-black flex items-center shadow-lg shadow-amber-500/20 animate-pulse">
                                        <UserCheck size={10} className="mr-1"/> TU
                                    </span>
                                )}
                            </div>
                            <div className={`text-[10px] font-bold truncate ${isMine ? 'text-amber-400' : 'text-gray-400'}`}>
                                @{task.staffer_details?.username}
                            </div>
                        </div>
                    </div>
                    <div className="flex items-center gap-1">
                        <div className={`transition-transform duration-300 ${expanded ? 'rotate-180' : ''} text-gray-500`}>
                            <ChevronDown size={20}/>
                        </div>
                        {isMaster && (
                            <button onClick={(e) => { e.stopPropagation(); onRemove(task.id); }} className="p-1.5 hover:bg-red-900/50 text-gray-500 hover:text-red-400 rounded transition-colors ml-2">
                                <Trash size={16}/>
                            </button>
                        )}
                    </div>
                </div>

                {task.ruolo === 'MOSTRO' && (
                    <div className="flex flex-wrap gap-2 mt-2 justify-start bg-black/40 p-2 rounded-lg border border-white/5 shadow-inner">
                        <StatMini icon={<Heart size={12}/>} label="PV" value={task.punti_vita} onUp={() => onStatChange(task.id, 'punti_vita', 1)} onDown={() => onStatChange(task.id, 'punti_vita', -1)} color="text-red-500" />
                        <StatMini icon={<SquareActivity size={12}/>} label="SC" value={task.guscio || 0} onUp={() => onStatChange(task.id, 'guscio', 1)} onDown={() => onStatChange(task.id, 'guscio', -1)} color="text-cyan-400" />
                        <StatMini icon={<Shield size={12}/>} label="ARM" value={task.armatura} onUp={() => onStatChange(task.id, 'armatura', 1)} onDown={() => onStatChange(task.id, 'armatura', -1)} color="text-gray-300" />
                    </div>
                )}
            </div>

            {/* --- BODY --- */}
            {expanded && (
                <div className="mt-3 pt-3 border-t border-white/10 space-y-3 animation-fade-in-down origin-top">
                    
                    {/* DESCRIZIONE TASK (Se presente) */}
                    {task.descrizione && (
                        <div className="bg-black/30 p-3 rounded-lg border border-white/5 text-gray-300 shadow-sm">
                            <div className="text-[9px] font-bold text-gray-500 uppercase mb-1 flex items-center gap-1">
                                <ScrollText size={10}/> Descrizione Narrativa
                            </div>
                            <div className="scale-100 origin-top-left">
                                <RichTextDisplay content={task.descrizione} />
                            </div>
                        </div>
                    )}

                    {/* ISTRUZIONI */}
                    {task.istruzioni && (
                        <div className="bg-black/30 p-3 rounded-lg border border-white/5 text-gray-300 shadow-sm">
                            <div className="text-[9px] font-bold text-gray-500 uppercase mb-1 flex items-center gap-1"><Edit2 size={10}/> Istruzioni Operative</div>
                            <div className="scale-100 origin-top-left">
                                <RichTextDisplay content={task.istruzioni} />
                            </div>
                        </div>
                    )}

                    {/* DETTAGLI MOSTRO */}
                    {task.ruolo === 'MOSTRO' && task.mostro_details && (
                        <div className="grid grid-cols-1 gap-2 text-xs">
                            {(task.mostro_details.costume || task.costume) && (
                                <div className="flex items-start gap-2 bg-black/30 p-2 rounded text-gray-300 border border-purple-500/20">
                                    <Shirt size={14} className="mt-0.5 text-purple-400 shrink-0"/>
                                    <div className="w-full">
                                        <span className="font-bold text-purple-400 text-[9px] uppercase block mb-0.5">Costume & Props</span>
                                        <div className="whitespace-pre-wrap leading-relaxed">{task.costume || task.mostro_details.costume}</div>
                                    </div>
                                </div>
                            )}
                            
                            {task.mostro_details.note_generali && (
                                <div className="flex items-start gap-2 bg-black/30 p-2 rounded text-gray-300 border border-yellow-500/20">
                                    <ScrollText size={14} className="mt-0.5 text-yellow-500 shrink-0"/>
                                    <div className="w-full">
                                        <span className="font-bold text-yellow-500 text-[9px] uppercase block mb-0.5">Comportamento & Note</span>
                                        <div className="whitespace-pre-wrap leading-relaxed">{task.mostro_details.note_generali}</div>
                                    </div>
                                </div>
                            )}

                            <div className="bg-red-950/20 border border-red-900/30 p-2.5 rounded">
                                <div className="flex items-center gap-1 font-bold text-red-400 text-[9px] uppercase mb-1 border-b border-red-900/30 pb-1">
                                    <Zap size={10}/> Elenco Attacchi & Capacità
                                </div>
                                <div className="text-[11px]">
                                    {renderAttacchi(task.mostro_details.attacchi)}
                                </div>
                            </div>
                        </div>
                    )}
                </div>
            )}
        </div>
    );
});

TaskCard.displayName = 'TaskCard';

const StatMini = memo(({ icon, label, value, onUp, onDown, color }) => (
    <div className={`flex items-center gap-2 bg-black/60 px-2 py-1.5 rounded-lg border border-gray-800 ${color} shadow-sm min-w-[75px] justify-between`}>
        <div className="flex items-center gap-1.5">
            {icon} 
            <div className="flex flex-col leading-none">
                <span className="text-[7px] font-bold opacity-60 uppercase">{label}</span>
                <span className="text-xs font-black text-white">{value}</span>
            </div>
        </div>
        <div className="flex flex-col ml-1 gap-px">
            <button onClick={onUp} className="text-[8px] leading-none text-gray-500 hover:text-white hover:bg-gray-700 px-1 py-px rounded transition-colors">▲</button>
            <button onClick={onDown} className="text-[8px] leading-none text-gray-500 hover:text-white hover:bg-gray-700 px-1 py-px rounded transition-colors">▼</button>
        </div>
    </div>
));

StatMini.displayName = 'StatMini';

// --- COMPONENTE PRINCIPALE ---
const QuestFaseSection = memo(({ fase, isMaster, risorse, onAddTask, onRemoveTask, onStatChange, onEdit, onDelete }) => {
    const [formOpen, setFormOpen] = useState(false);
    
    // STATO DEL FORM AGGIORNATO CON 'descrizione'
    const [form, setForm] = useState({ 
        ruolo: 'PNG', 
        staffer: '', 
        personaggio: '', 
        mostro_template: '', 
        compito_offgame: 'REG', 
        descrizione: '',
        istruzioni: '' 
    });

    const currentUserId = useMemo(() => {
        try {
            const userParams = JSON.parse(localStorage.getItem('user'));
            return userParams ? userParams.id : null;
        } catch (e) { return null; }
    }, []);

    const pngFiltrati = useMemo(() => {
        if (!form.staffer) return [];
        const stafferId = parseInt(form.staffer);
        const stafferObj = risorse.staff?.find(s => s.id === stafferId);
        const stafferName = stafferObj ? stafferObj.username : "";

        return risorse.png?.filter(p => {
            let isMio = false;
            if (p.proprietario_id !== undefined) isMio = (p.proprietario_id === stafferId);
            else if (typeof p.proprietario === 'object' && p.proprietario !== null) isMio = (p.proprietario.id === stafferId);
            else if (typeof p.proprietario === 'string') isMio = (p.proprietario === stafferName);
            else isMio = (p.proprietario == stafferId);
            
            const isPnG = (p.giocante === false || p.giocante === undefined);
            return isMio && isPnG;
        }) || [];
    }, [form.staffer, risorse.png, risorse.staff]);

    const tasks = fase.tasks || [];
    const groupedTasks = useMemo(() => ({
        PNG: tasks.filter(t => t.ruolo === 'PNG'),
        MOSTRO: tasks.filter(t => t.ruolo === 'MOSTRO'),
        OFF: tasks.filter(t => !['PNG', 'MOSTRO'].includes(t.ruolo))
    }), [tasks]);

    const handleFormSubmit = useCallback(() => {
        onAddTask({ fase: fase.id, ...form });
        setForm({ ruolo: 'PNG', staffer: '', personaggio: '', mostro_template: '', compito_offgame: 'REG', descrizione: '', istruzioni: '' });
        setFormOpen(false);
    }, [form, fase.id, onAddTask]);

    return (
        <div className="bg-gray-900/60 rounded-xl border border-gray-700/50 overflow-hidden mb-6 shadow-lg">
            
            {/* HEADER FASE */}
            <div className="bg-gray-800/80 px-4 py-3 flex justify-between items-center border-b border-gray-700 backdrop-blur-sm sticky top-0 z-10">
                <div className="flex items-center gap-3 overflow-hidden">
                    <span className="bg-indigo-600 text-white text-[10px] font-black px-2 py-1 rounded shadow-lg shrink-0">FASE {fase.ordine}</span>
                    <span className="text-sm font-bold text-gray-200 uppercase tracking-wide truncate">{fase.titolo}</span>
                </div>
                
                {isMaster && (
                    <div className="flex items-center gap-1 bg-black/30 rounded-lg p-1 shrink-0">
                        <button onClick={onEdit} className="text-gray-400 hover:text-white p-2 rounded hover:bg-gray-700 transition-colors"><Edit2 size={16}/></button>
                        <div className="w-px h-4 bg-gray-700 mx-0.5"></div>
                        <button onClick={() => { if(window.confirm("Eliminare questa fase e tutti i suoi task?")) onDelete(); }} className="text-gray-400 hover:text-red-500 p-2 rounded hover:bg-gray-700 transition-colors"><Trash size={16}/></button>
                    </div>
                )}
            </div>

            {/* DESCRIZIONE FASE */}
            {fase.descrizione && (
                <div className="bg-gray-900/40 px-4 py-3 border-b border-gray-700/50">
                    <div className="text-gray-300 text-xs leading-relaxed">
                        <RichTextDisplay content={fase.descrizione} />
                    </div>
                </div>
            )}

            <div className="p-3 space-y-6">
                
                {/* Liste Task */}
                {[ ['PNG', 'Personaggi Non Giocanti', <Users size={12}/>, 'indigo'], ['MOSTRO', 'Minacce & Mostri', <Swords size={12}/>, 'red'], ['OFF', 'Gestione Off-Game', <Monitor size={12}/>, 'gray'] ].map(([key, label, icon, color]) => (
                    groupedTasks[key].length > 0 && (
                        <div key={key}>
                            <div className={`text-[10px] font-black text-${color}-400 uppercase mb-2 flex items-center gap-2 ml-1`}>
                                {icon} {label}
                                <div className={`h-px bg-${color}-500/20 flex-1`}></div>
                            </div>
                            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                                {groupedTasks[key].map(task => (
                                    <TaskCard key={task.id} task={task} isMaster={isMaster} currentUserId={currentUserId} onRemove={onRemoveTask} onStatChange={onStatChange} />
                                ))}
                            </div>
                        </div>
                    )
                ))}

                {tasks.length === 0 && <div className="text-center py-8 text-gray-600 text-xs italic border-2 border-dashed border-gray-800 rounded-xl bg-black/20">Nessun incarico assegnato in questa fase.</div>}

                {/* Form Inserimento */}
                {isMaster && (
                    <div className="mt-6">
                        {!formOpen ? (
                            <button onClick={() => setFormOpen(true)} className="w-full py-3 bg-gray-800 hover:bg-gray-700 border border-gray-700 rounded-xl text-[11px] font-black text-gray-400 uppercase tracking-widest flex items-center justify-center gap-2 transition-all shadow-md">
                                <Plus size={16}/> Nuovo Incarico Staff
                            </button>
                        ) : (
                            <div className="bg-gray-950/50 rounded-xl border border-indigo-500/30 overflow-hidden animation-fade-in shadow-xl">
                                <div className="bg-indigo-900/20 px-4 py-3 border-b border-indigo-500/20 flex justify-between items-center">
                                    <span className="text-[11px] font-black text-indigo-400 uppercase tracking-wider">Configura Nuovo Task</span>
                                    <button onClick={() => setFormOpen(false)} className="text-indigo-400 hover:text-white"><ChevronUp size={16}/></button>
                                </div>
                                <div className="p-4 space-y-4">
                                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                                        <div className="space-y-1">
                                            <label className="text-[9px] font-bold text-gray-500 uppercase px-1">Membro Staff</label>
                                            <select className="w-full bg-gray-900 p-2.5 rounded-lg text-xs text-white border border-gray-700 focus:border-indigo-500 outline-none shadow-inner transition-colors" 
                                                value={form.staffer} onChange={e => setForm({...form, staffer: e.target.value, personaggio: ''})}>
                                                <option value="">Seleziona Staffer...</option>
                                                {risorse.staff?.map(s => <option key={s.id} value={s.id}>{s.username}</option>)}
                                            </select>
                                        </div>
                                        <div className="space-y-1">
                                            <label className="text-[9px] font-bold text-gray-500 uppercase px-1">Ruolo / Tipo</label>
                                            <select className="w-full bg-gray-900 p-2.5 rounded-lg text-xs text-indigo-400 border border-gray-700 font-black focus:border-indigo-500 outline-none shadow-inner transition-colors" 
                                                value={form.ruolo} onChange={e => setForm({...form, ruolo: e.target.value})}>
                                                <option value="PNG">RUOLO: PnG</option>
                                                <option value="MOSTRO">RUOLO: Mostro</option>
                                                <option value="OFF">RUOLO: Off-Game</option>
                                            </select>
                                        </div>
                                    </div>

                                    {/* Selettori Dinamici in base al ruolo */}
                                    {form.ruolo === 'PNG' && (
                                        <div className="space-y-1">
                                            <label className="text-[9px] font-bold text-gray-500 uppercase px-1">Personaggio PnG</label>
                                            <select className="w-full bg-gray-900 p-2.5 rounded-lg text-xs text-white border border-gray-700 focus:border-indigo-500 outline-none shadow-inner transition-colors" 
                                                value={form.personaggio} onChange={e => setForm({...form, personaggio: e.target.value})} disabled={!form.staffer}>
                                                <option value="">{form.staffer ? "Seleziona PnG dello Staffer..." : "Prima seleziona un membro dello Staff"}</option>
                                                {pngFiltrati.map(p => <option key={p.id} value={p.id}>{p.nome}</option>)}
                                            </select>
                                        </div>
                                    )}
                                    {form.ruolo === 'MOSTRO' && (
                                        <div className="space-y-1">
                                            <label className="text-[9px] font-bold text-gray-500 uppercase px-1">Template Mostro</label>
                                            <select className="w-full bg-gray-900 p-2.5 rounded-lg text-xs text-white border border-gray-700 focus:border-indigo-500 outline-none shadow-inner transition-colors" 
                                                value={form.mostro_template} onChange={e => setForm({...form, mostro_template: e.target.value})}>
                                                <option value="">Seleziona Template Mostro...</option>
                                                {risorse.templates?.map(t => <option key={t.id} value={t.id}>{t.nome}</option>)}
                                            </select>
                                        </div>
                                    )}
                                    {form.ruolo === 'OFF' && (
                                        <div className="flex gap-2 justify-center bg-gray-900 p-1 rounded-lg border border-gray-700">
                                            {[ ['REG', 'Regole'], ['AIU', 'Aiuto'], ['ALL', 'Allestimento'] ].map(([v, l]) => (
                                                <label key={v} className={`flex-1 text-center py-2 rounded-md cursor-pointer text-[10px] font-bold transition-all ${form.compito_offgame === v ? 'bg-indigo-600 text-white shadow-lg' : 'hover:bg-gray-800 text-gray-500'}`}>
                                                    <input type="radio" className="hidden" value={v} checked={form.compito_offgame === v} onChange={e => setForm({...form, compito_offgame: e.target.value})} /> {l}
                                                </label>
                                            ))}
                                        </div>
                                    )}

                                    {/* CAMPO ISTRUZIONI */}
                                    <div className="space-y-1">
                                        <label className="text-[9px] font-bold text-gray-500 uppercase px-1">Istruzioni Operative</label>
                                        <div className="h-32 border border-gray-700 rounded-lg overflow-hidden bg-gray-900 shadow-inner">
                                            <RichTextEditor value={form.istruzioni} onChange={(val) => setForm({...form, istruzioni: val})} placeholder="Dettagli tecnici e regole..." />
                                        </div>
                                    </div>
                                    
                                    <div className="flex gap-3 pt-2">
                                        <button onClick={() => setFormOpen(false)} className="flex-1 py-3 rounded-lg border border-gray-700 text-gray-400 text-[10px] font-bold hover:bg-gray-800 transition-colors uppercase">Annulla</button>
                                        <button onClick={handleFormSubmit} className="flex-2 bg-indigo-600 hover:bg-indigo-500 py-3 rounded-lg font-black text-[10px] uppercase text-white shadow-lg shadow-indigo-900/30 transition-all transform active:scale-95">Conferma Incarico</button>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
});

QuestFaseSection.displayName = 'QuestFaseSection';

export default QuestFaseSection;
