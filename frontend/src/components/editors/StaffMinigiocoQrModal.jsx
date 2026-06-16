import React from 'react';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';

const StaffMinigiocoQrModal = ({ item, onClose, onLogout, lookup = {} }) => {
  if (!item?.qrcodeId) return null;

  return (
    <div className="fixed inset-0 z-50 bg-black/90 flex flex-col">
      <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 shrink-0">
        <span className="font-bold text-white text-sm">
          Minigioco QR{item.label ? ` — ${item.label}` : ''}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 bg-red-600 rounded text-sm"
        >
          Chiudi
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 max-w-2xl mx-auto w-full">
        <StaffMinigiocoQrSection
          qrcodeId={item.qrcodeId}
          onLogout={onLogout}
          lookup={lookup}
        />
      </div>
    </div>
  );
};

export default StaffMinigiocoQrModal;
