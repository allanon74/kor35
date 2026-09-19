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
    <div className="flex w-full min-w-0 flex-col items-stretch gap-2 sm:items-end">
      <div className="flex w-full min-w-0 flex-col gap-2 sm:flex-row sm:flex-wrap sm:justify-end">
        <div className="relative min-w-0 w-full sm:w-auto" ref={menuRef}>
          <div className="inline-flex w-full overflow-hidden rounded-lg shadow-lg sm:w-auto">
            <button
              type="button"
              onClick={onSave}
              disabled={saving}
              className="min-h-11 flex-1 bg-emerald-600 hover:bg-emerald-500 disabled:bg-gray-700 disabled:cursor-not-allowed px-4 sm:px-6 py-2.5 font-black text-xs uppercase text-white sm:flex-none"
            >
              {saving ? 'Salvataggio...' : saveLabel}
            </button>
            {menuActions.length > 0 && (
              <button
                type="button"
                onClick={() => setMenuOpen((prev) => !prev)}
                disabled={saving}
                className="min-h-11 shrink-0 bg-emerald-700 hover:bg-emerald-600 disabled:bg-gray-700 disabled:cursor-not-allowed px-3 py-2 border-l border-emerald-500/50 text-white"
                title="Altre opzioni di salvataggio"
              >
                <ChevronDown size={14} />
              </button>
            )}
          </div>
          {menuOpen && menuActions.length > 0 && (
            <div className="absolute right-0 bottom-full z-50 mb-1 w-full min-w-56 max-w-xs bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden sm:w-56 lg:bottom-auto lg:top-full lg:mt-1 lg:mb-0">
              {menuActions.map((item) => (
                <button
                  key={item.key}
                  type="button"
                  onClick={() => {
                    setMenuOpen(false);
                    item.action();
                  }}
                  className="w-full min-h-11 text-left px-3 py-2.5 text-sm text-gray-200 hover:bg-gray-800 transition-colors"
                >
                  {item.label}
                </button>
              ))}
            </div>
          )}
        </div>
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            disabled={saving}
            className="min-h-11 w-full sm:w-auto bg-gray-700 hover:bg-gray-600 px-4 sm:px-6 py-2.5 rounded-lg font-bold text-xs uppercase text-white"
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
