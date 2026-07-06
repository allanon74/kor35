/**
 * Pattern staff CRUD KOR35: lista full-width + modale per create/edit.
 * Usare questo layout per tutti gli editor staff (no pannello affiancato).
 */
import React from 'react';
import { Pencil, Plus, Save, Trash2, X } from 'lucide-react';

export function StaffModal({
  open,
  title,
  onClose,
  onSave,
  saveLabel = 'Salva',
  saving = false,
  wide = false,
  children,
}) {
  if (!open) return null;
  return (
    <div
      className="fixed inset-0 z-[200] flex items-end justify-center bg-black/80 p-2 sm:items-center sm:p-4"
      onClick={onClose}
      role="presentation"
    >
      <div
        className={`flex max-h-[94vh] w-full flex-col rounded-xl border border-gray-600 bg-gray-950 shadow-2xl ${
          wide ? 'max-w-4xl' : 'max-w-2xl'
        }`}
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="staff-modal-title"
      >
        <div className="flex shrink-0 items-center justify-between border-b border-gray-800 px-4 py-3">
          <h3 id="staff-modal-title" className="text-lg font-bold text-white">{title}</h3>
          <button type="button" onClick={onClose} className="text-gray-400 hover:text-white" aria-label="Chiudi">
            <X size={22} />
          </button>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-3">{children}</div>
        <div className="flex shrink-0 justify-end gap-2 border-t border-gray-800 px-4 py-3">
          <button type="button" onClick={onClose} className="rounded border border-gray-600 px-3 py-1.5 text-sm text-gray-300">
            Annulla
          </button>
          {onSave && (
            <button
              type="button"
              disabled={saving}
              onClick={onSave}
              className="flex items-center gap-1 rounded bg-emerald-800 px-3 py-1.5 text-sm font-bold disabled:opacity-50"
            >
              <Save size={14} /> {saveLabel}
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

export function StaffListToolbar({ title, count, onAdd, addLabel = 'Nuovo' }) {
  return (
    <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
      <h3 className="font-bold text-gray-100">{title}{count != null ? ` (${count})` : ''}</h3>
      {onAdd && (
        <button
          type="button"
          onClick={onAdd}
          className="flex items-center gap-1 rounded bg-violet-800 px-2 py-1 text-xs font-bold"
        >
          <Plus size={12} /> {addLabel}
        </button>
      )}
    </div>
  );
}

export function StaffListRow({
  onEdit,
  onDelete,
  deleteConfirm = 'Eliminare questo elemento?',
  children,
  className = '',
}) {
  const handleDelete = () => {
    if (!onDelete) return;
    if (window.confirm(deleteConfirm)) onDelete();
  };
  return (
    <li
      className={`flex items-start gap-2 rounded border border-gray-800 bg-gray-900/40 px-2 py-2 hover:border-gray-700 ${className}`}
    >
      <div className="flex shrink-0 gap-0.5 pt-0.5">
        {onEdit && (
          <button
            type="button"
            title="Modifica"
            onClick={onEdit}
            className="rounded p-1 text-sky-400 hover:bg-gray-800"
          >
            <Pencil size={14} />
          </button>
        )}
        {onDelete && (
          <button
            type="button"
            title="Elimina"
            onClick={handleDelete}
            className="rounded p-1 text-red-400 hover:bg-gray-800"
          >
            <Trash2 size={14} />
          </button>
        )}
      </div>
      <div className="min-w-0 flex-1 text-sm">{children}</div>
    </li>
  );
}

export function LabeledField({
  label,
  hint,
  htmlFor,
  required = false,
  children,
  className = '',
}) {
  return (
    <label className={`block ${className}`} htmlFor={htmlFor}>
      <span className="text-xs font-bold text-gray-200">
        {label}
        {required && <span className="text-red-400"> *</span>}
      </span>
      {hint && <p className="mb-1 mt-0.5 text-[10px] leading-snug text-gray-500">{hint}</p>}
      <div className="mt-1">{children}</div>
    </label>
  );
}

export function staffInputClass(extra = '') {
  return `w-full rounded border border-gray-600 bg-gray-900 px-2 py-1.5 text-sm text-white ${extra}`;
}

export function StaffFieldGrid({ children, cols = 2 }) {
  const cls = cols === 3 ? 'grid-cols-1 sm:grid-cols-3' : 'grid-cols-1 sm:grid-cols-2';
  return <div className={`grid gap-3 ${cls}`}>{children}</div>;
}

export function StaffSection({ title, hint, children }) {
  return (
    <section className="rounded border border-gray-700/80 bg-gray-900/30 p-3">
      <h4 className="text-xs font-bold uppercase tracking-wide text-violet-300">{title}</h4>
      {hint && <p className="mb-2 mt-1 text-[10px] text-gray-500">{hint}</p>}
      <div className="space-y-3">{children}</div>
    </section>
  );
}
