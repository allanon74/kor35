import React, { useCallback, useEffect, useState } from 'react';
import { Dices, RefreshCw } from 'lucide-react';
import { getPoolPgGiocatoreDettaglio, postPoolPgGiocatoreSorteggia } from '../api';
import { PlayerTabHeader, PlayerTabShell } from './personaggi/layout/PlayerTabShell';
import { UiEmptyState, UiErrorState, UiLoadingState } from './ui/AsyncState';

function formatWhen(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
}

export default function PoolSorteggioPlayerTab({ poolId, personaggioId, onLogout }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [attivazione, setAttivazione] = useState(false);

  const load = useCallback(async () => {
    if (!poolId || !personaggioId) return;
    setLoading(true);
    setError('');
    try {
      const res = await getPoolPgGiocatoreDettaglio(poolId, personaggioId, onLogout);
      setData(res);
    } catch (e) {
      setData(null);
      setError(e.message || 'Impossibile caricare il pool.');
    } finally {
      setLoading(false);
    }
  }, [poolId, personaggioId, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const attiva = async () => {
    if (!poolId || !personaggioId || attivazione) return;
    setAttivazione(true);
    setError('');
    try {
      const res = await postPoolPgGiocatoreSorteggia(poolId, personaggioId, onLogout);
      setData(res);
    } catch (e) {
      setError(e.message || 'Attivazione fallita.');
    } finally {
      setAttivazione(false);
    }
  };

  if (!personaggioId) {
    return (
      <PlayerTabShell width="narrow">
        <UiEmptyState
          title="Seleziona un personaggio"
          message="Serve un PG per attivare questo sorteggio."
        />
      </PlayerTabShell>
    );
  }

  if (loading && !data) {
    return (
      <PlayerTabShell width="narrow">
        <UiLoadingState label="Caricamento pool…" />
      </PlayerTabShell>
    );
  }

  if (error && !data) {
    return (
      <PlayerTabShell width="narrow" className="space-y-3">
        <UiErrorState message={error} onRetry={load} />
      </PlayerTabShell>
    );
  }

  const nome = data?.nome || 'Pool';
  const rimanenti = Number(data?.rimanenti || 0);
  const massimo = Number(data?.max_sorteggi_giorno || 0);
  const puoAttivare = !!data?.puo_attivare && rimanenti > 0;
  const ultimi = Array.isArray(data?.ultimi_esiti) ? data.ultimi_esiti : [];

  return (
    <PlayerTabShell width="narrow" animate className="space-y-4">
      <PlayerTabHeader
        icon={<Dices size={22} className="text-amber-300" />}
        title={nome}
        subtitle={
          data?.statistica_sigla
            ? `Attivazioni oggi: ${data.usati_oggi ?? 0}/${massimo} · ${data.statistica_sigla}`
            : `Attivazioni oggi: ${data?.usati_oggi ?? 0}/${massimo}`
        }
        actions={(
          <button
            type="button"
            onClick={load}
            disabled={loading}
            className="min-h-11 min-w-11 p-2 rounded-lg bg-gray-800 border border-gray-700 text-gray-300 hover:bg-gray-700 disabled:opacity-50"
            title="Aggiorna"
            aria-label="Aggiorna pool"
          >
            <RefreshCw size={18} className={loading ? 'animate-spin' : ''} />
          </button>
        )}
      />

      {error ? <UiErrorState message={error} onRetry={load} /> : null}

      <section className="rounded-xl border border-gray-700 bg-gray-900/60 p-4 space-y-3">
        <p className="text-sm text-gray-300">
          Attivazioni rimanenti:{' '}
          <span className="font-bold text-white">{rimanenti}</span>
          {massimo > 0 ? <span className="text-gray-500"> / {massimo}</span> : null}
        </p>
        <button
          type="button"
          onClick={attiva}
          disabled={!puoAttivare || attivazione}
          className="w-full min-h-11 rounded-lg bg-amber-600 hover:bg-amber-500 disabled:bg-gray-700 disabled:text-gray-400 text-white font-bold px-4 py-3 break-words"
        >
          {attivazione ? 'Attivazione…' : `Attiva ${nome}`}
        </button>
        {!massimo ? (
          <p className="text-xs text-gray-500">
            Lo staff non ha abilitato attivazioni giornaliere per questo pool.
          </p>
        ) : null}
      </section>

      <section className="space-y-2">
        <h3 className="text-sm font-bold uppercase tracking-wide text-gray-400">Ultimi sorteggiati</h3>
        {ultimi.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun sorteggio ancora.</p>
        ) : (
          <ul className="space-y-2">
            {ultimi.map((esito, idx) => {
              const evidenza = idx === 0;
              return (
                <li
                  key={esito.id}
                  className={
                    evidenza
                      ? 'rounded-xl border-2 border-amber-400 bg-amber-950/50 px-3 py-3'
                      : 'rounded-lg border border-gray-800 bg-gray-900/50 px-3 py-2'
                  }
                >
                  {evidenza ? (
                    <p className="text-[10px] font-bold uppercase tracking-wide text-amber-300 mb-1">
                      Ultimo estratto
                    </p>
                  ) : null}
                  <p className={`break-words ${evidenza ? 'text-lg font-bold text-white' : 'text-sm font-semibold text-gray-100'}`}>
                    {esito.personaggio_nome || '—'}
                  </p>
                  <p className="text-[11px] text-gray-400">{formatWhen(esito.created_at)}</p>
                </li>
              );
            })}
          </ul>
        )}
      </section>
    </PlayerTabShell>
  );
}
