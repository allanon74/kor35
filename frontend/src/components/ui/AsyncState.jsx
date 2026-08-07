import React from 'react';
import { AlertCircle, FilterX, Loader2, RefreshCw } from 'lucide-react';

/** Spinner di caricamento condiviso (player + staff). */
export function UiLoadingState({ label = 'Caricamento…', className = '' }) {
  return (
    <div
      className={`flex flex-col items-center justify-center gap-3 py-12 text-gray-400 ${className}`}
      role="status"
      aria-live="polite"
    >
      <Loader2 className="animate-spin text-indigo-400" size={32} />
      <p className="text-sm font-medium">{label}</p>
    </div>
  );
}

/** Stato vuoto con icona e messaggio. */
export function UiEmptyState({
  icon: Icon = FilterX,
  title = 'Nessun elemento',
  message,
  className = '',
  children,
}) {
  return (
    <div className={`flex flex-col items-center justify-center gap-2 py-12 text-center text-gray-500 ${className}`}>
      <Icon size={40} className="opacity-40" aria-hidden="true" />
      <p className="text-sm font-bold text-gray-400">{title}</p>
      {message ? <p className="text-xs text-gray-500 max-w-sm">{message}</p> : null}
      {children}
    </div>
  );
}

/** Banner errore con retry opzionale. */
export function UiErrorState({
  message = 'Si è verificato un errore.',
  onRetry,
  className = '',
}) {
  return (
    <div
      className={`rounded-xl border border-red-800/60 bg-red-950/50 p-4 text-red-100 ${className}`}
      role="alert"
    >
      <div className="flex items-start gap-3">
        <AlertCircle className="shrink-0 text-red-400 mt-0.5" size={20} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-semibold">{message}</p>
          {onRetry ? (
            <button
              type="button"
              onClick={onRetry}
              className="mt-3 inline-flex items-center gap-1.5 rounded-lg bg-red-900/80 hover:bg-red-800 px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors"
            >
              <RefreshCw size={14} aria-hidden="true" />
              Riprova
            </button>
          ) : null}
        </div>
      </div>
    </div>
  );
}
