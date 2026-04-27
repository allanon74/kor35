import React, { useState, useEffect, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import QrAssociationConflictBody from './QrAssociationConflictBody';
import StaffQrBadge from './StaffQrBadge';
import {
  associaQrDiretto,
  staffGetInnescoTimers,
  staffCreateInnescoTimer,
  staffUpdateInnescoTimer,
  staffDeleteInnescoTimer,
  staffGetEre,
  staffGetRegioni,
  staffGetKorps,
} from '../../api';

const emptyForm = () => ({
  nome: '',
  testo: '',
  modalita_target: 'globale',
  durata_secondi: 60,
  max_cariche: 1,
  rigenera_cariche_ogni_secondi: '',
  segnale_luminoso: true,
  target_ere_ids: [],
  target_regioni_ids: [],
  target_korps_ids: [],
});

const TargetCheckboxGroup = ({ title, options, selectedIds, onChange }) => {
  const normalizedSelected = Array.isArray(selectedIds) ? selectedIds : [];
  return (
    <div className="text-sm border border-gray-700 rounded p-2 bg-gray-900/30">
      <div className="flex items-center justify-between mb-2">
        <span className="font-semibold text-gray-200">{title}</span>
        <div className="flex gap-2 text-[10px]">
          <button
            type="button"
            className="px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
            onClick={() => onChange(options.map((o) => o.id))}
          >
            Tutti
          </button>
          <button
            type="button"
            className="px-2 py-1 bg-gray-700 rounded hover:bg-gray-600"
            onClick={() => onChange([])}
          >
            Nessuno
          </button>
        </div>
      </div>
      {options.length === 0 ? (
        <p className="text-xs text-gray-500">Nessuna opzione disponibile.</p>
      ) : (
        <div className="max-h-40 overflow-y-auto space-y-1 pr-1">
          {options.map((row) => {
            const checked = normalizedSelected.includes(row.id);
            return (
              <label key={row.id} className="flex items-center gap-2 text-xs text-gray-200 cursor-pointer">
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onChange([...normalizedSelected, row.id]);
                    } else {
                      onChange(normalizedSelected.filter((id) => id !== row.id));
                    }
                  }}
                />
                <span>{row.nome}</span>
              </label>
            );
          })}
        </div>
      )}
    </div>
  );
};

const InnescoTimerManager = ({ onBack, onLogout }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [msg, setMsg] = useState('');
  const [ereOptions, setEreOptions] = useState([]);
  const [regioniOptions, setRegioniOptions] = useState([]);
  const [korpOptions, setKorpOptions] = useState([]);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetInnescoTimers(onLogout);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    const loadTargets = async () => {
      try {
        const [ere, regioni, korps] = await Promise.all([
          staffGetEre(onLogout),
          staffGetRegioni(onLogout),
          staffGetKorps(onLogout),
        ]);
        setEreOptions(Array.isArray(ere) ? ere : []);
        setRegioniOptions(Array.isArray(regioni) ? regioni : []);
        setKorpOptions(Array.isArray(korps) ? korps : []);
      } catch (_e) {
        // opzionali: falliamo soft senza bloccare il form
      }
    };
    loadTargets();
  }, [onLogout]);

  const toPayload = (f) => {
    const rig = f.rigenera_cariche_ogni_secondi;
    return {
      nome: f.nome,
      testo: f.testo || '',
      modalita_target: f.modalita_target,
      durata_secondi: parseInt(f.durata_secondi, 10) || 60,
      max_cariche: parseInt(f.max_cariche, 10) || 0,
      rigenera_cariche_ogni_secondi: rig === '' || rig == null ? null : parseInt(rig, 10),
      segnale_luminoso: !!f.segnale_luminoso,
      target_ere_ids: f.target_ere_ids || [],
      target_regioni_ids: f.target_regioni_ids || [],
      target_korps_ids: f.target_korps_ids || [],
    };
  };

  const save = async () => {
    if (!editing?.nome?.trim()) {
      setMsg('Il nome è obbligatorio');
      return;
    }
    try {
      const body = toPayload(editing);
      if (editing.id) {
        await staffUpdateInnescoTimer(editing.id, body, onLogout);
      } else {
        await staffCreateInnescoTimer(body, onLogout);
      }
      setEditing(null);
      setMsg('Salvato.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio');
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questo innesco timer?')) return;
    try {
      await staffDeleteInnescoTimer(id, onLogout);
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
      {msg && <div className="text-xs text-amber-200 border border-amber-800/40 rounded px-2 py-1">{msg}</div>}

      {!editing ? (
        <>
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Innesco timer (QR)</h2>
            <button type="button" className="px-3 py-2 bg-indigo-600 rounded text-sm" onClick={() => setEditing(emptyForm())}>
              Nuovo
            </button>
          </div>
          {loading ? (
            <p className="text-gray-400">Caricamento…</p>
          ) : (
            <ul className="divide-y divide-gray-700 border border-gray-700 rounded-lg">
              {items.map((t) => (
                <li key={t.id} className="flex justify-between items-center p-3 hover:bg-gray-800/50 gap-2">
                  <div className="flex items-start gap-2 min-w-0 flex-1">
                    <StaffQrBadge hasQr={t.has_qrcode} />
                    <div className="min-w-0">
                      <div className="font-semibold">{t.nome}</div>
                      <div className="text-[10px] text-gray-500">
                        {t.durata_secondi}s · {t.modalita_target} · cariche {t.max_cariche}
                      </div>
                    </div>
                  </div>
                  <div className="flex gap-2 shrink-0">
                    <button type="button" className="text-xs px-2 py-1 bg-gray-700 rounded" onClick={() => setEditing({ ...emptyForm(), ...t })}>
                      Modifica
                    </button>
                    <button type="button" className="text-xs px-2 py-1 bg-violet-800 rounded" onClick={() => setScanningId(t.id)}>
                      Associa QR
                    </button>
                    <button type="button" className="text-xs px-2 py-1 bg-red-900 rounded" onClick={() => remove(t.id)}>
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
          <h3 className="font-bold">{editing.id ? 'Modifica innesco' : 'Nuovo innesco'}</h3>
          <label className="block text-sm">
            Nome (mostrato sul timer)
            <input
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.nome}
              onChange={(e) => setEditing({ ...editing, nome: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Descrizione (opzionale)
            <textarea
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600 text-sm min-h-[60px]"
              value={editing.testo || ''}
              onChange={(e) => setEditing({ ...editing, testo: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-2 gap-2">
            <label className="text-sm">
              Durata (sec)
              <input
                type="number"
                className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
                value={editing.durata_secondi}
                onChange={(e) => setEditing({ ...editing, durata_secondi: e.target.value })}
              />
            </label>
            <label className="text-sm">
              Max cariche (0 = illimitato)
              <input
                type="number"
                className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
                value={editing.max_cariche}
                onChange={(e) => setEditing({ ...editing, max_cariche: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-sm">
            Rigenera cariche ogni (sec, vuoto = no)
            <input
              type="number"
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.rigenera_cariche_ogni_secondi ?? ''}
              onChange={(e) => setEditing({ ...editing, rigenera_cariche_ogni_secondi: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Target timer
            <select
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.modalita_target}
              onChange={(e) => setEditing({ ...editing, modalita_target: e.target.value })}
            >
              <option value="globale">Globale: tutti i giocatori ricevono il timer</option>
              <option value="filtri">Filtri: solo i personaggi che matchano i target</option>
            </select>
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!editing.segnale_luminoso}
              onChange={(e) => setEditing({ ...editing, segnale_luminoso: e.target.checked })}
            />
            Segnale luminoso in-app
          </label>
          {editing.modalita_target === 'filtri' && (
            <div className="space-y-2">
              <p className="text-xs text-amber-200/90 bg-amber-950/40 border border-amber-800/40 rounded p-2">
                Seleziona uno o più target. I personaggi ricevono il timer solo se rispettano i filtri selezionati.
                Se lasci tutti i box vuoti, il timer resta di fatto globale.
              </p>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                <TargetCheckboxGroup
                  title="Ere target"
                  options={ereOptions}
                  selectedIds={editing.target_ere_ids}
                  onChange={(ids) => setEditing({ ...editing, target_ere_ids: ids })}
                />
                <TargetCheckboxGroup
                  title="Regioni target"
                  options={regioniOptions}
                  selectedIds={editing.target_regioni_ids}
                  onChange={(ids) => setEditing({ ...editing, target_regioni_ids: ids })}
                />
                <TargetCheckboxGroup
                  title="KORP target"
                  options={korpOptions}
                  selectedIds={editing.target_korps_ids}
                  onChange={(ids) => setEditing({ ...editing, target_korps_ids: ids })}
                />
              </div>
            </div>
          )}
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
            <span className="font-bold text-white">Associa QR a innesco timer</span>
            <button type="button" onClick={() => setScanningId(null)} className="px-4 py-2 bg-red-600 rounded">
              Chiudi
            </button>
          </div>
          <div className="flex-1">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                try {
                  await associaQrDiretto(scanningId, qr_id, onLogout);
                  setScanningId(null);
                  setMsg('QR associato.');
                  load();
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({
                      targetId: scanningId,
                      qrId: qr_id,
                      errorData: error.data,
                    });
                    setScanningId(null);
                  } else {
                    setMsg(error.message || 'Errore');
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
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={async () => {
          const p = pendingQrConflict;
          if (!p?.qrId || !p?.targetId) return;
          try {
            await associaQrDiretto(p.targetId, p.qrId, onLogout, true);
            setPendingQrConflict(null);
            setScanningId(null);
            setMsg('QR associato (forzato).');
            load();
          } catch (e) {
            setMsg(e.message || 'Errore');
          }
        }}
      >
        {pendingQrConflict?.errorData ? (
          <QrAssociationConflictBody errorData={pendingQrConflict.errorData} targetHint="questo innesco timer" />
        ) : null}
      </ConfirmDialog>
    </div>
  );
};

export default memo(InnescoTimerManager);
