import React, { useCallback, useEffect, useRef, useState } from 'react';
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
  return Object.fromEntries(ALLARMI.map((a) => [a.id, {
    testo_audio: '',
    testo: '',
    korp: '',
    campione_url: '',
  }]));
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
  const fileRefs = useRef({});

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
        campione_url: row.campione_url || '',
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
    const file = fileRefs.current[colore]?.files?.[0];
    try {
      let id = esistente?.id;
      if (id) {
        await staffUpdatePilotProtocollo(id, payload, onLogout);
      } else {
        const created = await staffCreatePilotProtocollo({ ...payload, colore }, onLogout);
        id = created?.id;
      }
      if (file && id) {
        const fd = new FormData();
        fd.append('campione', file);
        await staffUpdatePilotProtocollo(id, fd, onLogout);
        if (fileRefs.current[colore]) fileRefs.current[colore].value = '';
      }
      setSalvo(colore);
      await load();
    } catch (err) {
      setError(err?.message || 'Salvataggio non riuscito.');
    }
  };

  const rimuoviCampione = async (colore) => {
    setError('');
    setSalvo('');
    const esistente = protocolli.find((row) => row.colore === colore);
    if (!esistente) return;
    try {
      await staffUpdatePilotProtocollo(esistente.id, { rimuovi_campione: true }, onLogout);
      setSalvo(colore);
      await load();
    } catch (err) {
      setError(err?.message || 'Rimozione audio non riuscita.');
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
          Il campione (mp3, wav, ogg, m4a o webm, fino a 8 MB) parte prima della voce.
          Vale per tutti i colori, anche giallo, rosso, nero, blu e crociera:
          se non carichi nulla, quei cinque usano ancora il file statico
          {' '}/pilot/sounds/allarmi/&lt;colore&gt;.mp3 se è presente sul server.
          Ambra, viola e bianco restano solo voce finché non carichi un campione.
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {dipartimenti.length === 0 ? (
        <p className="text-sm text-gray-500">Nessuna KORP. Creala in Carriere e KORP, poi assegna i personaggi.</p>
      ) : null}
      {ALLARMI.map((allarme) => {
        const bozza = bozze[allarme.id] || { testo_audio: '', testo: '', korp: '', campione_url: '' };
        return (
          <div key={allarme.id} className="rounded-lg border border-gray-700 p-3 space-y-2">
            <h4 className="text-sm font-semibold text-gray-100">{allarme.label}</h4>
            <p className="text-xs text-gray-500">Standard: {allarme.standard}</p>
            <div className="flex flex-col text-xs text-gray-400 gap-1">
              Campione audio
              {bozza.campione_url ? (
                <audio controls preload="none" src={bozza.campione_url} className="w-full max-w-md" />
              ) : (
                <span className="text-gray-500">Nessun file caricato.</span>
              )}
              <input
                ref={(node) => { fileRefs.current[allarme.id] = node; }}
                type="file"
                accept="audio/mpeg,audio/wav,audio/ogg,audio/mp4,audio/webm,.mp3,.wav,.ogg,.m4a,.webm"
                className="text-sm text-gray-200"
              />
              <span className="text-gray-500">Si carica insieme a Salva.</span>
              {bozza.campione_url ? (
                <button
                  type="button"
                  className="self-start px-2 py-1 rounded border border-gray-600 text-xs"
                  onClick={() => rimuoviCampione(allarme.id)}
                >
                  Rimuovi campione
                </button>
              ) : null}
            </div>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Frase letta dopo il campione
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
