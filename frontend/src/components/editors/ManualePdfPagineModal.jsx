import React, { useCallback, useEffect, useMemo, useState, memo } from 'react';
import {
  X, Save, ChevronUp, ChevronDown, BookMarked, BookOpen, Plus, Trash2, GripVertical,
} from 'lucide-react';
import {
  getStaffManualePdfPagine,
  updateStaffManualePdfPagine,
  getStaffWikiPagesSmall,
} from '../../api';

const emptyPicker = { open: false, search: '' };

const ManualePdfPagineModal = ({ manuale, onClose, onSaved, onLogout }) => {
  const [rows, setRows] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [wikiPages, setWikiPages] = useState([]);
  const [picker, setPicker] = useState(emptyPicker);

  const load = useCallback(async () => {
    if (!manuale?.slug) return;
    setLoading(true);
    try {
      const data = await getStaffManualePdfPagine(manuale.slug, onLogout);
      setRows(Array.isArray(data?.pagine) ? data.pagine : []);
    } catch (e) {
      console.error(e);
      setMessage('Errore caricamento pagine.');
    } finally {
      setLoading(false);
    }
  }, [manuale?.slug, onLogout]);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    getStaffWikiPagesSmall(onLogout)
      .then((data) => setWikiPages(Array.isArray(data) ? data : []))
      .catch(console.error);
  }, [onLogout]);

  const usedIds = useMemo(() => new Set(rows.map((r) => r.pagina_id)), [rows]);

  const addablePages = useMemo(() => {
    const q = picker.search.trim().toLowerCase();
    return wikiPages
      .filter((p) => !usedIds.has(p.id))
      .filter((p) => {
        if (!q) return true;
        return (
          (p.titolo || '').toLowerCase().includes(q)
          || (p.slug || '').toLowerCase().includes(q)
        );
      })
      .slice(0, 40);
  }, [wikiPages, usedIds, picker.search]);

  const moveRow = (index, delta) => {
    setRows((prev) => {
      const next = [...prev];
      const target = index + delta;
      if (target < 0 || target >= next.length) return prev;
      [next[index], next[target]] = [next[target], next[index]];
      return next.map((r, i) => ({ ...r, ordine: (i + 1) * 10 }));
    });
  };

  const removeRow = (paginaId) => {
    setRows((prev) => prev.filter((r) => r.pagina_id !== paginaId));
  };

  const addPage = (page) => {
    setRows((prev) => [
      ...prev,
      {
        pagina_id: page.id,
        titolo: page.titolo,
        slug: page.slug,
        ordine: (prev.length + 1) * 10,
        inizio_capitolo: true,
        pdf_titolo_capitolo: page.pdf_titolo_capitolo || '',
        pdf_solo_indice: !!page.pdf_solo_indice,
        pdf_forza_nuova_pagina: !!page.pdf_forza_nuova_pagina,
        public: page.public,
        visibile_solo_staff: page.visibile_solo_staff,
      },
    ]);
    setPicker(emptyPicker);
  };

  const updateRow = (paginaId, patch) => {
    setRows((prev) => prev.map((r) => (r.pagina_id === paginaId ? { ...r, ...patch } : r)));
  };

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const payload = rows.map((r, i) => ({
        pagina_id: r.pagina_id,
        ordine: r.ordine ?? (i + 1) * 10,
        inizio_capitolo: r.inizio_capitolo !== false,
        pdf_titolo_capitolo: r.pdf_titolo_capitolo ?? '',
        pdf_solo_indice: !!r.pdf_solo_indice,
        pdf_forza_nuova_pagina: !!r.pdf_forza_nuova_pagina,
      }));
      const data = await updateStaffManualePdfPagine(manuale.slug, payload, onLogout);
      setRows(Array.isArray(data?.pagine) ? data.pagine : rows);
      setMessage('Pagine salvate.');
      onSaved?.(data);
    } catch (e) {
      console.error(e);
      setMessage(e?.message || 'Errore salvataggio.');
    } finally {
      setSaving(false);
    }
  };

  if (!manuale) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70">
      <div className="bg-gray-900 border border-gray-700 rounded-2xl w-full max-w-3xl max-h-[90vh] flex flex-col shadow-2xl">
        <div className="flex items-start justify-between gap-4 p-4 border-b border-gray-800">
          <div>
            <h3 className="text-lg font-black text-white flex items-center gap-2">
              <BookOpen size={20} className="text-rose-400" />
              Pagine — {manuale.titolo}
            </h3>
            <p className="text-xs text-gray-500 mt-1">
              Ordine, capitoli e inclusione pagine wiki nel manuale PDF.
            </p>
          </div>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-white p-1">
            <X size={20} />
          </button>
        </div>

        {message && (
          <p className="mx-4 mt-3 text-sm text-gray-200 bg-gray-800 border border-gray-700 rounded-lg px-3 py-2">
            {message}
          </p>
        )}

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {loading ? (
            <p className="text-gray-500 text-sm">Caricamento...</p>
          ) : rows.length === 0 ? (
            <p className="text-gray-500 text-sm">Nessuna pagina nel manuale. Aggiungine una qui sotto.</p>
          ) : (
            rows.map((row, index) => (
              <div
                key={row.pagina_id}
                className={`flex flex-col sm:flex-row sm:items-center gap-2 p-3 rounded-xl border ${
                  row.inizio_capitolo !== false
                    ? 'border-rose-500/30 bg-rose-950/20'
                    : 'border-gray-800 bg-gray-950/50'
                }`}
              >
                <div className="flex items-center gap-2 min-w-0 flex-1">
                  <GripVertical size={16} className="text-gray-600 shrink-0 hidden sm:block" />
                  <div className="min-w-0">
                    <div className="font-bold text-sm text-white truncate">{row.titolo}</div>
                    <div className="text-xs text-gray-500">{row.slug}</div>
                    {(row.visibile_solo_staff || !row.public) && (
                      <div className="text-xs text-amber-400 mt-0.5">Non pubblica — non comparirà nel PDF</div>
                    )}
                  </div>
                </div>

                <input
                  type="text"
                  className="sm:w-40 bg-gray-950 border border-gray-700 rounded-lg px-2 py-1.5 text-xs"
                  value={row.pdf_titolo_capitolo || ''}
                  onChange={(e) => updateRow(row.pagina_id, { pdf_titolo_capitolo: e.target.value })}
                  placeholder="Titolo PDF"
                  title="Titolo capitolo nel PDF"
                />

                <div className="flex items-center gap-1 shrink-0">
                  <button
                    type="button"
                    title={row.inizio_capitolo !== false ? 'È inizio capitolo' : 'Promuovi a capitolo'}
                    onClick={() => updateRow(row.pagina_id, { inizio_capitolo: row.inizio_capitolo === false })}
                    className={`p-2 rounded-lg border ${
                      row.inizio_capitolo !== false
                        ? 'border-rose-500/50 text-rose-300 bg-rose-500/10'
                        : 'border-gray-700 text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    <BookMarked size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveRow(index, -1)}
                    disabled={index === 0}
                    className="p-2 rounded-lg border border-gray-700 text-gray-400 disabled:opacity-30"
                  >
                    <ChevronUp size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => moveRow(index, 1)}
                    disabled={index === rows.length - 1}
                    className="p-2 rounded-lg border border-gray-700 text-gray-400 disabled:opacity-30"
                  >
                    <ChevronDown size={16} />
                  </button>
                  <button
                    type="button"
                    onClick={() => removeRow(row.pagina_id)}
                    className="p-2 rounded-lg border border-red-900/50 text-red-400 hover:bg-red-950/30"
                  >
                    <Trash2 size={16} />
                  </button>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-gray-800 space-y-3">
          {picker.open ? (
            <div className="bg-gray-950 border border-gray-700 rounded-xl p-3 space-y-2">
              <input
                type="search"
                className="w-full bg-gray-900 border border-gray-700 rounded-lg px-3 py-2 text-sm"
                placeholder="Cerca pagina wiki..."
                value={picker.search}
                onChange={(e) => setPicker((p) => ({ ...p, search: e.target.value }))}
                autoFocus
              />
              <ul className="max-h-40 overflow-y-auto space-y-1">
                {addablePages.map((p) => (
                  <li key={p.id}>
                    <button
                      type="button"
                      onClick={() => addPage(p)}
                      className="w-full text-left px-2 py-1.5 rounded hover:bg-gray-800 text-sm"
                    >
                      <span className="font-medium">{p.titolo}</span>
                      <span className="text-gray-500 text-xs ml-2">{p.slug}</span>
                    </button>
                  </li>
                ))}
                {addablePages.length === 0 && (
                  <li className="text-xs text-gray-500 px-2">Nessuna pagina disponibile.</li>
                )}
              </ul>
              <button
                type="button"
                onClick={() => setPicker(emptyPicker)}
                className="text-xs text-gray-500 hover:text-gray-300"
              >
                Chiudi elenco
              </button>
            </div>
          ) : (
            <button
              type="button"
              onClick={() => setPicker({ open: true, search: '' })}
              className="inline-flex items-center gap-2 text-sm font-bold text-indigo-400 hover:text-indigo-300"
            >
              <Plus size={16} /> Aggiungi pagina wiki
            </button>
          )}

          <div className="flex flex-wrap gap-2 justify-end">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-gray-700 text-sm font-bold text-gray-400"
            >
              Chiudi
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 font-bold text-sm disabled:opacity-50"
            >
              <Save size={16} /> {saving ? 'Salvataggio...' : 'Salva pagine'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default memo(ManualePdfPagineModal);
