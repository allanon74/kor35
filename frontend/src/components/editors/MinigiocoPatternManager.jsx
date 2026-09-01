import React, { useCallback, useEffect, useState, memo } from 'react';
import { Plus, Trash2, Puzzle, RefreshCw } from 'lucide-react';
import { StaffToolShell, StaffToolHeader, staffSecondaryBtnClass } from '../../staff/StaffToolShell';
import { StaffModalTabs } from '../../staff/StaffCrudUi';
import StaffEditorModal from './StaffEditorModal';
import MasterGenericList from './MasterGenericList';
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

const PATTERN_COLUMNS = [
  {
    header: 'Nome',
    key: 'nome',
    sortable: true,
    filterable: true,
    render: (row) => <span className="font-semibold text-white">{row.nome}</span>,
  },
  {
    header: 'Entry',
    key: 'entries',
    sortable: true,
    getSortValue: (row) => (row.entries || []).length,
    align: 'right',
    render: (row) => (row.entries || []).length,
  },
  {
    header: 'Attivo',
    key: 'attivo',
    sortable: true,
    render: (row) => (
      <span className={row.attivo !== false ? 'text-emerald-400' : 'text-gray-500'}>
        {row.attivo !== false ? 'Sì' : 'No'}
      </span>
    ),
  },
];

const MinigiocoPatternManager = ({ onLogout }) => {
  const [patterns, setPatterns] = useState([]);
  const [editorOpen, setEditorOpen] = useState(false);
  const [selectedId, setSelectedId] = useState(null);
  const [form, setForm] = useState(emptyPattern());
  const [formSnapshot, setFormSnapshot] = useState(null);
  const [modalTab, setModalTab] = useState('dati');
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const isDirty = Boolean(formSnapshot && JSON.stringify(form) !== formSnapshot);

  const reload = useCallback(async () => {
    const data = await staffGetMinigiocoPatterns(onLogout);
    const list = Array.isArray(data) ? data : data?.results || [];
    setPatterns(list);
    return list;
  }, [onLogout]);

  useEffect(() => {
    (async () => {
      try {
        setLoading(true);
        await reload();
      } catch (e) {
        setError(e.message || 'Errore caricamento');
      } finally {
        setLoading(false);
      }
    })();
  }, [reload]);

  const formFromPattern = (p) => ({
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

  const openEditor = (p) => {
    if (p?.id) {
      const next = formFromPattern(p);
      setSelectedId(p.id);
      setForm(next);
      setFormSnapshot(JSON.stringify(next));
    } else {
      const next = emptyPattern();
      setSelectedId(null);
      setForm(next);
      setFormSnapshot(JSON.stringify(next));
    }
    setModalTab('dati');
    setError('');
    setEditorOpen(true);
  };

  const closeEditor = () => {
    setEditorOpen(false);
    setSelectedId(null);
    setForm(emptyPattern());
    setFormSnapshot(null);
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

  const save = async ({ thenTab = null } = {}) => {
    if (!form.nome.trim()) {
      setError('Nome obbligatorio.');
      return;
    }
    if (!form.entries.length) {
      setError('Aggiungi almeno una entry.');
      setModalTab('entry');
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
      const wasNew = !selectedId;
      let id = selectedId;
      if (selectedId) {
        await staffUpdateMinigiocoPattern(selectedId, payload, onLogout);
      } else {
        const created = await staffCreateMinigiocoPattern(payload, onLogout);
        id = created.id;
        setSelectedId(created.id);
      }
      const list = await reload();
      const cur = list.find((p) => p.id === id);
      if (cur) {
        const next = formFromPattern(cur);
        setForm(next);
        setFormSnapshot(JSON.stringify(next));
      }
      if (thenTab) setModalTab(thenTab);
      else if (wasNew) setModalTab('entry');
    } catch (e) {
      setError(e.message || 'Errore salvataggio');
    } finally {
      setBusy(false);
    }
  };

  const deleteFromList = async (id) => {
    await staffDeleteMinigiocoPattern(id, onLogout);
    if (selectedId === id) closeEditor();
    await reload();
  };

  return (
    <StaffToolShell fill>
      <StaffToolHeader
        icon={<Puzzle size={22} />}
        title="Pattern minigioco"
        description="Lista pattern: apri un record per dati ed entry pesate."
        actions={
          <button type="button" onClick={reload} className={staffSecondaryBtnClass}>
            <RefreshCw size={16} />
            Aggiorna
          </button>
        }
      />
      {error && !editorOpen && <p className="px-4 text-amber-300 text-sm">{error}</p>}
      <div className="flex-1 min-h-0 overflow-hidden p-4 md:p-6 flex flex-col">
        <MasterGenericList
          items={patterns}
          title="Elenco"
          loading={loading}
          persistKey="minigioco-pattern"
          addLabel="Nuovo pattern"
          onAdd={() => openEditor(null)}
          onEdit={openEditor}
          onDelete={deleteFromList}
          onRowClick={openEditor}
          columns={PATTERN_COLUMNS}
          searchPlaceholder="Cerca pattern…"
          emptyMessage="Nessun pattern. Creane uno per iniziare."
        />
      </div>

      {editorOpen && (
        <StaffEditorModal
          title={selectedId ? `Pattern: ${form.nome || 'senza nome'}` : 'Nuovo pattern'}
          size="xl"
          saving={busy}
          isDirty={isDirty}
          onClose={closeEditor}
          onSave={() => save({ thenTab: selectedId ? null : 'entry' })}
          saveLabel={selectedId ? 'Salva' : 'Crea e vai alle entry'}
        >
          <StaffModalTabs
            tabs={[
              { id: 'dati', label: 'Dati pattern' },
              { id: 'entry', label: 'Entry', count: form.entries.length },
            ]}
            active={modalTab}
            onChange={setModalTab}
          />
          {error ? <p className="text-sm text-amber-200">{error}</p> : null}

          {modalTab === 'dati' && (
            <div className="space-y-3">
              <label className="block text-sm">
                <span className="text-gray-400 text-xs">Nome</span>
                <input
                  className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-2 py-1.5"
                  value={form.nome}
                  onChange={(e) => setForm((f) => ({ ...f, nome: e.target.value }))}
                />
              </label>
              <label className="block text-sm">
                <span className="text-gray-400 text-xs">Descrizione</span>
                <textarea
                  className="w-full mt-0.5 bg-gray-950 border border-gray-600 rounded px-2 py-1.5 min-h-[56px]"
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
            </div>
          )}

          {modalTab === 'entry' && (
            <div className="space-y-3">
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
              <div className="rounded-lg border border-gray-700 overflow-hidden">
                <table className="w-full text-sm">
                  <thead className="bg-gray-950 text-[10px] uppercase tracking-wider text-gray-500">
                    <tr>
                      <th className="text-left px-3 py-2">Tipo</th>
                      <th className="text-right px-3 py-2">Peso</th>
                      <th className="text-right px-3 py-2">Diff.</th>
                      <th className="text-center px-3 py-2">On</th>
                      <th className="text-right px-3 py-2 w-16">Azioni</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-800">
                    {form.entries.map((row, idx) => (
                      <tr key={row.id || `new-${idx}`} className="bg-gray-900/40">
                        <td className="px-2 py-1">
                          <select
                            className="w-full bg-gray-950 border border-gray-600 rounded px-1 py-1 text-xs"
                            value={row.tipo}
                            onChange={(e) => patchEntry(idx, { tipo: e.target.value })}
                          >
                            {TIPO_OPTS.map((o) => (
                              <option key={o.id} value={o.id}>{o.label}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1">
                          <input
                            type="number"
                            min={1}
                            className="w-16 ml-auto block bg-gray-950 border border-gray-600 rounded px-1 py-1 text-right"
                            value={row.peso}
                            onChange={(e) => patchEntry(idx, { peso: Number(e.target.value) })}
                          />
                        </td>
                        <td className="px-2 py-1">
                          <select
                            className="w-14 ml-auto block bg-gray-950 border border-gray-600 rounded px-1 py-1"
                            value={row.difficolta}
                            onChange={(e) => patchEntry(idx, { difficolta: Number(e.target.value) })}
                          >
                            {[1, 2, 3, 4].map((n) => (
                              <option key={n} value={n}>{n}</option>
                            ))}
                          </select>
                        </td>
                        <td className="px-2 py-1 text-center">
                          <input
                            type="checkbox"
                            checked={row.attivo !== false}
                            onChange={(e) => patchEntry(idx, { attivo: e.target.checked })}
                          />
                        </td>
                        <td className="px-2 py-1 text-right">
                          <button
                            type="button"
                            onClick={() => removeEntry(idx)}
                            className="p-1 rounded bg-red-900/50 hover:bg-red-800 text-red-200"
                            disabled={form.entries.length <= 1}
                          >
                            <Trash2 size={12} />
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </StaffEditorModal>
      )}
    </StaffToolShell>
  );
};

export default memo(MinigiocoPatternManager);
