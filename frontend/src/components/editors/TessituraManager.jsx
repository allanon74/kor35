import React, { useState, useCallback, memo } from 'react';
import TessituraList from './TessituraList';
import TessituraEditor from './TessituraEditor';
import StaffQrTab from '../StaffQrTab';
import { associaQrDiretto, staffGetTessituraDetail } from '../../api';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrUsiMaxField, { parseStaffQrUsiMax } from './StaffQrUsiMaxField';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';
import { StaffToolShell, StaffFullscreenEditor, scrollStaffMainToTop } from '../../staff/StaffToolShell';

const TessituraManager = ({ onBack, onLogout }) => {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [view, setView] = useState('list'); // 'list' o 'edit'
  const [editingItem, setEditingItem] = useState(null);
  const [scanningForElement, setScanningForElement] = useState(null);
  const [qrUsiMax, setQrUsiMax] = useState('1');
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [listVersion, setListVersion] = useState(0);
  const [isLoadingEditorData, setIsLoadingEditorData] = useState(false);

  const handleAdd = useCallback(() => {
    setEditingItem(null);
    setView('edit');
    scrollStaffMainToTop();
  }, []);

  const handleEdit = useCallback(async (item) => {
    try {
      setIsLoadingEditorData(true);
      const fullItem = await staffGetTessituraDetail(item.id, onLogout);
      setEditingItem(fullItem || item);
      setView('edit');
      scrollStaffMainToTop();
    } catch (error) {
      setQrStatus({ type: 'error', message: `Errore caricamento tessitura: ${error.message || 'Errore sconosciuto'}` });
    } finally {
      setIsLoadingEditorData(false);
    }
  }, [onLogout]);

  const handleBackToList = useCallback(() => {
    setEditingItem(null);
    setView('list');
  }, []);

  const handleScanQr = useCallback((elementId) => {
    setQrUsiMax('1');
    setScanningForElement(elementId);
  }, []);

  return (
    <StaffToolShell>
      {qrStatus.message ? (
        <div className={`mb-4 text-xs border rounded-md px-3 py-1 inline-block ${
          qrStatus.type === 'error'
            ? 'text-red-200 bg-red-900/20 border-red-700/40'
            : 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40'
        }`}
        >
          {qrStatus.message}
        </div>
      ) : null}

      {view === 'list' ? (
        <>
          <TessituraList
            onAdd={handleAdd}
            onEdit={handleEdit}
            onScanQr={handleScanQr}
            onMinigioco={(item) => openMinigioco(item.qrcode_id, item.nome)}
            onLogout={onLogout}
            listVersion={listVersion}
          />
          {isLoadingEditorData ? (
            <div className="text-xs text-gray-400">Caricamento dettaglio tessitura...</div>
          ) : null}
        </>
      ) : (
        <StaffFullscreenEditor open onBack={handleBackToList}>
          <TessituraEditor
            initialData={editingItem}
            onBack={handleBackToList}
            onLogout={onLogout}
          />
        </StaffFullscreenEditor>
      )}

      {scanningForElement ? (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a Tessitura</span>
            <button
              type="button"
              onClick={() => setScanningForElement(null)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition-colors min-h-11"
            >
              Annulla
            </button>
          </div>
          <StaffQrUsiMaxField value={qrUsiMax} onChange={setQrUsiMax} />
          <div className="flex-1 min-h-0">
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
      ) : null}
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
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questa tessitura" />
        ) : null}
      </ConfirmDialog>
      {minigiocoModal}
    </StaffToolShell>
  );
};

export default memo(TessituraManager);