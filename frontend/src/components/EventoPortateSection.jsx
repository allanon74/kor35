import React, { useState, useMemo, useCallback, memo } from 'react';
import { Package, Plus, Trash2, Check, Filter } from 'lucide-react';
import { createVocePortare, updateVocePortare, deleteVocePortare } from '../api';

const FILTER_ALL = 'all';
const FILTER_UNASSIGNED = 'unassigned';

const EventoPortateSection = ({ evento, isMaster, onRefresh, onLogout }) => {
    const [filter, setFilter] = useState(FILTER_ALL);
    const [newDescrizione, setNewDescrizione] = useState('');
    const [newPortatore, setNewPortatore] = useState('');
    const [saving, setSaving] = useState(false);
    const [error, setError] = useState('');

    const currentUserId = useMemo(() => {
        try {
            const userParams = JSON.parse(localStorage.getItem('user'));
            return userParams ? userParams.id : null;
        } catch {
            return null;
        }
    }, []);

    const staffAssegnati = useMemo(
        () => evento.staff_details || [],
        [evento.staff_details],
    );

    const voci = useMemo(
        () => (Array.isArray(evento.voci_portare) ? [...evento.voci_portare] : []),
        [evento.voci_portare],
    );

    const vociFiltrate = useMemo(() => {
        if (filter === FILTER_ALL) return voci;
        if (filter === FILTER_UNASSIGNED) {
            return voci.filter((v) => !v.portatore && v.portatore !== 0);
        }
        const fid = parseInt(filter, 10);
        return voci.filter((v) => v.portatore === fid);
    }, [voci, filter]);

    const canToggleVoce = useCallback(
        (voce) => {
            if (isMaster) return true;
            if (!voce.portatore) return true;
            return String(voce.portatore) === String(currentUserId);
        },
        [isMaster, currentUserId],
    );

    const handleAdd = useCallback(async () => {
        const descrizione = newDescrizione.trim();
        if (!descrizione) return;
        setError('');
        setSaving(true);
        try {
            const payload = {
                evento: evento.id,
                descrizione,
            };
            if (newPortatore) {
                payload.portatore = parseInt(newPortatore, 10);
            }
            await createVocePortare(payload, onLogout);
            setNewDescrizione('');
            setNewPortatore('');
            onRefresh?.();
        } catch (e) {
            setError(e?.message || 'Errore durante il salvataggio.');
        } finally {
            setSaving(false);
        }
    }, [newDescrizione, newPortatore, evento.id, onLogout, onRefresh]);

    const handleToggle = useCallback(
        async (voce) => {
            if (!canToggleVoce(voce)) return;
            setError('');
            try {
                await updateVocePortare(voce.id, { a_posto: !voce.a_posto }, onLogout);
                onRefresh?.();
            } catch (e) {
                setError(e?.message || 'Errore aggiornamento stato.');
            }
        },
        [canToggleVoce, onLogout, onRefresh],
    );

    const handleAssign = useCallback(
        async (voce, portatoreRaw) => {
            if (!isMaster) return;
            setError('');
            const portatore = portatoreRaw ? parseInt(portatoreRaw, 10) : null;
            try {
                await updateVocePortare(voce.id, { portatore }, onLogout);
                onRefresh?.();
            } catch (e) {
                setError(e?.message || 'Errore aggiornamento assegnazione.');
            }
        },
        [isMaster, onLogout, onRefresh],
    );

    const handleDelete = useCallback(
        async (voceId) => {
            if (!isMaster) return;
            setError('');
            try {
                await deleteVocePortare(voceId, onLogout);
                onRefresh?.();
            } catch (e) {
                setError(e?.message || 'Errore eliminazione voce.');
            }
        },
        [isMaster, onLogout, onRefresh],
    );

    const displayName = (user) => {
        if (!user) return '—';
        const full = [user.first_name, user.last_name].filter(Boolean).join(' ').trim();
        return full || user.username;
    };

    const doneCount = voci.filter((v) => v.a_posto).length;

    return (
        <div className="border-t border-gray-800/50 pt-4 space-y-3">
            <div className="flex flex-wrap items-center justify-between gap-2">
                <div className="flex items-center gap-2 text-[10px] font-black text-indigo-400 uppercase tracking-widest">
                    <Package size={14} />
                    Cose da portare
                    <span className="text-gray-500 font-bold normal-case tracking-normal">
                        ({doneCount}/{voci.length} a posto)
                    </span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px]">
                    <Filter size={12} className="text-gray-500" aria-hidden />
                    <select
                        value={filter}
                        onChange={(e) => setFilter(e.target.value)}
                        className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-gray-300 outline-none focus:border-indigo-500"
                    >
                        <option value={FILTER_ALL}>Tutti</option>
                        <option value={FILTER_UNASSIGNED}>Non assegnate</option>
                        {staffAssegnati.map((s) => (
                            <option key={s.id} value={String(s.id)}>
                                {displayName(s)}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {error ? <p className="text-xs text-red-300">{error}</p> : null}

            <div className="space-y-1.5">
                {vociFiltrate.length === 0 ? (
                    <p className="text-xs text-gray-500 italic py-2">
                        {voci.length === 0
                            ? 'Nessuna voce inserita.'
                            : 'Nessuna voce per il filtro selezionato.'}
                    </p>
                ) : (
                    vociFiltrate.map((voce) => {
                        const mine =
                            voce.portatore &&
                            String(voce.portatore) === String(currentUserId);
                        const toggleOk = canToggleVoce(voce);
                        return (
                            <div
                                key={voce.id}
                                className={`flex flex-wrap items-center gap-2 rounded-lg border px-2 py-1.5 text-[11px] ${
                                    voce.a_posto
                                        ? 'border-emerald-800/60 bg-emerald-950/20'
                                        : mine
                                          ? 'border-amber-700/50 bg-amber-950/15'
                                          : 'border-gray-800 bg-gray-900/50'
                                }`}
                            >
                                <button
                                    type="button"
                                    disabled={!toggleOk}
                                    onClick={() => handleToggle(voce)}
                                    title={
                                        toggleOk
                                            ? voce.a_posto
                                                ? 'Segna come da fare'
                                                : 'Segna a posto'
                                            : 'Solo il master incaricato può segnare questa voce'
                                    }
                                    className={`shrink-0 w-6 h-6 rounded border flex items-center justify-center transition-colors ${
                                        voce.a_posto
                                            ? 'bg-emerald-600 border-emerald-500 text-white'
                                            : 'border-gray-600 text-gray-500 hover:border-indigo-500'
                                    } ${!toggleOk ? 'opacity-40 cursor-not-allowed' : ''}`}
                                >
                                    {voce.a_posto ? <Check size={14} /> : null}
                                </button>

                                <span
                                    className={`flex-1 min-w-[8rem] ${
                                        voce.a_posto ? 'line-through text-gray-500' : 'text-gray-200'
                                    }`}
                                >
                                    {voce.descrizione}
                                </span>

                                {isMaster ? (
                                    <select
                                        value={voce.portatore ?? ''}
                                        onChange={(e) => handleAssign(voce, e.target.value)}
                                        className="bg-gray-950 border border-gray-700 rounded px-1.5 py-0.5 text-[10px] text-gray-300 max-w-[10rem]"
                                    >
                                        <option value="">Non assegnato</option>
                                        {staffAssegnati.map((s) => (
                                            <option key={s.id} value={s.id}>
                                                {displayName(s)}
                                            </option>
                                        ))}
                                    </select>
                                ) : (
                                    <span className="text-[10px] text-indigo-300/90 shrink-0">
                                        {voce.portatore_details
                                            ? displayName(voce.portatore_details)
                                            : 'Non assegnato'}
                                    </span>
                                )}

                                {isMaster ? (
                                    <button
                                        type="button"
                                        onClick={() => handleDelete(voce.id)}
                                        className="text-gray-500 hover:text-red-400 p-0.5"
                                        title="Elimina voce"
                                    >
                                        <Trash2 size={13} />
                                    </button>
                                ) : null}
                            </div>
                        );
                    })
                )}
            </div>

            {isMaster ? (
                <div className="flex flex-wrap items-center gap-2 bg-gray-950/50 p-3 rounded-xl border border-gray-800">
                    <Plus size={14} className="text-emerald-500 shrink-0" />
                    <input
                        type="text"
                        value={newDescrizione}
                        onChange={(e) => setNewDescrizione(e.target.value)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleAdd();
                        }}
                        placeholder="Cosa portare…"
                        className="flex-1 min-w-[10rem] bg-transparent text-[11px] text-gray-200 outline-none placeholder:text-gray-600"
                    />
                    <select
                        value={newPortatore}
                        onChange={(e) => setNewPortatore(e.target.value)}
                        className="bg-gray-900 border border-gray-700 rounded px-2 py-1 text-[10px] text-gray-300"
                    >
                        <option value="">Master (opzionale)</option>
                        {staffAssegnati.map((s) => (
                            <option key={s.id} value={s.id}>
                                {displayName(s)}
                            </option>
                        ))}
                    </select>
                    <button
                        type="button"
                        disabled={saving || !newDescrizione.trim()}
                        onClick={handleAdd}
                        className="px-3 py-1 bg-indigo-700 hover:bg-indigo-600 disabled:opacity-40 text-white rounded text-[10px] font-bold uppercase"
                    >
                        Aggiungi
                    </button>
                </div>
            ) : null}
        </div>
    );
};

export default memo(EventoPortateSection);
