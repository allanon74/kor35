import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { Dices, RefreshCw } from 'lucide-react';
import {
  createStaffPoolPg,
  deleteStaffPoolPg,
  getStaffPoolPgConteggi,
  getStaffPoolPgList,
  getStaffPoolPgLog,
  getStaffPoolPgMeta,
  getStaffPoolPgPersonaggi,
  postStaffPoolPgSorteggia,
  setStaffPoolPgMembro,
  updateStaffPoolPg,
} from '../../api';
import RichTextEditor from '../RichTextEditor';
import { useCharacter } from '../CharacterContext';
import { UiErrorState, UiLoadingState } from '../ui/AsyncState';
import {
  StaffFullscreenEditor,
  StaffToolPageTitle,
  StaffToolShell,
  staffMutedClass,
  staffPanelClass,
  staffPrimaryBtnClass,
  staffSecondaryBtnClass,
} from '../../staff/StaffToolShell';
import { StaffListRow, StaffListToolbar, StaffModalTabs, staffInputClass } from '../../staff/StaffCrudUi';

const TABS = [
  { id: 'dati', label: 'Dati' },
  { id: 'personaggi', label: 'Personaggi' },
  { id: 'messaggio', label: 'Messaggio' },
  { id: 'conteggi', label: 'Conteggi' },
  { id: 'log', label: 'Log' },
];

const vuoto = () => ({
  nome: '',
  escludi_png: false,
  sorteggio_min: 1,
  sorteggio_max: 1,
  fattore_peso: '0.8',
  messaggio_titolo: '',
  messaggio_testo: '',
  invio_prioritario: false,
});

function formatWhen(iso) {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return String(iso);
  }
}

export default function PoolPersonaggiManager({ onLogout }) {
  const { isCampaignStaffer, isAdmin } = useCharacter();
  const canAccess = isCampaignStaffer || isAdmin;

  const [lista, setLista] = useState([]);
  const [meta, setMeta] = useState({ eventi: [], placeholders: [], evento_in_corso_id: null });
  const [caricamento, setCaricamento] = useState(true);
  const [errore, setErrore] = useState('');
  const [feedback, setFeedback] = useState('');
  const [editing, setEditing] = useState(null);
  const [form, setForm] = useState(vuoto);
  const [tab, setTab] = useState('dati');
  const [salvataggio, setSalvataggio] = useState(false);
  const [sorteggioInCorso, setSorteggioInCorso] = useState(false);
  const [ultimoSorteggio, setUltimoSorteggio] = useState(null);

  const [eventoFiltro, setEventoFiltro] = useState('');
  const [ricercaPg, setRicercaPg] = useState('');
  const [personaggi, setPersonaggi] = useState([]);
  const [loadingPg, setLoadingPg] = useState(false);
  const [conteggi, setConteggi] = useState(null);
  const [log, setLog] = useState([]);

  const isSaved = Boolean(editing?.id);

  const caricaListe = useCallback(async () => {
    setCaricamento(true);
    setErrore('');
    try {
      const [pools, metaRes] = await Promise.all([
        getStaffPoolPgList(onLogout),
        getStaffPoolPgMeta(onLogout),
      ]);
      setLista(Array.isArray(pools) ? pools : []);
      setMeta({
        eventi: metaRes?.eventi || [],
        placeholders: metaRes?.placeholders || [],
        evento_in_corso_id: metaRes?.evento_in_corso_id || null,
      });
    } catch (e) {
      setErrore(e.message || 'Impossibile caricare i pool.');
    } finally {
      setCaricamento(false);
    }
  }, [onLogout]);

  useEffect(() => {
    if (canAccess) caricaListe();
  }, [canAccess, caricaListe]);

  const caricaPersonaggi = useCallback(async (poolId, opts = {}) => {
    if (!poolId) return;
    setLoadingPg(true);
    try {
      const data = await getStaffPoolPgPersonaggi(
        poolId,
        {
          q: opts.q ?? ricercaPg,
          evento_id: opts.evento_id ?? eventoFiltro,
          escludi_png: form.escludi_png,
        },
        onLogout,
      );
      setPersonaggi(data?.results || []);
    } catch (e) {
      setErrore(e.message || 'Errore elenco personaggi.');
    } finally {
      setLoadingPg(false);
    }
  }, [eventoFiltro, form.escludi_png, onLogout, ricercaPg]);

  const caricaDettagliTab = useCallback(async (poolId, tabId) => {
    if (!poolId) return;
    try {
      if (tabId === 'personaggi') await caricaPersonaggi(poolId);
      if (tabId === 'conteggi') {
        const data = await getStaffPoolPgConteggi(poolId, onLogout);
        setConteggi(data);
      }
      if (tabId === 'log') {
        const data = await getStaffPoolPgLog(poolId, onLogout);
        setLog(Array.isArray(data) ? data : []);
      }
    } catch (e) {
      setErrore(e.message || 'Errore caricamento tab.');
    }
  }, [caricaPersonaggi, onLogout]);

  useEffect(() => {
    if (!isSaved || !editing?.id) return undefined;
    const t = setTimeout(() => {
      if (tab === 'personaggi') caricaPersonaggi(editing.id);
    }, 250);
    return () => clearTimeout(t);
  }, [caricaPersonaggi, editing?.id, isSaved, ricercaPg, eventoFiltro, tab, form.escludi_png]);

  const apriNuovo = () => {
    setEditing({});
    setForm(vuoto());
    setTab('dati');
    setUltimoSorteggio(null);
    setPersonaggi([]);
    setConteggi(null);
    setLog([]);
    setFeedback('');
  };

  const apriModifica = (pool) => {
    setEditing(pool);
    setForm({
      nome: pool.nome || '',
      escludi_png: !!pool.escludi_png,
      sorteggio_min: pool.sorteggio_min ?? 1,
      sorteggio_max: pool.sorteggio_max ?? 1,
      fattore_peso: String(pool.fattore_peso ?? '0.8'),
      messaggio_titolo: pool.messaggio_titolo || '',
      messaggio_testo: pool.messaggio_testo || '',
      invio_prioritario: !!pool.invio_prioritario,
    });
    setTab('dati');
    setUltimoSorteggio(null);
    setFeedback('');
    caricaDettagliTab(pool.id, 'dati');
  };

  const payloadForm = () => ({
    nome: form.nome.trim(),
    escludi_png: !!form.escludi_png,
    sorteggio_min: Number(form.sorteggio_min) || 1,
    sorteggio_max: Number(form.sorteggio_max) || 1,
    fattore_peso: form.fattore_peso,
    messaggio_titolo: form.messaggio_titolo,
    messaggio_testo: form.messaggio_testo,
    invio_prioritario: !!form.invio_prioritario,
  });

  const salva = async () => {
    if (!form.nome.trim()) {
      setErrore('Il nome del pool è obbligatorio.');
      return;
    }
    setSalvataggio(true);
    setErrore('');
    try {
      const body = payloadForm();
      const saved = editing?.id
        ? await updateStaffPoolPg(editing.id, body, onLogout)
        : await createStaffPoolPg(body, onLogout);
      setEditing(saved);
      setFeedback('Pool salvato.');
      await caricaListe();
    } catch (e) {
      setErrore(e.message || 'Salvataggio fallito.');
    } finally {
      setSalvataggio(false);
    }
  };

  const elimina = async (pool) => {
    if (!window.confirm(`Eliminare il pool «${pool.nome}» e i suoi log?`)) return;
    try {
      await deleteStaffPoolPg(pool.id, onLogout);
      if (editing?.id === pool.id) setEditing(null);
      caricaListe();
    } catch (e) {
      setErrore(e.message || 'Eliminazione fallita.');
    }
  };

  const togglePg = async (pg) => {
    if (!editing?.id) return;
    const next = !pg.attivo;
    setPersonaggi((prev) => prev.map((row) => (row.id === pg.id ? { ...row, attivo: next } : row)));
    try {
      await setStaffPoolPgMembro(editing.id, { personaggio_id: pg.id, attivo: next }, onLogout);
    } catch (e) {
      setPersonaggi((prev) => prev.map((row) => (row.id === pg.id ? { ...row, attivo: pg.attivo } : row)));
      setErrore(e.message || 'Impossibile aggiornare il personaggio.');
    }
  };

  const sorteggia = async () => {
    if (!editing?.id) return;
    setSorteggioInCorso(true);
    setErrore('');
    try {
      await updateStaffPoolPg(editing.id, payloadForm(), onLogout);
      const res = await postStaffPoolPgSorteggia(
        editing.id,
        { sorteggio_min: form.sorteggio_min, sorteggio_max: form.sorteggio_max },
        onLogout,
      );
      setUltimoSorteggio(res);
      setFeedback(`Sorteggiati ${res.n_estratti} personaggi.`);
      setTab('log');
      await caricaDettagliTab(editing.id, 'log');
      await caricaDettagliTab(editing.id, 'conteggi');
      await caricaListe();
    } catch (e) {
      setErrore(e.message || 'Sorteggio fallito.');
    } finally {
      setSorteggioInCorso(false);
    }
  };

  const onChangeTab = (id) => {
    setTab(id);
    if (editing?.id) caricaDettagliTab(editing.id, id);
  };

  const attiviVis = useMemo(() => personaggi.filter((p) => p.attivo).length, [personaggi]);

  if (!canAccess) {
    return (
      <StaffToolShell>
        <p className="text-red-300">Area riservata allo staff.</p>
      </StaffToolShell>
    );
  }

  return (
    <StaffToolShell fill>
      <StaffToolPageTitle
        icon={<Dices size={22} />}
        title="Pool e sorteggi"
        description="Pool nominati di personaggi, sorteggio pesato e messaggi in inbox."
      />
      {errore && <UiErrorState message={errore} onRetry={caricaListe} />}
      {feedback && <p className="mb-2 text-sm text-emerald-300">{feedback}</p>}
      {caricamento ? (
        <UiLoadingState />
      ) : (
        <>
          <StaffListToolbar title="Pool" count={lista.length} onAdd={apriNuovo} addLabel="Nuovo pool" />
          <ul className="space-y-2">
            {lista.map((pool) => (
              <StaffListRow
                key={pool.id}
                onEdit={() => apriModifica(pool)}
                onDelete={() => elimina(pool)}
                deleteConfirm={`Eliminare «${pool.nome}»?`}
              >
                <div className="min-w-0">
                  <div className="font-bold text-white break-words">{pool.nome}</div>
                  <div className={`${staffMutedClass} text-xs`}>
                    Attivi: {pool.attivi_count ?? 0} · Sorteggi: {pool.sorteggi_count ?? 0} · Range {pool.sorteggio_min}–{pool.sorteggio_max} · fattore {pool.fattore_peso}
                    {pool.invio_prioritario ? ' · priorità' : ''}
                  </div>
                </div>
              </StaffListRow>
            ))}
            {lista.length === 0 && (
              <li className={`${staffPanelClass} text-sm text-gray-400`}>Nessun pool. Creane uno per iniziare.</li>
            )}
          </ul>
        </>
      )}

      <StaffFullscreenEditor
        open={editing != null}
        onBack={() => setEditing(null)}
        backLabel="Torna ai pool"
        subHeader={(
          <div className="px-3 py-2">
            <StaffModalTabs
              tabs={TABS.map((t) => ({
                ...t,
                count: t.id === 'personaggi' && isSaved ? attiviVis : undefined,
              }))}
              active={tab}
              onChange={onChangeTab}
            />
          </div>
        )}
      >
        <div className="mx-auto w-full max-w-3xl space-y-4 pb-24">
          {tab === 'dati' && (
            <div className={`${staffPanelClass} space-y-3`}>
              <label className="block">
                <span className="text-xs font-bold text-gray-300">Nome pool</span>
                <input
                  className={`${staffInputClass()} min-h-11 mt-1`}
                  value={form.nome}
                  onChange={(e) => setForm((p) => ({ ...p, nome: e.target.value }))}
                />
              </label>
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                <label className="block">
                  <span className="text-xs font-bold text-gray-300">Min sorteggio</span>
                  <input
                    type="number"
                    min={1}
                    className={`${staffInputClass()} min-h-11 mt-1`}
                    value={form.sorteggio_min}
                    onChange={(e) => setForm((p) => ({ ...p, sorteggio_min: e.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-bold text-gray-300">Max sorteggio</span>
                  <input
                    type="number"
                    min={1}
                    className={`${staffInputClass()} min-h-11 mt-1`}
                    value={form.sorteggio_max}
                    onChange={(e) => setForm((p) => ({ ...p, sorteggio_max: e.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-bold text-gray-300">Fattore peso</span>
                  <input
                    type="number"
                    step="0.01"
                    className={`${staffInputClass()} min-h-11 mt-1`}
                    value={form.fattore_peso}
                    onChange={(e) => setForm((p) => ({ ...p, fattore_peso: e.target.value }))}
                  />
                </label>
              </div>
              <p className="text-[11px] text-gray-500">
                Default 0.8: ogni sorteggio precedente moltiplica il peso (0.8² = 0.64). 1 = probabilità fissa. Maggiore di 1 aumenta le chance di chi è già uscito.
                Range uguale (es. 1–1) estrae un solo personaggio; 2–5 ne estrae un numero casuale in quel intervallo.
              </p>
              <label className="flex min-h-11 items-center gap-2 text-sm text-gray-200">
                <input
                  type="checkbox"
                  checked={form.escludi_png}
                  onChange={(e) => setForm((p) => ({ ...p, escludi_png: e.target.checked }))}
                />
                Nascondi PnG nella tab personaggi
              </label>
              <label className="flex min-h-11 items-center gap-2 text-sm text-gray-200">
                <input
                  type="checkbox"
                  checked={form.invio_prioritario}
                  onChange={(e) => setForm((p) => ({ ...p, invio_prioritario: e.target.checked }))}
                />
                Messaggio prioritario (overlay a schermo pieno + allarme fino a «Ho letto e compreso»)
              </label>
              <div className="flex flex-col sm:flex-row gap-2">
                <button type="button" className={`${staffPrimaryBtnClass} min-h-11`} disabled={salvataggio} onClick={salva}>
                  {salvataggio ? 'Salvataggio…' : isSaved ? 'Salva dati' : 'Crea pool'}
                </button>
                {isSaved && (
                  <button
                    type="button"
                    className={`${staffSecondaryBtnClass} min-h-11`}
                    disabled={sorteggioInCorso}
                    onClick={sorteggia}
                  >
                    {sorteggioInCorso ? 'Sorteggio…' : 'Sorteggia'}
                  </button>
                )}
              </div>
              {ultimoSorteggio?.esiti?.length > 0 && (
                <div className="rounded-lg border border-amber-700/60 bg-amber-950/40 p-3">
                  <p className="text-xs font-bold uppercase text-amber-300 mb-2">Ultimo sorteggio</p>
                  <ul className="space-y-1">
                    {ultimoSorteggio.esiti.map((e) => (
                      <li key={e.id} className="text-sm text-white">
                        {e.personaggio_nome}
                        <span className="block text-[11px] text-gray-400">{e.giocatore_nome}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {tab === 'personaggi' && (
            <div className="space-y-3">
              {!isSaved && (
                <p className="text-sm text-amber-300">Salva prima il pool per selezionare i personaggi.</p>
              )}
              {isSaved && (
                <>
                  <label className="block">
                    <span className="text-xs font-bold text-gray-300">Evento (ordina iscritti in cima)</span>
                    <select
                      className={`${staffInputClass()} min-h-11 mt-1`}
                      value={eventoFiltro}
                      onChange={(e) => setEventoFiltro(e.target.value)}
                    >
                      <option value="">— Nessun filtro evento —</option>
                      {(meta.eventi || []).map((ev) => (
                        <option key={ev.id} value={ev.id}>
                          {ev.in_corso ? '● ' : ''}{ev.titolo}
                          {ev.data_inizio ? ` (${new Date(ev.data_inizio).toLocaleDateString()})` : ''}
                        </option>
                      ))}
                    </select>
                  </label>
                  <input
                    className={`${staffInputClass()} min-h-11`}
                    placeholder="Cerca personaggio o giocatore"
                    value={ricercaPg}
                    onChange={(e) => setRicercaPg(e.target.value)}
                  />
                  <p className={`${staffMutedClass} text-xs`}>
                    Default disattivo. I nuovi PG compaiono qui ma restano spenti finché non li attivi. Attivi: {attiviVis}.
                  </p>
                  {loadingPg ? (
                    <UiLoadingState />
                  ) : (
                    <ul className="space-y-1">
                      {personaggi.map((pg) => (
                        <li
                          key={pg.id}
                          className={`flex items-start gap-2 rounded-lg border px-2 py-2 ${
                            pg.iscritto_evento
                              ? 'border-emerald-800 bg-emerald-950/30'
                              : pg.attivo
                                ? 'border-indigo-800 bg-indigo-950/20'
                                : 'border-gray-800 bg-gray-900/40'
                          }`}
                        >
                          <input
                            type="checkbox"
                            className="mt-2 h-5 w-5 shrink-0"
                            checked={!!pg.attivo}
                            onChange={() => togglePg(pg)}
                            aria-label={`Attiva ${pg.nome}`}
                          />
                          <div className="min-w-0 flex-1">
                            <div className="font-semibold text-white break-words">{pg.nome}</div>
                            <div className="text-[11px] text-gray-400">{pg.giocatore_nome || pg.giocatore_username || '—'}</div>
                            <div className="text-[10px] text-gray-500">
                              {pg.iscritto_evento ? 'Iscritto all\'evento · ' : ''}
                              {pg.is_png ? 'PnG · ' : ''}
                              sorteggi: {pg.sorteggi_count}
                            </div>
                          </div>
                        </li>
                      ))}
                    </ul>
                  )}
                </>
              )}
            </div>
          )}

          {tab === 'messaggio' && (
            <div className={`${staffPanelClass} space-y-3`}>
              <label className="block">
                <span className="text-xs font-bold text-gray-300">Oggetto</span>
                <input
                  className={`${staffInputClass()} min-h-11 mt-1`}
                  value={form.messaggio_titolo}
                  onChange={(e) => setForm((p) => ({ ...p, messaggio_titolo: e.target.value }))}
                  placeholder="Titolo inbox (accetta {{nome_personaggio}})"
                />
              </label>
              <RichTextEditor
                label="Testo inviato ai sorteggiati"
                value={form.messaggio_testo}
                onChange={(html) => setForm((p) => ({ ...p, messaggio_testo: html }))}
              />
              <div>
                <p className="text-xs font-bold uppercase text-gray-400 mb-1">Campi variabili</p>
                <ul className="text-[12px] text-gray-400 space-y-1">
                  {(meta.placeholders || []).map((ph) => (
                    <li key={ph.token}>
                      <code className="text-emerald-300">{ph.token}</code>
                      {' — '}
                      {ph.descrizione}
                    </li>
                  ))}
                </ul>
              </div>
              <button type="button" className={`${staffPrimaryBtnClass} min-h-11`} disabled={salvataggio} onClick={salva}>
                Salva messaggio
              </button>
            </div>
          )}

          {tab === 'conteggi' && (
            <div className="space-y-2">
              {!isSaved && <p className="text-sm text-gray-400">Salva il pool per vedere i conteggi.</p>}
              <button type="button" className={`${staffSecondaryBtnClass} min-h-11`} onClick={() => editing?.id && caricaDettagliTab(editing.id, 'conteggi')}>
                <RefreshCw size={14} /> Aggiorna
              </button>
              {(conteggi?.results || []).map((row) => (
                <div key={row.id} className="rounded-lg border border-gray-800 bg-gray-900/50 px-3 py-2">
                  <div className="font-semibold text-white">{row.nome}</div>
                  <div className="text-[11px] text-gray-400">{row.giocatore_nome}</div>
                  <div className="text-xs text-gray-300">
                    Sorteggi: {row.sorteggi_count} · peso {row.peso} · p ≈ {Math.round((row.probabilita || 0) * 1000) / 10}%
                  </div>
                </div>
              ))}
              {isSaved && !(conteggi?.results || []).length && (
                <p className="text-sm text-gray-500">Nessun personaggio attivo.</p>
              )}
            </div>
          )}

          {tab === 'log' && (
            <div className="space-y-3">
              {!isSaved && <p className="text-sm text-gray-400">Salva il pool per vedere i log.</p>}
              {(log || []).map((s) => (
                <div key={s.id} className={`${staffPanelClass} space-y-2`}>
                  <div className="flex flex-wrap justify-between gap-2 text-xs text-gray-400">
                    <span>{formatWhen(s.created_at)}</span>
                    <span>
                      {s.n_estratti} estratti ({s.n_min}–{s.n_max})
                      {s.prioritario ? ' · priorità' : ''}
                    </span>
                  </div>
                  {s.evento_titolo && <p className="text-xs text-emerald-300">Evento: {s.evento_titolo}</p>}
                  <ul className="space-y-2">
                    {(s.esiti || []).map((e) => (
                      <li key={e.id} className="border-t border-gray-800 pt-2">
                        <div className="font-semibold text-white">{e.personaggio_nome}</div>
                        <div className="text-[11px] text-gray-400">{e.giocatore_nome}</div>
                        <div className="text-[11px] text-gray-500">
                          peso {e.peso} · pregressi {e.sorteggi_pregressi} · {formatWhen(e.created_at)}
                        </div>
                        {e.ack_richiesto && (
                          <div className="text-[11px] mt-1">
                            {e.confermato_at
                              ? `Confermato ${formatWhen(e.confermato_at)}${e.confermato_ip ? ` · IP ${e.confermato_ip}` : ''}${e.confermato_dispositivo?.platform ? ` · ${e.confermato_dispositivo.platform}` : ''}${e.confermato_dispositivo?.screen ? ` · ${e.confermato_dispositivo.screen}` : ''}`
                              : 'In attesa di «Ho letto e compreso»'}
                          </div>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>
              ))}
            </div>
          )}
        </div>
      </StaffFullscreenEditor>
    </StaffToolShell>
  );
}
