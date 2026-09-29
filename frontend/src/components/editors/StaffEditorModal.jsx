import React from 'react';
import { X } from 'lucide-react';
import { confirmCloseIfDirty } from '../../hooks/useDirtyModalClose';

/**
 * Modale staff generica (creazione guidata e altri editor).
 * Footer sticky; chiusura con conferma se `isDirty`.
 */
export default function StaffEditorModal({
  title,
  onClose,
  onSave,
  saveLabel = 'Salva',
  children,
  footerExtra = null,
  wide = false,
  size = null,
  saving = false,
  isDirty = false,
  showSave = true,
}) {
  const requestClose = () =>
    confirmCloseIfDirty(
      Boolean(isDirty) && !saving,
      onClose,
      'Ci sono modifiche non salvate. Chiudere comunque?'
    );

  const widthCls =
    size === 'xl' || size === '5xl'
      ? 'max-w-5xl'
      : size === 'lg' || wide
        ? 'max-w-3xl'
        : 'max-w-2xl';

  return (
    <div
      className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center p-0 sm:p-6 bg-black/80 backdrop-blur-sm"
      role="dialog"
      aria-modal="true"
      onClick={requestClose}
    >
      <div
        className={`bg-gray-900 border border-gray-600 rounded-t-2xl sm:rounded-xl shadow-2xl w-full flex flex-col max-h-[94vh] min-w-0 ${widthCls}`}
        onClick={(e) => e.stopPropagation()}
      >
        <div className="flex items-center justify-between gap-2 px-4 py-3 border-b border-gray-700 shrink-0">
          <h3 className="text-lg font-bold text-gray-100 min-w-0 break-words">{title}</h3>
          <button
            type="button"
            onClick={requestClose}
            className="min-h-11 min-w-11 shrink-0 flex items-center justify-center p-2 rounded-lg hover:bg-gray-800 text-gray-400"
            aria-label="Chiudi"
          >
            <X size={20} />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto p-4 space-y-3 min-h-0">{children}</div>
        <div className="flex flex-col-reverse sm:flex-row flex-wrap items-stretch sm:items-center justify-end gap-2 px-4 py-3 border-t border-gray-700 shrink-0 pb-[max(0.75rem,var(--kor-safe-bottom))] sm:pb-3">
          {footerExtra}
          <button
            type="button"
            onClick={requestClose}
            className="min-h-11 w-full sm:w-auto px-4 py-2 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm"
          >
            {showSave ? 'Annulla' : 'Chiudi'}
          </button>
          {showSave && onSave ? (
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="min-h-11 w-full sm:w-auto px-4 py-2 rounded-lg bg-violet-700 hover:bg-violet-600 text-sm font-bold disabled:opacity-50"
            >
              {saving ? 'Salvataggio...' : saveLabel}
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
