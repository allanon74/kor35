import React, { useState, useEffect } from 'react';
import { staffGetInfusioni, staffDeleteInfusione } from '../../api';
import MasterTechniqueList from './MasterTechniqueList';

const InfusioneList = ({ onSelect, onNew, onScanQr, onLogout }) => {
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
  }, []);

  const handleDelete = async (id) => {
    if (window.confirm("Sei sicuro di voler eliminare questa Infusione? Questa operazione è irreversibile.")) {
      try {
        await staffDeleteInfusione(id, onLogout);
        loadData();
      } catch (e) {
        alert("Errore durante la cancellazione: " + e.message);
      }
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
      onDelete={handleDelete}
    />
  );
};

export default InfusioneList;