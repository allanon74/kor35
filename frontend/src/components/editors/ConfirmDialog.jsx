import React from 'react';

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

  return (
    <div className={`fixed inset-0 ${zIndexClass} bg-black/70 flex items-center justify-center p-4`}>
      <div className="w-full max-w-md bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
        <div className="p-4 border-b border-gray-700">
          <h3 className="text-white font-bold text-lg">{title}</h3>
          {children ? <div className="mt-1">{children}</div> : null}
          {!children && message ? (
            <p className="text-sm text-gray-400 mt-1 whitespace-pre-line">{message}</p>
          ) : null}
        </div>
        <div className="p-4 flex justify-end gap-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded-lg text-sm font-bold text-white disabled:opacity-60"
          >
            {cancelLabel}
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={loading}
            className={`px-4 py-2 rounded-lg text-sm font-bold text-white disabled:opacity-60 ${confirmClass}`}
          >
            {loading ? 'Attendere...' : confirmLabel}
          </button>
        </div>
      </div>
    </div>
  );
};

export default ConfirmDialog;
