import React, { useState, useEffect } from 'react';
import { staffGetTessiture, staffDeleteTessitura } from '../../api';
import MasterTechniqueList from './MasterTechniqueList';

const TessituraList = ({ onAdd, onEdit, onScanQr, onLogout }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadData = () => {
    setLoading(true);
    staffGetTessiture(onLogout)
      .then(data => setItems(Array.isArray(data) ? data : []))
      .finally(() => setLoading(false));
  };

  useEffect(() => { loadData(); }, []);

  const handleDelete = async (id) => {
    if (window.confirm("Sei sicuro di voler eliminare questa Tessitura?")) {
      await staffDeleteTessitura(id, onLogout);
      loadData();
    }
  };

  return (
    <MasterTechniqueList 
      title="Gestione Tessiture"
      addLabel="Nuova Tessitura"
      items={items}
      loading={loading}
      onAdd={onAdd}
      onEdit={onEdit}
      onScanQr={onScanQr}
      onDelete={handleDelete}
    />
  );
};

export default TessituraList;