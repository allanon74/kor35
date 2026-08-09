import React from 'react';

/**
 * Banner consultazione offline / sola lettura (Game, Scheda, …).
 */
export function OfflineConsultBanner({
  isOfflineSnapshot = false,
  storedAt = null,
  className = '',
}) {
  return (
    <div
      className={`rounded-lg border border-amber-600/50 bg-amber-950/40 px-3 py-2 text-[11px] text-amber-100/95 text-center ${className}`}
      role="status"
    >
      {isOfflineSnapshot ? (
        <>
          Modalità consultazione offline: ultimo salvataggio locale
          {storedAt ? ` (${new Date(storedAt).toLocaleString()})` : ''}. Le modifiche sono
          disattivate finché non torna la connessione al server.
        </>
      ) : (
        <>
          Sei offline: le modifiche non possono essere salvate. Mostriamo i dati in cache del
          browser se disponibili.
        </>
      )}
    </div>
  );
}

export default OfflineConsultBanner;
