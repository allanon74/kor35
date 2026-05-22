import React from 'react';
import { X } from 'lucide-react';

/**
 * Modale staff generica (creazione guidata e altri editor).
 */
export default function StaffEditorModal({
  title,
  onClose,
  onSave,
  saveLabel = 'Salva',
  children,
  footerExtra = null,
  wide = false,
  saving = false,
}) {
  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-3 sm:p-6 bg-black/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={onClose}
    >
      <div
        className={`bg-gray-900 border border-gray-600 rounded-xl shadow-2xl w-full flex flex-col max-h-[92vh] ${
          wide ? 'max-w-3xl' : 'max-w-2xl'
        }`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700 shrink-0">
          <h3 className="text-lg font-bold text-gray-100">{title}</h3>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-gray-800 text-gray-400"
            aria-label="Chiudi"
          >
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">{children}</div>
        <div className="flex flex-wrap items-center justify-end gap-2 px-4 py-3 border-t border-gray-700 shrink-0">
          {footerExtra}
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm"
          >
            Annulla
          </button>
          <button
            type="button"
            onClick={onSave}
            disabled={saving}
            className="px-4 py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-sm font-bold disabled:opacity-50"
          >
            {saving ? 'Salvataggio...' : saveLabel}
          </button>
        </div>
      </div>
    </div>
  );
}
