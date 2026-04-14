import React, { useState, useEffect, useCallback, memo, useMemo } from 'react';
import { Loader2 } from 'lucide-react';
import MasterGenericList from './MasterGenericList';
import TabellaEditor from './TabellaEditor';
import { getTiers, createTier, updateTier, deleteTier, updateTierAbilita } from '../../api';

const TabellaManager = ({ onLogout }) => {
    const [tiers, setTiers] = useState([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isEditing, setIsEditing] = useState(false);
    const [currentTier, setCurrentTier] = useState(null);
    const [editorStatus, setEditorStatus] = useState({ type: 'success', message: '' });
    
    // RIMOSSO: const token = localStorage.getItem('access_token'); 
    // fetchAuthenticated gestisce il token internamente ('kor35_token')

    const fetchTiers = useCallback(async () => {
        setIsLoading(true);
        try {
            // CORRETTO: Passiamo onLogout, non il token
            const data = await getTiers(onLogout);
            setTiers(data);
        } catch (error) {
            console.error("Errore fetch tiers", error);
            // Se l'errore è gestito da fetchAuthenticated, onLogout potrebbe essere già stato chiamato
        } finally {
            setIsLoading(false);
        }
    }, [onLogout]);

    useEffect(() => {
        fetchTiers();
    }, [fetchTiers]);

    const handleCreate = useCallback(() => {
        setCurrentTier(null);
        setIsEditing(true);
    }, []);

    const handleEdit = useCallback((tier) => {
        setCurrentTier(tier);
        setIsEditing(true);
    }, []);

    const handleDelete = useCallback(async (id) => {
        try {
            await deleteTier(id, onLogout);
            setTiers(prev => prev.filter(t => t.id !== id));
        } catch (error) {
            alert("Errore durante l'eliminazione");
        }
    }, [onLogout]);

    const handleSave = useCallback(async (formData, connectedSkills, mode = 'save_close') => {
        try {
            let savedTier;
            const isSaveAsNew = mode === 'save_as_new';
            const isExisting = !!currentTier?.id && !isSaveAsNew;
            if (isExisting) {
                // Update Base Info
                savedTier = await updateTier(currentTier.id, formData, onLogout);
                // Update Skills Relation
                await updateTierAbilita(currentTier.id, connectedSkills, onLogout);
            } else {
                // Create
                savedTier = await createTier(formData, onLogout);
                // Update Skills Relation (ora che abbiamo l'ID)
                await updateTierAbilita(savedTier.id, connectedSkills, onLogout);
            }

            await fetchTiers(); // Ricarica per avere i dati aggiornati
            const recordName = savedTier?.nome || formData.nome || 'Record';
            if (mode === 'save_as_new') setEditorStatus({ type: 'success', message: `Nuovo record "${recordName}" inserito.` });
            if (mode === 'save_continue') setEditorStatus({ type: 'success', message: `"${recordName}" salvato.` });
            if (mode === 'save_new_blank') {
                setCurrentTier(null);
                setEditorStatus({ type: 'success', message: `"${recordName}" salvato. Pronto per un nuovo inserimento.` });
            }
            if (mode === 'save_close') {
                setIsEditing(false);
                setCurrentTier(null);
                setEditorStatus({ type: 'success', message: '' });
            } else if (savedTier?.id) {
                setCurrentTier(savedTier);
            }
        } catch (error) {
            console.error("Errore salvataggio", error);
            setEditorStatus({ type: 'error', message: `Errore salvataggio: ${error.message || 'Errore sconosciuto'}` });
            alert("Errore durante il salvataggio: " + error.message);
        }
    }, [currentTier, onLogout, fetchTiers]);

    const handleCancel = useCallback(() => {
        setIsEditing(false);
        setCurrentTier(null);
        setEditorStatus({ type: 'success', message: '' });
    }, []);

    if (isEditing) {
        return (
            <div className="h-full p-4 animate-in fade-in slide-in-from-bottom-4">
                <TabellaEditor 
                    tier={currentTier} 
                    onSave={handleSave} 
                    onCancel={handleCancel} 
                    onLogout={onLogout} // Passiamo onLogout anche all'editor
                    statusMessage={editorStatus.message}
                    statusType={editorStatus.type}
                />
            </div>
        );
    }

    const tierTypeLabels = {
        G0: 'Tabelle Generali',
        T1: 'Tier 1',
        T2: 'Tier 2',
        T3: 'Tier 3',
        T4: 'Tier 4',
    };

    const columns = useMemo(() => [
        { header: 'Nome', render: (t) => <span className="font-bold">{t.nome}</span> },
        { header: 'Tipo', render: (t) => tierTypeLabels[t.tipo] || t.tipo, width: 180 },
        { header: 'Abilita', render: (t) => t.abilita_count || 0, align: 'center', width: 100 },
        { header: 'Descrizione', render: (t) => <span className="text-gray-300">{(t.descrizione || '').replace(/<[^>]+>/g, '').slice(0, 90)}{(t.descrizione || '').length > 90 ? '...' : ''}</span> },
    ], []);

    const filterConfig = useMemo(() => ([
        {
            key: 'tipo',
            label: 'Tipo',
            options: [
                { id: 'G0', label: 'Tabelle Generali' },
                { id: 'T1', label: 'Tier 1' },
                { id: 'T2', label: 'Tier 2' },
                { id: 'T3', label: 'Tier 3' },
                { id: 'T4', label: 'Tier 4' },
            ],
        },
    ]), []);

    return (
        <div className="flex flex-col h-full bg-gray-900">
            <div className="flex-1 overflow-y-auto custom-scrollbar relative">
                {isLoading ? (
                    <div className="absolute inset-0 flex items-center justify-center">
                        <Loader2 size={40} className="text-indigo-500 animate-spin" />
                    </div>
                ) : (
                    <div className="h-full p-4">
                        <MasterGenericList
                            title="Gestione Tabelle (Tier)"
                            items={tiers}
                            columns={columns}
                            onAdd={handleCreate}
                            onEdit={handleEdit}
                            onDelete={handleDelete}
                            addLabel="Nuova Tabella"
                            filterConfig={filterConfig}
                            emptyMessage="Nessuna tabella presente."
                            persistKey="gestione-tabelle"
                            loading={isLoading}
                        />
                    </div>
                )}
            </div>
        </div>
    );
};

export default memo(TabellaManager);