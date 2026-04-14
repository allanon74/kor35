import React, { useState, useEffect } from 'react';
import { staffGetOggettiBase, staffDeleteOggettoBase, staffGetClassiOggetto } from '../../api';
import MasterGenericList from './MasterGenericList';

const TIPO_OGGETTO_CHOICES = [
    { id: 'FIS', nome: 'Fisico' },
    { id: 'MAT', nome: 'Materia' },
    { id: 'MOD', nome: 'Mod' },
    { id: 'INN', nome: 'Innesto' },
    { id: 'MUT', nome: 'Mutazione' },
    { id: 'AUM', nome: 'Aumento' },
    { id: 'POT', nome: 'Potenziamento' },
];

const OggettoBaseList = ({ onAdd, onEdit, onScanQr, onLogout }) => {
    const [items, setItems] = useState([]);
    const [classi, setClassi] = useState([]);
    const [loading, setLoading] = useState(true);

    const loadData = () => {
        setLoading(true);
        // Carichiamo sia i template che le classi per i filtri
        Promise.all([
            staffGetOggettiBase(onLogout),
            staffGetClassiOggetto(onLogout)
        ]).then(([data, cData]) => {
            setItems(data || []);
            setClassi(cData || []);
        }).finally(() => setLoading(false));
    };

    useEffect(() => { loadData(); }, []);

    // MODIFICA QUI: Rimossa la configurazione per 'tipo_oggetto'
    const filterConfig = [
        {
            key: 'classe_oggetto',
            label: 'Classe',
            type: 'button',
            options: classi.map(c => ({ id: c.id, label: c.nome }))
        }
    ];

    const columns = [
        { 
            header: 'Classe', 
            width: '120px',
            render: (item) => {
                const classeNome = item.classe_oggetto_nome
                    || item?.classe_oggetto?.nome
                    || classi.find((c) => String(c.id) === String(item.classe_oggetto))?.nome
                    || '—';
                return <span className="font-bold text-blue-400 text-xs">{classeNome}</span>;
            }
        },
        { 
            header: 'Tipo', 
            width: '100px',
            render: (item) => (
                <span className="text-[10px] bg-gray-900 border border-gray-700 px-2 py-0.5 rounded font-black text-gray-500">
                    {TIPO_OGGETTO_CHOICES.find(c => c.id === item.tipo_oggetto)?.nome || item.tipo_oggetto}
                </span>
            )
        },
        { 
            header: 'Nome Template', 
            render: (item) => (
                <div className="flex items-center gap-2">
                    <span className="font-bold text-white">{item.nome}</span>
                    {item.is_pesante && (
                        <span className="bg-red-900/30 text-red-500 text-[8px] px-1 border border-red-900 rounded font-black">PESANTE</span>
                    )}
                    {item.is_tecnologico && (
                        <span className="bg-amber-900/30 text-amber-300 text-[8px] px-1 border border-amber-700/60 rounded font-black">TECNOLOGICO</span>
                    )}
                    {!item.in_vendita && (
                        <span className="bg-gray-700 text-gray-400 text-[8px] px-1 rounded font-black italic uppercase">Off-List</span>
                    )}
                </div>
            ) 
        },
        {
            header: 'Costo',
            width: '100px',
            align: 'right',
            render: (item) => <span className="font-mono text-emerald-400 font-bold">{item.costo} <small className="text-[10px] text-gray-500">CR</small></span>
        }
    ];

    const sortLogic = (a, b) => {
        // Ordiniamo prima per Classe e poi per Nome
        const classA = a.classe_oggetto_nome
            || a?.classe_oggetto?.nome
            || classi.find((c) => String(c.id) === String(a.classe_oggetto))?.nome
            || "";
        const classB = b.classe_oggetto_nome
            || b?.classe_oggetto?.nome
            || classi.find((c) => String(c.id) === String(b.classe_oggetto))?.nome
            || "";
        if (classA !== classB) {
            return classA.localeCompare(classB);
        }
        return a.nome.localeCompare(b.nome);
    };

    const handleDelete = (id) => {
        staffDeleteOggettoBase(id, onLogout).then(loadData);
    };

    return (
        <MasterGenericList 
            title="Listino Oggetti Base (Template)"
            items={items}
            columns={columns}
            filterConfig={filterConfig}
            sortLogic={sortLogic}
            onAdd={onAdd} 
            onEdit={onEdit} 
            onScanQr={onScanQr}
            onDelete={handleDelete}
            loading={loading}
            addLabel="Nuovo Template"
            emptyMessage="Usa i filtri sopra per sfogliare il listino oggetti base."
        />
    );
};

export default OggettoBaseList;