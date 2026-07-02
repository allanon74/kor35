import React, { useState, useMemo, useCallback, useEffect, memo } from 'react';
import {
    MapPin, Edit2, Trash2, Calendar,
    Users, Star, UserPlus, X, ChevronDown, ChevronUp, ShieldCheck, Ticket, RefreshCw,
} from 'lucide-react';
import { RichTextViewer } from './RichTextDisplay';
import EventoPortateSection from './EventoPortateSection';

const normalizeStaffIds = (list) => (
    (list || [])
        .map((item) => Number(typeof item === 'object' ? item.id : item))
        .filter((id) => Number.isFinite(id))
);

const staffLabel = (user) => {
    const full = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
    return full || user.username || `Utente #${user.id}`;
};

const EventoSection = ({ evento, isMaster, risorse, onEdit, onDelete, onUpdateEvento, onAddGiorno, onIniziaEvento, onTerminaEvento, onReportRicompense, onRefresh, onRefreshRisorse, risorseLoading = false, onLogout }) => {
    const [showPartecipanti, setShowPartecipanti] = useState(false);
    const [showRicompense, setShowRicompense] = useState(false);
    const [reportLoading, setReportLoading] = useState(false);
    const [reportError, setReportError] = useState('');
    const [reportData, setReportData] = useState(null);
    const [localStaffIds, setLocalStaffIds] = useState([]);
    const [savingStaff, setSavingStaff] = useState(false);

    const allStaff = useMemo(() => risorse.staff || [], [risorse.staff]);
    const allStaffIds = useMemo(() => normalizeStaffIds(allStaff), [allStaff]);

    const serverStaffIds = useMemo(() => {
        const fromRaw = normalizeStaffIds(evento?.staff_assegnato);
        const fromDetails = normalizeStaffIds(evento?.staff_details);
        return fromRaw.length > 0 ? fromRaw : fromDetails;
    }, [evento?.staff_assegnato, evento?.staff_details]);

    const effectiveStaffIds = useMemo(() => {
        let ids;
        if (serverStaffIds.length === 0 && allStaffIds.length > 0) {
            ids = allStaffIds;
        } else {
            ids = serverStaffIds;
        }
        // Esclude chi non è più staff di campagna (es. Master → Player).
        return ids.filter((id) => allStaffIds.includes(id));
    }, [serverStaffIds, allStaffIds]);

    useEffect(() => {
        if (!savingStaff) {
            setLocalStaffIds(effectiveStaffIds);
        }
    }, [effectiveStaffIds, savingStaff, evento?.id]);

    // Filtriamo i personaggi per mostrare solo i GIOCANTI (flag giocante: true) per le iscrizioni (Memoized)
    const personaggiGiocanti = useMemo(() => 
        risorse.png?.filter(p => p.giocante === true) || [], 
        [risorse.png]
    );

    const fmtIscrizioneDt = useCallback((iso) => {
        if (!iso) return null;
        try {
            return new Date(iso).toLocaleString('it-IT', { dateStyle: 'short', timeStyle: 'short' });
        } catch {
            return String(iso);
        }
    }, []);

    const handleListChange = useCallback(async (fieldName, targetId, action) => {
        if (!evento) return;
        let currentList = evento[fieldName] || [];
        const currentIds = normalizeStaffIds(currentList);

        let newIds;
        const targetIdInt = parseInt(targetId, 10);

        if (action === 'add') {
            if (currentIds.includes(targetIdInt)) return;
            newIds = [...currentIds, targetIdInt];
        } else {
            newIds = currentIds.filter((id) => id !== targetIdInt);
        }

        await onUpdateEvento(evento.id, { [fieldName]: newIds });
    }, [evento, onUpdateEvento]);

    const handleStaffToggle = useCallback(async (userId, checked) => {
        if (!evento) return;
        const id = Number(userId);
        if (!Number.isFinite(id)) return;

        const previousIds = localStaffIds;
        const newIds = checked
            ? [...new Set([...localStaffIds, id])]
            : localStaffIds.filter((staffId) => staffId !== id);

        setLocalStaffIds(newIds);
        setSavingStaff(true);
        try {
            await onUpdateEvento(evento.id, { staff_assegnato: newIds });
        } catch (e) {
            setLocalStaffIds(previousIds);
            console.error(e);
        } finally {
            setSavingStaff(false);
        }
    }, [evento, localStaffIds, onUpdateEvento]);

    const handleLoadReport = useCallback(async () => {
        if (!onReportRicompense) return;
        setReportError('');
        setReportLoading(true);
        try {
            const data = await onReportRicompense();
            setReportData(data || null);
            setShowRicompense(true);
        } catch (e) {
            setReportError(e?.message || 'Errore caricamento report ricompense');
        } finally {
            setReportLoading(false);
        }
    }, [onReportRicompense]);

    if (!evento) return null;

    return (
        <div className="bg-indigo-900/10 border-b border-gray-800 p-6 space-y-6 shadow-inner">
            {/* Header Evento */}
            <div className="flex flex-col md:flex-row justify-between items-start gap-4">
                <div className="space-y-1">
                    <div className="flex items-center gap-3">
                        <h1 className="text-3xl font-black uppercase text-white tracking-tighter">{evento.titolo}</h1>
                        {isMaster && (
                            <button onClick={() => onEdit('evento', evento)} className="p-1.5 bg-gray-800 rounded-lg text-indigo-400 hover:text-white transition-colors">
                                <Edit2 size={18}/>
                            </button>
                        )}
                    </div>
                    
                    <div className="flex flex-wrap gap-4 text-[10px] font-bold uppercase text-gray-400 italic">
                        <span className="flex items-center gap-1"><MapPin size={12} className="text-indigo-400"/> {evento.luogo || 'Senza luogo'}</span>
                        <span className="flex items-center gap-1"><Calendar size={12} className="text-indigo-400"/> {new Date(evento.data_inizio).toLocaleDateString()}</span>
                        <span className="text-indigo-400 flex items-center gap-1">
                            <Star size={12} /> Premio iscritti: {evento.pc_guadagnati ?? 1} PC ·{' '}
                            {Number(evento.crediti_base_inizio_evento ?? 0).toLocaleString('it-IT', {
                                minimumFractionDigits: 0,
                                maximumFractionDigits: 2,
                            })}{' '}
                            CR base
                        </span>
                        <span className={evento.started_at && !evento.ended_at ? "text-amber-300" : "text-gray-500"}>
                            Stato: {evento.started_at && !evento.ended_at ? "IN CORSO" : "NON INIZIATO"}
                        </span>
                    </div>
                    {(evento.iscrizione_apertura ||
                        evento.iscrizione_chiusura ||
                        Number(evento.iscrizione_costo_euro) > 0 ||
                        evento.iscrizione_test_attiva) && (
                        <div className="mt-2 rounded-lg border border-indigo-800/50 bg-indigo-950/25 px-3 py-2 text-[11px] text-indigo-100/95 normal-case font-medium not-italic">
                            <span className="inline-flex items-center gap-1.5 font-black uppercase text-[10px] text-indigo-300 tracking-wide">
                                <Ticket size={12} aria-hidden />
                                Iscrizione PayPal
                            </span>
                            <div className="mt-1.5 flex flex-col gap-0.5 text-gray-300">
                                <span>
                                    Finestra:{' '}
                                    {fmtIscrizioneDt(evento.iscrizione_apertura) || '—'} →{' '}
                                    {fmtIscrizioneDt(evento.iscrizione_chiusura) || '—'}
                                </span>
                                <span>
                                    Costo base: {Number(evento.iscrizione_costo_euro || 0).toFixed(2)} €
                                </span>
                                {Array.isArray(evento.iscrizione_opzioni) && evento.iscrizione_opzioni.length > 0 && (
                                    <ul className="mt-1 space-y-0.5 list-disc pl-4">
                                        {evento.iscrizione_opzioni.map((op) => (
                                            <li key={op.sync_id}>
                                                {op.nome}: {Number(op.costo_euro || 0).toFixed(2)} €
                                                {!op.scelta_giocatore ? ' (automatica)' : null}
                                                {op.obbligatoria && op.scelta_giocatore ? ' (obbligatoria)' : null}
                                                {op.posti_limite != null ? ` · max ${op.posti_limite} posti` : null}
                                            </li>
                                        ))}
                                    </ul>
                                )}
                                {evento.iscrizione_test_attiva ? (
                                    <span className="text-amber-300 font-semibold">Modalità test attiva (solo staff campagna principale)</span>
                                ) : null}
                            </div>
                        </div>
                    )}
                </div>

                {isMaster && (
                    <div className="flex gap-2">
                        {!evento.started_at || evento.ended_at ? (
                            <button
                                onClick={onIniziaEvento}
                                className="px-4 py-2 bg-amber-600 text-white rounded-lg text-xs font-black uppercase shadow-lg hover:bg-amber-500 transition-all"
                            >
                                Inizia evento
                            </button>
                        ) : (
                            <button
                                onClick={onTerminaEvento}
                                className="px-4 py-2 bg-rose-700 text-white rounded-lg text-xs font-black uppercase shadow-lg hover:bg-rose-600 transition-all"
                            >
                                Termina evento
                            </button>
                        )}
                        <button
                            onClick={handleLoadReport}
                            className="px-4 py-2 bg-indigo-700 text-white rounded-lg text-xs font-black uppercase shadow-lg hover:bg-indigo-600 transition-all"
                        >
                            Report ricompense
                        </button>
                        <button onClick={onAddGiorno} className="px-4 py-2 bg-emerald-600 text-white rounded-lg text-xs font-black uppercase shadow-lg hover:bg-emerald-500 transition-all">
                            + Giorno
                        </button>
                        <button onClick={() => onDelete(evento.id)} className="p-2 bg-red-900/20 text-red-500 border border-red-900/30 rounded-lg hover:bg-red-600 hover:text-white transition-all">
                            <Trash2 size={20}/>
                        </button>
                    </div>
                )}
            </div>

            {isMaster && (
                <div className="rounded-lg border border-indigo-900/50 bg-gray-950/40 p-3 space-y-2">
                    <button
                        onClick={() => setShowRicompense((v) => !v)}
                        className="w-full text-left text-[11px] font-black uppercase text-indigo-300 tracking-wide"
                    >
                        {showRicompense ? 'Nascondi report ricompense' : 'Mostra report ricompense'}
                    </button>
                    {reportLoading ? <p className="text-xs text-gray-400">Caricamento report…</p> : null}
                    {reportError ? <p className="text-xs text-red-300">{reportError}</p> : null}
                    {showRicompense && reportData?.ricompense?.length ? (
                        <div className="space-y-2 max-h-64 overflow-y-auto pr-1">
                            {reportData.ricompense.map((r) => (
                                <div key={r.personaggio_id} className="rounded border border-gray-800 bg-gray-900/80 p-2">
                                    <div className="flex items-center justify-between text-xs">
                                        <span className="font-bold text-white">{r.personaggio_nome}</span>
                                        <span className={r.premio_gia_assegnato ? 'text-emerald-300' : 'text-amber-300'}>
                                            {r.premio_gia_assegnato ? 'Assegnato' : 'Non assegnato'}
                                        </span>
                                    </div>
                                    <div className="mt-1 text-[11px] text-gray-300">
                                        PC: {r.pc_evento} · Base evento: {Number(r.base_evento || 0).toLocaleString('it-IT')} CR ·
                                        Bonus: {Number(r.bonus_totale || 0).toLocaleString('it-IT')} CR ·
                                        Totale: {Number(r.totale_crediti || 0).toLocaleString('it-IT')} CR
                                    </div>
                                    {Array.isArray(r.righe_membership) && r.righe_membership.length > 0 ? (
                                        <div className="mt-1 text-[10px] text-gray-400 space-y-0.5">
                                            {r.righe_membership.map((m) => (
                                                <div key={m.membership_id}>
                                                    {m.carriera_nome}
                                                    {m.carica_nome ? ` / ${m.carica_nome}` : ''}: +{Number(m.totale_riga || 0).toLocaleString('it-IT')} CR
                                                </div>
                                            ))}
                                        </div>
                                    ) : null}
                                </div>
                            ))}
                        </div>
                    ) : null}
                </div>
            )}

            {evento.sinossi ? (
                <div className="text-gray-300 text-sm italic border-l-2 border-indigo-500 pl-4 bg-indigo-500/5 py-2 ql-editor-view">
                    <RichTextViewer content={evento.sinossi} />
                </div>
            ) : null}

            {/* SEZIONE STAFF (Sempre visibile) */}
            <div className="space-y-3 pt-2">
                <div className="flex items-center justify-between gap-2">
                    <div className="flex items-center gap-2 text-[10px] font-black text-indigo-400 uppercase tracking-widest">
                        <ShieldCheck size={14}/> Staff presente all&apos;evento
                    </div>
                    {onRefreshRisorse ? (
                        <button
                            type="button"
                            onClick={() => onRefreshRisorse()}
                            disabled={risorseLoading}
                            className="inline-flex items-center gap-1 rounded px-2 py-1 text-[10px] font-bold uppercase text-indigo-300 hover:bg-indigo-900/40 disabled:opacity-50"
                            title="Aggiorna elenco staff da campagna"
                        >
                            <RefreshCw size={12} className={risorseLoading ? 'animate-spin' : ''} />
                            Aggiorna lista
                        </button>
                    ) : null}
                </div>
                <p className="text-[10px] text-gray-500 normal-case font-medium">
                    {isMaster
                        ? 'Spunta i membri staff presenti. Di default tutti risultano selezionati.'
                        : 'Elenco staff assegnato a questo evento.'}
                    {savingStaff ? ' · Salvataggio…' : null}
                </p>
                {allStaff.length === 0 ? (
                    <p className="text-[11px] text-gray-500 italic">Nessun membro staff disponibile.</p>
                ) : (
                    <ul className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2 max-h-56 overflow-y-auto pr-1 custom-scrollbar">
                        {allStaff.map((user) => {
                            const userId = Number(user.id);
                            const checked = localStaffIds.includes(userId);
                            return (
                                <li key={user.id}>
                                    <label
                                        className={`flex items-center gap-2 rounded-lg border px-3 py-2 text-[11px] transition-colors ${
                                            checked
                                                ? 'border-indigo-500/40 bg-indigo-900/25 text-indigo-100'
                                                : 'border-gray-800 bg-gray-900/40 text-gray-400'
                                        } ${!isMaster || savingStaff ? 'cursor-default' : 'cursor-pointer hover:border-indigo-500/30'}`}
                                    >
                                        <input
                                            type="checkbox"
                                            className="rounded border-gray-600 text-indigo-500 focus:ring-indigo-500"
                                            checked={checked}
                                            disabled={!isMaster || savingStaff}
                                            onChange={(e) => handleStaffToggle(user.id, e.target.checked)}
                                        />
                                        <span className="font-semibold truncate">{staffLabel(user)}</span>
                                        {user.username && staffLabel(user) !== user.username ? (
                                            <span className="text-[10px] text-gray-500 truncate">@{user.username}</span>
                                        ) : null}
                                    </label>
                                </li>
                            );
                        })}
                    </ul>
                )}
            </div>

            <EventoPortateSection
                evento={evento}
                isMaster={isMaster}
                onRefresh={onRefresh}
                onLogout={onLogout}
            />

            {/* SEZIONE PARTECIPANTI (Collassabile) */}
            <div className="border-t border-gray-800/50 pt-4">
                <button 
                    onClick={() => setShowPartecipanti(!showPartecipanti)}
                    className="flex items-center justify-between w-full text-[10px] font-black text-gray-500 uppercase tracking-widest hover:text-gray-300 transition-colors"
                >
                    <div className="flex items-center gap-2">
                        <Users size={14}/> Partecipanti ({evento.partecipanti?.length || 0})
                    </div>
                    {showPartecipanti ? <ChevronUp size={16}/> : <ChevronDown size={16}/>}
                </button>

                {showPartecipanti && (
                    <div className="mt-4 space-y-4 animate-in fade-in slide-in-from-top-1 duration-200">
                        <div className="flex flex-wrap gap-2">
                            {evento.partecipanti_details?.map(char => (
                                <div key={char.id} className="flex items-center gap-2 bg-gray-800 border border-gray-700 px-2 py-1 rounded text-[11px]">
                                    <span>{char.nome}</span>
                                    {isMaster && (
                                        <button onClick={() => handleListChange('partecipanti', char.id, 'remove')} className="text-gray-500 hover:text-red-500">
                                            <X size={12}/>
                                        </button>
                                    )}
                                </div>
                            ))}
                        </div>

                        {isMaster && (
                            <div className="flex items-center gap-2 bg-gray-950/50 p-3 rounded-xl border border-gray-800">
                                <UserPlus size={14} className="text-emerald-500"/>
                                <select 
                                    className="bg-transparent text-[11px] text-gray-400 outline-none flex-1"
                                    onChange={(e) => {
                                        if(e.target.value) handleListChange('partecipanti', e.target.value, 'add');
                                        e.target.value = "";
                                    }}
                                >
                                    <option value="">Iscrivi un Personaggio Giocante...</option>
                                    {personaggiGiocanti.map(p => (
                                        <option key={p.id} value={p.id}>{p.nome}</option>
                                    ))}
                                </select>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default memo(EventoSection);