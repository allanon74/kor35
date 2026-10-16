import React, { useCallback, useEffect, useState } from 'react';
import { Check, X } from 'lucide-react';
import { accettaMissioneProposta, getMissioniProposte, rifiutaMissioneProposta } from '../../api';

const TIPO_LABEL = {
  MANUALE: 'Generale',
  QUEST: 'Quest',
  TECNICA: 'Tecnica',
  POST_SOCIAL: 'Post social',
};

/**
 * Coda staff: soluzioni inviate dai personaggi.
 * Accetta accredita la task; rifiuta invia il messaggio al PG.
 */
export default function MissioniPropostePanel({ onLogout, className = '' }) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [busyId, setBusyId] = useState(null);
  const [rifiutoId, setRifiutoId] = useState(null);
  const [messaggio, setMessaggio] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const data = await getMissioniProposte({ stato: 'IN_ATTESA' }, onLogout);
      setRows(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err?.message || 'Impossibile caricare le soluzioni');
      setRows([]);
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => { load(); }, [load]);

  const accetta = async (row) => {
    setBusyId(row.id);
    setError('');
    try {
      await accettaMissioneProposta(row.id, onLogout);
      setRifiutoId(null);
      await load();
    } catch (err) {
      setError(err?.message || 'Accettazione non riuscita');
    } finally {
      setBusyId(null);
    }
  };

  const rifiuta = async (row) => {
    const testo = messaggio.trim();
    if (!testo) {
      setError('Scrivi il messaggio da inviare al giocatore.');
      return;
    }
    setBusyId(row.id);
    setError('');
    try {
      await rifiutaMissioneProposta(row.id, testo, onLogout);
      setRifiutoId(null);
      setMessaggio('');
      await load();
    } catch (err) {
      setError(err?.message || 'Rifiuto non riuscito');
    } finally {
      setBusyId(null);
    }
  };

  return (
    <section className={`rounded-xl border border-amber-900/50 bg-amber-950/20 p-4 ${className}`.trim()}>
      <div className="mb-2 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <h3 className="text-xs font-black uppercase tracking-wide text-amber-100">
            Soluzioni da verificare
            {rows.length ? <span className="ml-2 text-amber-300">{rows.length}</span> : null}
          </h3>
          <p className="mt-1 text-[11px] text-gray-400">
            Accetta per segnare la task risolta e accreditare il premio, oppure rifiuta con un messaggio al personaggio.
          </p>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="min-h-11 shrink-0 rounded border border-gray-700 px-3 text-[10px] font-bold uppercase text-gray-300 hover:border-amber-700 disabled:opacity-40"
        >
          {loading ? '…' : 'Aggiorna'}
        </button>
      </div>
      {error ? <p className="mb-2 text-xs text-red-400">{error}</p> : null}
      {loading && rows.length === 0 ? (
        <p className="text-xs text-gray-500">Caricamento…</p>
      ) : rows.length === 0 ? (
        <p className="text-xs text-gray-500">Nessuna soluzione in attesa.</p>
      ) : (
        <ul className="min-w-0 space-y-2">
          {rows.map((row) => {
            const busy = busyId === row.id;
            const aperto = rifiutoId === row.id;
            return (
              <li key={row.id} className="rounded-lg border border-gray-800 bg-gray-950/50 p-3">
                <div className="flex flex-wrap items-baseline justify-between gap-2">
                  <p className="min-w-0 break-words text-sm font-semibold text-white">{row.missione_titolo}</p>
                  <span className="text-[10px] uppercase text-gray-500">
                    {TIPO_LABEL[row.tipo_risoluzione] || row.tipo_risoluzione}
                  </span>
                </div>
                <p className="mt-0.5 break-words text-xs text-lime-200">
                  {row.personaggio_nome}
                  {row.evento_titolo ? <span className="text-gray-500"> · {row.evento_titolo}</span> : null}
                </p>
                <p className="mt-2 whitespace-pre-wrap break-words text-sm text-gray-200">{row.testo}</p>
                <div className="mt-3 flex flex-col gap-2 sm:flex-row">
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => accetta(row)}
                    className="inline-flex min-h-11 items-center justify-center gap-1 rounded-lg bg-lime-700 px-3 text-xs font-bold uppercase text-white hover:bg-lime-600 disabled:opacity-40"
                  >
                    <Check size={14} /> Accetta
                  </button>
                  <button
                    type="button"
                    disabled={busy}
                    onClick={() => {
                      setRifiutoId(aperto ? null : row.id);
                      setMessaggio('');
                      setError('');
                    }}
                    className="inline-flex min-h-11 items-center justify-center gap-1 rounded-lg border border-red-800 bg-red-950/40 px-3 text-xs font-bold uppercase text-red-100 hover:bg-red-900/40 disabled:opacity-40"
                  >
                    <X size={14} /> Rifiuta
                  </button>
                </div>
                {aperto ? (
                  <div className="mt-2 space-y-2">
                    <label className="block text-[11px] font-semibold text-gray-300" htmlFor={`rifiuto-${row.id}`}>
                      Messaggio per il giocatore
                      <textarea
                        id={`rifiuto-${row.id}`}
                        value={messaggio}
                        onChange={(e) => setMessaggio(e.target.value)}
                        rows={3}
                        maxLength={2000}
                        className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-base text-white"
                        placeholder="Spiega perché la soluzione non è accettata"
                      />
                    </label>
                    <button
                      type="button"
                      disabled={busy || !messaggio.trim()}
                      onClick={() => rifiuta(row)}
                      className="min-h-11 w-full rounded-lg bg-red-800 px-3 text-xs font-bold uppercase text-white hover:bg-red-700 disabled:opacity-40 sm:w-auto"
                    >
                      Invia rifiuto
                    </button>
                  </div>
                ) : null}
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
