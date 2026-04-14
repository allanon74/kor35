import React, { useState, useEffect, useCallback } from 'react';
import { staffGetAbilitaList, staffDeleteAbilita, prefetchAbilitaEditorResources } from '../../api';
import MasterGenericList from './MasterGenericList';
import { useCharacter } from '../CharacterContext';

const AbilitaList = ({ onAdd, onEdit, onLogout }) => {
    const { punteggiList } = useCharacter();
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const [page, setPage] = useState(1);
    const [totalCount, setTotalCount] = useState(0);
    const [pageSize] = useState(50);
    const [hasNext, setHasNext] = useState(false);
    const [hasPrev, setHasPrev] = useState(false);
    const [query, setQuery] = useState({ search: '', isTrattoAura: undefined });

    const handleServerQueryChange = useCallback(({ search, activeFilters }) => {
        const types = activeFilters.is_tratto_aura || [];
        let isTrattoAura;
        if (types.length === 1) {
            isTrattoAura = types[0];
        }
        const s = (search || '').trim();
        setQuery((prev) => {
            if (prev.search === s && prev.isTrattoAura === isTrattoAura) {
                return prev;
            }
            setPage(1);
            return { search: s, isTrattoAura };
        });
    }, []);

    useEffect(() => {
        prefetchAbilitaEditorResources(onLogout).catch((error) => {
            console.warn('Prefetch risorse editor abilita fallito', error);
        });
    }, [onLogout]);

    useEffect(() => {
        let cancelled = false;
        (async () => {
            setLoading(true);
            try {
                const data = await staffGetAbilitaList(onLogout, {
                    page,
                    pageSize,
                    search: query.search || undefined,
                    isTrattoAura: query.isTrattoAura,
                });
                if (cancelled) return;

                if (Array.isArray(data)) {
                    setItems(data || []);
                    setTotalCount(data?.length || 0);
                    setHasNext(false);
                    setHasPrev(false);
                } else {
                    setItems(data?.results || []);
                    setTotalCount(data?.count || 0);
                    setHasNext(Boolean(data?.next));
                    setHasPrev(Boolean(data?.previous));
                }
            } catch (error) {
                if (!cancelled) {
                    console.error('Errore caricamento abilità:', error);
                }
            } finally {
                if (!cancelled) {
                    setLoading(false);
                }
            }
        })();
        return () => {
            cancelled = true;
        };
    }, [onLogout, page, pageSize, query.search, query.isTrattoAura]);

    const handleDelete = async (id) => {
        try {
            await staffDeleteAbilita(id, onLogout);
            setItems((prev) => prev.filter((item) => item.id !== id));
            setTotalCount((prev) => Math.max(0, prev - 1));
        } catch (error) {
            console.error("Errore durante l'eliminazione:", error);
        }
    };

    const columns = [
        { key: 'nome', header: 'Nome', width: '30%', render: (row) => <span className="font-bold text-white">{row.nome}</span> },
        { key: 'costo_pc', header: 'Costo PC', width: '15%', align: 'center', render: (row) => row.costo_pc },
        { key: 'costo_crediti', header: 'Crediti', width: '15%', align: 'center', render: (row) => row.costo_crediti },
        {
            key: 'tipo',
            header: 'Tipo',
            width: '20%',
            align: 'center',
            render: (row) => {
                const auraId = row?.aura_riferimento?.id ?? row?.aura_riferimento ?? null;
                const auraObj = row?.aura_riferimento?.id
                    ? row.aura_riferimento
                    : punteggiList.find((p) => String(p.id) === String(auraId));
                return row.is_tratto_aura ?
                <span className="text-purple-400 text-[10px] font-bold px-2 py-0.5 bg-purple-900/50 rounded border border-purple-500/30 uppercase tracking-wide">
                    AURA {auraObj?.nome || '-'} (Lv.{row.livello_riferimento})
                </span> :
                <span className="text-gray-500 text-xs">-</span>
            }
        }
    ];

    const filterConfig = [
        {
            key: 'is_tratto_aura',
            label: 'Tipo',
            options: [{ id: true, label: 'Tratti Aura' }, { id: false, label: 'Standard' }]
        }
    ];

    return (
        <div className="space-y-3">
            <MasterGenericList
                title="Database Abilità"
                items={items}
                loading={loading}
                onAdd={onAdd}
                onEdit={onEdit}
                onDelete={handleDelete}
                columns={columns}
                filterConfig={filterConfig}
                sortLogic={(a, b) => (a.nome || "").localeCompare(b.nome || "")}
                serverDrivenFiltering
                onServerQueryChange={handleServerQueryChange}
            />
            <div className="flex items-center justify-between text-xs text-gray-400 px-1">
                <span>{`Totale: ${totalCount}`}</span>
                <div className="flex items-center gap-2">
                    <button
                        type="button"
                        disabled={loading || !hasPrev}
                        onClick={() => setPage((p) => Math.max(1, p - 1))}
                        className="px-3 py-1 rounded border border-gray-700 disabled:opacity-40 hover:border-gray-500"
                    >
                        Precedente
                    </button>
                    <span>{`Pagina ${page}`}</span>
                    <button
                        type="button"
                        disabled={loading || !hasNext}
                        onClick={() => setPage((p) => p + 1)}
                        className="px-3 py-1 rounded border border-gray-700 disabled:opacity-40 hover:border-gray-500"
                    >
                        Successiva
                    </button>
                </div>
            </div>
        </div>
    );
};

export default AbilitaList;
