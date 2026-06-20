import React, { useCallback, useEffect, useState } from 'react';
import {
  applyDefaultMinigiocoToQr,
  staffSetMinigiocoUsaDefault,
} from '../../utils/staffMinigiocoDefaults';

/**
 * Checkbox lista: indica se il QR usa il template minigioco di pagina (persistito su MinigiocoQrConfig).
 */
const StaffMinigiocoUsaDefaultToggle = ({
  qrcodeId,
  usaDefault = false,
  pageKey,
  onLogout,
  onChange,
  disabled = false,
  compact = false,
}) => {
  const [checked, setChecked] = useState(Boolean(usaDefault));
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState('');

  useEffect(() => {
    setChecked(Boolean(usaDefault));
  }, [usaDefault]);

  const handleToggle = useCallback(
    async (e) => {
      const next = e.target.checked;
      if (!qrcodeId || busy) return;
      setBusy(true);
      setErr('');
      try {
        if (next) {
          await applyDefaultMinigiocoToQr(pageKey, qrcodeId, onLogout, null, {
            forceApply: true,
            usaDefaultPagina: true,
          });
        } else {
          await staffSetMinigiocoUsaDefault(qrcodeId, false, onLogout);
        }
        setChecked(next);
        onChange?.(next);
      } catch (error) {
        setErr(error?.message || 'Errore salvataggio flag default');
        setChecked(Boolean(usaDefault));
      } finally {
        setBusy(false);
      }
    },
    [qrcodeId, busy, pageKey, onLogout, onChange, usaDefault],
  );

  const title = !qrcodeId
    ? 'Associa un QR per usare il default minigioco'
    : 'Usa il template minigioco di pagina (salvato sul QR in DB)';

  return (
    <label
      className={`inline-flex items-center gap-1.5 cursor-pointer ${compact ? 'text-[10px]' : 'text-xs'} text-gray-300 ${disabled || !qrcodeId ? 'opacity-50 cursor-not-allowed' : ''}`}
      title={err || title}
    >
      <input
        type="checkbox"
        checked={checked}
        disabled={disabled || !qrcodeId || busy}
        onChange={handleToggle}
        className="rounded border-gray-600"
      />
      <span className="whitespace-nowrap">{compact ? 'Def.' : 'Default pagina'}</span>
      {busy ? <span className="text-[10px] text-gray-500">…</span> : null}
    </label>
  );
};

export default StaffMinigiocoUsaDefaultToggle;
