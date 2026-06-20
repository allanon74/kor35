import React from 'react';
import { createPortal } from 'react-dom';
import { X } from 'lucide-react';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';

const StaffMinigiocoQrModal = ({ item, onClose, onLogout, lookup = {} }) => {
  if (!item?.qrcodeId) return null;

  return createPortal(
    <div className="fixed inset-0 z-[120] bg-black/92 flex flex-col">
      <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 shrink-0 gap-2">
        <span className="font-bold text-white text-sm truncate">
          Minigioco QR{item.label ? ` — ${item.label}` : ''}
        </span>
        <button
          type="button"
          onClick={onClose}
          className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded text-sm flex items-center gap-1 shrink-0"
        >
          <X size={14} /> Chiudi
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-4 max-w-2xl mx-auto w-full">
        <StaffMinigiocoQrSection
          qrcodeId={item.qrcodeId}
          onLogout={onLogout}
          lookup={lookup}
        />
      </div>
    </div>,
    document.body,
  );
};

export default StaffMinigiocoQrModal;
