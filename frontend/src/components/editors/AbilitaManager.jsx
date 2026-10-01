import React, { useState, useCallback, memo } from 'react';
import { StaffToolShell, StaffFullscreenEditor, scrollStaffMainToTop } from '../../staff/StaffToolShell';
import AbilitaList from './AbilitaList';
import AbilitaEditor from './AbilitaEditor';

const AbilitaManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [selectedItem, setSelectedItem] = useState(null);

  const handleAdd = useCallback(() => {
    setSelectedItem(null);
    setView('editor');
    scrollStaffMainToTop();
  }, []);

  const handleEdit = useCallback((item) => {
    setSelectedItem(item);
    setView('editor');
    scrollStaffMainToTop();
  }, []);

  const handleBackToList = useCallback(() => {
    setView('list');
    setSelectedItem(null);
  }, []);

  return (
    <StaffToolShell className="space-y-4">

      {view === 'list' ? (
        <AbilitaList onAdd={handleAdd} onEdit={handleEdit} onLogout={onLogout} />
      ) : (
        <StaffFullscreenEditor open onBack={handleBackToList}>
          <AbilitaEditor initialData={selectedItem} onBack={handleBackToList} onLogout={onLogout} />
        </StaffFullscreenEditor>
      )}
    </StaffToolShell>
  );
};

export default memo(AbilitaManager);