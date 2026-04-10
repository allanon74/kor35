import React, { useState, useEffect } from 'react';
import { staffGetWikiImages, deleteWikiImage, getMediaUrl } from '../../api';
import MasterGenericList from './MasterGenericList';

const ALLINEAMENTO_CHOICES = [
    { id: 'left', nome: 'Sinistra' },
    { id: 'center', nome: 'Centro' },
    { id: 'right', nome: 'Destra' },
    { id: 'full', nome: 'Larghezza piena' },
];

const ImmagineList = ({ onAdd, onEdit, onLogout }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = () => {
        setLoading(true);
        staffGetWikiImages(onLogout)
            .then(data => {
                console.log("Dati immagini ricevuti:", data);
                setItems(data || []);
            })
            .catch(err => {
                console.error("Errore caricamento immagini:", err);
                alert("Errore durante il caricamento delle immagini: " + err.message);
            })
            .finally(() => setLoading(false));
    };

    useEffect(() => { 
        loadData(); 
    }, [onLogout]);

    const filterConfig = [
        {
            key: 'allineamento',
            label: 'Allineamento',
            type: 'button',
            options: ALLINEAMENTO_CHOICES
        }
    ];

    const columns = [
        { 
            header: 'Anteprima', 
            width: '120px',
            align: 'center',
            render: (item) => (
                item.immagine ? (
                    <div className="flex justify-center">
                        <img 
                            src={getMediaUrl(item.immagine)} 
                            alt={item.titolo || 'Immagine'}
                            className="w-20 h-20 object-cover rounded border border-gray-700"
                        />
                    </div>
                ) : (
                    <span className="text-gray-600 text-xs">Nessuna</span>
                )
            )
        },
        { 
            header: 'Titolo', 
            render: (item) => (
                <div className="flex flex-col">
                    <span className="font-bold text-cyan-50">{item.titolo || '(Senza titolo)'}</span>
                    {item.descrizione && (
                        <span className="text-[9px] text-gray-500 line-clamp-2" dangerouslySetInnerHTML={{ __html: item.descrizione }} />
                    )}
                </div>
            )
        },
        { 
            header: 'Allineamento', 
            width: '120px',
            render: (item) => (
                <span className="text-[10px] bg-gray-900 border border-gray-700 px-2 py-0.5 rounded font-black text-gray-400">
                    {ALLINEAMENTO_CHOICES.find(c => c.id === item.allineamento)?.nome || item.allineamento}
                </span>
            )
        },
        { 
            header: 'Larghezza Max', 
            width: '100px',
            align: 'center',
            render: (item) => (
                <span className="text-xs text-gray-400">
                    {item.larghezza_max > 0 ? `${item.larghezza_max}px` : 'Originale'}
                </span>
            )
        }
    ];

    const sortLogic = (a, b) => {
        // Ordina per data creazione (più recenti prima)
        const dateA = new Date(a.data_creazione || 0);
        const dateB = new Date(b.data_creazione || 0);
        return dateB - dateA;
    };

    const handleDelete = (id) => {
        if (window.confirm("Sei sicuro di voler eliminare definitivamente questa immagine?")) {
            deleteWikiImage(id, onLogout)
                .then(() => {
                    loadData();
                })
                .catch(err => {
                    console.error("Errore eliminazione immagine:", err);
                    alert("Errore durante l'eliminazione: " + err.message);
                });
        }
    };

    return (
        <MasterGenericList 
            title="Immagini Wiki"
            items={items}
            columns={columns}
            filterConfig={filterConfig}
            sortLogic={sortLogic}
            onAdd={onAdd} 
            onEdit={onEdit} 
            onDelete={handleDelete}
            loading={loading}
            addLabel="Carica Immagine"
            emptyMessage="Nessuna immagine trovata. Clicca su 'Carica Immagine' per aggiungerne una."
        />
    );
};

export default ImmagineList;
