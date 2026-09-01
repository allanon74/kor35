import React, { useState, useEffect, useCallback, useMemo, memo } from 'react';
import { QrCode, RefreshCw, Package } from 'lucide-react';
import { StaffToolShell, StaffToolHeader, staffSecondaryBtnClass } from '../../staff/StaffToolShell';
import { StaffModalTabs } from '../../staff/StaffCrudUi';
import StaffEditorModal from './StaffEditorModal';
import MasterGenericList from './MasterGenericList';
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
} from '../../api';

const emptyPool = () => ({
  nome: '',
  attivo: true,
  minigioco_sezione_attiva: false,
  minigioco_attivo: false,
  minigioco_difficolta: 4,
  minigioco_messaggio_pre: '',
  minigioco_messaggio_vittoria: '',
  minigioco_modalita_sblocco: 'permanente',
  minigioco_pattern: '',
});

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
});

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
  const [serieList, setSerieList] = useState([]);
  const [nodi, setNodi] = useState([]);
  const [patterns, setPatterns] = useState([]);
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
    const [serie, nodiData, patternData] = await Promise.all([
      staffGetSerieCollezioni(onLogout),
      staffGetNodi(onLogout),
      staffGetMinigiocoPatterns(onLogout),
    ]);
    setSerieList(Array.isArray(serie) ? serie : serie?.results || []);
    setNodi(Array.isArray(nodiData) ? nodiData : nodiData?.results || []);
    const plist = Array.isArray(patternData) ? patternData : patternData?.results || [];
    setPatterns(plist.filter((p) => p.attivo !== false));
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
      const next = {
        nome: p.nome || '',
        attivo: !!p.attivo,
        minigioco_sezione_attiva: !!p.minigioco_sezione_attiva,
        minigioco_attivo: !!p.minigioco_attivo,
        minigioco_difficolta: p.minigioco_difficolta ?? 4,
        minigioco_messaggio_pre: p.minigioco_messaggio_pre || '',
        minigioco_messaggio_vittoria: p.minigioco_messaggio_vittoria || '',
        minigioco_modalita_sblocco: p.minigioco_modalita_sblocco || 'permanente',
        minigioco_pattern: p.minigioco_pattern || '',
      };
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
    setError('');
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setSelectedId(null);
    setForm(emptyPool());
    setFormSnapshot(null);
    setError('');
  };

  const savePool = async ({ thenTab = null } = {}) => {
    try {
      setBusy(true);
      setError('');
      const payload = {
        ...form,
        minigioco_pattern: form.minigioco_pattern || null,
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
        const next = {
          nome: updated.nome || '',
          attivo: !!updated.attivo,
          minigioco_sezione_attiva: !!updated.minigioco_sezione_attiva,
          minigioco_attivo: !!updated.minigioco_attivo,
          minigioco_difficolta: updated.minigioco_difficolta ?? 4,
          minigioco_messaggio_pre: updated.minigioco_messaggio_pre || '',
          minigioco_messaggio_vittoria: updated.minigioco_messaggio_vittoria || '',
          minigioco_modalita_sblocco: updated.minigioco_modalita_sblocco || 'permanente',
          minigioco_pattern: updated.minigioco_pattern || '',
        };
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

  const addQr = async () => {
    if (!selectedId || !qrIdInput.trim()) return;
    try {
      setBusy(true);
      setError('');
      const res = await staffRandomQrPoolAddQr(selectedId, qrIdInput.trim(), onLogout);
      if (res?.warning_has_vista) {
        setError(res.message || 'QR ha già una vista; il pool ha priorità.');
      }
      setQrIdInput('');
      await reloadPools();
    } catch (e) {
      setError(e.message || 'Associazione QR fallita');
    } finally {
      setBusy(false);
    }
  };

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
      const payload = {
        ...effectForm,
        frequenza: Math.max(1, parseInt(effectForm.frequenza, 10) || 1),
        ordine: parseInt(effectForm.ordine, 10) || 0,
        nodo: effectForm.tipo === 'nodo' && effectForm.nodo ? Number(effectForm.nodo) : null,
        serie: effectForm.tipo === 'serie' && effectForm.serie ? effectForm.serie : null,
        durata_secondi:
          effectForm.tipo === 'trappola' && effectForm.durata_secondi !== ''
            ? Number(effectForm.durata_secondi)
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
                  Pattern estrazione
                  <select
                    className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm mt-0.5"
                    value={form.minigioco_pattern || ''}
                    onChange={(e) => setForm((f) => ({ ...f, minigioco_pattern: e.target.value }))}
                  >
                    <option value="">— Legacy (tipi/diff sul pool) —</option>
                    {patterns.map((p) => (
                      <option key={p.id} value={p.id}>{p.nome}</option>
                    ))}
                  </select>
                </label>
                <div className="grid grid-cols-2 gap-2">
                  <label className="text-xs text-gray-400">
                    Difficoltà
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
                  <div className="flex gap-2">
                    <input
                      className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1.5 text-sm font-mono"
                      placeholder="ID QR fisico"
                      value={qrIdInput}
                      onChange={(e) => setQrIdInput(e.target.value)}
                    />
                    <button type="button" onClick={addQr} className="px-3 py-1.5 bg-emerald-700 rounded text-sm font-bold">
                      Aggiungi
                    </button>
                  </div>
                  <div className="rounded-lg border border-gray-700 overflow-hidden">
                    <table className="w-full text-sm">
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
                            <td className="px-3 py-2 font-mono text-xs">{m.qr_code_id || m.qr_code}</td>
                            <td className="px-3 py-2 text-amber-400 text-xs">{m.has_vista ? 'ha vista' : '—'}</td>
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
                              Nessun QR. Aggiungine uno dal campo sopra.
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
                              {eff.titolo || eff.nodo_nome || eff.serie_nome || '—'}
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
    </StaffToolShell>
  );
};

export default memo(RandomQrPoolManager);
