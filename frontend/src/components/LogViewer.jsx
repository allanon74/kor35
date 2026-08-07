import React, { useState } from 'react';
import { usePersonaggioLogs } from '../hooks/useGameData';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { UiEmptyState, UiLoadingState } from './ui/AsyncState';
import { ScrollText } from 'lucide-react';

const LogViewer = () => {
  const [page, setPage] = useState(1);
  const { data, isLoading, isPlaceholderData } = usePersonaggioLogs(page);

  if (isLoading) {
    return (
      <PlayerTabShell width="wide">
        <UiLoadingState label="Caricamento log…" />
      </PlayerTabShell>
    );
  }

  const results = data?.results || [];

  return (
    <PlayerTabShell width="wide" animate className="space-y-4">
      <PlayerTabHeader icon={<ScrollText size={20} />} title="Registro Eventi" />

      {results.length === 0 ? (
        <UiEmptyState title="Nessun evento" message="Il diario del personaggio è vuoto." />
      ) : (
        <div className="space-y-2">
          {results.map((log, index) => (
            <div key={log.id || index} className="p-3 bg-gray-800 rounded border border-gray-700 text-sm">
              <div className="text-gray-400 text-xs mb-1">
                {new Date(log.data).toLocaleString()}
              </div>
              <div>{log.testo_log}</div>
            </div>
          ))}
        </div>
      )}

      <div className="flex justify-between mt-4">
        <button
          type="button"
          onClick={() => setPage((old) => Math.max(old - 1, 1))}
          disabled={page === 1}
          className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
        >
          Precedente
        </button>
        <span className="py-2">Pagina {page}</span>
        <button
          type="button"
          onClick={() => {
            if (!isPlaceholderData && data?.next) {
              setPage((old) => old + 1);
            }
          }}
          disabled={isPlaceholderData || !data?.next}
          className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
        >
          Successiva
        </button>
      </div>
    </PlayerTabShell>
  );
};

export default LogViewer;
