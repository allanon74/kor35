import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
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
  const [menuPos, setMenuPos] = useState(null);
  const menuRef = useRef(null);
  const triggerRef = useRef(null);

  const menuActions = useMemo(() => {
    const actions = [];
    if (onSaveAndContinue) actions.push({ key: 'continue', label: 'Salva e continua', action: onSaveAndContinue });
    if (onSaveAsNew) actions.push({ key: 'as-new', label: 'Salva come nuovo', action: onSaveAsNew });
    if (onSaveAndNew) actions.push({ key: 'new-blank', label: 'Salva ed inserisci un altro', action: onSaveAndNew });
    return actions;
  }, [onSaveAndContinue, onSaveAsNew, onSaveAndNew]);

  useLayoutEffect(() => {
    if (!menuOpen || !triggerRef.current) {
      setMenuPos(null);
      return undefined;
    }
    const update = () => {
      const rect = triggerRef.current.getBoundingClientRect();
      const spaceAbove = rect.top;
      const openUp = spaceAbove > 180 || spaceAbove > window.innerHeight - rect.bottom;
      const width = Math.max(rect.width, 224);
      const left = Math.max(8, Math.min(rect.right - width, window.innerWidth - width - 8));
      if (openUp) {
        setMenuPos({
          bottom: window.innerHeight - rect.top + 4,
          left,
          width,
        });
      } else {
        setMenuPos({
          top: rect.bottom + 4,
          left,
          width,
        });
      }
    };
    update();
    window.addEventListener('resize', update);
    window.addEventListener('scroll', update, true);
    return () => {
      window.removeEventListener('resize', update);
      window.removeEventListener('scroll', update, true);
    };
  }, [menuOpen]);

  useEffect(() => {
    if (!menuOpen) return undefined;
    const handlePointerOutside = (event) => {
      const menuEl = document.getElementById('editor-save-actions-menu');
      if (menuRef.current?.contains(event.target)) return;
      if (menuEl?.contains(event.target)) return;
      setMenuOpen(false);
    };
    document.addEventListener('pointerdown', handlePointerOutside);
    return () => document.removeEventListener('pointerdown', handlePointerOutside);
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
          <div className="inline-flex w-full overflow-hidden rounded-lg shadow-lg sm:w-auto" ref={triggerRef}>
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
          {menuOpen && menuActions.length > 0 && menuPos && typeof document !== 'undefined'
            ? createPortal(
                <div
                  id="editor-save-actions-menu"
                  className="fixed z-[130] bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden"
                  style={{
                    top: menuPos.top != null ? `${menuPos.top}px` : undefined,
                    bottom: menuPos.bottom != null ? `${menuPos.bottom}px` : undefined,
                    left: `${menuPos.left}px`,
                    width: `${menuPos.width}px`,
                  }}
                >
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
                </div>,
                document.body,
              )
            : null}
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
