import React, { useCallback, useEffect, useState, memo } from 'react';
import { RefreshCw, Ship } from 'lucide-react';
import { getPilotStiva } from '../api';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { UiEmptyState, UiErrorState, UiLoadingState } from './ui/AsyncState';

const StivaNaveTab = ({ onLogout, personaggioId }) => {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    if (!personaggioId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getPilotStiva(personaggioId, onLogout);
      setData(res);
    } catch (e) {
      setData(null);
      setError(e.message || 'Impossibile caricare la stiva nave.');
    } finally {
      setLoading(false);
    }
  }, [personaggioId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  if (!personaggioId) {
    return (
      <PlayerTabShell width="wide">
        <UiEmptyState
          title="Seleziona un personaggio"
          message="Serve un PG con accesso stiva per consultare i componenti nave."
        />
      </PlayerTabShell>
    );
  }

  if (loading && !data) {
    return (
      <PlayerTabShell width="wide">
        <UiLoadingState label="Caricamento stiva nave…" />
      </PlayerTabShell>
    );
  }

  if (error) {
    return (
      <PlayerTabShell width="wide" className="space-y-3">
        <UiErrorState message={error} onRetry={load} />
      </PlayerTabShell>
    );
  }

  const catalogo = data?.mattoni_catalogo || data?.righe || [];
  const righeMap = Object.fromEntries((data?.righe || []).map((r) => [r.mattone_id, r]));

  return (
    <PlayerTabShell width="wide" animate className="space-y-4">
      <PlayerTabHeader
        icon={<Ship size={22} className="text-emerald-400" />}
        title="Stiva componenti nave"
        subtitle={
          data?.stat_accesso_sigla
            ? `Inventario globale · accesso ${data.stat_accesso_sigla} > 0`
            : 'Inventario globale condiviso. Solo consultazione.'
        }
        actions={(
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
            title="Aggiorna"
            aria-label="Aggiorna stiva"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        )}
      />

      {data?.coppie_opposite?.length ? (
        <section className="space-y-2">
          <h3 className="text-xs font-bold uppercase tracking-wider text-gray-500">Coppie opposte</h3>
          <div className="grid gap-2 sm:grid-cols-2">
            {data.coppie_opposite.map((c) => (
              <div
                key={c.id}
                className="rounded-lg border border-gray-700 bg-gray-900/60 p-3 text-xs"
              >
                <div className="font-medium text-gray-200">
                  {c.colore_a.nome}
                  {' '}
                  ↔
                  {' '}
                  {c.colore_b.nome}
                </div>
                <div className="text-gray-400 mt-1">
                  In stiva:
                  {' '}
                  {c.colore_a.quantita}
                  {' / '}
                  {c.colore_b.quantita}
                  {c.entrambi_presenti ? (
                    <span className="text-amber-300 ml-2">
                      Coesistenza
                      {' '}
                      {c.tick_coesistenza}
                      /
                      {c.tick_coesistenza_max}
                    </span>
                  ) : null}
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}

      <section className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="w-full text-sm">
          <thead>
            <tr className="text-left text-gray-400 border-b border-gray-700 bg-gray-900/80">
              <th className="py-2 px-2 font-medium">#</th>
              <th className="py-2 px-2 font-medium">Componente</th>
              <th className="py-2 px-2 font-medium">Colore</th>
              <th className="py-2 px-2 font-medium text-right">Qty</th>
            </tr>
          </thead>
          <tbody>
            {catalogo.length === 0 ? (
              <tr>
                <td colSpan={4} className="py-6 text-center text-gray-500 text-sm">
                  Catalogo componenti non disponibile.
                </td>
              </tr>
            ) : (
              catalogo.map((m) => {
                const id = m.id || m.mattone_id;
                const row = righeMap[id];
                const qty = row?.quantita ?? m.quantita ?? 0;
                return (
                  <tr key={id} className="border-b border-gray-800/80">
                    <td className="py-2 px-2 font-mono text-gray-400">{m.indice_componente ?? '—'}</td>
                    <td className="py-2 px-2 text-gray-200">{m.nome || row?.nome}</td>
                    <td className="py-2 px-2 text-gray-400">{m.colore_nome || row?.colore_nome || '—'}</td>
                    <td className={`py-2 px-2 text-right font-mono ${qty > 0 ? 'text-emerald-300' : 'text-gray-600'}`}>
                      {qty}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </section>
    </PlayerTabShell>
  );
};

export default memo(StivaNaveTab);
