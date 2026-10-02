import React from 'react';
import { ChevronRight } from 'lucide-react';
import { RichTextViewer } from '../RichTextDisplay';
import { descrizioneVoce, labelTipoVoce } from './negozioVoceUi';

/**
 * Riga di listino negozio: tocca il contenuto per aprire la scheda completa,
 * il pulsante prezzo (se presente) per acquistare/prendere in prestito.
 *
 * Su telefono il pulsante va a capo a tutta larghezza, su schermi larghi resta
 * a destra: niente overflow che nasconda il prezzo.
 */
const NegozioVoceRow = ({
  voce,
  prezzoLabel,
  onOpen,
  onBuy,
  buyDisabled = false,
  buyTone = 'amber',
}) => {
  const descrizione = descrizioneVoce(voce);
  const tipoLabel = labelTipoVoce(voce);
  const componenti = Array.isArray(voce.componenti) ? voce.componenti : [];

  const buyClass =
    buyTone === 'violet'
      ? 'bg-violet-700 hover:bg-violet-600'
      : buyTone === 'sky'
        ? 'bg-sky-700 hover:bg-sky-600'
        : 'bg-amber-700 hover:bg-amber-600';

  return (
    <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 p-3 rounded-lg border border-gray-700 bg-gray-800/80 min-w-0">
      <button
        type="button"
        onClick={onOpen}
        className="flex items-start gap-2 text-left min-w-0 flex-1 rounded focus:outline-none focus-visible:ring-2 focus-visible:ring-amber-500"
        title="Apri la scheda completa"
      >
        <span className="min-w-0 flex-1">
          <span className="block font-semibold text-white break-words">{voce.nome}</span>
          <span className="flex flex-wrap items-center gap-1.5 mt-0.5">
            {tipoLabel && (
              <span className="text-[10px] uppercase tracking-wide text-gray-400">{tipoLabel}</span>
            )}
            {voce.usato && (
              <span className="text-[10px] uppercase tracking-wide text-emerald-400">Usato</span>
            )}
            {voce.non_vendibile && (
              <span className="text-[10px] uppercase tracking-wide text-gray-500">
                Solo in pacchetto
              </span>
            )}
            {voce.richiede_montaggio && (
              <span className="text-[10px] uppercase tracking-wide text-fuchsia-300">
                Montaggio in locazione
              </span>
            )}
          </span>
          {descrizione ? (
            <span className="block text-xs text-gray-400 mt-1 leading-relaxed prose prose-invert prose-sm max-w-none line-clamp-3">
              <RichTextViewer content={descrizione} />
            </span>
          ) : null}
          {componenti.length > 0 && (
            <span className="block text-xs text-gray-400 mt-1 break-words">
              {componenti
                .map((c) => `${c.nome}${c.quantita > 1 ? ` ×${c.quantita}` : ''}`)
                .join(' · ')}
            </span>
          )}
          {voce.messaggio_usabilita && (
            <span
              className={`block text-xs mt-1 break-words ${
                voce.acquistabile ? 'text-gray-400' : 'text-amber-300'
              }`}
            >
              {voce.messaggio_usabilita}
            </span>
          )}
          {voce.quantita_residua != null && (
            <span className="block text-xs text-gray-500 mt-0.5">
              Disponibili: {voce.quantita_residua}
            </span>
          )}
          <span className="inline-flex items-center gap-1 text-[10px] uppercase tracking-wide text-amber-500/80 mt-1">
            Dettagli <ChevronRight size={12} />
          </span>
        </span>
      </button>
      {onBuy ? (
        <button
          type="button"
          disabled={buyDisabled}
          onClick={onBuy}
          className={`w-full sm:w-auto shrink-0 min-h-11 px-3 rounded text-white text-sm font-bold disabled:opacity-40 ${buyClass}`}
        >
          {prezzoLabel}
        </button>
      ) : (
        <span className="shrink-0 self-start px-3 py-1.5 rounded bg-gray-900/70 border border-gray-700 text-amber-300 text-sm font-mono font-bold">
          {prezzoLabel}
        </span>
      )}
    </div>
  );
};

export default NegozioVoceRow;
