import React, { useCallback, useEffect, useState } from 'react';
import {
  staffCreatePilotProtocollo,
  staffDeletePilotProtocollo,
  staffGetPilotDipartimentiKorp,
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
  { id: 'bianco', label: 'Bianco — medico' },
  { id: 'crociera', label: 'Verde — crociera' },
];

const protocolloVuoto = () => ({
  colore: 'ambra',
  korp: '',
  testo: 'Riparare {sottosistema}.',
  testo_audio: 'Allarme Ambra. Squadra tecnica su {sottosistema}.',
  attivo: true,
});

/**
 * Protocolli colore → dipartimento KORP, testo ai membri e audio di plancia.
 * Le KORP si creano in Carriere e KORP.
 */
export default function ComunicazioniStaffPanel({ onLogout }) {
  const [dipartimenti, setDipartimenti] = useState([]);
  const [protocolli, setProtocolli] = useState([]);
  const [protocollo, setProtocollo] = useState(protocolloVuoto);
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    const [lista, prot] = await Promise.all([
      staffGetPilotDipartimentiKorp(onLogout),
      staffGetPilotProtocolli(onLogout),
    ]);
    setDipartimenti(Array.isArray(lista) ? lista : []);
    setProtocolli(Array.isArray(prot) ? prot : (prot?.results || []));
  }, [onLogout]);

  useEffect(() => {
    load().catch((err) => setError(err?.message || 'Caricamento comunicazioni non riuscito.'));
  }, [load]);

  const creaProtocollo = async () => {
    setError('');
    try {
      await staffCreatePilotProtocollo({
        colore: protocollo.colore,
        korp: protocollo.korp || null,
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
          Ogni colore manda un testo ai personaggi della KORP e una frase all&apos;audio della plancia.
          Le KORP, i dipartimenti, si creano in Carriere e KORP.
          La frase letta in plancia si modifica anche in Allarmi.
          Nel testo puoi usare {'{sottosistema}'} e {'{evento}'}.
          Sull&apos;ambra i sottosistemi offline vengono sempre nominati, nel messaggio e nell&apos;audio.
        </p>
      </div>

      {error ? <p className="text-sm text-red-300">{error}</p> : null}

      <div className="space-y-2">
        <h4 className="text-sm font-semibold text-gray-200">Protocollo colore</h4>
        {dipartimenti.length === 0 ? (
          <p className="text-sm text-gray-500">
            Nessuna KORP. Creala in Carriere e KORP, poi assegna i personaggi in Appartenenze.
          </p>
        ) : null}
        <div className="flex flex-wrap gap-2 items-end">
          <label className="flex flex-col text-xs text-gray-400 gap-1">
            Colore
            <select className="bg-gray-800 rounded px-2 py-1 text-sm" value={protocollo.colore} onChange={(e) => setProtocollo((p) => ({ ...p, colore: e.target.value }))}>
              {COLORI.map((c) => <option key={c.id} value={c.id}>{c.label}</option>)}
            </select>
          </label>
          <label className="flex flex-col text-xs text-gray-400 gap-1 flex-1 min-w-[12rem]">
            Dipartimento (KORP)
            <select className="bg-gray-800 rounded px-2 py-1 text-sm" value={protocollo.korp} onChange={(e) => setProtocollo((p) => ({ ...p, korp: e.target.value }))}>
              <option value="">— nessuno —</option>
              {dipartimenti.map((d) => (
                <option key={d.id} value={d.id}>{d.nome} — {Number(d.membri || 0)} membri</option>
              ))}
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
          <p className="text-sm text-gray-500">Nessun protocollo. Senza protocollo il colore usa solo l&apos;annuncio standard. L&apos;ambra nomina comunque i guasti in plancia.</p>
        ) : protocolli.map((row) => (
          <div key={row.id} className="bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            <div className="flex justify-between gap-2">
              <span>
                {row.colore} → {row.korp_nome || 'nessun dipartimento'}
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
