import React from 'react';
import { Coins, Package } from 'lucide-react';
import { getMessageAttachmentsSummary } from './messageAttachments';

/**
 * Riga allegati in una bubble chat (crediti e/o oggetti).
 */
export default function MessageAttachmentsLine({ msg, compact = false, className = '' }) {
  const summary = getMessageAttachmentsSummary(msg);
  if (!summary) return null;

  const crediti = Number(msg?.crediti_allegati || 0);
  const oggetti = Array.isArray(msg?.oggetti_allegati_snapshot)
    ? msg.oggetti_allegati_snapshot
    : [];

  if (compact) {
    return (
      <span className={`inline-flex items-center gap-1 text-[11px] text-amber-200/90 ${className}`}>
        {crediti > 0 ? <Coins size={12} className="shrink-0" /> : null}
        {oggetti.length > 0 ? <Package size={12} className="shrink-0" /> : null}
        <span className="truncate">Allegati: {summary}</span>
      </span>
    );
  }

  return (
    <div
      className={`mt-2 mb-1 rounded-lg border border-amber-500/35 bg-black/25 px-2.5 py-1.5 text-[11px] text-amber-100 ${className}`}
    >
      <div className="flex items-center gap-1.5 font-semibold uppercase tracking-wide text-amber-200/90 mb-1">
        {crediti > 0 ? <Coins size={12} /> : null}
        {oggetti.length > 0 ? <Package size={12} /> : null}
        <span>Allegati trasferiti</span>
      </div>
      <div className="space-y-0.5 normal-case font-normal text-amber-50/95">
        {crediti > 0 ? (
          <div>
            {crediti} credit{crediti === 1 ? 'o' : 'i'}
            {msg.conto_crediti_allegati === 'DEPOSITO' ? ' (deposito)' : ''}
          </div>
        ) : null}
        {oggetti.length > 0 ? (
          <ul className="list-disc list-inside space-y-0.5">
            {oggetti.map((item, idx) => (
              <li key={`${msg.id || 'm'}-att-${item?.id || idx}`}>
                {item?.nome || item?.name || `Oggetto ${item?.id || idx + 1}`}
              </li>
            ))}
          </ul>
        ) : null}
      </div>
    </div>
  );
}
