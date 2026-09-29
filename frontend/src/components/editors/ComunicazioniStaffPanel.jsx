import React, { useCallback, useEffect, useState } from 'react';
import {
  staffCercaPersonaggiBreve,
  staffCreatePilotDipartimento,
  staffCreatePilotProtocollo,
  staffDeletePilotDipartimento,
  staffDeletePilotProtocollo,
  staffGetPilotDipartimenti,
  staffGetPilotProtocolli,
  staffUpdatePilotProtocollo,
} from '../../api';

const COLORI = [
  { id: 'giallo', label: 'Giallo — allerta' },
  { id: 'rosso', label: 'Rosso — combattimento' },
  { id: 'nero', label: 'Nero — esotico' },
  { id: 'blu', label: 'Blu — manovra' },
  { id: 'ambra', label: 'Ambra — riparazione sottosistema' },
  { id: 'viola', label: 'Viola — invasione' },
];

const protocolloVuoto = () => ({
  colore: 'ambra',
  dipartimento: '',
  testo: 'Riparare {sottosistema}.',
  testo_audio: 'Allarme Ambra. Squadra tecnica su {sottosistema}.',
  attivo: true,
});

/**
 * Dipartimenti di bordo e protocollo colore → testo + audio di plancia.
 */
export default function ComunicazioniStaffPanel({ onLogout }) {
  const [dipartimenti, setDipartimenti] = useState([]);
  const [protocolli, setProtocolli] = useState([]);
  const [nome, setNome] = useState('');
  const [ricerca, setRicerca] = useState('');
  const [trovati, setTrovati] = useState([]);
  const [selezionati, setSelezionati] = useState([]);
  const [protocollo, setProtocollo] = useState(protocolloVuoto);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [dip, prot] = await Promise.all([
      staffGetPilotDipartimenti(onLogout),
      staffGetPilotProtocolli(onLogout),
    ]);
    setDipartimenti(Array.isArray(dip) ? dip : (dip?.results || []));
    setProtocolli(Array.isArray(prot) ? prot : (prot?.results || []));
  }, [onLogout]);

  useEffect(() => {
    load().catch((err) => setError(err?.message || 'Caricamento comunicazioni non riuscito.'));
  }, [load]);

  useEffect(() => {
    const q = ricerca.trim();
    if (q.length < 2) {
      setTrovati([]);
      return undefined;
    }
    const timer = window.setTimeout(() => {
      staffCercaPersonaggiBreve(q, onLogout)
        .then((rows) => setTrovati(Array.isArray(rows) ? rows : []))
        .catch(() => setTrovati([]));
    }, 250);
    return () => window.clearTimeout(timer);
  }, [ricerca, onLogout]);

  const aggiungiMembro = (persona) => {
    setSelezionati((prev) => (
      prev.some((p) => String(p.id) === String(persona.id)) ? prev : [...prev, persona]
    ));
  };

  const creaDipartimento = async () => {
    const label = nome.trim();
    if (!label) {
      setError('Il nome del dipartimento è obbligatorio.');
      return;
    }
    setError('');
    try {
      await staffCreatePilotDipartimento({
        nome: label,
        attivo: true,
        membri_ids: selezionati.map((p) => p.id),
      }, onLogout);
      setNome('');
      setSelezionati([]);
      setRicerca('');
      await load();
    } catch (err) {
      setError(err?.message || 'Dipartimento non creato.');
    }
  };

  const creaProtocollo = async () => {
    setError('');
    try {
      await staffCreatePilotProtocollo({
        colore: protocollo.colore,
        dipartimento: protocollo.dipartimento || null,
        testo: protocollo.testo,
        testo_audio: protocollo.testo_audio,
        attivo: true,
      }, onLogout);
      setProtocollo(protocolloVuoto());
      await load();
    } catch (err) {
      setError(err?.message || 'Protocollo non creato. Un colore può avere un solo protocollo.');
    }
  };

  return (
    <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60 space-y-6">
      <div>
        <h3 className="font-semibold mb-1">Comunicazioni</h3>
        <p className="text-xs text-gray-400">
          Ogni colore manda un testo ai membri del dipartimento e una frase all&apos;audio della plancia.
          Nel testo puoi usare {'{sottosistema}'} e {'{evento}'}.
        </p>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-200">Nuovo dipartimento</h4>
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex flex-col text-xs text-gray-400 gap-1 flex-1 min-w-[12rem]">
            Nome
            <input className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="Ingegneria, Sicurezza…" />
          </label>
          <button type="button" className="px-3 py-1 rounded bg-indigo-600" onClick={creaDipartimento}>Aggiungi</button>
        </div>
        <label className="flex flex-col text-xs text-gray-400 gap-1">
          Cerca personaggi da associare
          <input className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100" value={ricerca} onChange={(e) => setRicerca(e.target.value)} placeholder="Almeno 2 lettere" />
        </label>
        {trovati.length ? (
          <div className="flex flex-wrap gap-2">
            {trovati.map((p) => (
              <button key={p.id} type="button" className="text-xs px-2 py-1 rounded bg-gray-800" onClick={() => aggiungiMembro(p)}>
                {p.nome}
              </button>
            ))}
          </div>
        ) : null}
        {selezionati.length ? (
          <p className="text-xs text-gray-300">
            Membri: {selezionati.map((p) => p.nome).join(', ')}
            <button type="button" className="ml-2 text-gray-400" onClick={() => setSelezionati([])}>svuota</button>
          </p>
        ) : null}
        {dipartimenti.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun dipartimento.</p>
        ) : dipartimenti.map((row) => (
          <div key={row.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm gap-2">
            <span>
              {row.nome}
              <span className="text-gray-400"> · {(row.membri || []).map((m) => m.nome).join(', ') || 'nessun membro'}</span>
              {row.attivo === false ? <span className="text-amber-400"> · spento</span> : null}
            </span>
            <button
              type="button"
              className="text-red-400 shrink-0"
              onClick={() => staffDeletePilotDipartimento(row.id, onLogout).then(load).catch((err) => setError(err?.message || 'Eliminazione non riuscita.'))}
            >
              Elimina
            </button>
          </div>
        ))}
      </div>

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-200">Protocollo colore</h4>
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex flex-col text-xs text-gray-400 gap-1">
            Colore
            <select className="bg-gray-800 rounded px-2 py-1 text-sm" value={protocollo.colore} onChange={(e) => setProtocollo((p) => ({ ...p, colore: e.target.value }))}>
              {COLORI.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </label>
          <label className="flex flex-col text-xs text-gray-400 gap-1 flex-1 min-w-[10rem]">
            Dipartimento
            <select className="bg-gray-800 rounded px-2 py-1 text-sm" value={protocollo.dipartimento} onChange={(e) => setProtocollo((p) => ({ ...p, dipartimento: e.target.value }))}>
              <option value="">— nessuno —</option>
              {dipartimenti.map((d) => <option key={d.id} value={d.id}>{d.nome}</option>)}
            </select>
          </label>
        </div>
        <label className="flex flex-col text-xs text-gray-400 gap-1">
          Testo ai membri
          <textarea className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-[4rem]" value={protocollo.testo} onChange={(e) => setProtocollo((p) => ({ ...p, testo: e.target.value }))} />
        </label>
        <label className="flex flex-col text-xs text-gray-400 gap-1">
          Audio della plancia
          <textarea className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-[3rem]" value={protocollo.testo_audio} onChange={(e) => setProtocollo((p) => ({ ...p, testo_audio: e.target.value }))} />
        </label>
        <button type="button" className="px-3 py-1 rounded bg-indigo-600" onClick={creaProtocollo}>Aggiungi protocollo</button>
        {protocolli.length === 0 ? (
          <p className="text-sm text-gray-500">Nessun protocollo. Senza protocollo il colore usa solo l&apos;annuncio standard.</p>
        ) : protocolli.map((row) => (
          <div key={row.id} className="bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            <div className="flex justify-between gap-2">
              <span>
                {row.colore} → {row.dipartimento_nome || 'nessun dipartimento'}
                {row.attivo === false ? <span className="text-amber-400"> · spento</span> : null}
              </span>
              <span className="flex gap-3 shrink-0">
                <button
                  type="button"
                  className="text-gray-300"
                  onClick={() => staffUpdatePilotProtocollo(row.id, { attivo: row.attivo === false }, onLogout).then(load)}
                >
                  {row.attivo === false ? 'Attiva' : 'Spegni'}
                </button>
                <button
                  type="button"
                  className="text-red-400"
                  onClick={() => staffDeletePilotProtocollo(row.id, onLogout).then(load).catch((err) => setError(err?.message || 'Eliminazione non riuscita.'))}
                >
                  Elimina
                </button>
              </span>
            </div>
            {row.testo ? <p className="text-xs text-gray-400 mt-1">{row.testo}</p> : null}
          </div>
        ))}
      </div>
    </section>
  );
}
