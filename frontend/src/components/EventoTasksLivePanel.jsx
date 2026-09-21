import React, { useCallback, useEffect, useState } from 'react';
import { Eye, EyeOff, ListTodo, Power, PowerOff } from 'lucide-react';
import { getMissioniEventoAttivo, getMissioniEventoTasks, setMissioneAttivaEvento } from '../api';

/**
 * Pannello staff: attiva/disattiva le task di un evento (live).
 * Una task disattiva è invisibile ai PG e non può essere risolta.
 */
export default function EventoTasksLivePanel({
  onLogout,
  eventoId: eventoIdProp,
  compact = false,
  className = '',
}) {
  const [evento, setEvento] = useState(null);
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(!!eventoIdProp);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);

  const resolveEventoId = useCallback(async () => {
    if (eventoIdProp) return Number(eventoIdProp);
    const data = await getMissioniEventoAttivo(null, onLogout);
    if (data?.id) return Number(data.id);
    return null;
  }, [eventoIdProp, onLogout]);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const eid = await resolveEventoId();
      if (!eid) {
        setEvento(null);
        setRows([]);
        return;
      }
      const data = await getMissioniEventoTasks(eid, onLogout);
      setEvento({
        id: data.evento_id,
        titolo: data.evento_titolo,
        in_corso: !!data.in_corso,
      });
      setRows(Array.isArray(data.tasks) ? data.tasks : []);
    } catch (err) {
      setError(err?.message || 'Impossibile caricare le task dell\'evento');
      setEvento(null);
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [onLogout, resolveEventoId]);

  useEffect(() => { load(); }, [load]);

  const toggle = async (row, nextAttiva) => {
    if (!evento?.id) return;
    setBusyId(row.id);
    setError('');
    try {
      await setMissioneAttivaEvento(row.id, evento.id, nextAttiva, onLogout);
      setRows((prev) => prev.map((r) => (r.id === row.id ? { ...r, attiva: nextAttiva } : r)));
    } catch (err) {
      setError(err?.message || 'Toggle fallito');
    } finally {
      setBusyId(null);
    }
  };

  // Senza eventoId: mostra solo se c'è un evento in corso (niente flash a vuoto).
  if (!eventoIdProp && !evento && !error) return null;

  const shell = compact
    ? 'rounded-lg border border-lime-900/50 bg-lime-950/20 p-3'
    : 'rounded-xl border border-lime-800/60 bg-lime-950/30 p-4';

  return (
    <section className={`${shell} ${className}`.trim()}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-lime-200">
            <ListTodo size={16} className="shrink-0" />
            <h3 className="text-xs font-black uppercase tracking-wide">
              Tasks evento{evento?.in_corso ? ' in corso' : ''}
            </h3>
          </div>
          {evento?.titolo ? (
            <p className="mt-0.5 truncate text-[11px] text-gray-400">{evento.titolo}</p>
          ) : null}
          <p className="mt-1 text-[10px] text-gray-500">
            Attiva = visibile ai PG iscritti e risolvibile. Disattiva = invisibile e non risolvibile.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="shrink-0 rounded border border-gray-700 px-2 py-1 text-[10px] font-bold uppercase text-gray-300 hover:border-lime-700 disabled:opacity-40"
        >
          {loading ? '…' : 'Aggiorna'}
        </button>
      </div>
      {error ? <p className="mb-2 text-xs text-red-400">{error}</p> : null}
      {loading && rows.length === 0 ? (
        <p className="text-xs text-gray-500">Caricamento…</p>
      ) : rows.length === 0 ? (
        <p className="text-xs text-gray-500">Nessuna task collegata a questo evento.</p>
      ) : (
        <ul className="max-h-64 space-y-1.5 overflow-y-auto pr-1">
          {rows.map((row) => {
            const liveOn = !!row.attiva;
            const catalogOff = row.attiva_catalogo === false;
            const busy = busyId === row.id;
            return (
              <li
                key={row.id}
                className={`flex items-center justify-between gap-2 rounded-lg border px-2.5 py-2 ${
                  liveOn && !catalogOff
                    ? 'border-lime-800/60 bg-lime-950/40'
                    : 'border-gray-800 bg-gray-900/50'
                }`}
              >
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-white">{row.titolo}</div>
                  <div className="mt-0.5 flex flex-wrap gap-1.5 text-[10px] uppercase text-gray-500">
                    {row.tipo_risoluzione ? <span>{row.tipo_risoluzione}</span> : null}
                    {row.korp_nome ? (
                      <span>{row.korp_nome}{row.esclusiva ? ' · esclusiva' : ''}</span>
                    ) : (
                      <span>Generica</span>
                    )}
                    {catalogOff ? (
                      <span className="text-amber-400">Catalogo spento</span>
                    ) : null}
                  </div>
                </div>
                <button
                  type="button"
                  disabled={busy}
                  onClick={() => toggle(row, !liveOn)}
                  className={`inline-flex shrink-0 items-center gap-1 rounded-lg px-2.5 py-1.5 text-[10px] font-black uppercase transition-colors disabled:opacity-40 ${
                    liveOn
                      ? 'bg-lime-700 text-white hover:bg-lime-600'
                      : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
                  }`}
                  title={liveOn ? 'Disattiva per questo evento' : 'Attiva per questo evento'}
                >
                  {liveOn ? <Power size={12} /> : <PowerOff size={12} />}
                  {liveOn ? (
                    <span className="inline-flex items-center gap-1">
                      <Eye size={12} /> Attiva
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1">
                      <EyeOff size={12} /> Disattiva
                    </span>
                  )}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
