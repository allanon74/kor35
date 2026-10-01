import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { Camera, QrCode, RefreshCw, Package } from 'lucide-react';
import { StaffToolShell, StaffToolHeader, staffSecondaryBtnClass } from '../../staff/StaffToolShell';
import { StaffModalTabs } from '../../staff/StaffCrudUi';
import StaffEditorModal from './StaffEditorModal';
import MasterGenericList from './MasterGenericList';
import StaffQrTab from '../StaffQrTab';
import {
  staffGetRandomQrPools,
  staffCreateRandomQrPool,
  staffUpdateRandomQrPool,
  staffDeleteRandomQrPool,
  staffRandomQrPoolAddQr,
  staffRandomQrPoolRemoveQr,
  staffCreateRandomQrPoolEffect,
  staffUpdateRandomQrPoolEffect,
  staffDeleteRandomQrPoolEffect,
  staffGetSerieCollezioni,
  staffGetNodi,
  staffGetMinigiocoPatterns,
  staffGetManifesti,
  staffGetOggettiBase,
  staffGetTessiture,
  staffGetInfusioni,
  staffGetCerimoniali,
  staffGetNegoziMercante,
} from '../../api';

const defaultPesiDiff = () => ({ 1: 0, 2: 0, 3: 0, 4: 1 });

const normalizePesiDiff = (raw, fallbackDiff = 4) => {
  const base = defaultPesiDiff();
  if (raw && typeof raw === 'object') {
    [1, 2, 3, 4].forEach((d) => {
      const v = raw[d] ?? raw[String(d)];
      const n = Number(v);
      base[d] = Number.isFinite(n) && n >= 0 ? n : 0;
    });
  } else {
    const fd = Math.max(1, Math.min(4, Number(fallbackDiff) || 4));
    base[1] = 0;
    base[2] = 0;
    base[3] = 0;
    base[4] = 0;
    base[fd] = 1;
  }
  return base;
};

const emptyPool = () => ({
  nome: '',
  attivo: true,
  cooldown_attivo: false,
  cooldown_minuti_min: 5,
  cooldown_minuti_max: 25,
  minigioco_sezione_attiva: false,
  minigioco_attivo: false,
  minigioco_difficolta: 4,
  minigioco_pesi_difficolta: defaultPesiDiff(),
  minigioco_messaggio_pre: '',
  minigioco_messaggio_vittoria: '',
  minigioco_modalita_sblocco: 'permanente',
  minigioco_pattern: '',
});

const formFromPool = (p) => ({
  nome: p?.nome || '',
  attivo: !!p?.attivo,
  cooldown_attivo: !!p?.cooldown_attivo,
  cooldown_minuti_min: p?.cooldown_minuti_min ?? 5,
  cooldown_minuti_max: p?.cooldown_minuti_max ?? 25,
  minigioco_sezione_attiva: !!p?.minigioco_sezione_attiva,
  minigioco_attivo: !!p?.minigioco_attivo,
  minigioco_difficolta: p?.minigioco_difficolta ?? 4,
  minigioco_pesi_difficolta: normalizePesiDiff(
    p?.minigioco_pesi_difficolta,
    p?.minigioco_difficolta ?? 4,
  ),
  minigioco_messaggio_pre: p?.minigioco_messaggio_pre || '',
  minigioco_messaggio_vittoria: p?.minigioco_messaggio_vittoria || '',
  minigioco_modalita_sblocco: p?.minigioco_modalita_sblocco || 'permanente',
  minigioco_pattern: p?.minigioco_pattern || '',
});

const membershipNote = (m) => {
  const parts = [];
  if (m.has_negozio_mercante) parts.push('negozio mercante');
  else if (m.has_vista) parts.push('ha vista');
  if (m.in_cooldown) {
    const until = m.disponibile_dal ? new Date(m.disponibile_dal).toLocaleString() : '';
    parts.push(until ? `spento fino ${until}` : 'in cooldown');
  }
  return parts.length ? parts.join(' · ') : '—';
};
const emptyEffect = () => ({
  tipo: 'testo',
  frequenza: 1,
  ordine: 0,
  attivo: true,
  titolo: '',
  testo: '',
  nodo: '',
  durata_secondi: '',
  serie: '',
  manifesto: '',
  oggetto_base: '',
  tessitura: '',
  infusione: '',
  cerimoniale: '',
  attivata: '',
  negozio_mercante: '',
});

const effectDetailLabel = (eff) =>
  eff.titolo
  || eff.nodo_nome
  || eff.serie_nome
  || eff.manifesto_nome
  || eff.negozio_mercante_nome
  || eff.oggetto_base_nome
  || eff.tessitura_nome
  || eff.infusione_nome
  || eff.cerimoniale_nome
  || eff.attivata_nome
  || '—';

const POOL_COLUMNS = [
  {
    header: 'Nome',
    key: 'nome',
    sortable: true,
    filterable: true,
    render: (row) => <span className="font-semibold text-white">{row.nome}</span>,
  },
  {
    header: 'QR',
    key: 'qr_count',
    sortable: true,
    align: 'right',
    render: (row) => row.qr_count || 0,
  },
  {
    header: 'Effetti',
    key: 'effetti_count',
    sortable: true,
    align: 'right',
    render: (row) => row.effetti_count || 0,
  },
  {
    header: 'Attivo',
    key: 'attivo',
    sortable: true,
    render: (row) => (
      <span className={row.attivo ? 'text-emerald-400' : 'text-gray-500'}>
        {row.attivo ? 'Sì' : 'No'}
      </span>
    ),
  },
];

const RandomQrPoolManager = ({ onLogout }) => {
  const [pools, setPools] = useState([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyPool());
  const [formSnapshot, setFormSnapshot] = useState(null);
  const [modalTab, setModalTab] = useState('dati');
  const [effectForm, setEffectForm] = useState(emptyEffect());
  const [qrIdInput, setQrIdInput] = useState('');
  const [scanningQr, setScanningQr] = useState(false);
  const [serieList, setSerieList] = useState([]);
  const [nodi, setNodi] = useState([]);
  const [patterns, setPatterns] = useState([]);
  const [manifesti, setManifesti] = useState([]);
  const [oggettiBase, setOggettiBase] = useState([]);
  const [tessiture, setTessiture] = useState([]);
  const [infusioni, setInfusioni] = useState([]);
  const [cerimoniali, setCerimoniali] = useState([]);
  const [negozi, setNegozi] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const selected = pools.find((p) => p.id === selectedId) || null;
  const isDirty = Boolean(formSnapshot && JSON.stringify(form) !== formSnapshot);

  const reloadPools = useCallback(async () => {
    const data = await staffGetRandomQrPools(onLogout);
    const list = Array.isArray(data) ? data : data?.results || [];
    setPools(list);
    return list;
  }, [onLogout]);

  const reloadLookups = useCallback(async () => {
    const [
      serie,
      nodiData,
      patternData,
      manifestiData,
      oggettiData,
      tessData,
      infData,
      cerData,
      negoziData,
    ] = await Promise.all([
      staffGetSerieCollezioni(onLogout),
      staffGetNodi(onLogout),
      staffGetMinigiocoPatterns(onLogout),
      staffGetManifesti(onLogout),
      staffGetOggettiBase(onLogout),
      staffGetTessiture(onLogout, { page_size: 500 }),
      staffGetInfusioni(onLogout, { page_size: 500 }),
      staffGetCerimoniali(onLogout, { page_size: 500 }),
      staffGetNegoziMercante(onLogout),
    ]);
    setSerieList(Array.isArray(serie) ? serie : serie?.results || []);
    setNodi(Array.isArray(nodiData) ? nodiData : nodiData?.results || []);
    const plist = Array.isArray(patternData) ? patternData : patternData?.results || [];
    setPatterns(plist.filter((p) => p.attivo !== false));
    const manList = Array.isArray(manifestiData) ? manifestiData : manifestiData?.results || [];
    setManifesti(manList);
    const obList = Array.isArray(oggettiData) ? oggettiData : oggettiData?.results || [];
    setOggettiBase(obList.filter((o) => !o.non_vendibile));
    setTessiture(
      (Array.isArray(tessData) ? tessData : tessData?.results || []).filter((t) => !t.non_vendibile),
    );
    setInfusioni(
      (Array.isArray(infData) ? infData : infData?.results || []).filter((t) => !t.non_vendibile),
    );
    setCerimoniali(
      (Array.isArray(cerData) ? cerData : cerData?.results || []).filter((t) => !t.non_vendibile),
    );
    const negList = Array.isArray(negoziData) ? negoziData : negoziData?.results || [];
    setNegozi(negList.filter((n) => n.attivo !== false));
  }, [onLogout]);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        await Promise.all([reloadPools(), reloadLookups()]);
      } catch (e) {
        setError(e.message || 'Errore caricamento');
      } finally {
        setLoading(false);
      }
    })();
  }, [reloadPools, reloadLookups]);

  const openEditor = (p) => {
    if (p?.id) {
      const next = formFromPool(p);
      setSelectedId(p.id);
      setForm(next);
      setFormSnapshot(JSON.stringify(next));
      setModalTab('dati');
    } else {
      const next = emptyPool();
      setSelectedId(null);
      setForm(next);
      setFormSnapshot(JSON.stringify(next));
      setModalTab('dati');
    }
    setEffectForm(emptyEffect());
    setQrIdInput('');
    setScanningQr(false);
    setError('');
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setSelectedId(null);
    setForm(emptyPool());
    setFormSnapshot(null);
    setScanningQr(false);
    setError('');
  };

  const savePool = async ({ thenTab = null } = {}) => {
    try {
      setBusy(true);
      setError('');
      const payload = {
        ...form,
        minigioco_pattern: form.minigioco_pattern || null,
        minigioco_pesi_difficolta: {
          1: Number(form.minigioco_pesi_difficolta?.[1] ?? 0) || 0,
          2: Number(form.minigioco_pesi_difficolta?.[2] ?? 0) || 0,
          3: Number(form.minigioco_pesi_difficolta?.[3] ?? 0) || 0,
          4: Number(form.minigioco_pesi_difficolta?.[4] ?? 0) || 0,
        },
      };
      const wasNew = !selectedId;
      let id = selectedId;
      if (selectedId) {
        await staffUpdateRandomQrPool(selectedId, payload, onLogout);
      } else {
        const created = await staffCreateRandomQrPool(payload, onLogout);
        id = created.id;
        setSelectedId(created.id);
      }
      const list = await reloadPools();
      const updated = list.find((p) => p.id === id);
      if (updated) {
        const next = formFromPool(updated);
        setForm(next);
        setFormSnapshot(JSON.stringify(next));
      }
      if (thenTab) setModalTab(thenTab);
      else if (wasNew) setModalTab('qr');
    } catch (e) {
      setError(e.message || 'Salvataggio fallito');
    } finally {
      setBusy(false);
    }
  };

  const addQrById = async (rawId, { fromScan = false } = {}) => {
    const qrId = (rawId || '').trim();
    if (!selectedId || !qrId) return;
    try {
      setBusy(true);
      setError('');
      const res = await staffRandomQrPoolAddQr(selectedId, qrId, onLogout);
      if (res?.warning_has_negozio_mercante || res?.warning_has_vista) {
        setError(res.message || 'QR aggiunto con nota: il pool ha priorità alla scansione.');
      }
      setQrIdInput('');
      if (fromScan) setScanningQr(false);
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Associazione QR fallita');
    } finally {
      setBusy(false);
    }
  };

  const addQr = async () => addQrById(qrIdInput);
  const removeQr = async (qrCodeId) => {
    try {
      setBusy(true);
      await staffRandomQrPoolRemoveQr(selectedId, qrCodeId, onLogout);
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Rimozione fallita');
    } finally {
      setBusy(false);
    }
  };

  const saveEffect = async () => {
    if (!selectedId) return;
    try {
      setBusy(true);
      setError('');
      const tipo = effectForm.tipo;
      const payload = {
        tipo,
        frequenza: Math.max(1, parseInt(effectForm.frequenza, 10) || 1),
        ordine: parseInt(effectForm.ordine, 10) || 0,
        attivo: true,
        titolo: effectForm.titolo || '',
        testo: effectForm.testo || '',
        nodo: tipo === 'nodo' && effectForm.nodo ? Number(effectForm.nodo) : null,
        serie: tipo === 'serie' && effectForm.serie ? effectForm.serie : null,
        durata_secondi:
          tipo === 'trappola' && effectForm.durata_secondi !== ''
            ? Number(effectForm.durata_secondi)
            : null,
        manifesto: tipo === 'manifesto' && effectForm.manifesto ? Number(effectForm.manifesto) : null,
        oggetto_base:
          tipo === 'oggetto_base' && effectForm.oggetto_base ? Number(effectForm.oggetto_base) : null,
        tessitura: tipo === 'tessitura' && effectForm.tessitura ? Number(effectForm.tessitura) : null,
        infusione:
          (tipo === 'infusione' || tipo === 'da_infusione') && effectForm.infusione
            ? Number(effectForm.infusione)
            : null,
        cerimoniale:
          tipo === 'cerimoniale' && effectForm.cerimoniale ? Number(effectForm.cerimoniale) : null,
        attivata: tipo === 'attivata' && effectForm.attivata ? Number(effectForm.attivata) : null,
        negozio_mercante:
          tipo === 'negozio_mercante' && effectForm.negozio_mercante
            ? effectForm.negozio_mercante
            : null,
      };
      await staffCreateRandomQrPoolEffect(selectedId, payload, onLogout);
      setEffectForm(emptyEffect());
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Effetto non salvato');
    } finally {
      setBusy(false);
    }
  };

  const patchEffectFreq = async (eff, frequenza) => {
    try {
      await staffUpdateRandomQrPoolEffect(eff.id, { frequenza: Math.max(1, Number(frequenza) || 1) }, onLogout);
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Update frequenza fallito');
    }
  };

  const deleteEffect = async (id) => {
    try {
      await staffDeleteRandomQrPoolEffect(id, onLogout);
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Eliminazione effetto fallita');
    }
  };

  const deletePool = async (id) => {
    await staffDeleteRandomQrPool(id, onLogout);
    if (selectedId === id) closeEditor();
    await reloadPools();
  };

  const modalTabs = useMemo(
    () => [
      { id: 'dati', label: 'Dati pool' },
      { id: 'qr', label: 'QR', count: selected?.memberships?.length || 0 },
      { id: 'effetti', label: 'Effetti', count: selected?.effetti?.length || 0 },
    ],
    [selected],
  );

  return (
    <StaffToolShell fill>
      <StaffToolHeader
        icon={<QrCode size={22} />}
        title="QR — Pool randomico"
        description="Lista pool: apri un record per dati, QR ed effetti."
        actions={
          <button type="button" onClick={reloadPools} className={staffSecondaryBtnClass}>
            <RefreshCw size={16} />
            Aggiorna
          </button>
        }
      />
      <div className="flex-1 min-h-0 overflow-hidden p-4 md:p-6 flex flex-col">
        <MasterGenericList
          items={pools}
          title="Elenco"
          loading={loading}
          persistKey="qr-random-pool"
          addLabel="Nuovo pool"
          onAdd={() => openEditor(null)}
          onEdit={openEditor}
          onDelete={deletePool}
          onRowClick={openEditor}
          columns={POOL_COLUMNS}
          searchPlaceholder="Cerca pool…"
          emptyMessage="Nessun pool. Creane uno per iniziare."
        />
      </div>

      {editorOpen && (
        <StaffEditorModal
          title={selectedId ? `Pool: ${form.nome || 'senza nome'}` : 'Nuovo pool'}
          size="xl"
          saving={busy}
          isDirty={isDirty}
          onClose={closeEditor}
          onSave={() => savePool({ thenTab: selectedId ? null : 'qr' })}
          saveLabel={selectedId ? 'Salva dati' : 'Crea e vai ai QR'}
        >
          <StaffModalTabs tabs={modalTabs} active={modalTab} onChange={setModalTab} />
          {error ? <p className="text-sm text-amber-200">{error}</p> : null}

          {modalTab === 'dati' && (
            <div className="space-y-3">
              <input
                className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm"
                placeholder="Nome pool"
                value={form.nome}
                onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
              />
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={form.attivo}
                  onChange={(e) => setForm((f) => ({ ...f, attivo: e.target.checked }))}
                />
                Pool attivo
              </label>
              <div className="border border-gray-700 rounded-lg p-3 space-y-2">
                <div className="text-xs uppercase text-gray-400">Spegnimento QR (stile nodi)</div>
                <p className="text-[11px] text-gray-500 leading-snug">
                  Dopo una scansione riuscita il QR fisico si spegne per tutti per un intervallo
                  casuale (min–max). Separato dall&apos;anti-farm: ogni PG può comunque usare ogni QR
                  una sola volta.
                </p>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.cooldown_attivo}
                    onChange={(e) => setForm((f) => ({ ...f, cooldown_attivo: e.target.checked }))}
                  />
                  Attiva cooldown / spegnimento
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-gray-400">
                    Minuti min
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                      value={form.cooldown_minuti_min}
                      onChange={(e) => setForm((f) => ({
                        ...f,
                        cooldown_minuti_min: Number(e.target.value),
                      }))}
                      disabled={!form.cooldown_attivo}
                    />
                  </label>
                  <label className="text-xs text-gray-400">
                    Minuti max
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                      value={form.cooldown_minuti_max}
                      onChange={(e) => setForm((f) => ({
                        ...f,
                        cooldown_minuti_max: Number(e.target.value),
                      }))}
                      disabled={!form.cooldown_attivo}
                    />
                  </label>
                </div>
              </div>
              <div className="border border-gray-700 rounded-lg p-3 space-y-2">
                <div className="text-xs uppercase text-gray-400">Minigioco a monte (tutti i QR del pool)</div>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.minigioco_sezione_attiva}
                    onChange={(e) => setForm((f) => ({ ...f, minigioco_sezione_attiva: e.target.checked }))}
                  />
                  Sezione minigioco attiva
                </label>
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={form.minigioco_attivo}
                    onChange={(e) => setForm((f) => ({ ...f, minigioco_attivo: e.target.checked }))}
                  />
                  Richiedi minigioco
                </label>
                <label className="block text-xs text-gray-400">
                  Pattern estrazione minigioco
                  <select
                    className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm mt-0.5"
                    value={form.minigioco_pattern || ''}
                    onChange={(e) => setForm((f) => ({ ...f, minigioco_pattern: e.target.value }))}
                  >
                    <option value="">— Senza pattern: tipi/difficoltà sul pool (legacy) —</option>
                    {patterns.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                  </select>
                </label>
                <p className="text-[11px] text-gray-500 leading-snug">
                  Controlla quale puzzle (tipo + difficoltà) viene estratto prima dell&apos;effetto,
                  non la tabella effetti pesati del pool. I pattern si creano nel tool «Pattern
                  minigioco». Senza pattern: usa i pesi difficoltà sotto (e i tipi abilitati sul pool).
                </p>
                {!form.minigioco_pattern ? (
                  <div className="space-y-1">
                    <div className="text-xs text-gray-400">Frequenza difficoltà minigioco (pesi relativi)</div>
                    <p className="text-[11px] text-gray-500 leading-snug">
                      Es. 20-20-50-10 oppure 2-2-5-1: probabilità proporzionali alla somma dei pesi.
                      Tutti zero → fallback alla difficoltà legacy sotto.
                    </p>
                    <div className="grid grid-cols-4 gap-2">
                      {[1, 2, 3, 4].map((d) => (
                        <label key={d} className="text-xs text-gray-400">
                          Diff. {d}
                          <input
                            type="number"
                            min={0}
                            className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                            value={form.minigioco_pesi_difficolta?.[d] ?? 0}
                            onChange={(e) => {
                              const n = Number(e.target.value);
                              setForm((f) => ({
                                ...f,
                                minigioco_pesi_difficolta: {
                                  ...f.minigioco_pesi_difficolta,
                                  [d]: Number.isFinite(n) ? Math.max(0, n) : 0,
                                },
                              }));
                            }}
                          />
                        </label>
                      ))}
                    </div>
                  </div>
                ) : null}
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-gray-400">
                    Difficoltà fallback
                    <input
                      type="number"
                      min={1}
                      max={4}
                      className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                      value={form.minigioco_difficolta}
                      onChange={(e) => setForm((f) => ({ ...f, minigioco_difficolta: Number(e.target.value) }))}
                      disabled={Boolean(form.minigioco_pattern)}
                    />
                  </label>
                  <label className="text-xs text-gray-400">
                    Modalità sblocco
                    <select
                      className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                      value={form.minigioco_modalita_sblocco}
                      onChange={(e) => setForm((f) => ({ ...f, minigioco_modalita_sblocco: e.target.value }))}
                    >
                      <option value="permanente">Permanente</option>
                      <option value="ogni_scansione">Ogni scansione</option>
                      <option value="temporaneo">Temporaneo</option>
                    </select>
                  </label>
                </div>
                <textarea
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                  rows={2}
                  placeholder="Messaggio pre-minigioco"
                  value={form.minigioco_messaggio_pre}
                  onChange={(e) => setForm((f) => ({ ...f, minigioco_messaggio_pre: e.target.value }))}
                />
              </div>
            </div>
          )}

          {modalTab === 'qr' && (
            <div className="space-y-3">
              {!selectedId ? (
                <div className="rounded-lg border border-amber-800 bg-amber-950/40 p-4 text-sm text-amber-100">
                  Salva prima i dati del pool, poi aggiungi i QR.
                  <button
                    type="button"
                    className="mt-3 block px-3 py-1.5 bg-amber-700 rounded font-bold"
                    onClick={() => savePool({ thenTab: 'qr' })}
                  >
                    Crea pool e apri QR
                  </button>
                </div>
              ) : (
                <>
                  <p className="text-[11px] text-gray-500 leading-snug">
                    Aggiungi i QR fisici del pool: incolla l&apos;ID oppure scansiona con la fotocamera.
                    Se il QR era un negozio mercante, resta nel pool e alla scansione estrae gli effetti
                    (il negozio non si apre finché è membership).
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      className="flex-1 min-w-0 bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm font-mono"
                      placeholder="ID QR fisico"
                      value={qrIdInput}
                      onChange={(e) => setQrIdInput(e.target.value)}
                      onKeyDown={(e) => {
                        if (e.key === 'Enter') {
                          e.preventDefault();
                          addQr();
                        }
                      }}
                    />
                    <div className="flex gap-2 shrink-0">
                      <button
                        type="button"
                        onClick={addQr}
                        disabled={busy || !qrIdInput.trim()}
                        className="flex-1 sm:flex-none px-3 py-1.5 bg-emerald-700 rounded text-sm font-bold disabled:opacity-50"
                      >
                        Aggiungi
                      </button>
                      <button
                        type="button"
                        onClick={() => setScanningQr(true)}
                        disabled={busy}
                        className="flex-1 sm:flex-none inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-sky-700 rounded text-sm font-bold disabled:opacity-50"
                        title="Scansiona QR fisico"
                      >
                        <Camera size={16} />
                        Scansiona
                      </button>
                    </div>
                  </div>
                  <div className="rounded-lg border border-gray-700 overflow-x-auto">
                    <table className="w-full text-sm min-w-[280px]">
                      <thead className="bg-gray-950 text-[10px] uppercase tracking-wider text-gray-500">
                        <tr>
                          <th className="text-left px-3 py-2">QR</th>
                          <th className="text-left px-3 py-2">Note</th>
                          <th className="text-right px-3 py-2 w-24">Azioni</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {(selected?.memberships || []).map((m) => (
                          <tr key={m.id} className="bg-gray-900/40">
                            <td className="px-3 py-2 font-mono text-xs break-all">{m.qr_code_id || m.qr_code}</td>
                            <td className={`px-3 py-2 text-xs ${m.in_cooldown || m.has_negozio_mercante ? 'text-amber-400' : 'text-gray-400'}`}>
                              {membershipNote(m)}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <button
                                type="button"
                                className="text-red-400 text-xs hover:text-red-300"
                                onClick={() => removeQr(m.qr_code_id || m.qr_code)}
                              >
                                Rimuovi
                              </button>
                            </td>
                          </tr>
                        ))}
                        {!(selected?.memberships || []).length && (
                          <tr>
                            <td colSpan={3} className="px-3 py-6 text-center text-gray-500 text-sm">
                              Nessun QR. Aggiungine uno dal campo o con Scansiona.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}

          {modalTab === 'effetti' && (
            <div className="space-y-3">
              {!selectedId ? (
                <p className="text-sm text-gray-400">Salva il pool per aggiungere effetti.</p>
              ) : (
                <>
                  <div className="rounded-lg border border-gray-700 bg-gray-950/60 p-3 space-y-2">
                    <div className="flex items-center gap-2 text-sm font-bold text-gray-200">
                      <Package size={16} className="text-rose-400" />
                      Nuovo effetto
                    </div>
                    <div className="grid sm:grid-cols-2 gap-2 text-sm">
                      <select
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={effectForm.tipo}
                        onChange={(e) => setEffectForm((f) => ({ ...f, tipo: e.target.value }))}
                      >
                        <option value="testo">Testo</option>
                        <option value="nodo">Nodo</option>
                        <option value="trappola">Trappola</option>
                        <option value="serie">Serie</option>
                        <option value="manifesto">Manifesto (anche condizionale)</option>
                        <option value="negozio_mercante">Negozio mercante</option>
                        <option value="oggetto_base">Oggetto (listino Accademia)</option>
                        <option value="da_infusione">Materia/Mod (da Infusione)</option>
                        <option value="tessitura">Tessitura</option>
                        <option value="infusione">Infusione (ricetta)</option>
                        <option value="cerimoniale">Cerimoniale</option>
                      </select>
                      <input
                        type="number"
                        min={1}
                        className="bg-gray-900 border border-gray-600 rounded p-2"
                        value={effectForm.frequenza}
                        onChange={(e) => setEffectForm((f) => ({ ...f, frequenza: e.target.value }))}
                        placeholder="Frequenza"
                      />
                      {(effectForm.tipo === 'testo' || effectForm.tipo === 'trappola') && (
                        <>
                          <input
                            className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                            placeholder="Titolo"
                            value={effectForm.titolo}
                            onChange={(e) => setEffectForm((f) => ({ ...f, titolo: e.target.value }))}
                          />
                          <textarea
                            className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                            rows={2}
                            placeholder="Testo"
                            value={effectForm.testo}
                            onChange={(e) => setEffectForm((f) => ({ ...f, testo: e.target.value }))}
                          />
                        </>
                      )}
                      {effectForm.tipo === 'trappola' && (
                        <input
                          type="number"
                          min={0}
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          placeholder="Durata secondi (vuoto = solo testo)"
                          value={effectForm.durata_secondi}
                          onChange={(e) => setEffectForm((f) => ({ ...f, durata_secondi: e.target.value }))}
                        />
                      )}
                      {effectForm.tipo === 'nodo' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.nodo}
                          onChange={(e) => setEffectForm((f) => ({ ...f, nodo: e.target.value }))}
                        >
                          <option value="">Seleziona nodo…</option>
                          {nodi.map((n) => (
                            <option key={n.id} value={n.id}>{n.nome}</option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'serie' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.serie}
                          onChange={(e) => setEffectForm((f) => ({ ...f, serie: e.target.value }))}
                        >
                          <option value="">Seleziona serie…</option>
                          {serieList.map((s) => (
                            <option key={s.id} value={s.id}>
                              {s.nome} ({s.pezzi_rimanenti}/{s.totale} liberi)
                            </option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'manifesto' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.manifesto}
                          onChange={(e) => setEffectForm((f) => ({ ...f, manifesto: e.target.value }))}
                        >
                          <option value="">Seleziona manifesto…</option>
                          {manifesti.map((m) => (
                            <option key={m.id} value={m.id}>{m.nome}</option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'negozio_mercante' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.negozio_mercante}
                          onChange={(e) => setEffectForm((f) => ({ ...f, negozio_mercante: e.target.value }))}
                        >
                          <option value="">Seleziona negozio mercante…</option>
                          {negozi.map((n) => (
                            <option key={n.id} value={n.id}>{n.nome}</option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'oggetto_base' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.oggetto_base}
                          onChange={(e) => setEffectForm((f) => ({ ...f, oggetto_base: e.target.value }))}
                        >
                          <option value="">Seleziona oggetto listino…</option>
                          {oggettiBase.map((o) => (
                            <option key={o.id} value={o.id}>{o.nome}</option>
                          ))}
                        </select>
                      )}
                      {(effectForm.tipo === 'da_infusione' || effectForm.tipo === 'infusione') && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.infusione}
                          onChange={(e) => setEffectForm((f) => ({ ...f, infusione: e.target.value }))}
                        >
                          <option value="">
                            {effectForm.tipo === 'da_infusione'
                              ? 'Seleziona Infusione (matrice Materia/Mod)…'
                              : 'Seleziona Infusione (ricetta)…'}
                          </option>
                          {infusioni.map((t) => (
                            <option key={t.id} value={t.id}>{t.nome}</option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'tessitura' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.tessitura}
                          onChange={(e) => setEffectForm((f) => ({ ...f, tessitura: e.target.value }))}
                        >
                          <option value="">Seleziona tessitura…</option>
                          {tessiture.map((t) => (
                            <option key={t.id} value={t.id}>{t.nome}</option>
                          ))}
                        </select>
                      )}
                      {effectForm.tipo === 'cerimoniale' && (
                        <select
                          className="sm:col-span-2 bg-gray-900 border border-gray-600 rounded p-2"
                          value={effectForm.cerimoniale}
                          onChange={(e) => setEffectForm((f) => ({ ...f, cerimoniale: e.target.value }))}
                        >
                          <option value="">Seleziona cerimoniale…</option>
                          {cerimoniali.map((t) => (
                            <option key={t.id} value={t.id}>{t.nome}</option>
                          ))}
                        </select>
                      )}
                    </div>
                    <button
                      type="button"
                      onClick={saveEffect}
                      className="px-3 py-1.5 bg-rose-700 hover:bg-rose-600 rounded text-sm font-bold"
                    >
                      Aggiungi effetto
                    </button>
                  </div>
                  <div className="rounded-lg border border-gray-700 overflow-hidden">
                    <table className="w-full text-sm">
                      <thead className="bg-gray-950 text-[10px] uppercase tracking-wider text-gray-500">
                        <tr>
                          <th className="text-left px-3 py-2">Tipo</th>
                          <th className="text-left px-3 py-2">Dettaglio</th>
                          <th className="text-right px-3 py-2">Freq</th>
                          <th className="text-right px-3 py-2 w-24">Azioni</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {(selected?.effetti || []).map((eff) => (
                          <tr key={eff.id} className="bg-gray-900/40">
                            <td className="px-3 py-2 uppercase text-rose-300 font-bold text-xs">{eff.tipo}</td>
                            <td className="px-3 py-2 text-white truncate">
                              {effectDetailLabel(eff)}
                            </td>
                            <td className="px-3 py-2 text-right">
                              <input
                                type="number"
                                min={1}
                                className="w-16 bg-gray-950 border border-gray-600 rounded px-1 text-right"
                                defaultValue={eff.frequenza}
                                onBlur={(e) => patchEffectFreq(eff, e.target.value)}
                              />
                            </td>
                            <td className="px-3 py-2 text-right">
                              <button type="button" className="text-red-400 text-xs" onClick={() => deleteEffect(eff.id)}>
                                Elimina
                              </button>
                            </td>
                          </tr>
                        ))}
                        {!(selected?.effetti || []).length && (
                          <tr>
                            <td colSpan={4} className="px-3 py-6 text-center text-gray-500 text-sm">
                              Nessun effetto. Aggiungine uno dal modulo sopra.
                            </td>
                          </tr>
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </div>
          )}
        </StaffEditorModal>
      )}

      {scanningQr && (
        <div className="fixed inset-0 z-[60] bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center gap-3 bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white text-sm sm:text-base">
              Scansiona QR da aggiungere al pool
            </span>
            <button
              type="button"
              onClick={() => setScanningQr(false)}
              className="px-4 py-2 bg-red-600 rounded shrink-0"
            >
              Chiudi
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <StaffQrTab
              onLogout={onLogout}
              onScanSuccess={async (qr_id) => {
                await addQrById(qr_id, { fromScan: true });
              }}
            />
          </div>
        </div>
      )}
    </StaffToolShell>
  );
};

export default memo(RandomQrPoolManager);
