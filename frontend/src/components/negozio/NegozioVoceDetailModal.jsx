import React from 'react';
import { Dialog } from '@headlessui/react';
import { X } from 'lucide-react';
import { RichTextViewer } from '../RichTextDisplay';
import { descrizioneVoce, labelTipoVoce } from './negozioVoceUi';

/**
 * Scheda completa di una voce di listino (negozio mercante).
 *
 * Usata sia dal listino giocatore (con azione di acquisto/prestito) sia
 * dall'anteprima staff (sola lettura). Sheet dal basso su telefono, dialog
 * centrato da tablet in su: il testo scorre e l'azione resta sempre visibile.
 */
const NegozioVoceDetailModal = ({
  voce,
  prezzoLabel,
  onClose,
  onAction,
  actionLabel,
  actionDisabled = false,
  actionTone = 'amber',
  footerNote,
}) => {
  if (!voce) return null;

  const descrizione = descrizioneVoce(voce);
  const tipoLabel = labelTipoVoce(voce);
  const componenti = Array.isArray(voce.componenti) ? voce.componenti : [];
  const slotPermessi = Array.isArray(voce.slot_corpo_permessi) ? voce.slot_corpo_permessi : [];
  const slotDisponibili = Array.isArray(voce.slot_disponibili) ? voce.slot_disponibili : [];

  const actionClass =
    actionTone === 'sky'
      ? 'bg-sky-700 hover:bg-sky-600'
      : actionTone === 'violet'
        ? 'bg-violet-700 hover:bg-violet-600'
        : 'bg-amber-700 hover:bg-amber-600';

  // z-130: la scheda sta sopra il listino giocatore e sopra la modale staff (z-100).
  return (
    <Dialog open onClose={onClose} className="relative z-[130]">
      <div className="fixed inset-0 bg-black/80 backdrop-blur-sm" aria-hidden="true" />
      <div className="fixed inset-0 flex items-end sm:items-center justify-center p-0 sm:p-4">
        <Dialog.Panel className="w-full sm:max-w-xl max-h-[92dvh] sm:max-h-[88vh] flex flex-col bg-gray-900 border border-amber-700/40 rounded-t-2xl sm:rounded-2xl shadow-2xl min-w-0">
          <div className="flex items-start justify-between gap-3 p-4 border-b border-gray-700 shrink-0">
            <div className="min-w-0">
              <Dialog.Title className="text-base sm:text-lg font-bold text-amber-300 break-words">
                {voce.nome}
              </Dialog.Title>
              <div className="flex flex-wrap items-center gap-1.5 mt-1">
                {tipoLabel && (
                  <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-gray-800 text-gray-300">
                    {tipoLabel}
                  </span>
                )}
                {voce.usato && (
                  <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-emerald-950 text-emerald-300">
                    Usato
                  </span>
                )}
                {voce.non_vendibile && (
                  <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-gray-800 text-gray-400">
                    Solo in pacchetto
                  </span>
                )}
                {voce.richiede_montaggio && (
                  <span className="text-[10px] uppercase tracking-wide px-2 py-0.5 rounded bg-fuchsia-950 text-fuchsia-300">
                    Montaggio in locazione
                  </span>
                )}
              </div>
            </div>
            <button
              type="button"
              onClick={onClose}
              aria-label="Chiudi scheda articolo"
              className="shrink-0 min-h-11 min-w-11 flex items-center justify-center text-gray-400 hover:text-white"
            >
              <X size={22} />
            </button>
          </div>

          <div className="p-4 overflow-y-auto flex-1 space-y-4 min-w-0">
            <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm">
              {prezzoLabel && (
                <span className="font-mono font-bold text-amber-300 break-words">{prezzoLabel}</span>
              )}
              {voce.quantita_residua != null && (
                <span className="text-gray-400">Disponibili: {voce.quantita_residua}</span>
              )}
            </div>

            {descrizione ? (
              <div className="text-sm text-gray-200 leading-relaxed prose prose-invert prose-sm max-w-none break-words">
                <RichTextViewer content={descrizione} />
              </div>
            ) : (
              <p className="text-sm text-gray-500 italic">Nessuna descrizione disponibile.</p>
            )}

            {componenti.length > 0 && (
              <div>
                <p className="text-[10px] font-black uppercase tracking-widest text-violet-300 mb-1">
                  Contenuto del pacchetto
                </p>
                <ul className="text-sm text-gray-300 list-disc list-inside space-y-0.5">
                  {componenti.map((c) => (
                    <li key={`${c.voce_id}-${c.nome}`} className="break-words">
                      {c.nome}
                      {c.quantita > 1 ? ` ×${c.quantita}` : ''}
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {voce.richiede_montaggio && (slotPermessi.length > 0 || slotDisponibili.length > 0) && (
              <div className="text-xs text-gray-400 space-y-1">
                {slotPermessi.length > 0 && (
                  <p className="break-words">
                    Locazioni ammesse: <span className="text-gray-300">{slotPermessi.join(', ')}</span>
                  </p>
                )}
                <p className="break-words">
                  Locazioni libere su di te:{' '}
                  <span className="text-gray-300">
                    {slotDisponibili.length
                      ? slotDisponibili.map((s) => s.label || s.code).join(', ')
                      : 'nessuna'}
                  </span>
                </p>
              </div>
            )}

            {voce.messaggio_usabilita && (
              <p
                className={`text-sm rounded-lg px-3 py-2 border ${
                  voce.acquistabile
                    ? 'text-gray-300 border-gray-700 bg-gray-800/60'
                    : 'text-amber-200 border-amber-800/60 bg-amber-950/40'
                }`}
              >
                {voce.messaggio_usabilita}
              </p>
            )}
          </div>

          <div className="p-4 border-t border-gray-700 shrink-0 space-y-2 pb-[max(1rem,env(safe-area-inset-bottom))]">
            {footerNote && <p className="text-xs text-gray-500">{footerNote}</p>}
            <div className="flex flex-col sm:flex-row gap-2">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 min-h-11 px-4 rounded-lg bg-gray-700 hover:bg-gray-600 text-sm font-semibold text-white"
              >
                Chiudi
              </button>
              {onAction && (
                <button
                  type="button"
                  onClick={onAction}
                  disabled={actionDisabled}
                  className={`flex-1 min-h-11 px-4 rounded-lg text-sm font-bold text-white disabled:opacity-40 ${actionClass}`}
                >
                  {actionLabel}
                </button>
              )}
            </div>
          </div>
        </Dialog.Panel>
      </div>
    </Dialog>
  );
};

export default NegozioVoceDetailModal;
