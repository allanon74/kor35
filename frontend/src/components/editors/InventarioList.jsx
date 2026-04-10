import React, { useState, useEffect } from 'react';
import { staffGetInventari, staffDeleteInventario } from '../../api';
import MasterGenericList from './MasterGenericList';

const InventarioList = ({ onAdd, onEdit, onScanQr, onLogout }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = () => {
        setLoading(true);
        staffGetInventari(onLogout)
            .then(data => setItems(data || []))
            .catch(err => {
                console.error("Errore caricamento inventari:", err);
                alert("Errore durante il caricamento degli inventari: " + err.message);
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => { 
        loadData(); 
    }, [onLogout]);

    const columns = [
        { 
            header: 'Nome', 
            render: (item) => (
                <div className="flex flex-col">
                    <span className="font-bold text-cyan-50">{item.nome || '(Senza nome)'}</span>
                    {item.testo && (
                        <span className="text-[9px] text-gray-500 line-clamp-1">{item.testo}</span>
                    )}
                </div>
            )
        },
        { 
            header: 'Oggetti', 
            width: '100px',
            align: 'center',
            render: (item) => (
                <span className="text-xs text-gray-400">
                    {item.oggetti_count || 0}
                </span>
            )
        },
        { 
            header: 'Tipo', 
            width: '120px',
            render: (item) => (
                <span className="text-[10px] bg-gray-900 border border-gray-700 px-2 py-0.5 rounded font-black text-gray-400">
                    {item.is_personaggio ? 'Personaggio' : 'Inventario'}
                </span>
            )
        }
    ];

    const sortLogic = (a, b) => {
        // Ordina per nome
        return (a.nome || '').localeCompare(b.nome || '');
    };

    const handleDelete = (id) => {
        if (window.confirm("Sei sicuro di voler eliminare definitivamente questo inventario? Gli oggetti verranno messi senza posizione.")) {
            staffDeleteInventario(id, onLogout)
                .then(() => {
                    loadData();
                })
                .catch(err => {
                    console.error("Errore eliminazione inventario:", err);
                    alert("Errore durante l'eliminazione: " + err.message);
                });
        }
    };

    return (
        <MasterGenericList 
            title="Inventari (Non Personaggi)"
            items={items}
            columns={columns}
            sortLogic={sortLogic}
            onAdd={onAdd} 
            onEdit={onEdit} 
            onScanQr={onScanQr}
            onDelete={handleDelete}
            loading={loading}
            addLabel="Crea Inventario"
            emptyMessage="Nessun inventario trovato. Clicca su 'Crea Inventario' per aggiungerne uno."
        />
    );
};

export default InventarioList;
