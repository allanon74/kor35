import React, { useState, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
import ImmagineList from './ImmagineList';
import ImmagineEditor from './ImmagineEditor';

const ImmagineManager = ({ onBack, onLogout }) => {
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
    <div className="space-y-6">
      <button 
        onClick={view === 'list' ? onBack : handleBackToList}
        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors text-sm font-bold uppercase"
      >
        <ArrowLeft size={16} /> 
        {view === 'list' ? 'Torna agli Strumenti' : 'Annulla e Torna alla Lista'}
      </button>

      {view === 'list' ? (
        <ImmagineList 
          onAdd={handleAdd} 
          onEdit={handleEdit} 
          onLogout={onLogout} 
        />
      ) : (
        <ImmagineEditor 
          initialData={selectedItem} 
          onBack={handleBackToList} 
          onLogout={onLogout} 
        />
      )}
    </div>
  );
};

export default memo(ImmagineManager);
