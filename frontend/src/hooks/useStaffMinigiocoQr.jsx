import { useCallback, useState } from 'react';
import StaffMinigiocoQrModal from '../components/editors/StaffMinigiocoQrModal';

/**
 * Hook riusabile: apri modale minigioco da qualsiasi schermata staff con associazione QR.
 */
export function useStaffMinigiocoQr(onLogout, lookup = {}) {
  const [item, setItem] = useState(null);

  const openMinigioco = useCallback((qrcodeId, label = '') => {
    if (!qrcodeId) return;
    setItem({ qrcodeId, label: label || '' });
  }, []);

  const closeMinigioco = useCallback(() => setItem(null), []);

  const minigiocoModal = (
    <StaffMinigiocoQrModal
      item={item}
      onClose={closeMinigioco}
      onLogout={onLogout}
      lookup={lookup}
    />
  );

  return { openMinigioco, closeMinigioco, minigiocoModal };
}

export default useStaffMinigiocoQr;
