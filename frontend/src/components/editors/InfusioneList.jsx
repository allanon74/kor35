import React, { useState, useEffect } from 'react';
import { PackagePlus } from 'lucide-react';
import { staffGetInfusioni, staffDeleteInfusione } from '../../api';
import MasterTechniqueList from './MasterTechniqueList';

const InfusioneList = ({ onSelect, onNew, onScanQr, onMinigioco, onCreateInstance, onLogout, listVersion = 0 }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Carichiamo i dati. 
  // Nota: MasterTechniqueList filtra localmente, quindi cerchiamo di 
  // ottenere la lista completa se possibile, o gestiamo la paginazione 
  // se il backend è molto popolato.
  const loadData = async () => {
    setLoading(true);
    try {
      const response = await staffGetInfusioni(onLogout);
      
      // Gestione sicura del formato DRF (paginato o array diretto)
      if (Array.isArray(response)) {
        setItems(response);
      } else if (response && response.results) {
        setItems(response.results);
      } else {
        setItems([]);
      }
    } catch (err) {
      console.error("Errore caricamento infusioni:", err);
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [listVersion]);

  const handleDelete = async (id) => {
    try {
      await staffDeleteInfusione(id, onLogout);
      loadData();
    } catch (e) {
      console.error("Errore durante la cancellazione:", e);
    }
  };

  return (
    <MasterTechniqueList 
      title="Gestione Infusioni"
      addLabel="Nuova Infusione"
      items={items}
      loading={loading}
      onAdd={onNew}
      onEdit={onSelect}
      onScanQr={onScanQr}
      onMinigioco={onMinigioco}
      onDelete={handleDelete}
      extraRowActions={onCreateInstance ? (item) => (
        <button
          type="button"
          onClick={() => onCreateInstance(item)}
          className="min-h-11 min-w-11 inline-flex items-center justify-center p-2.5 lg:p-2 bg-purple-600/20 text-purple-300 hover:bg-purple-600 hover:text-white rounded-lg transition-all"
          title="Crea istanza"
          aria-label={`Crea istanza di ${item.nome}`}
        >
          <PackagePlus size={16} />
        </button>
      ) : null}
    />
  );
};

export default InfusioneList;