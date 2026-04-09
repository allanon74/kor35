import React, { useState, useEffect, useMemo } from 'react'; // <--- Aggiungi useMemo
import { staffGetMostriTemplates, staffDeleteMostroTemplate } from '../../api'; 
import MasterGenericList from './MasterGenericList';
import { Heart, Shield, Layout } from 'lucide-react';

const MostroList = ({ onAdd, onEdit, onLogout }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = () => {
        setLoading(true);
        if (typeof staffGetMostriTemplates === 'function') {
            staffGetMostriTemplates(onLogout)
                .then(data => {
                    console.log("DEBUG MOSTRI:", data);
                    if (data && data.results && Array.isArray(data.results)) {
                        setItems(data.results);
                    } else if (Array.isArray(data)) {
                        setItems(data);
                    } else {
                        setItems([]);
                    }
                })
                .catch(err => {
                    console.error("Errore fetch mostri:", err);
                    setItems([]);
                })
                .finally(() => setLoading(false));
        } else {
            setLoading(false);
        }
    };

    useEffect(() => { loadData(); }, []);

    // --- CORREZIONE: Avvolgi columns in useMemo ---
    const columns = useMemo(() => [
        { 
            header: 'Nome Template', 
            render: (item) => (
                <span className="font-bold text-lg text-red-400">{item.nome}</span>
            )
        },
        { 
            header: 'Stats Base', 
            width: '200px',
            render: (item) => (
                <div className="flex gap-3 text-sm font-mono">
                    <span className="flex items-center gap-1 text-red-500" title="PV"><Heart size={12} fill="currentColor"/> {item.punti_vita_base}</span>
                    <span className="flex items-center gap-1 text-gray-400" title="Armatura"><Shield size={12}/> {item.armatura_base}</span>
                    <span className="flex items-center gap-1 text-indigo-400" title="Guscio"><Layout size={12}/> {item.guscio_base}</span>
                </div>
            )
        },
        {
            header: 'Attacchi',
            render: (item) => (
                <span className="text-xs text-gray-500">
                    {item.attacchi ? item.attacchi.length : 0} attacchi definiti
                </span>
            )
        }
    ], []); // Dipendenze vuote perché le colonne sono statiche
    // ----------------------------------------------

    const sortLogic = (a, b) => a.nome.localeCompare(b.nome);

    const handleDelete = (id) => {
        if (window.confirm("Sei sicuro di voler eliminare definitivamente questo template di mostro?")) {
            if (typeof staffDeleteMostroTemplate === 'function') {
                staffDeleteMostroTemplate(id, onLogout).then(loadData);
            }
        }
    };

    return (
        <MasterGenericList 
            title="Database Template Mostri"
            items={items}
            columns={columns}
            sortLogic={sortLogic}
            onAdd={onAdd} 
            onEdit={onEdit} 
            onDelete={handleDelete}
            loading={loading}
            addLabel="Nuovo Mostro"
        />
    );
};

export default MostroList;