import React from 'react';
import { createPortal } from 'react-dom';

const ConfirmDialog = ({
  open = false,
  title = 'Conferma',
  message = '',
  children = null,
  confirmLabel = 'Conferma',
  cancelLabel = 'Annulla',
  confirmTone = 'danger',
  onConfirm,
  onCancel,
  loading = false,
  // Sopra overlay scanner (z-50) e plugin tipo Html5Qrcode
  zIndexClass = 'z-[10000]',
}) => {
  if (!open) return null;

  const confirmClass = confirmTone === 'danger'
    ? 'bg-red-600 hover:bg-red-500'
    : 'bg-amber-600 hover:bg-amber-500';

  const dialog = (
    <div
      className={`fixed inset-0 ${zIndexClass} overflow-y-auto overscroll-contain bg-black/70`}
      role="dialog"
      aria-modal="true"
    >
      <div className="flex min-h-full items-end sm:items-center justify-center p-0 sm:p-4">
        <div className="w-full max-w-md bg-gray-900 border border-gray-700 rounded-t-2xl sm:rounded-xl shadow-2xl">
          <div className="p-4 border-b border-gray-700">
            <h3 className="text-white font-bold text-lg break-words">{title}</h3>
            {children ? <div className="mt-1 min-w-0">{children}</div> : null}
            {!children && message ? (
              <p className="text-sm text-gray-400 mt-1 whitespace-pre-line break-words">{message}</p>
            ) : null}
          </div>
          <div className="p-4 flex flex-col-reverse sm:flex-row justify-end gap-2 pb-[max(1rem,var(--kor-safe-bottom))] sm:pb-4">
            <button
              type="button"
              onClick={onCancel}
              disabled={loading}
              className="min-h-11 w-full sm:w-auto px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-bold text-white disabled:opacity-60"
            >
              {cancelLabel}
            </button>
            <button
              type="button"
              onClick={onConfirm}
              disabled={loading}
              className={`min-h-11 w-full sm:w-auto px-4 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-60 ${confirmClass}`}
            >
              {loading ? 'Attendere...' : confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  if (typeof document === 'undefined') return dialog;
  return createPortal(dialog, document.body);
};

export default ConfirmDialog;
