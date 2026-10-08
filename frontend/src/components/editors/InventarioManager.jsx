import React, { useState, useCallback, memo } from 'react';
import { StaffToolShell, StaffFullscreenEditor, scrollStaffMainToTop } from '../../staff/StaffToolShell';
import InventarioList from './InventarioList';
import InventarioEditor from './InventarioEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto } from '../../api';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrUsiMaxField, { parseStaffQrUsiMax } from './StaffQrUsiMaxField';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';

const InventarioManager = ({ onBack, onLogout }) => {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [view, setView] = useState('list'); // 'list' | 'editor'
  const [selectedItem, setSelectedItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);
  const [qrUsiMax, setQrUsiMax] = useState('1');
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [listVersion, setListVersion] = useState(0);

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

  const handleScanQr = useCallback((elementId) => {
    setQrUsiMax('1');
    setScanningForElement(elementId);
  }, []);

  return (
    <StaffToolShell className="space-y-4">
      {qrStatus.message && (
          <div className={`mt-3 text-xs border rounded-md px-3 py-1 inline-block ${
            qrStatus.type === 'error'
              ? 'text-red-200 bg-red-900/20 border-red-700/40'
              : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
          }`}>
            {qrStatus.message}
          </div>
        )}

      {view === 'list' ? (
        <InventarioList 
          onAdd={handleAdd} 
          onEdit={handleEdit} 
          onScanQr={handleScanQr}
          onMinigioco={(item) => openMinigioco(item.qrcode_id, item.nome)}
          onLogout={onLogout}
          listVersion={listVersion}
        />
      ) : (
        <StaffFullscreenEditor open onBack={handleBackToList}>
          <InventarioEditor 
          initialData={selectedItem} 
          onBack={handleBackToList} 
          onLogout={onLogout} />
        </StaffFullscreenEditor>
      )}

      {scanningForElement && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Inventario</span>
            <button 
              onClick={() => setScanningForElement(null)} 
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition-colors"
            >
              Annulla
            </button>
          </div>
          <StaffQrUsiMaxField value={qrUsiMax} onChange={setQrUsiMax} />
          <div className="flex-1">
            <StaffQrTab 
              onScanSuccess={async (qr_id) => {
                const usiMax = parseStaffQrUsiMax(qrUsiMax);
                try {
                  await associaQrDiretto(scanningForElement, qr_id, onLogout, false, usiMax);
                  setScanningForElement(null);
                  setQrStatus({ type: 'success', message: 'QR associato con successo.' });
                  setListVersion((v) => v + 1);
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({
                      targetId: scanningForElement,
                      qrId: qr_id,
                      errorData: error.data,
                      usiMax,
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
            await associaQrDiretto(p.targetId, p.qrId, onLogout, true, p.usiMax);
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
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questo inventario" />
        ) : null}
      </ConfirmDialog>
      {minigiocoModal}
    </StaffToolShell>
  );
};

export default memo(InventarioManager);
