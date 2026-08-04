import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ListTodo } from 'lucide-react';
import { getMissioniMie } from '../api';

/** Elenco task del PG: KORP in cima, svolte, ricompense (claim automatico lato server). */
export default function MissioniPersonaggioPanel({ personaggioId, onLogout }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    if (!personaggioId) return;
    setLoading(true);
    setError('');
    try {
      const data = await getMissioniMie(personaggioId, onLogout);
      setRows(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || 'Impossibile caricare le task');
    } finally {
      setLoading(false);
    }
  }, [personaggioId, onLogout]);

  useEffect(() => { load(); }, [load]);

  if (!personaggioId) return null;

  return (
    <section className="rounded-xl border border-lime-900/60 bg-lime-950/20 p-4">
      <div className="mb-3 flex items-center gap-2">
        <ListTodo className="text-lime-400" size={20} />
        <h2 className="text-sm font-black uppercase tracking-wide text-lime-200">Tasks</h2>
      </div>
      {error ? <p className="mb-2 text-xs text-red-400">{error}</p> : null}
      {loading ? (
        <p className="text-xs text-gray-500">Caricamento…</p>
      ) : rows.length === 0 ? (
        <p className="text-xs text-gray-500">Nessuna task disponibile.</p>
      ) : (
        <ul className="space-y-2">
          {rows.map((m) => {
            const korpBonus = !!m.is_korp_bonus;
            return (
              <li
                key={m.id}
                className={`rounded-lg border px-3 py-2 ${
                  korpBonus
                    ? 'border-violet-500/60 bg-violet-950/40'
                    : m.svolta
                      ? 'border-gray-700 bg-gray-900/50 opacity-80'
                      : 'border-gray-800 bg-gray-900/40'
                }`}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-semibold text-white">{m.titolo}</span>
                  {m.korp_nome ? (
                    <span className="rounded bg-violet-800/60 px-1.5 py-0.5 text-[10px] uppercase text-violet-100">
                      {m.korp_nome}
                      {m.esclusiva ? ' · esclusiva' : ''}
                      {korpBonus ? ` ×${m.fattore_applicato}` : ''}
                    </span>
                  ) : null}
                  {m.svolta ? (
                    <span className="inline-flex items-center gap-1 text-[10px] uppercase text-emerald-400">
                      <CheckCircle2 size={12} /> Svolta
                    </span>
                  ) : m.effettuabile ? (
                    <span className="text-[10px] uppercase text-lime-400">Disponibile</span>
                  ) : null}
                </div>
                {m.descrizione ? <p className="mt-1 text-[11px] text-gray-400 line-clamp-2">{m.descrizione}</p> : null}
                <div className={`mt-1 font-mono text-xs ${korpBonus ? 'font-bold text-violet-200' : 'text-lime-200'}`}>
                  {Number(m.reward_crediti || 0).toLocaleString('it-IT')} Cr · {m.reward_prestigio || 0} Pr
                </div>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
