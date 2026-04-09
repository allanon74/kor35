import React, { useState, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
import OggettoList from './OggettoList';
import OggettoEditor from './OggettoEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto } from '../../api';

const OggettoManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [selectedItem, setSelectedItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);

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

  const handleScanQr = useCallback((elementId) => {
    setScanningForElement(elementId);
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
        <OggettoList 
          onAdd={handleAdd} 
          onEdit={handleEdit} 
          onScanQr={handleScanQr}
          onLogout={onLogout} 
        />
      ) : (
        <OggettoEditor 
          initialData={selectedItem} 
          onBack={handleBackToList} 
          onLogout={onLogout} 
        />
      )}

      {scanningForElement && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Oggetto</span>
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

export default memo(OggettoManager);