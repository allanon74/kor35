import React, { useState, useEffect, useCallback, memo } from 'react';
import { StaffToolShell, StaffToolSubnav } from '../../staff/StaffToolShell';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrBadge from './StaffQrBadge';
import StaffMinigiocoQrSection from './StaffMinigiocoQrSection';
import StaffMinigiocoPageToolbar from './StaffMinigiocoPageToolbar';
import StaffMinigiocoUsaDefaultToggle from './StaffMinigiocoUsaDefaultToggle';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';
import { useStaffQrAssociation } from '../../hooks/useStaffQrAssociation';
import {
  applyDefaultMinigiocoToQr,
  MINIGIOCO_PAGE_KEYS,
  patchStaffListMinigiocoDefault,
  unwrapStaffList,
} from '../../utils/staffMinigiocoDefaults';
import {
  associaQrDiretto,
  staffGetManifesti,
  staffCreateManifesto,
  staffUpdateManifesto,
  staffDeleteManifesto,
  staffGetSerieCollezioni,
  staffCreateSerieCollezione,
  staffDeleteSerieCollezione,
  staffGetSerieQr,
  staffCreateSerieQr,
  staffGetTrappole,
  staffCreateTrappola,
  staffDeleteTrappola,
} from '../../api';

const TABS = [
  { id: 'manifesti', label: 'Manifesti' },
  { id: 'serie', label: 'Serie' },
  { id: 'trappole', label: 'Trappole' },
];

const ManifestoManager = ({ onBack, onLogout }) => {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [tab, setTab] = useState('manifesti');
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [scanningKind, setScanningKind] = useState('manifesto'); // manifesto | serie | trappola
  const [msg, setMsg] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const [serieList, setSerieList] = useState([]);
  const [serieForm, setSerieForm] = useState({ nome: '', totale: 30, descrizione: '' });
  const [serieQrList, setSerieQrList] = useState([]);
  const [serieQrForm, setSerieQrForm] = useState({ nome: '', testo: '', serie: '' });
  const [trappole, setTrappole] = useState([]);
  const [trappolaForm, setTrappolaForm] = useState({ nome: '', testo: '', durata_secondi: 60 });

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetManifesti(onLogout);
      setItems(unwrapStaffList(data));
    } catch (e) {
      setMsg(e.message || 'Errore caricamento manifesti');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  const loadSerieTrappole = useCallback(async () => {
    try {
      const [serie, sqr, traps] = await Promise.all([
        staffGetSerieCollezioni(onLogout),
        staffGetSerieQr(onLogout),
        staffGetTrappole(onLogout),
      ]);
      setSerieList(Array.isArray(serie) ? serie : serie?.results || []);
      setSerieQrList(Array.isArray(sqr) ? sqr : sqr?.results || []);
      setTrappole(Array.isArray(traps) ? traps : traps?.results || []);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento serie/trappole');
    }
  }, [onLogout]);

  const {
    pendingQrConflict,
    conflictLoading,
    handleQrScan,
    confirmConflict,
    cancelConflict,
  } = useStaffQrAssociation({ onLogout, onReload: load });

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (tab === 'serie' || tab === 'trappole') {
      loadSerieTrappole();
    }
  }, [tab, loadSerieTrappole]);

  const save = async () => {
    if (!editing?.nome?.trim()) {
      setMsg('Il nome è obbligatorio');
      return;
    }
    try {
      if (editing.id) {
        await staffUpdateManifesto(
          editing.id,
          {
            nome: editing.nome,
            testo: editing.testo || '',
            requisiti_lettura: editing.requisiti_lettura_json
              ? JSON.parse(editing.requisiti_lettura_json)
              : [],
          },
          onLogout
        );
      } else {
        await staffCreateManifesto(
          {
            nome: editing.nome,
            testo: editing.testo || '',
            requisiti_lettura: editing.requisiti_lettura_json
              ? JSON.parse(editing.requisiti_lettura_json)
              : [],
          },
          onLogout
        );
      }
      setEditing(null);
      setMsg('Salvato.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio');
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questo manifesto?')) return;
    try {
      await staffDeleteManifesto(id, onLogout);
      load();
    } catch (e) {
      setMsg(e.message || 'Errore eliminazione');
    }
  };

  const startScan = (avistaId, kind) => {
    setScanningId(avistaId);
    setScanningKind(kind);
  };

  const renderManifesti = () => (
    <>
      {!editing ? (
        <>
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Manifesti (QR)</h2>
            <button
              type="button"
              className="px-3 py-2 bg-indigo-600 rounded text-sm"
              onClick={() =>
                setEditing({
                  nome: '',
                  testo: '',
                  requisiti_lettura_json: '[]',
                })
              }
            >
              Nuovo
            </button>
          </div>
          <StaffMinigiocoPageToolbar
            pageKey={MINIGIOCO_PAGE_KEYS.manifesti}
            pageLabel="Manifesti"
            onLogout={onLogout}
          />
          {loading ? (
            <p className="text-gray-400">Caricamento…</p>
          ) : (
            <ul className="divide-y divide-gray-700 border border-gray-700 rounded-lg">
              {items.map((m) => (
                <li key={m.id} className="flex justify-between items-center p-3 hover:bg-gray-800/50 gap-2">
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    <StaffQrBadge hasQr={m.has_qrcode} />
                    <div className="min-w-0">
                      <div className="font-semibold">{m.nome}</div>
                      <div className="text-[10px] text-gray-500">id {m.id}</div>
                    </div>
                  </div>
                  <div className="flex gap-2 flex-wrap items-center justify-end">
                    <StaffMinigiocoUsaDefaultToggle
                      qrcodeId={m.qrcode_id}
                      usaDefault={m.minigioco_usa_default}
                      pageKey={MINIGIOCO_PAGE_KEYS.manifesti}
                      onLogout={onLogout}
                      compact
                      onChange={(val) => patchStaffListMinigiocoDefault(setItems, m.id, val)}
                    />
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-gray-700 rounded"
                      onClick={() =>
                        setEditing({
                          ...m,
                          requisiti_lettura_json: JSON.stringify(m.requisiti_lettura || [], null, 2),
                        })
                      }
                    >
                      Modifica
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-indigo-800 rounded"
                      onClick={() => openMinigioco(m.qrcode_id, m.nome)}
                      disabled={!m.qrcode_id}
                      title={m.qrcode_id ? 'Configura minigioco QR' : 'Associa prima un QR'}
                    >
                      Minigioco
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-violet-800 rounded"
                      onClick={() => startScan(m.id, 'manifesto')}
                    >
                      Associa QR
                    </button>
                    <button type="button" className="text-xs px-2 py-1 bg-red-900 rounded" onClick={() => remove(m.id)}>
                      Elimina
                    </button>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <div className="space-y-3 border border-gray-700 rounded-lg p-4 bg-gray-900/40">
          <h3 className="font-bold">{editing.id ? 'Modifica manifesto' : 'Nuovo manifesto'}</h3>
          <label className="block text-sm">
            Nome
            <input
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.nome}
              onChange={(e) => setEditing({ ...editing, nome: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Contenuto (HTML / ricco)
            <textarea
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600 font-mono text-sm min-h-[180px]"
              value={editing.testo || ''}
              onChange={(e) => setEditing({ ...editing, testo: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Requisiti lettura (JSON, lista vuota = tutti)
            <textarea
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600 font-mono text-xs min-h-[80px]"
              value={editing.requisiti_lettura_json || '[]'}
              onChange={(e) => setEditing({ ...editing, requisiti_lettura_json: e.target.value })}
            />
          </label>
          <StaffMinigiocoQrSection qrcodeId={editing.qrcode_id} onLogout={onLogout} />
          <div className="flex gap-2">
            <button type="button" className="px-4 py-2 bg-indigo-600 rounded" onClick={save}>
              Salva
            </button>
            <button type="button" className="px-4 py-2 bg-gray-700 rounded" onClick={() => setEditing(null)}>
              Annulla
            </button>
          </div>
        </div>
      )}
    </>
  );

  const renderSerie = () => (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Serie (collezioni uniche)</h2>
      <p className="text-sm text-gray-400">
        Ogni pezzo («Nome X di N») viene assegnato una sola volta a livello globale. Usabile da QR standalone o come effetto di un pool randomico.
      </p>
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
            try {
              await staffCreateSerieCollezione(serieForm, onLogout);
              setSerieForm({ nome: '', totale: 30, descrizione: '' });
              setMsg('Serie creata.');
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore creazione serie');
            }
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

      <h3 className="font-bold text-amber-300 mt-4">QR Serie standalone</h3>
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
          className="px-3 py-1 bg-indigo-600 rounded text-sm md:col-span-2"
          onClick={async () => {
            try {
              await staffCreateSerieQr(serieQrForm, onLogout);
              setSerieQrForm({ nome: '', testo: '', serie: '' });
              setMsg('QR Serie creato.');
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore creazione QR Serie');
            }
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
              className="text-xs px-2 py-1 bg-violet-800 rounded"
              onClick={() => startScan(row.id, 'serie')}
            >
              Associa QR
            </button>
          </li>
        ))}
      </ul>
    </div>
  );

  const renderTrappole = () => (
    <div className="space-y-4">
      <h2 className="text-xl font-bold">Trappole (QR)</h2>
      <p className="text-sm text-gray-400">
        Alla scansione mostra un testo e, se impostata una durata, avvia un timer personale evidente. Usabile anche come effetto nei pool randomici.
      </p>
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
          placeholder="Durata s (vuoto = solo testo)"
          value={trappolaForm.durata_secondi}
          onChange={(e) => setTrappolaForm((f) => ({ ...f, durata_secondi: e.target.value }))}
        />
        <button
          type="button"
          className="px-3 py-1 bg-indigo-600 rounded text-sm"
          onClick={async () => {
            try {
              await staffCreateTrappola(
                {
                  ...trappolaForm,
                  durata_secondi: trappolaForm.durata_secondi === '' ? null : Number(trappolaForm.durata_secondi),
                },
                onLogout,
              );
              setTrappolaForm({ nome: '', testo: '', durata_secondi: 60 });
              setMsg('Trappola creata.');
              await loadSerieTrappole();
            } catch (e) {
              setMsg(e.message || 'Errore creazione trappola');
            }
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
              className="text-xs px-2 py-1 bg-violet-800 rounded"
              onClick={() => startScan(t.id, 'trappola')}
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

  const scanTitle =
    scanningKind === 'serie' ? 'Associa QR a serie' : scanningKind === 'trappola' ? 'Associa QR a trappola' : 'Associa QR a manifesto';

  return (
    <StaffToolShell maxWidth="4xl" className="space-y-4">
      <div>
        <h1 className="text-xl font-bold text-white tracking-tight">QR — Manifesti / Serie / Trappole</h1>
        <StaffToolSubnav
          tabs={TABS}
          active={tab}
          onChange={(id) => {
            setTab(id);
            setEditing(null);
            setMsg('');
          }}
          className="mt-3"
        />
      </div>

      {msg && (
        <div className="text-xs text-amber-200 border border-amber-800/40 rounded px-2 py-1">{msg}</div>
      )}

      {tab === 'manifesti' && renderManifesti()}
      {tab === 'serie' && renderSerie()}
      {tab === 'trappole' && renderTrappole()}

      {scanningId && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">{scanTitle}</span>
            <button type="button" onClick={() => setScanningId(null)} className="px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                if (scanningKind === 'manifesto') {
                  const res = await handleQrScan(scanningId, qr_id, {
                    closeScan: () => setScanningId(null),
                    onMessage: setMsg,
                  });
                  if (res?.ok) {
                    await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.manifesti, qr_id, onLogout);
                  }
                } else {
                  try {
                    await associaQrDiretto(scanningId, qr_id, onLogout);
                    setScanningId(null);
                    setMsg('QR associato.');
                    await loadSerieTrappole();
                  } catch (e) {
                    setMsg(e.message || 'Associazione QR fallita');
                  }
                }
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      )}

      <ConfirmDialog
        open={Boolean(pendingQrConflict)}
        title="QR già associato"
        message=""
        confirmLabel="Sostituisci associazione"
        confirmTone="warning"
        loading={conflictLoading}
        onCancel={cancelConflict}
        onConfirm={async () => {
          const qrId = pendingQrConflict?.qrId;
          await confirmConflict(setMsg);
          if (qrId) {
            await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.manifesti, qrId, onLogout);
          }
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questo manifesto" />
        ) : null}
      </ConfirmDialog>

      <ConfirmDialog
        open={!!confirmDelete}
        title="Conferma eliminazione"
        message={confirmDelete ? `Eliminare «${confirmDelete.label}»?` : ''}
        onCancel={() => setConfirmDelete(null)}
        onConfirm={async () => {
          const c = confirmDelete;
          setConfirmDelete(null);
          if (!c) return;
          try {
            if (c.type === 'serie') {
              await staffDeleteSerieCollezione(c.id, onLogout);
            } else if (c.type === 'trappola') {
              await staffDeleteTrappola(c.id, onLogout);
            }
            await loadSerieTrappole();
            setMsg('Eliminato.');
          } catch (e) {
            setMsg(e.message || 'Eliminazione fallita');
          }
        }}
      />
      {minigiocoModal}
    </StaffToolShell>
  );
};

export default memo(ManifestoManager);
