import React, { useCallback, useEffect, useState, memo } from 'react';
import { Plus, Trash2, Save, Puzzle } from 'lucide-react';
import { StaffToolShell, StaffToolHeader } from '../../staff/StaffToolShell';
import ConfirmDialog from './ConfirmDialog';
import {
  staffGetMinigiocoPatterns,
  staffCreateMinigiocoPattern,
  staffUpdateMinigiocoPattern,
  staffDeleteMinigiocoPattern,
} from '../../api';

const TIPO_OPTS = [
  { id: 'sliding_puzzle', label: 'Sliding puzzle' },
  { id: 'memory', label: 'Memory' },
  { id: 'rotate_tiles', label: 'Tessere rotabili' },
  { id: 'simon', label: 'Simon' },
  { id: 'pattern_lock', label: 'Pattern lock' },
  { id: 'pipe_connect', label: 'Collega i tubi' },
  { id: 'wire_match', label: 'Collega i fili' },
  { id: 'tap_order', label: 'Tocca in ordine' },
];

const emptyEntry = (ordine = 0) => ({
  tipo: 'simon',
  peso: 1,
  difficolta: 3,
  ordine,
  attivo: true,
});

const emptyPattern = () => ({
  nome: '',
  descrizione: '',
  attivo: true,
  entries: [emptyEntry(0)],
});

const MinigiocoPatternManager = ({ onLogout }) => {
  const [patterns, setPatterns] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyPattern());
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [confirmDelete, setConfirmDelete] = useState(null);

  const selected = patterns.find((p) => p.id === selectedId) || null;

  const reload = useCallback(async () => {
    const data = await staffGetMinigiocoPatterns(onLogout);
    const list = Array.isArray(data) ? data : data?.results || [];
    setPatterns(list);
    return list;
  }, [onLogout]);

  useEffect(() => {
    (async () => {
      try {
        setBusy(true);
        await reload();
      } catch (e) {
        setError(e.message || 'Errore caricamento');
      } finally {
        setBusy(false);
      }
    })();
  }, [reload]);

  const selectPattern = (p) => {
    setSelectedId(p.id);
    setForm({
      nome: p.nome || '',
      descrizione: p.descrizione || '',
      attivo: p.attivo !== false,
      entries: (p.entries || []).map((e, idx) => ({
        id: e.id,
        tipo: e.tipo,
        peso: e.peso ?? 1,
        difficolta: e.difficolta ?? 3,
        ordine: e.ordine ?? idx,
        attivo: e.attivo !== false,
      })),
    });
    setError('');
  };

  const startNew = () => {
    setSelectedId(null);
    setForm(emptyPattern());
    setError('');
  };

  const patchEntry = (idx, patch) => {
    setForm((f) => ({
      ...f,
      entries: f.entries.map((row, i) => (i === idx ? { ...row, ...patch } : row)),
    }));
  };

  const addEntry = () => {
    setForm((f) => ({
      ...f,
      entries: [...f.entries, emptyEntry(f.entries.length)],
    }));
  };

  const removeEntry = (idx) => {
    setForm((f) => ({
      ...f,
      entries: f.entries.filter((_, i) => i !== idx),
    }));
  };

  const save = async () => {
    if (!form.nome.trim()) {
      setError('Nome obbligatorio.');
      return;
    }
    if (!form.entries.length) {
      setError('Aggiungi almeno una entry.');
      return;
    }
    setBusy(true);
    setError('');
    try {
      const payload = {
        nome: form.nome.trim(),
        descrizione: form.descrizione || '',
        attivo: !!form.attivo,
        entries: form.entries.map((e, idx) => ({
          ...(e.id ? { id: e.id } : {}),
          tipo: e.tipo,
          peso: Math.max(1, Number(e.peso) || 1),
          difficolta: Math.max(1, Math.min(4, Number(e.difficolta) || 3)),
          ordine: idx,
          attivo: e.attivo !== false,
        })),
      };
      if (selectedId) {
        await staffUpdateMinigiocoPattern(selectedId, payload, onLogout);
      } else {
        const created = await staffCreateMinigiocoPattern(payload, onLogout);
        setSelectedId(created.id);
      }
      const list = await reload();
      const cur = list.find((p) => p.id === (selectedId || list[list.length - 1]?.id));
      if (cur) selectPattern(cur);
    } catch (e) {
      setError(e.message || 'Errore salvataggio');
    } finally {
      setBusy(false);
    }
  };

  const doDelete = async () => {
    if (!confirmDelete) return;
    setBusy(true);
    try {
      await staffDeleteMinigiocoPattern(confirmDelete, onLogout);
      setConfirmDelete(null);
      startNew();
      await reload();
    } catch (e) {
      setError(e.message || 'Errore eliminazione');
    } finally {
      setBusy(false);
    }
  };

  return (
    <StaffToolShell>
      <StaffToolHeader
        title="Pattern minigioco"
        description="Pool pesati (tipo + difficoltà) riusabili su QR e pool random"
        icon={Puzzle}
      />
      {error && <p className="text-amber-300 text-sm mb-2">{error}</p>}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="space-y-2">
          <button
            type="button"
            onClick={startNew}
            className="w-full px-3 py-2 rounded bg-indigo-700 hover:bg-indigo-600 text-sm flex items-center justify-center gap-1"
          >
            <Plus size={14} /> Nuovo pattern
          </button>
          <ul className="space-y-1 max-h-[70vh] overflow-y-auto">
            {patterns.map((p) => (
              <li key={p.id}>
                <button
                  type="button"
                  onClick={() => selectPattern(p)}
                  className={`w-full text-left px-3 py-2 rounded text-sm border ${
                    selectedId === p.id
                      ? 'bg-indigo-900/60 border-indigo-500'
                      : 'bg-gray-900 border-gray-700 hover:border-gray-500'
                  }`}
                >
                  <span className="font-semibold">{p.nome}</span>
                  <span className="block text-[10px] text-gray-400">
                    {(p.entries || []).length} entry · {p.attivo ? 'attivo' : 'off'}
                  </span>
                </button>
              </li>
            ))}
          </ul>
        </div>

        <div className="lg:col-span-2 space-y-3 p-4 rounded-lg border border-gray-700 bg-gray-900/50">
          <label className="block text-sm">
            <span className="text-gray-400 text-xs">Nome</span>
            <input
              className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-2 py-1"
              value={form.nome}
              onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
            />
          </label>
          <label className="block text-sm">
            <span className="text-gray-400 text-xs">Descrizione</span>
            <textarea
              className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-2 py-1 min-h-[56px]"
              value={form.descrizione}
              onChange={(e) => setForm((f) => ({ ...f, descrizione: e.target.value }))}
            />
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!form.attivo}
              onChange={(e) => setForm((f) => ({ ...f, attivo: e.target.checked }))}
            />
            Attivo
          </label>

          <div className="border-t border-gray-700 pt-3 space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-xs uppercase tracking-wide text-indigo-300 font-semibold">Entry pesate</span>
              <button
                type="button"
                onClick={addEntry}
                className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600"
              >
                <Plus size={12} className="inline" /> Aggiungi
              </button>
            </div>
            {form.entries.map((row, idx) => (
              <div
                key={row.id || `new-${idx}`}
                className="grid grid-cols-2 md:grid-cols-5 gap-2 items-end p-2 rounded border border-gray-700/80"
              >
                <label className="text-xs col-span-2 md:col-span-1">
                  Tipo
                  <select
                    className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-1 py-1"
                    value={row.tipo}
                    onChange={(e) => patchEntry(idx, { tipo: e.target.value })}
                  >
                    {TIPO_OPTS.map((o) => (
                      <option key={o.id} value={o.id}>{o.label}</option>
                    ))}
                  </select>
                </label>
                <label className="text-xs">
                  Peso
                  <input
                    type="number"
                    min={1}
                    className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-1 py-1"
                    value={row.peso}
                    onChange={(e) => patchEntry(idx, { peso: Number(e.target.value) })}
                  />
                </label>
                <label className="text-xs">
                  Difficoltà
                  <select
                    className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-1 py-1"
                    value={row.difficolta}
                    onChange={(e) => patchEntry(idx, { difficolta: Number(e.target.value) })}
                  >
                    {[1, 2, 3, 4].map((n) => (
                      <option key={n} value={n}>{n}</option>
                    ))}
                  </select>
                </label>
                <label className="flex items-center gap-1 text-xs pb-1">
                  <input
                    type="checkbox"
                    checked={row.attivo !== false}
                    onChange={(e) => patchEntry(idx, { attivo: e.target.checked })}
                  />
                  On
                </label>
                <button
                  type="button"
                  onClick={() => removeEntry(idx)}
                  className="px-2 py-1 text-xs rounded bg-red-900/50 hover:bg-red-800 text-red-200"
                  disabled={form.entries.length <= 1}
                >
                  <Trash2 size={12} className="inline" />
                </button>
              </div>
            ))}
          </div>

          <div className="flex gap-2 pt-2">
            <button
              type="button"
              disabled={busy}
              onClick={save}
              className="px-3 py-2 rounded bg-indigo-600 hover:bg-indigo-500 text-sm flex items-center gap-1 disabled:opacity-50"
            >
              <Save size={14} /> Salva
            </button>
            {selectedId && (
              <button
                type="button"
                onClick={() => setConfirmDelete(selectedId)}
                className="px-3 py-2 rounded bg-red-900/60 hover:bg-red-800 text-sm"
              >
                Elimina
              </button>
            )}
          </div>
        </div>
      </div>
      <ConfirmDialog
        open={Boolean(confirmDelete)}
        title="Eliminare pattern?"
        message="I QR/pool collegati perderanno il riferimento (SET NULL)."
        onConfirm={doDelete}
        onCancel={() => setConfirmDelete(null)}
      />
    </StaffToolShell>
  );
};

export default memo(MinigiocoPatternManager);
