import React, { useState, useCallback, memo } from 'react';
import CerimonialeList from './CerimonialeList';
import CerimonialeEditor from './CerimonialeEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto } from '../../api';

const CerimonialeManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [editingItem, setEditingItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);

  const handleAdd = useCallback(() => {
    setEditingItem(null);
    setView('edit');
  }, []);

  const handleEdit = useCallback((item) => {
    setEditingItem(item);
    setView('edit');
  }, []);

  const handleBackToList = useCallback(() => {
    setEditingItem(null);
    setView('list');
  }, []);

  const handleScanQr = useCallback((elementId) => {
    setScanningForElement(elementId);
  }, []);

  if (view === 'edit') {
    return (
      <CerimonialeEditor 
        initialData={editingItem} 
        onBack={handleBackToList} 
        onLogout={onLogout} 
      />
    );
  }

  return (
    <div className="space-y-6">
      <button 
        onClick={onBack}
        className="text-gray-400 hover:text-white flex items-center gap-2 mb-4 transition-colors"
      >
        ← Torna agli Strumenti Master
      </button>
      
      <CerimonialeList 
        onAdd={handleAdd} 
        onEdit={handleEdit} 
        onScanQr={handleScanQr}
        onLogout={onLogout} 
      />

      {scanningForElement && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Cerimoniale</span>
            <button 
              onClick={() => setScanningForElement(null)} 
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition-colors"
            >
              Annulla
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab 
              onScanSuccess={async (qr_id) => {
                try {
                  await associaQrDiretto(scanningForElement, qr_id, onLogout);
                  setScanningForElement(null);
                  alert('QR associato con successo!');
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    const conferma = window.confirm(
                      `⚠️ ATTENZIONE!\n\n${error.data.message}\n\nVuoi procedere comunque e spostare il QR su questo elemento?`
                    );
                    if (conferma) {
                      await associaQrDiretto(scanningForElement, qr_id, onLogout, true);
                      setScanningForElement(null);
                      alert('QR riassociato con successo!');
                    }
                  } else {
                    alert('Errore: ' + (error.message || 'Errore sconosciuto'));
                  }
                }
              }} 
              onLogout={onLogout} 
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(CerimonialeManager);