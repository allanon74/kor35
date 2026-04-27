import React from 'react';

/**
 * Indicatore in lista staff: l'elemento A_vista ha un QrCode collegato (campo has_qrcode dal backend).
 */
const StaffQrBadge = ({ hasQr }) => {
  const on = Boolean(hasQr);
  return (
    <span
      title={on ? 'Ha un QR associato' : 'Nessun QR associato'}
      className={`inline-flex items-center justify-center min-w-[2.25rem] px-1.5 py-0.5 rounded text-[9px] font-black uppercase tracking-wide border shrink-0 ${
        on
          ? 'bg-emerald-950/60 text-emerald-300 border-emerald-700/50'
          : 'bg-gray-900 text-gray-600 border-gray-700'
      }`}
    >
      {on ? 'QR' : '—'}
    </span>
  );
};

export default StaffQrBadge;
