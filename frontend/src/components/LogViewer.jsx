import React, { useState } from 'react';
import { usePersonaggioLogs } from '../hooks/useGameData';

const LogViewer = () => {
  const [page, setPage] = useState(1);
  const { data, isLoading, isPlaceholderData } = usePersonaggioLogs(page);

  if (isLoading) return <div className="p-4 text-center">Caricamento log...</div>;

  return (
    <div className="log-container">
      <h3 className="text-xl font-bold mb-4">Registro Eventi</h3>
      
      <div className="space-y-2">
        {data?.results?.map((log, index) => (
          <div key={log.id || index} className="p-3 bg-gray-800 rounded border border-gray-700 text-sm">
            <div className="text-gray-400 text-xs mb-1">
              {new Date(log.data).toLocaleString()}
            </div>
            <div>{log.testo_log}</div>
          </div>
        ))}
      </div>

      {/* Controlli Paginazione */}
      <div className="flex justify-between mt-4">
        <button
          onClick={() => setPage(old => Math.max(old - 1, 1))}
          disabled={page === 1}
          className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
        >
          Precedente
        </button>
        <span className="py-2">Pagina {page}</span>
        <button
          onClick={() => {
            if (!isPlaceholderData && data.next) {
              setPage(old => old + 1);
            }
          }}
          disabled={isPlaceholderData || !data?.next}
          className="px-4 py-2 bg-blue-600 rounded disabled:opacity-50"
        >
          Successivo
        </button>
      </div>
    </div>
  );
};

export default LogViewer;