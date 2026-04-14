import React, { useEffect, useMemo, useRef, useState } from 'react';
import { ChevronDown } from 'lucide-react';

const EditorSaveActions = ({
  onSave,
  onSaveAndContinue,
  onSaveAsNew,
  onSaveAndNew,
  onCancel,
  saving = false,
  saveLabel = 'Salva',
  statusMessage = '',
  statusType = 'success',
}) => {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);

  const menuActions = useMemo(() => {
    const actions = [];
    if (onSaveAndContinue) actions.push({ key: 'continue', label: 'Salva e continua', action: onSaveAndContinue });
    if (onSaveAsNew) actions.push({ key: 'as-new', label: 'Salva come nuovo', action: onSaveAsNew });
    if (onSaveAndNew) actions.push({ key: 'new-blank', label: 'Salva ed inserisci un altro', action: onSaveAndNew });
    return actions;
  }, [onSaveAndContinue, onSaveAsNew, onSaveAndNew]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setMenuOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, [menuOpen]);

  const statusClasses = {
    success: 'text-emerald-300 bg-emerald-900/20 border-emerald-700/40',
    warning: 'text-amber-200 bg-amber-900/20 border-amber-700/40',
    error: 'text-red-200 bg-red-900/20 border-red-700/40',
  };
  const currentStatusClass = statusClasses[statusType] || statusClasses.success;

  return (
    <div className="flex flex-col items-end gap-2">
      <div className="flex flex-wrap gap-2 justify-end">
        <div className="relative" ref={menuRef}>
          <div className="inline-flex rounded-lg overflow-hidden shadow-lg">
            <button
              onClick={onSave}
              disabled={saving}
              className="bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-6 py-2 font-black text-xs uppercase text-white"
            >
              {saving ? 'Salvataggio...' : saveLabel}
            </button>
            {menuActions.length > 0 && (
              <button
                type="button"
                onClick={() => setMenuOpen((prev) => !prev)}
                disabled={saving}
                className="bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 disabled:cursor-not-allowed px-3 py-2 border-l border-emerald-500/50 text-white"
                title="Altre opzioni di salvataggio"
              >
                <ChevronDown size={14} />
              </button>
            )}
          </div>
          {menuOpen && menuActions.length > 0 && (
            <div className="absolute right-0 mt-1 w-56 bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden z-50">
              {menuActions.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    item.action();
                  }}
                  className="w-full text-left px-3 py-2 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
        {onCancel && (
          <button
            onClick={onCancel}
            disabled={saving}
            className="bg-gray-700 hover:bg-gray-600 px-6 py-2 rounded-lg font-bold text-xs uppercase text-white"
          >
            Annulla
          </button>
        )}
      </div>
      {statusMessage && (
        <div className={`text-xs border rounded-md px-3 py-1 ${currentStatusClass}`}>
          {statusMessage}
        </div>
      )}
    </div>
  );
};

export default EditorSaveActions;
