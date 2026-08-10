import React, { useState, useEffect, useCallback, memo } from 'react';
import { StaffToolShell, StaffToolHeader } from '../../staff/StaffToolShell';
import ConfirmDialog from './ConfirmDialog';
import StaffQrBadge from './StaffQrBadge';
import StaffQrTab from '../StaffQrTab';
import {
  associaQrDiretto,
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
  staffCreateSerieCollezione,
  staffDeleteSerieCollezione,
  staffGetTrappole,
  staffCreateTrappola,
  staffDeleteTrappola,
  staffGetSerieQr,
  staffCreateSerieQr,
  staffGetNodi,
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

const RandomQrPoolManager = ({ onLogout }) => {
  const [tab, setTab] = useState('pools');
  const [pools, setPools] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyPool());
  const [effectForm, setEffectForm] = useState(emptyEffect());
  const [qrIdInput, setQrIdInput] = useState('');
  const [serieList, setSerieList] = useState([]);
  const [serieForm, setSerieForm] = useState({ nome: '', totale: 30, descrizione: '' });
  const [trappole, setTrappole] = useState([]);
  const [trappolaForm, setTrappolaForm] = useState({ nome: '', testo: '', durata_secondi: 60 });
  const [serieQrList, setSerieQrList] = useState([]);
  const [serieQrForm, setSerieQrForm] = useState({ nome: '', testo: '', serie: '' });
  const [nodi, setNodi] = useState([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);
  const [scanningId, setScanningId] = useState(null);

  const selected = pools.find((p) => p.id === selectedId) || null;

  const reloadPools = useCallback(async () => {
    const data = await staffGetRandomQrPools(onLogout);
    const list = Array.isArray(data) ? data : data?.results || [];
    setPools(list);
    return list;
  }, [onLogout]);

  const reloadMeta = useCallback(async () => {
    const [serie, traps, sqr, nodiData] = await Promise.all([
      staffGetSerieCollezioni(onLogout),
      staffGetTrappole(onLogout),
      staffGetSerieQr(onLogout),
      staffGetNodi(onLogout),
    ]);
    setSerieList(Array.isArray(serie) ? serie : serie?.results || []);
    setTrappole(Array.isArray(traps) ? traps : traps?.results || []);
    setSerieQrList(Array.isArray(sqr) ? sqr : sqr?.results || []);
    setNodi(Array.isArray(nodiData) ? nodiData : nodiData?.results || []);
  }, [onLogout]);

  useEffect(() => {
    (async () => {
      try {
        setBusy(true);
        await Promise.all([reloadPools(), reloadMeta()]);
      } catch (e) {
        setError(e.message || 'Errore caricamento');
      } finally {
        setBusy(false);
      }
    })();
  }, [reloadPools, reloadMeta]);

  const selectPool = (p) => {
    setSelectedId(p.id);
    setForm({
      nome: p.nome || '',
      attivo: !!p.attivo,
      minigioco_sezione_attiva: !!p.minigioco_sezione_attiva,
      minigioco_attivo: !!p.minigioco_attivo,
      minigioco_difficolta: p.minigioco_difficolta ?? 4,
      minigioco_messaggio_pre: p.minigioco_messaggio_pre || '',
      minigioco_messaggio_vittoria: p.minigioco_messaggio_vittoria || '',
      minigioco_modalita_sblocco: p.minigioco_modalita_sblocco || 'permanente',
    });
    setEffectForm(emptyEffect());
  };

  const savePool = async () => {
    try {
      setBusy(true);
      setError('');
      if (selectedId) {
        await staffUpdateRandomQrPool(selectedId, form, onLogout);
      } else {
        const created = await staffCreateRandomQrPool(form, onLogout);
        setSelectedId(created.id);
      }
      await reloadPools();
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

  const renderPoolsTab = () => (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div className="space-y-2">
        <button
          type="button"
          className="w-full px-3 py-2 bg-rose-700 hover:bg-rose-600 rounded text-sm"
          onClick={() => {
            setSelectedId(null);
            setForm(emptyPool());
          }}
        >
          + Nuovo pool
        </button>
        <div className="max-h-[70vh] overflow-y-auto space-y-1">
          {pools.map((p) => (
            <button
              key={p.id}
              type="button"
              onClick={() => selectPool(p)}
              className={`w-full text-left px-3 py-2 rounded border ${
                selectedId === p.id ? 'border-rose-500 bg-rose-950/40' : 'border-gray-700 bg-gray-900/40'
              }`}
            >
              <div className="font-semibold text-sm">{p.nome}</div>
              <div className="text-[10px] text-gray-400">
                {p.qr_count || 0} QR · {p.effetti_count || 0} effetti
                {!p.attivo ? ' · OFF' : ''}
              </div>
            </button>
          ))}
        </div>
      </div>

      <div className="lg:col-span-2 space-y-4">
        <div className="bg-gray-900/50 border border-gray-700 rounded p-3 space-y-2">
          <h3 className="font-bold text-rose-300">{selectedId ? 'Modifica pool' : 'Nuovo pool'}</h3>
          <input
            className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
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
          <div className="border-t border-gray-700 pt-2 mt-2">
            <div className="text-xs uppercase text-gray-400 mb-1">Minigioco a monte (tutti i QR del pool)</div>
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
            <div className="grid grid-cols-2 gap-2 mt-1">
              <label className="text-xs text-gray-400">
                Difficoltà
                <input
                  type="number"
                  min={1}
                  max={4}
                  className="w-full bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                  value={form.minigioco_difficolta}
                  onChange={(e) => setForm((f) => ({ ...f, minigioco_difficolta: Number(e.target.value) }))}
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
              className="w-full mt-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
              rows={2}
              placeholder="Messaggio pre-minigioco"
              value={form.minigioco_messaggio_pre}
              onChange={(e) => setForm((f) => ({ ...f, minigioco_messaggio_pre: e.target.value }))}
            />
          </div>
          <div className="flex gap-2">
            <button
              type="button"
              disabled={busy || !form.nome.trim()}
              onClick={savePool}
              className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 rounded text-sm disabled:opacity-50"
            >
              Salva
            </button>
            {selectedId && (
              <button
                type="button"
                className="px-3 py-1.5 bg-red-800 hover:bg-red-700 rounded text-sm"
                onClick={() => setConfirmDelete({ type: 'pool', id: selectedId, label: form.nome })}
              >
                Elimina
              </button>
            )}
          </div>
        </div>

        {selected && (
          <>
            <div className="bg-gray-900/50 border border-gray-700 rounded p-3 space-y-2">
              <h3 className="font-bold text-sm">QR nel pool</h3>
              <div className="flex gap-2">
                <input
                  className="flex-1 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm font-mono"
                  placeholder="ID QR fisico"
                  value={qrIdInput}
                  onChange={(e) => setQrIdInput(e.target.value)}
                />
                <button type="button" onClick={addQr} className="px-3 py-1 bg-emerald-700 rounded text-sm">
                  Aggiungi
                </button>
              </div>
              <ul className="space-y-1 text-sm">
                {(selected.memberships || []).map((m) => (
                  <li key={m.id} className="flex items-center justify-between gap-2 bg-gray-800/50 px-2 py-1 rounded">
                    <span className="font-mono text-xs">{m.qr_code_id || m.qr_code}</span>
                    {m.has_vista ? <span className="text-[10px] text-amber-400">ha vista</span> : null}
                    <button type="button" className="text-red-400 text-xs" onClick={() => removeQr(m.qr_code_id || m.qr_code)}>
                      Rimuovi
                    </button>
                  </li>
                ))}
              </ul>
            </div>

            <div className="bg-gray-900/50 border border-gray-700 rounded p-3 space-y-2">
              <h3 className="font-bold text-sm">Effetti (frequenza = peso)</h3>
              <ul className="space-y-1">
                {(selected.effetti || []).map((eff) => (
                  <li key={eff.id} className="flex flex-wrap items-center gap-2 bg-gray-800/40 px-2 py-1 rounded text-xs">
                    <span className="uppercase text-rose-300 font-bold">{eff.tipo}</span>
                    <span className="truncate max-w-[140px]">{eff.titolo || eff.nodo_nome || eff.serie_nome || '—'}</span>
                    <label className="flex items-center gap-1">
                      freq
                      <input
                        type="number"
                        min={1}
                        className="w-16 bg-gray-900 border border-gray-600 rounded px-1"
                        defaultValue={eff.frequenza}
                        onBlur={(e) => patchEffectFreq(eff, e.target.value)}
                      />
                    </label>
                    <button type="button" className="text-red-400 ml-auto" onClick={() => deleteEffect(eff.id)}>
                      Elimina
                    </button>
                  </li>
                ))}
              </ul>
              <div className="grid grid-cols-2 gap-2 border-t border-gray-700 pt-2">
                <select
                  className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
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
                  className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                  value={effectForm.frequenza}
                  onChange={(e) => setEffectForm((f) => ({ ...f, frequenza: e.target.value }))}
                  placeholder="Frequenza"
                />
                {(effectForm.tipo === 'testo' || effectForm.tipo === 'trappola') && (
                  <>
                    <input
                      className="col-span-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                      placeholder="Titolo"
                      value={effectForm.titolo}
                      onChange={(e) => setEffectForm((f) => ({ ...f, titolo: e.target.value }))}
                    />
                    <textarea
                      className="col-span-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
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
                    className="col-span-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                    placeholder="Durata secondi (vuoto = solo testo)"
                    value={effectForm.durata_secondi}
                    onChange={(e) => setEffectForm((f) => ({ ...f, durata_secondi: e.target.value }))}
                  />
                )}
                {effectForm.tipo === 'nodo' && (
                  <select
                    className="col-span-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
                    value={effectForm.nodo}
                    onChange={(e) => setEffectForm((f) => ({ ...f, nodo: e.target.value }))}
                  >
                    <option value="">Seleziona nodo…</option>
                    {nodi.map((n) => (
                      <option key={n.id} value={n.id}>
                        {n.nome}
                      </option>
                    ))}
                  </select>
                )}
                {effectForm.tipo === 'serie' && (
                  <select
                    className="col-span-2 bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
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
                <button
                  type="button"
                  onClick={saveEffect}
                  className="col-span-2 px-3 py-1.5 bg-rose-700 hover:bg-rose-600 rounded text-sm"
                >
                  Aggiungi effetto
                </button>
              </div>
            </div>
          </>
        )}
      </div>
    </div>
  );

  const renderSerieTab = () => (
    <div className="space-y-4">
      <div className="bg-gray-900/50 border border-gray-700 rounded p-3 grid grid-cols-1 md:grid-cols-4 gap-2">
        <input
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Nome serie (es. Pecora)"
          value={serieForm.nome}
          onChange={(e) => setSerieForm((f) => ({ ...f, nome: e.target.value }))}
        />
        <input
          type="number"
          min={1}
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Totale N"
          value={serieForm.totale}
          onChange={(e) => setSerieForm((f) => ({ ...f, totale: Number(e.target.value) }))}
        />
        <input
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Descrizione"
          value={serieForm.descrizione}
          onChange={(e) => setSerieForm((f) => ({ ...f, descrizione: e.target.value }))}
        />
        <button
          type="button"
          className="px-3 py-1 bg-indigo-600 rounded text-sm"
          onClick={async () => {
            await staffCreateSerieCollezione(serieForm, onLogout);
            setSerieForm({ nome: '', totale: 30, descrizione: '' });
            await reloadMeta();
          }}
        >
          Crea serie
        </button>
      </div>
      <ul className="space-y-2">
        {serieList.map((s) => (
          <li key={s.id} className="flex items-center justify-between bg-gray-800/40 px-3 py-2 rounded text-sm">
            <div>
              <div className="font-semibold">{s.nome}</div>
              <div className="text-xs text-gray-400">
                Assegnati {s.pezzi_assegnati}/{s.totale} · restano {s.pezzi_rimanenti}
              </div>
            </div>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={() => setConfirmDelete({ type: 'serie', id: s.id, label: s.nome })}
            >
              Elimina
            </button>
          </li>
        ))}
      </ul>

      <h3 className="font-bold text-rose-300 mt-4">QR Serie standalone</h3>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        <input
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Nome QR"
          value={serieQrForm.nome}
          onChange={(e) => setSerieQrForm((f) => ({ ...f, nome: e.target.value }))}
        />
        <select
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          value={serieQrForm.serie}
          onChange={(e) => setSerieQrForm((f) => ({ ...f, serie: e.target.value }))}
        >
          <option value="">Serie…</option>
          {serieList.map((s) => (
            <option key={s.id} value={s.id}>
              {s.nome}
            </option>
          ))}
        </select>
        <button
          type="button"
          className="px-3 py-1 bg-indigo-600 rounded text-sm"
          onClick={async () => {
            await staffCreateSerieQr(serieQrForm, onLogout);
            setSerieQrForm({ nome: '', testo: '', serie: '' });
            await reloadMeta();
          }}
        >
          Crea QR Serie
        </button>
      </div>
      <ul className="space-y-2">
        {serieQrList.map((row) => (
          <li key={row.id} className="flex items-center gap-2 bg-gray-800/40 px-3 py-2 rounded text-sm">
            <span className="font-semibold flex-1">{row.nome}</span>
            <span className="text-xs text-gray-400">{row.serie_nome}</span>
            <StaffQrBadge hasQr={row.has_qrcode} />
            <button
              type="button"
              className="text-xs px-2 py-1 bg-yellow-800 rounded"
              onClick={() => setScanningId(row.id)}
            >
              Associa QR
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  const renderTrappoleTab = () => (
    <div className="space-y-4">
      <div className="grid grid-cols-1 md:grid-cols-4 gap-2">
        <input
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Nome"
          value={trappolaForm.nome}
          onChange={(e) => setTrappolaForm((f) => ({ ...f, nome: e.target.value }))}
        />
        <input
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Testo"
          value={trappolaForm.testo}
          onChange={(e) => setTrappolaForm((f) => ({ ...f, testo: e.target.value }))}
        />
        <input
          type="number"
          min={0}
          className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm"
          placeholder="Durata s"
          value={trappolaForm.durata_secondi}
          onChange={(e) => setTrappolaForm((f) => ({ ...f, durata_secondi: e.target.value }))}
        />
        <button
          type="button"
          className="px-3 py-1 bg-indigo-600 rounded text-sm"
          onClick={async () => {
            await staffCreateTrappola(
              {
                ...trappolaForm,
                durata_secondi: trappolaForm.durata_secondi === '' ? null : Number(trappolaForm.durata_secondi),
              },
              onLogout,
            );
            setTrappolaForm({ nome: '', testo: '', durata_secondi: 60 });
            await reloadMeta();
          }}
        >
          Crea trappola
        </button>
      </div>
      <ul className="space-y-2">
        {trappole.map((t) => (
          <li key={t.id} className="flex items-center gap-2 bg-gray-800/40 px-3 py-2 rounded text-sm">
            <div className="flex-1">
              <div className="font-semibold">{t.nome}</div>
              <div className="text-xs text-gray-400">
                {t.durata_secondi ? `Timer ${t.durata_secondi}s` : 'Solo testo'}
              </div>
            </div>
            <StaffQrBadge hasQr={t.has_qrcode} />
            <button
              type="button"
              className="text-xs px-2 py-1 bg-yellow-800 rounded"
              onClick={() => setScanningId(t.id)}
            >
              Associa QR
            </button>
            <button
              type="button"
              className="text-red-400 text-xs"
              onClick={() => setConfirmDelete({ type: 'trappola', id: t.id, label: t.nome })}
            >
              Elimina
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  return (
    <StaffToolShell maxWidth="6xl" className="space-y-4">
      <StaffToolHeader
        title="QR — Pool randomico"
        description="Pool con effetti pesati, trappole e serie uniche. Minigioco configurabile a monte sul pool (override per-QR possibile)."
      />
      {error ? <div className="mb-3 text-sm text-amber-300 bg-amber-950/40 border border-amber-800 rounded px-3 py-2">{error}</div> : null}
      <div className="flex gap-2 mb-4">
        {[
          ['pools', 'Pool'],
          ['serie', 'Serie'],
          ['trappole', 'Trappole'],
        ].map(([id, label]) => (
          <button
            key={id}
            type="button"
            onClick={() => setTab(id)}
            className={`px-3 py-1.5 rounded text-sm ${tab === id ? 'bg-rose-700' : 'bg-gray-800'}`}
          >
            {label}
          </button>
        ))}
      </div>
      {tab === 'pools' && renderPoolsTab()}
      {tab === 'serie' && renderSerieTab()}
      {tab === 'trappole' && renderTrappoleTab()}

      {scanningId && (
        <div className="fixed inset-0 z-50 bg-black/70 flex items-center justify-center p-4">
          <div className="bg-gray-900 border border-gray-700 rounded-xl p-4 max-w-md w-full space-y-3">
            <div className="flex justify-between items-center">
              <h3 className="font-bold">Associa QR</h3>
              <button type="button" className="text-sm text-gray-400" onClick={() => setScanningId(null)}>
                Chiudi
              </button>
            </div>
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                await associaQrDiretto(scanningId, qr_id, onLogout);
                setScanningId(null);
                await reloadMeta();
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      )}

      <ConfirmDialog
        open={!!confirmDelete}
        title="Conferma eliminazione"
        message={confirmDelete ? `Eliminare «${confirmDelete.label}»?` : ''}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={async () => {
          const c = confirmDelete;
          setConfirmDelete(null);
          if (!c) return;
          if (c.type === 'pool') {
            await staffDeleteRandomQrPool(c.id, onLogout);
            setSelectedId(null);
            setForm(emptyPool());
            await reloadPools();
          } else if (c.type === 'serie') {
            await staffDeleteSerieCollezione(c.id, onLogout);
            await reloadMeta();
          } else if (c.type === 'trappola') {
            await staffDeleteTrappola(c.id, onLogout);
            await reloadMeta();
          }
        }}
      />
    </StaffToolShell>
  );
};

export default memo(RandomQrPoolManager);
