import React, { useState, useEffect } from 'react';
import { staffGetOggetti, staffDeleteOggetto } from '../../api';
import { useCharacter } from '../CharacterContext';
import MasterGenericList from './MasterGenericList';
import IconaPunteggio from '../IconaPunteggio';

const TIPO_OGGETTO_CHOICES = [
    { id: 'FIS', nome: 'Fisico' },
    { id: 'MAT', nome: 'Materia' },
    { id: 'MOD', nome: 'Mod' },
    { id: 'INN', nome: 'Innesto' },
    { id: 'MUT', nome: 'Mutazione' },
    { id: 'AUM', nome: 'Aumento' },
    { id: 'POT', nome: 'Potenziamento' },
];

const OggettoList = ({ onAdd, onEdit, onScanQr, onLogout }) => {
    const [items, setItems] = useState([]);
    const [loading, setLoading] = useState(true);
    const { punteggiList } = useCharacter();

    const loadData = () => {
        setLoading(true);
        staffGetOggetti(onLogout)
            .then(data => setItems(data || []))
            .finally(() => setLoading(false));
    };

    useEffect(() => { loadData(); }, []);

    const filterConfig = [
        {
            key: 'aura',
            label: 'Aura',
            type: 'icon',
            options: punteggiList.filter(p => p.tipo === 'AU'),
            renderOption: (opt) => (
                <IconaPunteggio url={opt.icona_url} color={opt.colore} size="xs" mode="cerchio_inv" />
            )
        },
        {
            key: 'tipo_oggetto',
            label: 'Tipo',
            type: 'button',
            options: TIPO_OGGETTO_CHOICES
        }
    ];

    const columns = [
        { 
            header: 'Au', 
            width: '50px', 
            align: 'center',
            render: (item) => item.aura ? (
                <IconaPunteggio url={item.aura.icona_url} color={item.aura.colore} size="xs" mode="cerchio_inv" />
            ) : <span className="text-gray-600">—</span>
        },
        { 
            header: 'Tipo', 
            width: '100px',
            render: (item) => (
                <span className="text-[10px] bg-gray-900 border border-gray-700 px-2 py-0.5 rounded font-black text-gray-400">
                    {TIPO_OGGETTO_CHOICES.find(c => c.id === item.tipo_oggetto)?.nome || item.tipo_oggetto}
                </span>
            )
        },
        { 
            header: 'Nome', 
            render: (item) => (
                <div className="flex flex-col">
                    <span className="font-bold text-cyan-50">{item.nome}</span>
                    {item.classe_oggetto_nome && (
                        <span className="text-[9px] text-gray-500 uppercase tracking-tighter">{item.classe_oggetto_nome}</span>
                    )}
                </div>
            )
        }
    ];

    const sortLogic = (a, b) => {
        const auraA = a.aura?.ordine ?? 999;
        const auraB = b.aura?.ordine ?? 999;
        if (auraA !== auraB) return auraA - auraB;
        if (a.tipo_oggetto !== b.tipo_oggetto) return a.tipo_oggetto.localeCompare(b.tipo_oggetto);
        return a.nome.localeCompare(b.nome);
    };

    const handleDelete = (id) => {
        if (window.confirm("Sei sicuro di voler eliminare definitivamente questo oggetto?")) {
            staffDeleteOggetto(id, onLogout).then(loadData);
        }
    };

    return (
        <MasterGenericList 
            title="Istanze Oggetti in Gioco"
            items={items}
            columns={columns}
            filterConfig={filterConfig}
            sortLogic={sortLogic}
            onAdd={onAdd} 
            onEdit={onEdit} 
            onScanQr={onScanQr}
            onDelete={handleDelete}
            loading={loading}
            addLabel="Crea Oggetto"
        />
    );
};

export default OggettoList;