import React, { useCallback, useEffect, useMemo, useState } from 'react';
import StaffQrTab from '../StaffQrTab';
import {
  staffAssociaPilotSottosistemaQr,
  staffCreatePilotComando,
  staffCreatePilotEvento,
  staffCreatePilotIntensita,
  staffCreatePilotSequenza,
  staffCreatePilotSottosistema,
  staffDeletePilotComando,
  staffDeletePilotEvento,
  staffDeletePilotIntensita,
  staffDeletePilotSequenza,
  staffDeletePilotSottosistema,
  staffGetPilotComandi,
  staffGetPilotEventi,
  staffGetPilotIntensita,
  staffGetPilotSequenze,
  staffGetPilotSottosistemi,
  staffUpdatePilotComando,
  staffUpdatePilotEvento,
  staffUpdatePilotIntensita,
  staffUpdatePilotSequenza,
  staffUpdatePilotSottosistema,
} from '../../api';

const defaultEvento = {
  nome: '',
  descrizione: '',
  codice_soluzione_esatta: '',
  codici_soluzione_parziale: '',
  durata_base_secondi: 20,
  peso_random: 10,
  sottosistema: '',
  attivo: true,
};

export default function PilotaggioManager({ onLogout }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sottosistemi, setSottosistemi] = useState([]);
  const [comandi, setComandi] = useState([]);
  const [intensita, setIntensita] = useState([]);
  const [eventi, setEventi] = useState([]);
  const [sequenze, setSequenze] = useState([]);
  const [nuovoSotto, setNuovoSotto] = useState({ codice: '', nome: '' });
  const [nuovoComando, setNuovoComando] = useState({ codice: '', nome: '' });
  const [nuovaIntensita, setNuovaIntensita] = useState({ valore: 0, nome: '' });
  const [nuovoEvento, setNuovoEvento] = useState(defaultEvento);
  const [nuovaSequenza, setNuovaSequenza] = useState({ tipo: 'decollo', nome: '', codici: '', attiva: true });
  const [editSottoId, setEditSottoId] = useState(null);
  const [editSotto, setEditSotto] = useState({ codice: '', nome: '' });
  const [editComandoId, setEditComandoId] = useState(null);
  const [editComando, setEditComando] = useState({ codice: '', nome: '' });
  const [editIntensitaId, setEditIntensitaId] = useState(null);
  const [editIntensita, setEditIntensita] = useState({ valore: 0, nome: '' });
  const [editEventoId, setEditEventoId] = useState(null);
  const [editEvento, setEditEvento] = useState(defaultEvento);
  const [editSequenzaId, setEditSequenzaId] = useState(null);
  const [editSequenza, setEditSequenza] = useState({ tipo: 'decollo', nome: '', codici: '', attiva: true });

  const [scanningForSottosistemaId, setScanningForSottosistemaId] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [s, c, i, e, seq] = await Promise.all([
        staffGetPilotSottosistemi(onLogout),
        staffGetPilotComandi(onLogout),
        staffGetPilotIntensita(onLogout),
        staffGetPilotEventi(onLogout),
        staffGetPilotSequenze(onLogout),
      ]);
      setSottosistemi(Array.isArray(s) ? s : []);
      setComandi(Array.isArray(c) ? c : []);
      setIntensita(Array.isArray(i) ? i : []);
      setEventi(Array.isArray(e) ? e : []);
      setSequenze(Array.isArray(seq) ? seq : []);
    } catch (err) {
      setError(err?.message || 'Errore caricamento pilotaggio.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const listaCombinata = useMemo(() => {
    const righe = [];
    for (const s of sottosistemi) {
      for (const i of intensita) {
        for (const c of comandi) {
          righe.push({
            codice: `${s.codice}${c.codice}${i.valore}`,
            sottosistema_codice: s.codice,
            sottosistema_nome: s.nome,
            comando_codice: c.codice,
            comando_nome: c.nome,
            intensita: i.valore,
          });
        }
      }
    }
    return righe;
  }, [sottosistemi, comandi, intensita]);

  const listaSottosistemaNumeroComando = useMemo(() => {
    const righe = [];
    for (const s of sottosistemi) {
      for (const i of intensita) {
        righe.push({
          chiave: `${s.codice}${i.valore}`,
          comandi_disponibili: comandi.map((c) => `${c.codice}:${c.nome}`),
        });
      }
    }
    return righe;
  }, [sottosistemi, comandi, intensita]);

  const addSottosistema = async () => {
    await staffCreatePilotSottosistema(
      { codice: nuovoSotto.codice.toUpperCase(), nome: nuovoSotto.nome },
      onLogout
    );
    setNuovoSotto({ codice: '', nome: '' });
    loadData();
  };
  const addComando = async () => {
    await staffCreatePilotComando({ ...nuovoComando, codice: nuovoComando.codice.toUpperCase() }, onLogout);
    setNuovoComando({ codice: '', nome: '' });
    loadData();
  };
  const addIntensita = async () => {
    await staffCreatePilotIntensita({ ...nuovaIntensita, valore: Number(nuovaIntensita.valore) }, onLogout);
    setNuovaIntensita({ valore: 0, nome: '' });
    loadData();
  };
  const addEvento = async () => {
    const patterns = String(nuovoEvento.codici_soluzione_parziale || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffCreatePilotEvento(
      {
        ...nuovoEvento,
        codice_soluzione_esatta: nuovoEvento.codice_soluzione_esatta.toUpperCase(),
        codici_soluzione_parziale: patterns,
        sottosistema: nuovoEvento.sottosistema || null,
      },
      onLogout
    );
    setNuovoEvento(defaultEvento);
    loadData();
  };
  const addSequenza = async () => {
    const codici = String(nuovaSequenza.codici || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffCreatePilotSequenza({ ...nuovaSequenza, codici }, onLogout);
    setNuovaSequenza({ tipo: 'decollo', nome: '', codici: '', attiva: true });
    loadData();
  };
  const salvaSottosistema = async () => {
    await staffUpdatePilotSottosistema(
      editSottoId,
      { codice: editSotto.codice.toUpperCase(), nome: editSotto.nome },
      onLogout
    );
    setEditSottoId(null);
    loadData();
  };
  const salvaComando = async () => {
    await staffUpdatePilotComando(editComandoId, { codice: editComando.codice.toUpperCase(), nome: editComando.nome }, onLogout);
    setEditComandoId(null);
    loadData();
  };
  const salvaIntensita = async () => {
    await staffUpdatePilotIntensita(editIntensitaId, { valore: Number(editIntensita.valore), nome: editIntensita.nome }, onLogout);
    setEditIntensitaId(null);
    loadData();
  };
  const salvaEvento = async () => {
    const patterns = String(editEvento.codici_soluzione_parziale || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffUpdatePilotEvento(
      editEventoId,
      {
        ...editEvento,
        codice_soluzione_esatta: editEvento.codice_soluzione_esatta.toUpperCase(),
        codici_soluzione_parziale: patterns,
        sottosistema: editEvento.sottosistema || null,
      },
      onLogout
    );
    setEditEventoId(null);
    loadData();
  };
  const salvaSequenza = async () => {
    const codici = String(editSequenza.codici || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffUpdatePilotSequenza(editSequenzaId, { ...editSequenza, codici }, onLogout);
    setEditSequenzaId(null);
    loadData();
  };

  if (loading) {
    return <div className="p-6 text-gray-300">Caricamento modulo pilotaggio...</div>;
  }

  return (
    <div className="p-6 space-y-6 text-gray-100">
      <h2 className="text-xl font-bold">Gestione Pilotaggio</h2>
      {error ? <div className="rounded bg-red-900/40 border border-red-600 p-3 text-sm">{error}</div> : null}

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Sottosistemi (1° carattere)</h3>
        <p className="text-xs text-gray-400 mb-3 leading-relaxed">
          Inserisci codice e nome, poi aggiungi la riga. Usa <strong className="text-gray-300">Scansiona QR</strong> sul
          sottosistema: il sistema collega il QR al sottosistema (se il cartellino è nuovo crea anche il manifesto pilota
          dietro le quinte). Non serve cercare id di vista a mano.
        </p>
        {qrStatus.message ? (
          <div
            className={`mb-3 rounded px-3 py-2 text-sm ${
              qrStatus.type === 'success' ? 'bg-emerald-900/40 border border-emerald-700 text-emerald-100' : 'bg-red-900/40 border border-red-700 text-red-100'
            }`}
          >
            {qrStatus.message}
          </div>
        ) : null}
        <div className="flex flex-col sm:flex-row gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1 w-16 shrink-0" maxLength={1} value={nuovoSotto.codice} onChange={(e) => setNuovoSotto((p) => ({ ...p, codice: e.target.value }))} placeholder="A" />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1 min-w-0" value={nuovoSotto.nome} onChange={(e) => setNuovoSotto((p) => ({ ...p, nome: e.target.value }))} placeholder="Nome sottosistema" />
          <button className="px-3 py-1 rounded bg-indigo-600 shrink-0" onClick={addSottosistema}>Aggiungi</button>
        </div>
        <div className="space-y-1 text-sm">
          {sottosistemi.map((s) => (
            <div key={s.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-gray-800/60 rounded px-2 py-2">
              {editSottoId === s.id ? (
                <div className="flex flex-wrap gap-2 w-full items-center">
                  <input className="bg-gray-700 rounded px-2 py-1 w-16 shrink-0" maxLength={1} value={editSotto.codice} onChange={(e) => setEditSotto((p) => ({ ...p, codice: e.target.value }))} />
                  <input className="bg-gray-700 rounded px-2 py-1 flex-1 min-w-[10rem]" value={editSotto.nome} onChange={(e) => setEditSotto((p) => ({ ...p, nome: e.target.value }))} />
                  <button className="text-emerald-400 shrink-0" type="button" onClick={salvaSottosistema}>Salva</button>
                  <button className="text-gray-300 shrink-0" type="button" onClick={() => setEditSottoId(null)}>Annulla</button>
                </div>
              ) : (
                <>
                  <span className="break-words">
                    <strong>{s.codice}</strong> — {s.nome}
                    {s.stato_qr === 'pronto'
                      ? ' · QR collegato'
                      : s.stato_qr === 'incompleto'
                        ? ' · vista OK, manca ancora lo scan del cartellino'
                        : ' · nessun QR'}
                  </span>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <button
                      type="button"
                      className="px-2 py-1 rounded bg-gray-700 text-sm text-white"
                      onClick={() => setScanningForSottosistemaId(s.id)}
                    >
                      Scansiona QR
                    </button>
                    <button
                      type="button"
                      className="text-indigo-300 text-sm"
                      onClick={() => {
                        setEditSottoId(s.id);
                        setEditSotto({
                          codice: s.codice || '',
                          nome: s.nome || '',
                        });
                      }}
                    >
                      Modifica nome
                    </button>
                    <button type="button" className="text-red-400 text-sm" onClick={() => staffDeletePilotSottosistema(s.id, onLogout).then(loadData)}>Elimina</button>
                  </div>
                </>
              )}
            </div>
          ))}
        </div>
      </section>

      {scanningForSottosistemaId ? (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 gap-2">
            <span className="font-bold text-white text-sm sm:text-base">
              Associa QR al sottosistema selezionato
            </span>
            <button
              type="button"
              onClick={() => setScanningForSottosistemaId(null)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition-colors shrink-0"
            >
              Chiudi
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                try {
                  await staffAssociaPilotSottosistemaQr(scanningForSottosistemaId, qr_id, onLogout);
                  setScanningForSottosistemaId(null);
                  setQrStatus({ type: 'success', message: 'QR associato al sottosistema.' });
                  loadData();
                } catch (error) {
                  const detail =
                    error?.data?.error ||
                    error?.message ||
                    (typeof error?.data === 'string' ? error.data : null) ||
                    'Errore sconosciuto';
                  setQrStatus({ type: 'error', message: `Errore: ${detail}` });
                }
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      ) : null}

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Comandi (2° carattere)</h3>
        <div className="flex gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1 w-16" maxLength={1} value={nuovoComando.codice} onChange={(e) => setNuovoComando((p) => ({ ...p, codice: e.target.value }))} placeholder="B" />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1" value={nuovoComando.nome} onChange={(e) => setNuovoComando((p) => ({ ...p, nome: e.target.value }))} placeholder="Nome comando" />
          <button className="px-3 py-1 rounded bg-indigo-600" onClick={addComando}>Aggiungi</button>
        </div>
        {comandi.map((c) => (
          <div key={c.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editComandoId === c.id ? (
              <div className="flex gap-2 w-full">
                <input className="bg-gray-700 rounded px-2 py-1 w-16" maxLength={1} value={editComando.codice} onChange={(e) => setEditComando((p) => ({ ...p, codice: e.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 flex-1" value={editComando.nome} onChange={(e) => setEditComando((p) => ({ ...p, nome: e.target.value }))} />
                <button className="text-emerald-400" onClick={salvaComando}>Salva</button>
                <button className="text-gray-300" onClick={() => setEditComandoId(null)}>Annulla</button>
              </div>
            ) : (
              <>
                <span>{c.codice} - {c.nome}</span>
                <div className="flex gap-3">
                  <button className="text-indigo-300" onClick={() => { setEditComandoId(c.id); setEditComando({ codice: c.codice || '', nome: c.nome || '' }); }}>Modifica</button>
                  <button className="text-red-400" onClick={() => staffDeletePilotComando(c.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Intensità (3° carattere numerico)</h3>
        <div className="flex gap-2 mb-3">
          <input type="number" min={0} max={9} className="bg-gray-800 rounded px-2 py-1 w-20" value={nuovaIntensita.valore} onChange={(e) => setNuovaIntensita((p) => ({ ...p, valore: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1" value={nuovaIntensita.nome} onChange={(e) => setNuovaIntensita((p) => ({ ...p, nome: e.target.value }))} placeholder="Nome intensità (opzionale)" />
          <button className="px-3 py-1 rounded bg-indigo-600" onClick={addIntensita}>Aggiungi</button>
        </div>
        {intensita.map((i) => (
          <div key={i.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editIntensitaId === i.id ? (
              <div className="flex gap-2 w-full">
                <input type="number" min={0} max={9} className="bg-gray-700 rounded px-2 py-1 w-20" value={editIntensita.valore} onChange={(e) => setEditIntensita((p) => ({ ...p, valore: e.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 flex-1" value={editIntensita.nome} onChange={(e) => setEditIntensita((p) => ({ ...p, nome: e.target.value }))} />
                <button className="text-emerald-400" onClick={salvaIntensita}>Salva</button>
                <button className="text-gray-300" onClick={() => setEditIntensitaId(null)}>Annulla</button>
              </div>
            ) : (
              <>
                <span>{i.valore} - {i.nome || `Intensità ${i.valore}`}</span>
                <div className="flex gap-3">
                  <button className="text-indigo-300" onClick={() => { setEditIntensitaId(i.id); setEditIntensita({ valore: i.valore ?? 0, nome: i.nome || '' }); }}>Modifica</button>
                  <button className="text-red-400" onClick={() => staffDeletePilotIntensita(i.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Eventi viaggio (randomici)</h3>
        <div className="grid md:grid-cols-2 gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Nome evento" value={nuovoEvento.nome} onChange={(e) => setNuovoEvento((p) => ({ ...p, nome: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Codice esatto (es. AB3)" value={nuovoEvento.codice_soluzione_esatta} onChange={(e) => setNuovoEvento((p) => ({ ...p, codice_soluzione_esatta: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Descrizione" value={nuovoEvento.descrizione} onChange={(e) => setNuovoEvento((p) => ({ ...p, descrizione: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Pattern parziali separati da virgola (es. A_3,_B5)" value={nuovoEvento.codici_soluzione_parziale} onChange={(e) => setNuovoEvento((p) => ({ ...p, codici_soluzione_parziale: e.target.value }))} />
          <button className="px-3 py-1 rounded bg-indigo-600 md:col-span-2" onClick={addEvento}>Aggiungi evento</button>
        </div>
        {eventi.map((e) => (
          <div key={e.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editEventoId === e.id ? (
              <div className="grid md:grid-cols-2 gap-2 w-full">
                <input className="bg-gray-700 rounded px-2 py-1" value={editEvento.nome} onChange={(ev) => setEditEvento((p) => ({ ...p, nome: ev.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1" value={editEvento.codice_soluzione_esatta} onChange={(ev) => setEditEvento((p) => ({ ...p, codice_soluzione_esatta: ev.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 md:col-span-2" value={editEvento.descrizione} onChange={(ev) => setEditEvento((p) => ({ ...p, descrizione: ev.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 md:col-span-2" value={editEvento.codici_soluzione_parziale} onChange={(ev) => setEditEvento((p) => ({ ...p, codici_soluzione_parziale: ev.target.value }))} />
                <div className="flex gap-3 md:col-span-2">
                  <button className="text-emerald-400" onClick={salvaEvento}>Salva</button>
                  <button className="text-gray-300" onClick={() => setEditEventoId(null)}>Annulla</button>
                </div>
              </div>
            ) : (
              <>
                <span>{e.nome} [{e.codice_soluzione_esatta}]</span>
                <div className="flex gap-3">
                  <button
                    className="text-indigo-300"
                    onClick={() => {
                      setEditEventoId(e.id);
                      setEditEvento({
                        nome: e.nome || '',
                        descrizione: e.descrizione || '',
                        codice_soluzione_esatta: e.codice_soluzione_esatta || '',
                        codici_soluzione_parziale: Array.isArray(e.codici_soluzione_parziale) ? e.codici_soluzione_parziale.join(',') : '',
                        durata_base_secondi: e.durata_base_secondi ?? 20,
                        peso_random: e.peso_random ?? 10,
                        sottosistema: e.sottosistema || '',
                        attivo: e.attivo ?? true,
                      });
                    }}
                  >
                    Modifica
                  </button>
                  <button className="text-red-400" onClick={() => staffDeletePilotEvento(e.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Sequenze decollo/atterraggio</h3>
        <div className="grid md:grid-cols-2 gap-2 mb-3">
          <select className="bg-gray-800 rounded px-2 py-1" value={nuovaSequenza.tipo} onChange={(e) => setNuovaSequenza((p) => ({ ...p, tipo: e.target.value }))}>
            <option value="decollo">Decollo</option>
            <option value="atterraggio">Atterraggio</option>
          </select>
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Nome sequenza" value={nuovaSequenza.nome} onChange={(e) => setNuovaSequenza((p) => ({ ...p, nome: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Codici in ordine, separati da virgola (es. AB1,CD2,EF3)" value={nuovaSequenza.codici} onChange={(e) => setNuovaSequenza((p) => ({ ...p, codici: e.target.value }))} />
          <button className="px-3 py-1 rounded bg-indigo-600 md:col-span-2" onClick={addSequenza}>Aggiungi sequenza</button>
        </div>
        {sequenze.map((s) => (
          <div key={s.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editSequenzaId === s.id ? (
              <div className="grid md:grid-cols-2 gap-2 w-full">
                <select className="bg-gray-700 rounded px-2 py-1" value={editSequenza.tipo} onChange={(e) => setEditSequenza((p) => ({ ...p, tipo: e.target.value }))}>
                  <option value="decollo">Decollo</option>
                  <option value="atterraggio">Atterraggio</option>
                </select>
                <input className="bg-gray-700 rounded px-2 py-1" value={editSequenza.nome} onChange={(e) => setEditSequenza((p) => ({ ...p, nome: e.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 md:col-span-2" value={editSequenza.codici} onChange={(e) => setEditSequenza((p) => ({ ...p, codici: e.target.value }))} />
                <div className="flex gap-3 md:col-span-2">
                  <button className="text-emerald-400" onClick={salvaSequenza}>Salva</button>
                  <button className="text-gray-300" onClick={() => setEditSequenzaId(null)}>Annulla</button>
                </div>
              </div>
            ) : (
              <>
                <span>{s.tipo} - {s.nome || '(senza nome)'}: {(s.codici || []).join(', ')}</span>
                <div className="flex gap-3">
                  <button className="text-indigo-300" onClick={() => { setEditSequenzaId(s.id); setEditSequenza({ tipo: s.tipo || 'decollo', nome: s.nome || '', codici: Array.isArray(s.codici) ? s.codici.join(',') : '', attiva: s.attiva ?? true }); }}>Modifica</button>
                  <button className="text-red-400" onClick={() => staffDeletePilotSequenza(s.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>

      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Lista richiesta: sottosistema = carattere + numero = comando</h3>
        <div className="max-h-48 overflow-y-auto space-y-1 text-xs mb-4">
          {listaSottosistemaNumeroComando.map((r) => (
            <div key={r.chiave} className="bg-gray-800/60 rounded px-2 py-1">
              {r.chiave} = {r.comandi_disponibili.join(' | ')}
            </div>
          ))}
        </div>
        <h4 className="font-semibold mb-2 text-sm text-gray-300">Dettaglio combinazioni complete (3 caratteri)</h4>
        <div className="max-h-96 overflow-y-auto space-y-1 text-xs">
          {listaCombinata.map((r, idx) => (
            <div key={`${r.codice}-${idx}`} className="bg-gray-800/60 rounded px-2 py-1">
              {r.codice}: {r.sottosistema_codice}={r.sottosistema_nome} + {r.comando_codice}={r.comando_nome} + {r.intensita}
            </div>
          ))}
          {!listaCombinata.length ? <div className="text-gray-400">Nessuna combinazione disponibile.</div> : null}
        </div>
      </section>
    </div>
  );
}
