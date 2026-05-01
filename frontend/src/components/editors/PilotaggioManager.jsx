import React, { useCallback, useEffect, useMemo, useState } from 'react';
import StaffQrTab from '../StaffQrTab';
import {
  staffAssociaPilotSottosistemaQr,
  staffCreatePilotComando,
  staffCreatePilotComandoCritico,
  staffCreatePilotEvento,
  staffCreatePilotIntensita,
  staffCreatePilotSequenza,
  staffCreatePilotSottosistema,
  staffDeletePilotComando,
  staffDeletePilotComandoCritico,
  staffDeletePilotEvento,
  staffDeletePilotIntensita,
  staffDeletePilotSequenza,
  staffDeletePilotSottosistema,
  staffGetPilotComandi,
  staffGetPilotComandiCritici,
  staffGetPilotEventi,
  staffGetPilotIntensita,
  staffGetPilotSequenze,
  staffGetPilotSottosistemi,
  staffGetPilotStatiAllerta,
  staffUpdatePilotComando,
  staffUpdatePilotComandoCritico,
  staffUpdatePilotEvento,
  staffUpdatePilotIntensita,
  staffUpdatePilotSequenza,
  staffUpdatePilotSottosistema,
  staffUpdatePilotStatoAllerta,
} from '../../api';

const PILOT_TABS = [
  { id: 'sottosistemi', label: 'Sottosistemi' },
  { id: 'comandi', label: 'Comandi' },
  { id: 'intensita', label: 'Intensità' },
  { id: 'eventi', label: 'Eventi' },
  { id: 'comandi_critici', label: 'Comandi critici (globali)' },
  { id: 'sequenze', label: 'Sequenze' },
  { id: 'stati_allerta', label: 'Stati allerta (DEFCON)' },
  { id: 'combinazioni', label: 'Combinazioni' },
];

const defaultEvento = {
  nome: '',
  descrizione: '',
  codice_soluzione_esatta: '',
  codici_soluzione_parziale: '',
  codici_precipizio: '',
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
  const [comandiCritici, setComandiCritici] = useState([]);
  const [nuovoSotto, setNuovoSotto] = useState({ codice: '', nome: '' });
  const [nuovoComando, setNuovoComando] = useState({ codice: '', nome: '' });
  const [nuovaIntensita, setNuovaIntensita] = useState({ valore: 0, nome: '' });
  const [nuovoEvento, setNuovoEvento] = useState(defaultEvento);
  const [nuovaSequenza, setNuovaSequenza] = useState({ tipo: 'decollo', nome: '', codici: '', attiva: true });
  const [nuovoCritico, setNuovoCritico] = useState({ pattern: '', nome: '', attivo: true });
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
  const [editCriticoId, setEditCriticoId] = useState(null);
  const [editCritico, setEditCritico] = useState({ pattern: '', nome: '', attivo: true });

  const [scanningForSottosistemaId, setScanningForSottosistemaId] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [activeTab, setActiveTab] = useState('sottosistemi');
  const [statiAllerta, setStatiAllerta] = useState([]);
  const [editStatoId, setEditStatoId] = useState(null);
  const [editStato, setEditStato] = useState({});

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [s, c, i, e, seq, crit, stati] = await Promise.all([
        staffGetPilotSottosistemi(onLogout),
        staffGetPilotComandi(onLogout),
        staffGetPilotIntensita(onLogout),
        staffGetPilotEventi(onLogout),
        staffGetPilotSequenze(onLogout),
        staffGetPilotComandiCritici(onLogout).catch(() => []),
        staffGetPilotStatiAllerta(onLogout).catch(() => []),
      ]);
      setSottosistemi(Array.isArray(s) ? s : []);
      setComandi(Array.isArray(c) ? c : []);
      setIntensita(Array.isArray(i) ? i : []);
      setEventi(Array.isArray(e) ? e : []);
      setSequenze(Array.isArray(seq) ? seq : []);
      setComandiCritici(Array.isArray(crit) ? crit : []);
      setStatiAllerta(Array.isArray(stati) ? stati : []);
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
    const precipizi = String(nuovoEvento.codici_precipizio || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffCreatePilotEvento(
      {
        ...nuovoEvento,
        codice_soluzione_esatta: nuovoEvento.codice_soluzione_esatta.toUpperCase(),
        codici_soluzione_parziale: patterns,
        codici_precipizio: precipizi,
        sottosistema: nuovoEvento.sottosistema || null,
      },
      onLogout
    );
    setNuovoEvento(defaultEvento);
    loadData();
  };
  const addComandoCritico = async () => {
    await staffCreatePilotComandoCritico(
      {
        pattern: nuovoCritico.pattern.trim().toUpperCase(),
        nome: nuovoCritico.nome.trim(),
        attivo: Boolean(nuovoCritico.attivo),
      },
      onLogout
    );
    setNuovoCritico({ pattern: '', nome: '', attivo: true });
    loadData();
  };
  const salvaComandoCritico = async () => {
    await staffUpdatePilotComandoCritico(
      editCriticoId,
      {
        pattern: editCritico.pattern.trim().toUpperCase(),
        nome: editCritico.nome.trim(),
        attivo: Boolean(editCritico.attivo),
      },
      onLogout
    );
    setEditCriticoId(null);
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
    const precipizi = String(editEvento.codici_precipizio || '')
      .split(',')
      .map((s) => s.trim().toUpperCase())
      .filter(Boolean);
    await staffUpdatePilotEvento(
      editEventoId,
      {
        ...editEvento,
        codice_soluzione_esatta: editEvento.codice_soluzione_esatta.toUpperCase(),
        codici_soluzione_parziale: patterns,
        codici_precipizio: precipizi,
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

  const salvaStatoAllerta = async () => {
    await staffUpdatePilotStatoAllerta(
      editStatoId,
      {
        nome: editStato.nome,
        colore: editStato.colore,
        frequenza_evento_min_sec: Number(editStato.frequenza_evento_min_sec),
        frequenza_evento_max_sec: Number(editStato.frequenza_evento_max_sec),
        tempo_risoluzione_secondi: Number(editStato.tempo_risoluzione_secondi),
        equivale_nave_abbattuta: Boolean(editStato.equivale_nave_abbattuta),
      },
      onLogout
    );
    setEditStatoId(null);
    loadData();
  };

  if (loading) {
    return <div className="p-6 text-gray-300">Caricamento modulo pilotaggio...</div>;
  }

  return (
    <div className="p-6 space-y-6 text-gray-100">
      <h2 className="text-xl font-bold">Gestione Pilotaggio</h2>
      {error ? <div className="rounded bg-red-900/40 border border-red-600 p-3 text-sm">{error}</div> : null}

      <div className="flex flex-wrap gap-2 border-b border-gray-600 pb-3">
        {PILOT_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-2 rounded-t text-sm font-medium transition-colors ${
              activeTab === t.id
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'sottosistemi' ? (
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
      ) : null}

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

      {activeTab === 'comandi' ? (
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
      ) : null}

      {activeTab === 'intensita' ? (
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
      ) : null}

      {activeTab === 'eventi' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Eventi viaggio (randomici)</h3>
        <div className="grid md:grid-cols-2 gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Nome evento" value={nuovoEvento.nome} onChange={(e) => setNuovoEvento((p) => ({ ...p, nome: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Codice esatto (es. AB3)" value={nuovoEvento.codice_soluzione_esatta} onChange={(e) => setNuovoEvento((p) => ({ ...p, codice_soluzione_esatta: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Descrizione" value={nuovoEvento.descrizione} onChange={(e) => setNuovoEvento((p) => ({ ...p, descrizione: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Parziali successo parziale (virgola): A_3, _B5, ML(4-9)" value={nuovoEvento.codici_soluzione_parziale} onChange={(e) => setNuovoEvento((p) => ({ ...p, codici_soluzione_parziale: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2 border border-red-900/50" placeholder="Precipizio immediato (virgola, stessa sintassi): es. XX9, ZZ(8-9) → DEFCON massimo + crash" value={nuovoEvento.codici_precipizio} onChange={(e) => setNuovoEvento((p) => ({ ...p, codici_precipizio: e.target.value }))} />
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
                <input className="bg-gray-700 rounded px-2 py-1 md:col-span-2 border border-red-900/40" value={editEvento.codici_precipizio} onChange={(ev) => setEditEvento((p) => ({ ...p, codici_precipizio: ev.target.value }))} placeholder="Pattern precipizio (virgola)" />
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
                        codici_precipizio: Array.isArray(e.codici_precipizio) ? e.codici_precipizio.join(',') : '',
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
      ) : null}

      {activeTab === 'comandi_critici' ? (
      <section className="rounded-xl border border-red-900/40 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2 text-red-200">Comandi critici globali</h3>
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          Definisci pattern sul codice a 3 caratteri (stessa sintassi degli eventi: jolly <strong className="text-gray-300">_</strong>, intervalli{' '}
          <strong className="text-gray-300 font-mono">XY(N-M)</strong>). Se il pilota inserisce un codice valido che matcha una riga{' '}
          <em>attiva</em>, la nave precipita subito — anche senza evento attivo o durante decollo/atterraggio.
        </p>
        <div className="flex flex-wrap gap-2 mb-3 items-end">
          <input className="bg-gray-800 rounded px-2 py-1 font-mono w-28" maxLength={48} placeholder="XX9" value={nuovoCritico.pattern} onChange={(e) => setNuovoCritico((p) => ({ ...p, pattern: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1 min-w-[8rem]" placeholder="Etichetta (opzionale)" value={nuovoCritico.nome} onChange={(e) => setNuovoCritico((p) => ({ ...p, nome: e.target.value }))} />
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={nuovoCritico.attivo} onChange={(e) => setNuovoCritico((p) => ({ ...p, attivo: e.target.checked }))} />
            Attivo
          </label>
          <button type="button" className="px-3 py-1 rounded bg-red-800 hover:bg-red-700 text-white shrink-0" onClick={addComandoCritico}>Aggiungi</button>
        </div>
        <div className="space-y-1 text-sm">
          {comandiCritici.map((row) => (
            <div key={row.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-gray-800/60 rounded px-2 py-2 border border-gray-700">
              {editCriticoId === row.id ? (
                <div className="flex flex-wrap gap-2 w-full items-center">
                  <input className="bg-gray-700 rounded px-2 py-1 font-mono w-28" maxLength={48} value={editCritico.pattern} onChange={(e) => setEditCritico((p) => ({ ...p, pattern: e.target.value }))} />
                  <input className="bg-gray-700 rounded px-2 py-1 flex-1 min-w-[10rem]" value={editCritico.nome} onChange={(e) => setEditCritico((p) => ({ ...p, nome: e.target.value }))} />
                  <label className="flex items-center gap-2 text-xs text-gray-300 shrink-0">
                    <input type="checkbox" checked={Boolean(editCritico.attivo)} onChange={(e) => setEditCritico((p) => ({ ...p, attivo: e.target.checked }))} />
                    Attivo
                  </label>
                  <button type="button" className="text-emerald-400 shrink-0" onClick={salvaComandoCritico}>Salva</button>
                  <button type="button" className="text-gray-300 shrink-0" onClick={() => setEditCriticoId(null)}>Annulla</button>
                </div>
              ) : (
                <>
                  <span>
                    <span className="font-mono text-amber-200">{row.pattern}</span>
                    {row.nome ? <span className="text-gray-400 ml-2">— {row.nome}</span> : null}
                    {!row.attivo ? <span className="text-gray-500 ml-2 text-xs">(disattivato)</span> : null}
                  </span>
                  <div className="flex gap-3 shrink-0">
                    <button
                      type="button"
                      className="text-indigo-300"
                      onClick={() => {
                        setEditCriticoId(row.id);
                        setEditCritico({
                          pattern: row.pattern || '',
                          nome: row.nome || '',
                          attivo: row.attivo ?? true,
                        });
                      }}
                    >
                      Modifica
                    </button>
                    <button type="button" className="text-red-400" onClick={() => staffDeletePilotComandoCritico(row.id, onLogout).then(loadData)}>Elimina</button>
                  </div>
                </>
              )}
            </div>
          ))}
          {!comandiCritici.length ? <p className="text-gray-500 text-sm">Nessun pattern critico configurato.</p> : null}
        </div>
      </section>
      ) : null}

      {activeTab === 'sequenze' ? (
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
      ) : null}

      {activeTab === 'stati_allerta' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Stati di allerta (DEFCON 0–6)</h3>
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          Livelli allineati al DEFCON della sessione. Imposta intervallo tra un evento e l&apos;altro (secondi) e il countdown per risolvere un evento mentre sei in quel livello.
          Segna un solo livello come <strong className="text-gray-300">nave abbattuta</strong> (crash / DEFCON oltre il massimo).
        </p>
        <div className="space-y-3 text-sm">
          {statiAllerta.map((st) => (
            <div key={st.id} className="bg-gray-800/70 rounded-lg p-3 border border-gray-600">
              {editStatoId === st.id ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 items-end">
                  <div className="text-xs text-gray-500 sm:col-span-2 lg:col-span-3">Livello {st.livello}</div>
                  <label className="block">
                    <span className="text-xs text-gray-400">Nome</span>
                    <input className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.nome || ''} onChange={(e) => setEditStato((p) => ({ ...p, nome: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Colore (#RRGGBB)</span>
                    <div className="flex gap-2 mt-0.5">
                      <input type="color" className="h-9 w-14 rounded cursor-pointer border-0 p-0 bg-transparent" value={(editStato.colore || '#888888').slice(0, 7)} onChange={(e) => setEditStato((p) => ({ ...p, colore: e.target.value }))} />
                      <input className="bg-gray-700 rounded px-2 py-1 flex-1 font-mono text-xs" value={editStato.colore || ''} onChange={(e) => setEditStato((p) => ({ ...p, colore: e.target.value }))} />
                    </div>
                  </label>
                  <label className="block sm:col-span-2 lg:col-span-1">
                    <span className="text-xs text-gray-400">Freq. eventi min–max (s)</span>
                    <div className="flex gap-2 mt-0.5">
                      <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_min_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_min_sec: e.target.value }))} />
                      <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_max_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_max_sec: e.target.value }))} />
                    </div>
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Tempo risoluzione evento (s)</span>
                    <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.tempo_risoluzione_secondi} onChange={(e) => setEditStato((p) => ({ ...p, tempo_risoluzione_secondi: e.target.value }))} />
                  </label>
                  <label className="flex items-center gap-2 sm:col-span-2 lg:col-span-3 cursor-pointer">
                    <input type="checkbox" checked={Boolean(editStato.equivale_nave_abbattuta)} onChange={(e) => setEditStato((p) => ({ ...p, equivale_nave_abbattuta: e.target.checked }))} />
                    <span className="text-sm text-red-300">Equivale a nave abbattuta / precipitata</span>
                  </label>
                  <div className="flex gap-2 sm:col-span-2 lg:col-span-3">
                    <button type="button" className="text-emerald-400" onClick={salvaStatoAllerta}>Salva</button>
                    <button type="button" className="text-gray-400" onClick={() => setEditStatoId(null)}>Annulla</button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg font-bold text-white shrink-0" style={{ backgroundColor: st.colore || '#555' }}>
                      {st.livello}
                    </span>
                    <div>
                      <div className="font-semibold">{st.nome}</div>
                      <div className="text-xs text-gray-400">
                        Eventi ogni {st.frequenza_evento_min_sec}–{st.frequenza_evento_max_sec}s · Risoluzione {st.tempo_risoluzione_secondi}s
                        {st.equivale_nave_abbattuta ? <span className="text-red-400 ml-2">· Nave abbattuta</span> : null}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="text-indigo-300 shrink-0 self-start md:self-center"
                    onClick={() => {
                      setEditStatoId(st.id);
                      setEditStato({
                        nome: st.nome || '',
                        colore: st.colore || '#888888',
                        frequenza_evento_min_sec: st.frequenza_evento_min_sec ?? 60,
                        frequenza_evento_max_sec: st.frequenza_evento_max_sec ?? 90,
                        tempo_risoluzione_secondi: st.tempo_risoluzione_secondi ?? 20,
                        equivale_nave_abbattuta: Boolean(st.equivale_nave_abbattuta),
                      });
                    }}
                  >
                    Modifica
                  </button>
                </div>
              )}
            </div>
          ))}
          {!statiAllerta.length ? (
            <p className="text-gray-400 text-sm">Nessuno stato caricato. Esegui le migrazioni (<code className="text-xs">0005_statoallertapilot</code>).</p>
          ) : null}
        </div>
      </section>
      ) : null}

      {activeTab === 'combinazioni' ? (
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
      ) : null}
    </div>
  );
}
