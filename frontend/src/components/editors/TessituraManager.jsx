import React, { useState, useCallback, memo } from 'react';
import TessituraList from './TessituraList';
import TessituraEditor from './TessituraEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto } from '../../api';
import ConfirmDialog from './ConfirmDialog';

const TessituraManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [editingItem, setEditingItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });

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
      <TessituraEditor 
        initialData={editingItem} 
        onBack={handleBackToList} 
        onLogout={onLogout} 
      />
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <button 
          onClick={onBack}
          className="text-gray-400 hover:text-white flex items-center gap-2 mb-4 transition-colors"
        >
          ← Torna agli Strumenti Master
        </button>
        {qrStatus.message && (
          <div className={`text-xs border rounded-md px-3 py-1 inline-block ${
            qrStatus.type === 'error'
              ? 'text-red-200 bg-red-900/20 border-red-700/40'
              : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
          }`}>
            {qrStatus.message}
          </div>
        )}
      </div>
      
      <TessituraList 
        onAdd={handleAdd} 
        onEdit={handleEdit} 
        onScanQr={handleScanQr}
        onLogout={onLogout} 
      />

      {scanningForElement && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Tessitura</span>
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
                  setQrStatus({ type: 'success', message: 'QR associato con successo.' });
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({
                      qrId: qr_id,
                      message: error.data.message,
                    });
                  } else {
                    setQrStatus({ type: 'error', message: `Errore: ${error.message || 'Errore sconosciuto'}` });
                  }
                }
              }} 
              onLogout={onLogout} 
            />
          </div>
        </div>
      )}
      <ConfirmDialog
        open={Boolean(pendingQrConflict)}
        title="QR gia associato"
        message={`${pendingQrConflict?.message || ''} Vuoi procedere comunque e spostare il QR su questo elemento?`}
        confirmLabel="Sposta QR"
        confirmTone="warning"
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={async () => {
          if (!pendingQrConflict?.qrId || !scanningForElement) return;
          try {
            await associaQrDiretto(scanningForElement, pendingQrConflict.qrId, onLogout, true);
            setScanningForElement(null);
            setPendingQrConflict(null);
            setQrStatus({ type: 'success', message: 'QR riassociato con successo.' });
          } catch (error) {
            setQrStatus({ type: 'error', message: `Errore: ${error.message || 'Errore sconosciuto'}` });
          }
        }}
      />
    </div>
  );
};

export default memo(TessituraManager);