import { useCallback, useState } from 'react';
import { associaQrDiretto } from '../api';

/**
 * Handler riusabile per associazione QR staff (scan + dialogo conflitto 409).
 */
export function useStaffQrAssociation({ onLogout, onReload }) {
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [conflictLoading, setConflictLoading] = useState(false);

  const handleQrScan = useCallback(
    async (targetId, qrId, { closeScan, onMessage } = {}) => {
      try {
        await associaQrDiretto(targetId, qrId, onLogout);
        closeScan?.();
        onMessage?.('QR associato.');
        onReload?.();
        return { ok: true };
      } catch (error) {
        if (error.status === 409 && error.data?.already_associated) {
          closeScan?.();
          setPendingQrConflict({ targetId, qrId, errorData: error.data });
          return { ok: false, conflict: true };
        }
        closeScan?.();
        onMessage?.(error.message || 'Errore associazione QR');
        return { ok: false, message: error.message };
      }
    },
    [onLogout, onReload]
  );

  const confirmConflict = useCallback(
    async (onMessage) => {
      const p = pendingQrConflict;
      if (!p?.qrId || !p?.targetId) return;
      setConflictLoading(true);
      try {
        await associaQrDiretto(p.targetId, p.qrId, onLogout, true);
        setPendingQrConflict(null);
        onMessage?.('QR associato (forzato).');
        onReload?.();
      } catch (error) {
        onMessage?.(error.message || 'Errore sostituzione associazione QR');
      } finally {
        setConflictLoading(false);
      }
    },
    [onLogout, onReload, pendingQrConflict]
  );

  const cancelConflict = useCallback(() => {
    if (!conflictLoading) setPendingQrConflict(null);
  }, [conflictLoading]);

  return {
    pendingQrConflict,
    conflictLoading,
    handleQrScan,
    confirmConflict,
    cancelConflict,
  };
}
