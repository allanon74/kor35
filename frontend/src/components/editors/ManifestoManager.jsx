import React, { useState, useEffect, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
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
  staffGetManifesti,
  staffCreateManifesto,
  staffUpdateManifesto,
  staffDeleteManifesto,
} from '../../api';

const ManifestoManager = ({ onBack, onLogout }) => {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [msg, setMsg] = useState('');

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

  return (
    <div className="space-y-4 text-white max-w-4xl mx-auto">
      <button
        type="button"
        onClick={onBack}
        className="flex items-center gap-2 text-gray-400 hover:text-white text-sm font-bold uppercase"
      >
        <ArrowLeft size={16} /> Torna agli strumenti
      </button>
      {msg && (
        <div className="text-xs text-amber-200 border border-amber-800/40 rounded px-2 py-1">{msg}</div>
      )}

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
                      onClick={() => setScanningId(m.id)}
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

      {scanningId && (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Associa QR a manifesto</span>
            <button type="button" onClick={() => setScanningId(null)} className="px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                const res = await handleQrScan(scanningId, qr_id, {
                  closeScan: () => setScanningId(null),
                  onMessage: setMsg,
                });
                if (res?.ok) {
                  await applyDefaultMinigiocoToQr(MINIGIOCO_PAGE_KEYS.manifesti, qr_id, onLogout);
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
      {minigiocoModal}
    </div>
  );
};

export default memo(ManifestoManager);
