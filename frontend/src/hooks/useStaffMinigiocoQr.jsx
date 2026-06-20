import { useCallback, useState } from 'react';
import { createPortal } from 'react-dom';
import StaffMinigiocoQrModal from '../components/editors/StaffMinigiocoQrModal';

/**
 * Hook riusabile: apri modale minigioco da qualsiasi schermata staff con associazione QR.
 */
export function useStaffMinigiocoQr(onLogout, lookup = {}) {
  const [item, setItem] = useState(null);
  const [hint, setHint] = useState('');

  const openMinigioco = useCallback((qrcodeId, label = '') => {
    if (!qrcodeId) {
      setHint('Associa prima un QR per configurare il minigioco.');
      window.setTimeout(() => setHint(''), 3500);
      return;
    }
    setHint('');
    setItem({ qrcodeId, label: label || '' });
  }, []);

  const closeMinigioco = useCallback(() => setItem(null), []);

  const minigiocoModal = (
    <>
      <StaffMinigiocoQrModal
        item={item}
        onClose={closeMinigioco}
        onLogout={onLogout}
        lookup={lookup}
      />
      {hint
        ? createPortal(
            <div className="fixed bottom-6 left-1/2 -translate-x-1/2 z-[130] px-4 py-2 rounded-lg bg-amber-900/95 border border-amber-600 text-amber-100 text-sm shadow-lg">
              {hint}
            </div>,
            document.body,
          )
        : null}
    </>
  );

  return { openMinigioco, closeMinigioco, minigiocoModal };
}

export default useStaffMinigiocoQr;
