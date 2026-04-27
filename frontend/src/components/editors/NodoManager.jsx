import React, { useState, useEffect, useCallback, memo } from 'react';
import { ArrowLeft } from 'lucide-react';
import StaffQrTab from '../StaffQrTab';
import ConfirmDialog from './ConfirmDialog';
import {
  associaQrDiretto,
  staffGetNodi,
  staffCreateNodo,
  staffUpdateNodo,
  staffDeleteNodo,
} from '../../api';

const emptyForm = () => ({
  nome: '',
  testo: '',
  tipo_nodo: 'MIN',
  disponibile_dal: '',
  foto_posizione: null,
  foto_posizione_url: '',
});

const toInputDateTimeLocal = (iso) => {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  const pad = (n) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

const NodoManager = ({ onBack, onLogout }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(null);
  const [scanningId, setScanningId] = useState(null);
  const [pendingQrConflict, setPendingQrConflict] = useState(null);
  const [expandedPhotoUrl, setExpandedPhotoUrl] = useState(null);
  const [msg, setMsg] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await staffGetNodi(onLogout);
      setItems(Array.isArray(data) ? data : []);
    } catch (e) {
      setMsg(e.message || 'Errore caricamento nodi');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  const save = async () => {
    if (!editing?.nome?.trim()) {
      setMsg('Il nome è obbligatorio');
      return;
    }
    const formData = new FormData();
    formData.append('nome', editing.nome);
    formData.append('testo', editing.testo || '');
    formData.append('tipo_nodo', editing.tipo_nodo || 'MIN');
    if (editing.disponibile_dal) formData.append('disponibile_dal', editing.disponibile_dal);
    if (editing.foto_posizione instanceof File) formData.append('foto_posizione', editing.foto_posizione);
    try {
      if (editing.id) {
        await staffUpdateNodo(editing.id, formData, onLogout);
      } else {
        await staffCreateNodo(formData, onLogout);
      }
      setEditing(null);
      setMsg('Nodo salvato.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore salvataggio nodo');
    }
  };

  const remove = async (id) => {
    if (!window.confirm('Eliminare questo nodo?')) return;
    try {
      await staffDeleteNodo(id, onLogout);
      setMsg('Nodo eliminato.');
      load();
    } catch (e) {
      setMsg(e.message || 'Errore eliminazione');
    }
  };

  const editingPreviewUrl = editing?.foto_posizione
    ? URL.createObjectURL(editing.foto_posizione)
    : (editing?.foto_posizione_url || null);

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
            <h2 className="text-xl font-bold">Nodi (QR)</h2>
            <button type="button" className="px-3 py-2 bg-indigo-600 rounded text-sm" onClick={() => setEditing(emptyForm())}>
              Nuovo
            </button>
          </div>
          {loading ? (
            <p className="text-gray-400">Caricamento…</p>
          ) : (
            <ul className="divide-y divide-gray-700 border border-gray-700 rounded-lg">
              {items.map((n) => (
                <li key={n.id} className="flex justify-between items-center p-3 hover:bg-gray-800/50">
                  <div>
                    <div className="font-semibold">{n.nome}</div>
                    <div className="text-[10px] text-gray-500">
                      Tipo: {n.tipo_nodo === 'MAG' ? 'Nodo maggiore' : 'Nodo minore'}
                      {n.disponibile_dal ? ` · disponibile da ${new Date(n.disponibile_dal).toLocaleString()}` : ''}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    {n.foto_posizione_url && (
                      <button
                        type="button"
                        className="text-xs px-2 py-1 bg-cyan-800 rounded"
                        onClick={() => setExpandedPhotoUrl(n.foto_posizione_url)}
                      >
                        Apri foto
                      </button>
                    )}
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-gray-700 rounded"
                      onClick={() =>
                        setEditing({
                          ...n,
                          disponibile_dal: toInputDateTimeLocal(n.disponibile_dal),
                          foto_posizione: null,
                        })
                      }
                    >
                      Modifica
                    </button>
                    <button
                      type="button"
                      className="text-xs px-2 py-1 bg-violet-800 rounded"
                      onClick={() => setScanningId(n.id)}
                    >
                      Associa QR
                    </button>
                    <button type="button" className="text-xs px-2 py-1 bg-red-900 rounded" onClick={() => remove(n.id)}>
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
          <h3 className="font-bold">{editing.id ? 'Modifica nodo' : 'Nuovo nodo'}</h3>
          <label className="block text-sm">
            Nome
            <input
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              value={editing.nome}
              onChange={(e) => setEditing({ ...editing, nome: e.target.value })}
            />
          </label>
          <label className="block text-sm">
            Testo (opzionale)
            <textarea
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600 min-h-[90px]"
              value={editing.testo || ''}
              onChange={(e) => setEditing({ ...editing, testo: e.target.value })}
            />
          </label>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
            <label className="block text-sm">
              Tipo nodo
              <select
                className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
                value={editing.tipo_nodo || 'MIN'}
                onChange={(e) => setEditing({ ...editing, tipo_nodo: e.target.value })}
              >
                <option value="MIN">Nodo minore</option>
                <option value="MAG">Nodo maggiore</option>
              </select>
            </label>
            <label className="block text-sm">
              Disponibile dal (forzatura, opzionale)
              <input
                type="datetime-local"
                className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
                value={editing.disponibile_dal || ''}
                onChange={(e) => setEditing({ ...editing, disponibile_dal: e.target.value })}
              />
            </label>
          </div>
          <label className="block text-sm">
            Foto posizione nodo (solo master, salvata in bassa risoluzione)
            <input
              type="file"
              accept="image/*"
              className="w-full mt-1 px-2 py-1 rounded bg-gray-800 border border-gray-600"
              onChange={(e) => setEditing({ ...editing, foto_posizione: e.target.files?.[0] || null })}
            />
          </label>
          {(editing.foto_posizione_url || editing.foto_posizione) && (
            <div className="border border-gray-700 rounded p-2 bg-black/20">
              <div className="text-xs text-gray-400 mb-2">Anteprima posizione</div>
              <img
                src={editingPreviewUrl}
                alt="Posizione nodo"
                className="max-h-48 rounded border border-gray-700 object-contain"
              />
              <button
                type="button"
                className="mt-2 text-xs px-2 py-1 bg-cyan-800 rounded"
                onClick={() => setExpandedPhotoUrl(editingPreviewUrl)}
              >
                Apri in grande
              </button>
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
            <span className="font-bold text-white">Associa QR a nodo</span>
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
                } catch (error) {
                  if (error.status === 409 && error.data?.already_associated) {
                    setPendingQrConflict({ qrId: qr_id, message: error.data.message });
                  } else {
                    setMsg(error.message || 'Errore associazione QR');
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
        message={`${pendingQrConflict?.message || ''} Vuoi spostare il QR su questo nodo?`}
        confirmLabel="Sposta QR"
        confirmTone="warning"
        onCancel={() => setPendingQrConflict(null)}
        onConfirm={async () => {
          if (!pendingQrConflict?.qrId || !scanningId) return;
          try {
            await associaQrDiretto(scanningId, pendingQrConflict.qrId, onLogout, true);
            setPendingQrConflict(null);
            setScanningId(null);
            setMsg('QR associato (forzato).');
          } catch (e) {
            setMsg(e.message || 'Errore');
          }
        }}
      />

      {expandedPhotoUrl && (
        <div className="fixed inset-0 z-60 bg-black/95 flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800">
            <span className="font-bold text-white">Foto posizione nodo</span>
            <button
              type="button"
              onClick={() => setExpandedPhotoUrl(null)}
              className="px-4 py-2 bg-red-600 rounded"
            >
              Chiudi
            </button>
          </div>
          <div className="flex-1 p-4 flex items-center justify-center">
            <img
              src={expandedPhotoUrl}
              alt="Foto posizione nodo - grande"
              className="max-w-full max-h-full object-contain rounded border border-gray-700"
            />
          </div>
        </div>
      )}
    </div>
  );
};

export default memo(NodoManager);
