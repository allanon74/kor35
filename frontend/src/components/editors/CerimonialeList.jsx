import React, { useState, useEffect } from 'react';
import { staffGetCerimoniali, staffDeleteCerimoniale } from '../../api';
import MasterTechniqueList from './MasterTechniqueList';

const CerimonialeList = ({ onAdd, onEdit, onScanQr, onLogout }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    staffGetCerimoniali(onLogout)
      .then(data => setItems(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleDelete = async (id) => {
    if (window.confirm("Eliminare questo Cerimoniale?")) {
      await staffDeleteCerimoniale(id, onLogout);
      loadData();
    }
  };

  return (
    <MasterTechniqueList 
      title="Gestione Cerimoniali"
      addLabel="Nuovo Cerimoniale"
      items={items}
      loading={loading}
      onAdd={onAdd}
      onEdit={onEdit}
      onScanQr={onScanQr}
      onDelete={handleDelete}
    />
  );
};

export default CerimonialeList;