import React, { useCallback, useEffect, useState } from 'react';
import {
  staffCreatePilotProtocollo,
  staffGetPilotDipartimentiKorp,
  staffGetPilotProtocolli,
  staffUpdatePilotProtocollo,
} from '../../api';

const ALLARMI = [
  { id: 'giallo', label: 'Giallo — allerta', standard: 'Allarme Giallo. Condizione di allerta dell\'equipaggio.' },
  { id: 'rosso', label: 'Rosso — combattimento', standard: 'Allarme Rosso. Tutti ai posti di combattimento. Questa non è un\'esercitazione.' },
  { id: 'nero', label: 'Nero — esotico', standard: 'Allarme Nero. Sistema esotico in attivazione. Prepararsi a condizioni impreviste.' },
  { id: 'blu', label: 'Blu — manovra', standard: 'Allarme Blu. Manovre atmosferiche in corso, prepararsi a scompensi nel volo.' },
  { id: 'ambra', label: 'Ambra — riparazione', standard: 'Allarme Ambra. Squadra tecnica al sottosistema guasto.' },
  { id: 'viola', label: 'Viola — invasione', standard: 'Allarme Viola. Sicurezza, intercettare gli invasori.' },
  { id: 'bianco', label: 'Bianco — medico', standard: 'Allarme Bianco. Personale medico, pronto intervento.' },
  { id: 'crociera', label: 'Verde — crociera', standard: 'Allarme Verde. Ripristino condizione di crociera. Nessun allarme attivo.' },
];

function vuoto() {
  return Object.fromEntries(ALLARMI.map((a) => [a.id, { testo_audio: '', testo: '', korp: '' }]));
}

/**
 * Frase audio di ogni allarme cromatico, più KORP e testo ai membri.
 * Vuoto in audio = annuncio standard letto dalla plancia.
 */
export default function AllarmiStaffPanel({ onLogout }) {
  const [protocolli, setProtocolli] = useState([]);
  const [dipartimenti, setDipartimenti] = useState([]);
  const [bozze, setBozze] = useState(vuoto);
  const [error, setError] = useState('');
  const [salvo, setSalvo] = useState('');

  const load = useCallback(async () => {
    const [prot, dip] = await Promise.all([
      staffGetPilotProtocolli(onLogout),
      staffGetPilotDipartimentiKorp(onLogout),
    ]);
    const rows = Array.isArray(prot) ? prot : (prot?.results || []);
    setProtocolli(rows);
    setDipartimenti(Array.isArray(dip) ? dip : []);
    const next = vuoto();
    rows.forEach((row) => {
      if (!next[row.colore]) return;
      next[row.colore] = {
        testo_audio: row.testo_audio || '',
        testo: row.testo || '',
        korp: row.korp ? String(row.korp) : '',
      };
    });
    setBozze(next);
  }, [onLogout]);

  useEffect(() => {
    load().catch((err) => setError(err?.message || 'Caricamento allarmi non riuscito.'));
  }, [load]);

  const patch = (colore, campo, valore) => {
    setBozze((prev) => ({
      ...prev,
      [colore]: { ...prev[colore], [campo]: valore },
    }));
  };

  const salva = async (colore) => {
    setError('');
    setSalvo('');
    const bozza = bozze[colore] || { testo_audio: '', testo: '', korp: '' };
    const payload = {
      testo_audio: bozza.testo_audio,
      testo: bozza.testo,
      korp: bozza.korp || null,
      attivo: true,
    };
    const esistente = protocolli.find((row) => row.colore === colore);
    try {
      if (esistente) {
        await staffUpdatePilotProtocollo(esistente.id, payload, onLogout);
      } else {
        await staffCreatePilotProtocollo({ ...payload, colore }, onLogout);
      }
      setSalvo(colore);
      await load();
    } catch (err) {
      setError(err?.message || 'Salvataggio non riuscito.');
    }
  };

  return (
    <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60 space-y-4">
      <div>
        <h3 className="font-semibold mb-1">Allarmi</h3>
        <p className="text-xs text-gray-400">
          Ogni colore ha una frase letta dagli speaker della console di pilotaggio.
          Se la lasci vuota, la plancia usa l&apos;annuncio standard.
          Il testo, con {'{sottosistema}'} e {'{evento}'}, arriva ai membri della KORP.
          Il bianco è l&apos;allarme medico: scegli la KORP del personale medico.
          Sull&apos;ambra i sottosistemi offline vengono aggiunti anche se non usi il segnaposto.
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {dipartimenti.length === 0 ? (
        <p className="text-sm text-gray-500">Nessuna KORP. Creala in Carriere e KORP, poi assegna i personaggi.</p>
      ) : null}
      {ALLARMI.map((allarme) => {
        const bozza = bozze[allarme.id] || { testo_audio: '', testo: '', korp: '' };
        return (
          <div key={allarme.id} className="rounded-lg border border-gray-700 p-3 space-y-2">
            <h4 className="text-sm font-semibold text-gray-100">{allarme.label}</h4>
            <p className="text-xs text-gray-500">Standard: {allarme.standard}</p>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Audio della plancia
              <textarea
                className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-[3rem]"
                value={bozza.testo_audio}
                placeholder={allarme.standard}
                onChange={(e) => patch(allarme.id, 'testo_audio', e.target.value)}
              />
            </label>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Dipartimento (KORP)
              <select
                className="bg-gray-800 rounded px-2 py-1 text-sm"
                value={bozza.korp}
                onChange={(e) => patch(allarme.id, 'korp', e.target.value)}
              >
                <option value="">— nessuno —</option>
                {dipartimenti.map((d) => (
                  <option key={d.id} value={d.id}>{d.nome} — {Number(d.membri || 0)} membri</option>
                ))}
              </select>
            </label>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Testo ai membri
              <textarea
                className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-[3rem]"
                value={bozza.testo}
                onChange={(e) => patch(allarme.id, 'testo', e.target.value)}
              />
            </label>
            <button type="button" className="px-3 py-1 rounded bg-indigo-600 text-sm" onClick={() => salva(allarme.id)}>
              Salva {allarme.label.split(' — ')[0]}
            </button>
            {salvo === allarme.id ? <span className="ml-2 text-xs text-emerald-300">Salvato.</span> : null}
          </div>
        );
      })}
    </section>
  );
}
