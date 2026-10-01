import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  staffCreatePilotProtocollo,
  staffGetPilotDipartimentiKorp,
  staffGetPilotProtocolli,
  staffUpdatePilotProtocollo,
} from '../../api';
import {
  previewAlarmAnnouncement,
  resolveStaffAlarmSampleUrl,
  stopAlarmPreview,
} from '../../lib/pilotAlarmPreview';

const ALLARMI = [
  { id: 'giallo', label: 'Giallo — allerta', standard: 'Allarme Giallo. Condizione di allerta dell\'equipaggio.', ordine: 10 },
  { id: 'rosso', label: 'Rosso — combattimento', standard: 'Allarme Rosso. Tutti ai posti di combattimento. Questa non è un\'esercitazione.', ordine: 20 },
  { id: 'nero', label: 'Nero — esotico', standard: 'Allarme Nero. Sistema esotico in attivazione. Prepararsi a condizioni impreviste.', ordine: 30 },
  { id: 'blu', label: 'Blu — manovra', standard: 'Allarme Blu. Manovre atmosferiche in corso, prepararsi a scompensi nel volo.', ordine: 40 },
  { id: 'ambra', label: 'Ambra — riparazione', standard: 'Allarme Ambra. Squadra tecnica al sottosistema guasto.', ordine: 50 },
  { id: 'viola', label: 'Viola — invasione', standard: 'Allarme Viola. Sicurezza, intercettare gli invasori.', ordine: 60 },
  { id: 'bianco', label: 'Bianco — medico', standard: 'Allarme Bianco. Personale medico, pronto intervento.', ordine: 70 },
  { id: 'crociera', label: 'Verde — crociera', standard: 'Allarme Verde. Ripristino condizione di crociera. Nessun allarme attivo.', ordine: 80 },
];

function vuoto() {
  return Object.fromEntries(ALLARMI.map((a) => [a.id, {
    testo_audio: '',
    testo: '',
    korp: '',
    campione_url: '',
    ordine: a.ordine,
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
  const [previewing, setPreviewing] = useState('');
  const fileRefs = useRef({});
  const objectUrlRef = useRef('');

  const revokeObjectUrl = useCallback(() => {
    if (objectUrlRef.current) {
      URL.revokeObjectURL(objectUrlRef.current);
      objectUrlRef.current = '';
    }
  }, []);

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
      const meta = ALLARMI.find((a) => a.id === row.colore);
      const ordineRaw = Number(row.ordine);
      next[row.colore] = {
        testo_audio: row.testo_audio || '',
        testo: row.testo || '',
        korp: row.korp ? String(row.korp) : '',
        campione_url: row.campione_url || '',
        ordine: Number.isFinite(ordineRaw) && ordineRaw > 0
          ? ordineRaw
          : (meta?.ordine ?? 0),
      };
    });
    setBozze(next);
  }, [onLogout]);

  useEffect(() => {
    load().catch((err) => setError(err?.message || 'Caricamento allarmi non riuscito.'));
  }, [load]);

  useEffect(() => () => {
    stopAlarmPreview();
    revokeObjectUrl();
  }, [revokeObjectUrl]);

  const patch = (colore, campo, valore) => {
    setBozze((prev) => ({
      ...prev,
      [colore]: { ...prev[colore], [campo]: valore },
    }));
  };

  const resolveCampionePerAnteprima = (colore) => {
    revokeObjectUrl();
    const file = fileRefs.current[colore]?.files?.[0];
    if (file) {
      const url = URL.createObjectURL(file);
      objectUrlRef.current = url;
      return url;
    }
    const bozza = bozze[colore] || {};
    return resolveStaffAlarmSampleUrl(colore, bozza.campione_url || '');
  };

  const anteprima = async (colore) => {
    setError('');
    const meta = ALLARMI.find((a) => a.id === colore);
    const bozza = bozze[colore] || {};
    const frase = String(bozza.testo_audio || '').trim() || (meta?.standard || '');
    if (!frase) {
      setError('Nessuna frase da leggere per questo allarme.');
      return;
    }
    const campioneUrl = resolveCampionePerAnteprima(colore);
    setPreviewing(colore);
    try {
      await previewAlarmAnnouncement({
        allarmeId: colore,
        testo: frase,
        campioneUrl,
      });
    } catch (err) {
      setError(err?.message || 'Anteprima non riuscita.');
    } finally {
      setPreviewing((cur) => (cur === colore ? '' : cur));
      revokeObjectUrl();
    }
  };

  const fermaAnteprima = () => {
    stopAlarmPreview();
    setPreviewing('');
    revokeObjectUrl();
  };

  const salva = async (colore) => {
    setError('');
    setSalvo('');
    const meta = ALLARMI.find((a) => a.id === colore);
    const bozza = bozze[colore] || { testo_audio: '', testo: '', korp: '', ordine: meta?.ordine ?? 0 };
    const ordineNum = Number(bozza.ordine);
    const payload = {
      testo_audio: bozza.testo_audio,
      testo: bozza.testo,
      korp: bozza.korp || null,
      ordine: Number.isFinite(ordineNum) ? Math.max(0, Math.trunc(ordineNum)) : (meta?.ordine ?? 0),
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
          Il campione (mp3, wav, ogg, m4a o webm, fino a 8 MB) parte subito; la frase entra dopo un secondo e mezzo, sopra il suono. Se il campione finisce prima resta solo la voce. Se la frase finisce prima, il suono resta due secondi e poi sfuma in due secondi.
          Vale per tutti i colori, anche giallo, rosso, nero, blu e crociera:
          se non carichi nulla, quei cinque usano ancora il file statico
          {' '}/pilot/sounds/allarmi/&lt;colore&gt;.mp3 se è presente sul server.
          Ambra, viola e bianco restano solo voce finché non carichi un campione.
          <strong className="font-semibold text-gray-300"> Ordine</strong> decide la posizione
          del pulsante sulla console radio (numeri più bassi = più a sinistra / in alto).
          Usa <strong className="font-semibold text-gray-300">Anteprima</strong> per
          ascoltare campione + voce come sulla plancia (anche il file scelto ma non ancora salvato).
        </p>
      </div>
      {error ? <p className="text-sm text-red-300">{error}</p> : null}
      {dipartimenti.length === 0 ? (
        <p className="text-sm text-gray-500">Nessuna KORP. Creala in Carriere e KORP, poi assegna i personaggi.</p>
      ) : null}
      {[...ALLARMI]
        .sort((a, b) => {
          const oa = Number(bozze[a.id]?.ordine ?? a.ordine);
          const ob = Number(bozze[b.id]?.ordine ?? b.ordine);
          if (oa !== ob) return oa - ob;
          return String(a.id).localeCompare(String(b.id));
        })
        .map((allarme) => {
        const bozza = bozze[allarme.id] || {
          testo_audio: '', testo: '', korp: '', campione_url: '', ordine: allarme.ordine,
        };
        const isPreview = previewing === allarme.id;
        return (
          <div key={allarme.id} className="rounded-lg border border-gray-700 p-3 space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <h4 className="text-sm font-semibold text-gray-100">{allarme.label}</h4>
              <label className="flex items-center gap-2 text-xs text-gray-400">
                Ordine layout
                <input
                  type="number"
                  min={0}
                  step={1}
                  className="w-20 bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-11"
                  value={bozza.ordine}
                  onChange={(e) => patch(allarme.id, 'ordine', e.target.value)}
                />
              </label>
            </div>
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
                  className="self-start min-h-11 px-3 py-2 rounded border border-gray-600 text-xs"
                  onClick={() => rimuoviCampione(allarme.id)}
                >
                  Rimuovi campione
                </button>
              ) : null}
            </div>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Frase letta sopra il campione
              <textarea
                className="bg-gray-800 rounded px-2 py-1 text-sm text-gray-100 min-h-[3rem]"
                value={bozza.testo_audio}
                placeholder={allarme.standard}
                onChange={(e) => patch(allarme.id, 'testo_audio', e.target.value)}
              />
            </label>
            <label className="flex flex-col text-xs text-gray-400 gap-1">
              Dipartimento (KORP o dipartimento)
              <select
                className="bg-gray-800 rounded px-2 py-1 text-sm min-h-11"
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
            <div className="flex flex-wrap items-center gap-2">
              <button
                type="button"
                className="min-h-11 px-3 py-2 rounded bg-indigo-600 text-sm font-semibold"
                onClick={() => salva(allarme.id)}
              >
                Salva {allarme.label.split(' — ')[0]}
              </button>
              <button
                type="button"
                className="min-h-11 px-3 py-2 rounded bg-emerald-700 hover:bg-emerald-600 text-sm font-semibold disabled:opacity-60"
                disabled={Boolean(previewing) && !isPreview}
                onClick={() => (isPreview ? fermaAnteprima() : anteprima(allarme.id))}
              >
                {isPreview ? 'Ferma anteprima' : 'Anteprima audio'}
              </button>
              {salvo === allarme.id ? <span className="text-xs text-emerald-300">Salvato.</span> : null}
              {isPreview ? <span className="text-xs text-amber-300">In riproduzione…</span> : null}
            </div>
          </div>
        );
      })}
    </section>
  );
}
