import React, { useState, useEffect, useCallback, memo } from 'react';
import { Sparkles, Plus, RefreshCw } from 'lucide-react';
import { staffGetRisorsePool, staffIncrementaRisorsaPool } from '../api';

const StaffRisorsaPoolTab = ({ onLogout }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [busy, setBusy] = useState({});

    const load = useCallback(async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await staffGetRisorsePool(onLogout);
            setData(res);
        } catch (e) {
            setError(e?.message || 'Errore caricamento');
        } finally {
            setLoading(false);
        }
    }, [onLogout]);

    useEffect(() => {
        load();
    }, [load]);

    const onIncrement = async (personaggioId, sigla) => {
        const key = `${personaggioId}-${sigla}`;
        setBusy((b) => ({ ...b, [key]: true }));
        try {
            await staffIncrementaRisorsaPool(personaggioId, sigla, '', onLogout);
            await load();
        } catch (e) {
            alert(e?.message || 'Errore');
        } finally {
            setBusy((b) => ({ ...b, [key]: false }));
        }
    };

    if (loading && !data) {
        return (
            <div className="flex items-center justify-center h-64 text-gray-400">
                <RefreshCw className="animate-spin w-8 h-8 mr-2" /> Caricamento…
            </div>
        );
    }

    if (error) {
        return (
            <div className="p-6 text-red-400">
                {error}
                <button type="button" onClick={load} className="ml-4 text-indigo-400 underline">
                    Riprova
                </button>
            </div>
        );
    }

    const rows = data?.personaggi || [];
    const statMeta = data?.statistiche || [];

    return (
        <div className="p-4 md:p-8 max-w-6xl mx-auto text-gray-100">
            <div className="flex items-center justify-between mb-6 border-b border-gray-800 pb-4">
                <div className="flex items-center gap-3">
                    <Sparkles className="w-8 h-8 text-amber-400" />
                    <div>
                        <h1 className="text-2xl font-bold">Risorse a pool</h1>
                        <p className="text-sm text-gray-500 mt-1">
                            Personaggi con almeno una statistica configurata come risorsa (es. Fortuna). +1 aumenta il
                            totale attuale senza superare il massimo di scheda.
                        </p>
                    </div>
                </div>
                <button
                    type="button"
                    onClick={load}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-800 hover:bg-gray-700 text-sm"
                >
                    <RefreshCw size={16} /> Aggiorna
                </button>
            </div>

            {statMeta.length === 0 && (
                <p className="text-gray-500 text-sm">
                    Nessuna statistica con flag &quot;Risorsa a pool&quot; nel database. Abilitala su Statistiche (Django
                    admin) per una sigla (es. FRT).
                </p>
            )}

            <div className="overflow-x-auto rounded-xl border border-gray-800">
                <table className="w-full text-sm">
                    <thead className="bg-gray-900/80 text-left text-gray-400 uppercase text-xs">
                        <tr>
                            <th className="p-3">Personaggio</th>
                            <th className="p-3">Risorsa</th>
                            <th className="p-3 text-right">Attuale / Max</th>
                            <th className="p-3 w-32">Azione</th>
                        </tr>
                    </thead>
                    <tbody>
                        {rows.flatMap((pg) =>
                            (pg.pools || []).map((pool) => {
                                const key = `${pg.id}-${pool.sigla}`;
                                const atMax = pool.valore_corrente >= pool.valore_max;
                                return (
                                    <tr key={key} className="border-t border-gray-800 hover:bg-gray-900/40">
                                        <td className="p-3 font-medium">{pg.nome}</td>
                                        <td className="p-3 text-gray-300">
                                            {pool.nome}{' '}
                                            <span className="text-gray-600 font-mono text-xs">({pool.sigla})</span>
                                        </td>
                                        <td className="p-3 text-right font-mono">
                                            {pool.valore_corrente} / {pool.valore_max}
                                        </td>
                                        <td className="p-3">
                                            <button
                                                type="button"
                                                disabled={!!busy[key] || atMax}
                                                onClick={() => onIncrement(pg.id, pool.sigla)}
                                                className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-amber-900/40 hover:bg-amber-800/50 text-amber-200 text-xs font-bold disabled:opacity-40 disabled:cursor-not-allowed"
                                                title={atMax ? 'Già al massimo' : '+1 al totale attuale'}
                                            >
                                                <Plus size={14} /> +1
                                            </button>
                                        </td>
                                    </tr>
                                );
                            })
                        )}
                    </tbody>
                </table>
                {rows.length === 0 && statMeta.length > 0 && (
                    <p className="p-6 text-gray-500 text-center">Nessun personaggio con massimo &gt; 0 sulle risorse pool.</p>
                )}
            </div>
        </div>
    );
};

export default memo(StaffRisorsaPoolTab);
