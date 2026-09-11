import React, { useState } from 'react';
import { useTransazioni } from '../hooks/useGameData';
import { useCharacter } from './CharacterContext';
import { useQueryClient } from '@tanstack/react-query';
import TransazioneDetailModal from './TransazioneDetailModal';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { UiEmptyState, UiLoadingState } from './ui/AsyncState';
import { ArrowLeftRight } from 'lucide-react';
import { formatImportiCessione, importiDaProposta } from '../utils/creditiCessione';

const TransazioniViewer = ({ onLogout, charId }) => {
  const [page, setPage] = useState(1);
  const [tipo, setTipo] = useState('entrata');
  const [selectedTransazioneId, setSelectedTransazioneId] = useState(null);

  const { selectedCharacterId: contextCharId, transazioniGiocatoreAbilitate, bypassEventoGate } = useCharacter();
  const selectedCharacterId = charId || contextCharId;
  const queryClient = useQueryClient();

  const { data, isLoading, isPlaceholderData } = useTransazioni(page, tipo, selectedCharacterId);

  const handleTransazioneClick = (transazioneId) => {
    setSelectedTransazioneId(transazioneId);
  };

  const handleUpdate = () => {
    queryClient.invalidateQueries({ queryKey: ['personaggio_transazioni'] });
  };

  if (!selectedCharacterId) {
    return (
      <PlayerTabShell width="wide">
        <UiEmptyState title="Seleziona un personaggio" message="Apri la tab Personaggi per vedere le transazioni." />
      </PlayerTabShell>
    );
  }

  return (
    <PlayerTabShell width="wide" animate className="space-y-4">
      <PlayerTabHeader icon={<ArrowLeftRight size={20} />} title="Transazioni" />
      {!transazioniGiocatoreAbilitate && !bypassEventoGate && (
        <p className="text-sm text-amber-300/90 bg-amber-950/40 border border-amber-800/50 rounded p-3">
          Nuovi scambi e accettazioni sono disponibili solo durante un evento aperto. Puoi consultare lo storico e rifiutare proposte in sospeso.
        </p>
      )}
      <div className="flex space-x-4 border-b border-gray-700 pb-2">
        <button
          type="button"
          onClick={() => { setTipo('entrata'); setPage(1); }}
          className={`px-3 py-1 rounded transition-colors ${tipo === 'entrata' ? 'bg-green-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
        >
          In Entrata (Richieste a te)
        </button>
        <button
          type="button"
          onClick={() => { setTipo('uscita'); setPage(1); }}
          className={`px-3 py-1 rounded transition-colors ${tipo === 'uscita' ? 'bg-red-600 text-white' : 'bg-gray-700 text-gray-300 hover:bg-gray-600'}`}
        >
          In Uscita (Tue richieste)
        </button>
      </div>

      {isLoading ? (
        <UiLoadingState label="Caricamento transazioni…" />
      ) : (
        <div className="space-y-2">
          {data?.results?.length === 0 && (
            <UiEmptyState title="Nessuna transazione" message={`Nessuna transazione trovata in ${tipo}.`} />
          )}

          {data?.results?.map((t) => (
            <div
              key={t.id}
              onClick={() => handleTransazioneClick(t.id)}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') handleTransazioneClick(t.id); }}
              role="button"
              tabIndex={0}
              className="p-3 bg-gray-800 rounded border border-gray-700 flex justify-between items-center hover:border-gray-500 cursor-pointer transition-all"
            >
              <div className="flex-1">
                <div className="font-bold text-indigo-300">
                  {t.oggetto || (t.iniziatore_nome && t.destinatario_nome
                    ? `Transazione ${tipo === 'entrata' ? t.iniziatore_nome : t.destinatario_nome}`
                    : 'Transazione')}
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {tipo === 'entrata' ? (
                    <>Da: <span className="text-white">{t.iniziatore_nome || t.richiedente}</span></>
                  ) : (
                    <>A: <span className="text-white">{t.destinatario_nome || t.mittente}</span></>
                  )}
                  <span className="mx-2 text-gray-600">|</span>
                  {new Date(t.data_ultima_modifica || t.data_richiesta || t.data_creazione).toLocaleDateString()}
                </div>
                {t.ultima_proposta_iniziatore && (
                  <div className="text-xs text-gray-500 mt-1">
                    Proposta: {(() => {
                      const imp = importiDaProposta(t.ultima_proposta_iniziatore);
                      return `${formatImportiCessione(imp.corrente, imp.deposito)} → ${formatImportiCessione(imp.ricevereCorrente, imp.ricevereDeposito)}`;
                    })()}
                  </div>
                )}
              </div>
              <div className={`text-xs px-2 py-1 rounded font-bold ${
                t.stato === 'IN_ATTESA' ? 'bg-yellow-900 text-yellow-200' :
                t.stato === 'ACCETTATA' ? 'bg-green-900 text-green-200' :
                'bg-red-900 text-red-200'
              }`}
              >
                {t.stato.replace('_', ' ')}
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between pt-2 border-t border-gray-800">
        <button
          type="button"
          onClick={() => setPage((old) => Math.max(old - 1, 1))}
          disabled={page === 1}
          className="px-3 py-1 bg-gray-700 rounded disabled:opacity-30 hover:bg-gray-600 text-sm"
        >
          &lt; Indietro
        </button>
        <span className="text-xs py-1.5 text-gray-500">Pagina {page}</span>
        <button
          type="button"
          onClick={() => {
            if (!isPlaceholderData && data?.next) setPage((old) => old + 1);
          }}
          disabled={isPlaceholderData || !data?.next}
          className="px-3 py-1 bg-gray-700 rounded disabled:opacity-30 hover:bg-gray-600 text-sm"
        >
          Avanti &gt;
        </button>
      </div>

      {selectedTransazioneId && (
        <TransazioneDetailModal
          transazioneId={selectedTransazioneId}
          onClose={() => setSelectedTransazioneId(null)}
          onLogout={onLogout}
          onUpdate={handleUpdate}
        />
      )}
    </PlayerTabShell>
  );
};

export default TransazioniViewer;
