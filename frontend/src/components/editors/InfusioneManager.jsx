import React, { useState, useCallback, memo } from 'react';
import InfusioneList from './InfusioneList';
import InfusioneEditor from './InfusioneEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto } from '../../api';

const InfusioneManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [selectedItem, setSelectedItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);

  const handleEdit = useCallback((item) => {
    setSelectedItem(item);
    setView('edit');
  }, []);

  const handleNew = useCallback(() => {
    setSelectedItem(null);
    setView('edit');
  }, []);

  const handleEditorBack = useCallback(() => {
    setView('list');
    setSelectedItem(null);
  }, []);

  const handleScanQr = useCallback((elementId) => {
    setScanningForElement(elementId);
  }, []);

  return (
    <div className="max-w-6xl mx-auto">
      <div className="mb-6">
        <button onClick={onBack} className="text-amber-500 hover:text-amber-400 text-sm font-bold flex items-center gap-1">
          ← TORNA AGLI STRUMENTI MASTER
        </button>
      </div>

      {view === 'list' ? (
        <InfusioneList 
          onSelect={handleEdit} 
          onNew={handleNew} 
          onScanQr={handleScanQr}
          onLogout={onLogout} 
        />
      ) : (
        <InfusioneEditor 
          initialData={selectedItem} 
          onBack={handleEditorBack} 
          onLogout={onLogout} 
        />
      )}

      {scanningForElement && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Infusione</span>
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

export default memo(InfusioneManager);