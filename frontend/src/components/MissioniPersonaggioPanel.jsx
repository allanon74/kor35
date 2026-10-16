import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ChevronDown, ListTodo, RefreshCw } from 'lucide-react';
import { getMissioniMie, proponiSoluzioneMissione } from '../api';
import RichHtml from './RichHtml';

export const SOLUZIONE_DISCLAIMER =
  'Invia la soluzione solo se hai compiuto quel che era richiesto ma non hai ricevuto il compenso.';

function premioLabel(m) {
  const cr = Number(m.reward_crediti || 0).toLocaleString('it-IT');
  return `${cr} Cr · ${m.reward_prestigio || 0} Pr`;
}

function TaskCard({ task, open, onToggle, onLogout, personaggioId, onSaved }) {
  const korpBonus = !!task.is_korp_bonus;
  const proposta = task.proposta || null;
  const inAttesa = proposta?.stato === 'IN_ATTESA';
  const rifiutata = proposta?.stato === 'RIFIUTATA';
  const [testo, setTesto] = useState(proposta?.testo || '');
  const [busy, setBusy] = useState(false);
  const [errore, setErrore] = useState('');

  useEffect(() => {
    setTesto(proposta?.testo || '');
  }, [proposta?.id, proposta?.testo, proposta?.stato]);

  const invia = async () => {
    const eventoId = task.evento_soluzione_id || task.eventi_ids?.[0];
    if (!eventoId || !personaggioId) return;
    setBusy(true);
    setErrore('');
    try {
      await proponiSoluzioneMissione({
        missione_id: task.id,
        evento_id: eventoId,
        personaggio_id: Number(personaggioId),
        testo,
      }, onLogout);
      onSaved?.();
    } catch (err) {
      setErrore(err?.message || 'Invio non riuscito');
    } finally {
      setBusy(false);
    }
  };

  return (
    <li
      className={`rounded-lg border ${
        korpBonus
          ? 'border-violet-500/60 bg-violet-950/40'
          : task.svolta
            ? 'border-emerald-900/60 bg-emerald-950/20'
            : 'border-gray-800 bg-gray-900/40'
      }`}
    >
      <button
        type="button"
        onClick={onToggle}
        aria-expanded={open}
        className="flex min-h-11 w-full flex-col gap-1 px-3 py-2 text-left"
      >
        <div className="flex items-start justify-between gap-2">
          <span className="min-w-0 break-words font-semibold text-white">{task.titolo}</span>
          <ChevronDown
            size={16}
            className={`mt-0.5 shrink-0 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          />
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {korpBonus ? (
            <span className="rounded bg-violet-800/60 px-1.5 py-0.5 text-[10px] uppercase text-violet-100">
              Sovrapagata ×{task.fattore_crediti_applicato} Cr · ×{task.fattore_prestigio_applicato} Pr
            </span>
          ) : null}
          {task.svolta ? (
            <span className="inline-flex items-center gap-1 text-[10px] uppercase text-emerald-300">
              <CheckCircle2 size={12} /> Completata
            </span>
          ) : inAttesa ? (
            <span className="text-[10px] uppercase text-amber-300">Soluzione in attesa</span>
          ) : rifiutata ? (
            <span className="text-[10px] uppercase text-red-300">Soluzione rifiutata</span>
          ) : task.effettuabile ? (
            <span className="text-[10px] uppercase text-lime-400">Disponibile</span>
          ) : null}
        </div>
        {!open && task.descrizione ? (
          <p className="text-[11px] text-gray-400 line-clamp-2">{task.descrizione}</p>
        ) : null}
        <div className={`font-mono text-xs ${korpBonus ? 'font-bold text-violet-200' : 'text-lime-200'}`}>
          {premioLabel(task)}
        </div>
      </button>
      {open ? (
        <div className="space-y-3 border-t border-white/5 px-3 py-3">
          {task.descrizione ? (
            <RichHtml content={task.descrizione} className="text-sm text-gray-200" />
          ) : (
            <p className="text-sm text-gray-500">Nessuna descrizione.</p>
          )}
          {task.svolta ? (
            <div className="rounded-lg border border-emerald-800/50 bg-emerald-950/30 px-3 py-2 text-sm text-emerald-100">
              Task completata.
              {proposta?.testo ? (
                <p className="mt-1 whitespace-pre-wrap text-emerald-50/90">{proposta.testo}</p>
              ) : null}
            </div>
          ) : (
            <div className="space-y-2">
              {rifiutata && proposta?.messaggio_rifiuto ? (
                <p className="rounded-lg border border-red-800/60 bg-red-950/40 px-3 py-2 text-sm text-red-100 whitespace-pre-wrap">
                  {proposta.messaggio_rifiuto}
                </p>
              ) : null}
              <label className="block text-xs font-semibold text-gray-300" htmlFor={`soluzione-${task.id}`}>
                Soluzione
                <textarea
                  id={`soluzione-${task.id}`}
                  value={testo}
                  onChange={(e) => setTesto(e.target.value)}
                  rows={4}
                  maxLength={4000}
                  className="mt-1 w-full rounded-lg border border-gray-700 bg-gray-950 px-3 py-2 text-base text-white"
                  placeholder="Descrivi come hai svolto la task"
                />
              </label>
              <p className="text-[11px] leading-snug text-amber-100/90">{SOLUZIONE_DISCLAIMER}</p>
              {errore ? <p className="text-xs text-red-400">{errore}</p> : null}
              <button
                type="button"
                onClick={invia}
                disabled={busy || !testo.trim()}
                className="min-h-11 w-full rounded-lg bg-lime-700 px-4 text-sm font-bold text-white hover:bg-lime-600 disabled:opacity-40 sm:w-auto"
              >
                {busy ? 'Invio…' : inAttesa ? 'Aggiorna soluzione' : 'Invia soluzione'}
              </button>
            </div>
          )}
        </div>
      ) : null}
    </li>
  );
}

function TaskList({ title, hint, rows, empty, openId, setOpenId, onLogout, personaggioId, onSaved }) {
  return (
    <div className="space-y-2">
      <div>
        <h3 className="text-xs font-black uppercase tracking-wide text-gray-300">{title}</h3>
        {hint ? <p className="text-[11px] text-gray-500">{hint}</p> : null}
      </div>
      {rows.length === 0 ? (
        <p className="rounded-xl border border-dashed border-gray-700 bg-gray-900/40 p-4 text-center text-sm text-gray-500">
          {empty}
        </p>
      ) : (
        <ul className="space-y-2">
          {rows.map((task) => (
            <TaskCard
              key={task.id}
              task={task}
              open={openId === task.id}
              onToggle={() => setOpenId((cur) => (cur === task.id ? null : task.id))}
              onLogout={onLogout}
              personaggioId={personaggioId}
              onSaved={onSaved}
            />
          ))}
        </ul>
      )}
    </div>
  );
}

/** Elenco task del PG: sovrapagate della propria KORP evidenziate, senza mittente né allineamento. */
export default function MissioniPersonaggioPanel({
  personaggioId,
  personaggioNome,
  onLogout,
  standalone = false,
}) {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [openId, setOpenId] = useState(null);

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

  useEffect(() => {
    setOpenId(null);
  }, [personaggioId]);

  if (!personaggioId) return null;

  const shellClass = standalone
    ? 'space-y-4'
    : 'rounded-xl border border-lime-900/60 bg-lime-950/20 p-4';
  const aperte = rows.filter((row) => !row.svolta);
  const completate = rows.filter((row) => row.svolta);

  return (
    <section className={`min-w-0 ${shellClass}`}>
      <div className="flex items-start justify-between gap-3">
        <div className="flex min-w-0 items-center gap-2">
          <ListTodo className="shrink-0 text-lime-400" size={standalone ? 24 : 20} />
          <div className="min-w-0">
            <h2 className={`font-black uppercase tracking-wide text-lime-200 ${standalone ? 'text-lg' : 'text-sm'}`}>
              Tasks
            </h2>
            {standalone && personaggioNome ? (
              <p className="truncate text-xs text-gray-400">{personaggioNome}</p>
            ) : null}
            {standalone ? (
              <p className="mt-1 text-xs text-gray-500">
                Apri una task per leggere la descrizione. Quelle evidenziate sono sovrapagate per la tua KORP.
              </p>
            ) : null}
          </div>
        </div>
        <button
          type="button"
          onClick={load}
          disabled={loading}
          className="min-h-11 shrink-0 rounded-lg border border-gray-700 bg-gray-900/60 px-3 text-gray-300 hover:border-lime-700 hover:text-white disabled:opacity-40"
          aria-label="Aggiorna task"
          title="Aggiorna"
        >
          <RefreshCw size={16} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>
      {error ? <p className="text-xs text-red-400">{error}</p> : null}
      {loading && rows.length === 0 ? (
        <p className="text-xs text-gray-500">Caricamento…</p>
      ) : (
        <div className="space-y-5">
          <TaskList
            title="Da svolgere"
            rows={aperte}
            empty="Nessuna task da svolgere per l'evento attivo."
            openId={openId}
            setOpenId={setOpenId}
            onLogout={onLogout}
            personaggioId={personaggioId}
            onSaved={load}
          />
          <TaskList
            title="Completate"
            hint="Restano qui anche dopo che lo staff ha accettato la soluzione."
            rows={completate}
            empty="Nessuna task completata in questo evento."
            openId={openId}
            setOpenId={setOpenId}
            onLogout={onLogout}
            personaggioId={personaggioId}
            onSaved={load}
          />
        </div>
      )}
    </section>
  );
}
