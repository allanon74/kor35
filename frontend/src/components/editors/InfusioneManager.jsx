import React, { useState, useCallback, memo } from 'react';
import InfusioneList from './InfusioneList';
import InfusioneEditor from './InfusioneEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto, staffGetInfusioneDetail } from '../../api';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';

const InfusioneManager = ({ onBack, onLogout }) => {
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [selectedItem, setSelectedItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [listVersion, setListVersion] = useState(0);
  const [isLoadingEditorData, setIsLoadingEditorData] = useState(false);

  const handleEdit = useCallback(async (item) => {
    try {
      setIsLoadingEditorData(true);
      const fullItem = await staffGetInfusioneDetail(item.id, onLogout);
      setSelectedItem(fullItem || item);
      setView('edit');
    } catch (error) {
      setQrStatus({ type: 'error', message: `Errore caricamento infusione: ${error.message || 'Errore sconosciuto'}` });
    } finally {
      setIsLoadingEditorData(false);
    }
  }, [onLogout]);

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
        {qrStatus.message && (
          <div className={`mt-3 text-xs border rounded-md px-3 py-1 inline-block ${
            qrStatus.type === 'error'
              ? 'text-red-200 bg-red-900/20 border-red-700/40'
              : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
          }`}>
            {qrStatus.message}
          </div>
        )}
      </div>

      {view === 'list' ? (
        <>
          <InfusioneList 
            onSelect={handleEdit} 
            onNew={handleNew} 
            onScanQr={handleScanQr}
            onLogout={onLogout}
            listVersion={listVersion}
          />
          {isLoadingEditorData && (
            <div className="text-xs text-gray-400 mt-2">Caricamento dettaglio infusione...</div>
          )}
        </>
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
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questa infusione" />
        ) : null}
      </ConfirmDialog>
    </div>
  );
};

export default memo(InfusioneManager);