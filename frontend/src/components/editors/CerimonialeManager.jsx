import React, { useState, useCallback, memo } from 'react';
import CerimonialeList from './CerimonialeList';
import CerimonialeEditor from './CerimonialeEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto, staffGetCerimonialeDetail } from '../../api';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';

const CerimonialeManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [editingItem, setEditingItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [listVersion, setListVersion] = useState(0);
  const [isLoadingEditorData, setIsLoadingEditorData] = useState(false);

  const handleAdd = useCallback(() => {
    setEditingItem(null);
    setView('edit');
  }, []);

  const handleEdit = useCallback(async (item) => {
    try {
      setIsLoadingEditorData(true);
      const fullItem = await staffGetCerimonialeDetail(item.id, onLogout);
      setEditingItem(fullItem || item);
      setView('edit');
    } catch (error) {
      setQrStatus({ type: 'error', message: `Errore caricamento cerimoniale: ${error.message || 'Errore sconosciuto'}` });
    } finally {
      setIsLoadingEditorData(false);
    }
  }, [onLogout]);

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
      
      <CerimonialeList 
        onAdd={handleAdd} 
        onEdit={handleEdit} 
        onScanQr={handleScanQr}
        onLogout={onLogout}
        listVersion={listVersion}
      />
      {isLoadingEditorData && (
        <div className="text-xs text-gray-400">Caricamento dettaglio cerimoniale...</div>
      )}

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
                  setQrStatus({ type: 'success', message: 'QR associato con successo.' });
                  setListVersion((v) => v + 1);
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({
                      targetId: scanningForElement,
                      qrId: qr_id,
                      errorData: error.data,
                    });
                    setScanningForElement(null);
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
        title="QR già associato"
        message=""
        confirmLabel="Sostituisci associazione"
        confirmTone="warning"
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={async () => {
          const p = pendingQrConflict;
          if (!p?.qrId || !p?.targetId) return;
          try {
            await associaQrDiretto(p.targetId, p.qrId, onLogout, true);
            setScanningForElement(null);
            setPendingQrConflict(null);
            setQrStatus({ type: 'success', message: 'QR riassociato con successo.' });
            setListVersion((v) => v + 1);
          } catch (error) {
            setQrStatus({ type: 'error', message: `Errore: ${error.message || 'Errore sconosciuto'}` });
          }
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questo cerimoniale" />
        ) : null}
      </ConfirmDialog>
    </div>
  );
};

export default memo(CerimonialeManager);