import React, { useState, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
import { StaffToolShell } from '../../staff/StaffToolShell';
import MostroList from './MostroList';
import MostroEditor from './MostroEditor';

const MostroManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [selectedItem, setSelectedItem] = useState(null);

  const handleAdd = useCallback(() => {
    setSelectedItem(null);
    setView('editor');
  }, []);

  const handleEdit = useCallback((item) => {
    setSelectedItem(item);
    setView('editor');
  }, []);

  const handleBackToList = useCallback(() => {
    setView('list');
    setSelectedItem(null);
  }, []);

  return (
    <StaffToolShell className="space-y-4">
      {view !== 'list' && (
      <button 
        onClick={handleBackToList}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm font-bold uppercase"
      >
        <ArrowLeft size={16} />
        Annulla e Torna alla Lista
      </button>
      )}

      {view === 'list' ? (
        <MostroList 
          onAdd={handleAdd} 
          onEdit={handleEdit} 
          onLogout={onLogout} 
        />
      ) : (
        <MostroEditor 
          initialData={selectedItem} 
          onBack={handleBackToList} 
          onLogout={onLogout} 
        />
      )}
    </StaffToolShell>
  );
};

export default memo(MostroManager);