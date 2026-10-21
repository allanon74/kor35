import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';
import { Info, X } from 'lucide-react';
import MattoneWikiCard from './wg/MattoneWikiCard';

/**
 * Popup della descrizione mattone, stessa scheda della wiki.
 * Si apre dal pulsante e si chiude toccando il mattone (intestazione), lo sfondo o Chiudi.
 */
export default function MattoneDescrizioneModal({ mattone, onClose }) {
  useEffect(() => {
    if (!mattone) return undefined;
    const onKey = (event) => {
      if (event.key === 'Escape') onClose();
    };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [mattone, onClose]);

  if (!mattone || typeof document === 'undefined') return null;

  return createPortal(
    <div
      className="fixed inset-0 z-[220] overflow-y-auto overscroll-contain bg-black/80"
      role="dialog"
      aria-modal="true"
      aria-label={`Descrizione di ${mattone.nome || 'mattone'}`}
      onClick={onClose}
    >
      <div className="flex min-h-full items-end sm:items-center justify-center p-0 sm:p-4">
        <div
          className="w-full max-w-lg max-h-[min(94dvh,100dvh)] overflow-y-auto rounded-t-2xl sm:rounded-2xl bg-gray-900 border border-gray-600 shadow-2xl min-w-0 pb-[max(0.75rem,var(--kor-safe-bottom))]"
          onClick={(event) => event.stopPropagation()}
        >
          <div className="flex items-center justify-between gap-3 px-3 py-2 sm:px-4">
            <p className="text-[11px] text-gray-400 min-w-0 break-words">
              Tocca il mattone per chiudere
            </p>
            <button
              type="button"
              onClick={onClose}
              className="min-h-11 min-w-11 inline-flex items-center justify-center rounded-full text-gray-300 hover:text-white hover:bg-gray-800 shrink-0"
              aria-label="Chiudi descrizione"
            >
              <X size={20} />
            </button>
          </div>
          <div className="px-3 sm:px-4 pb-4">
            <MattoneWikiCard mattone={mattone} onMattoneClick={onClose} />
          </div>
        </div>
      </div>
    </div>,
    document.body,
  );
}

export function MattoneInfoButton({ mattone, className = '' }) {
  const [aperto, setAperto] = useState(false);
  if (!mattone) return null;
  const nome = mattone.nome || 'mattone';
  return (
    <>
      <button
        type="button"
        className={`min-h-11 min-w-11 inline-flex items-center justify-center rounded-lg border border-cyan-700/70 bg-cyan-950/50 text-cyan-200 hover:bg-cyan-900/60 shrink-0 ${className}`}
        aria-label={`Mostra descrizione di ${nome}`}
        title="Descrizione del mattone"
        onClick={(event) => {
          event.preventDefault();
          event.stopPropagation();
          setAperto(true);
        }}
      >
        <Info size={16} />
      </button>
      {aperto ? (
        <MattoneDescrizioneModal mattone={mattone} onClose={() => setAperto(false)} />
      ) : null}
    </>
  );
}
