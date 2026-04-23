import React, { useEffect } from 'react';
import { CheckCircle2, AlertTriangle, Info, XCircle, X } from 'lucide-react';

const TYPE_STYLE = {
  success: {
    icon: CheckCircle2,
    wrap: 'border-emerald-500/60 bg-emerald-950/80 text-emerald-100',
  },
  error: {
    icon: XCircle,
    wrap: 'border-red-500/60 bg-red-950/80 text-red-100',
  },
  warning: {
    icon: AlertTriangle,
    wrap: 'border-amber-500/60 bg-amber-950/80 text-amber-100',
  },
  info: {
    icon: Info,
    wrap: 'border-indigo-500/60 bg-indigo-950/80 text-indigo-100',
  },
};

const AppToastStack = ({ toasts, onClose }) => {
  useEffect(() => {
    if (!Array.isArray(toasts) || toasts.length === 0) return undefined;
    const timers = toasts.map((toast) =>
      window.setTimeout(() => onClose(toast.id), Math.max(1000, Number(toast.durationMs || 3000)))
    );
    return () => timers.forEach((id) => window.clearTimeout(id));
  }, [toasts, onClose]);

  if (!Array.isArray(toasts) || toasts.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[100] flex flex-col gap-2 w-[min(92vw,360px)]">
      {toasts.map((toast) => {
        const style = TYPE_STYLE[toast.type] || TYPE_STYLE.info;
        const Icon = style.icon;
        return (
          <div key={toast.id} className={`rounded-xl border px-3 py-2 shadow-2xl backdrop-blur ${style.wrap}`}>
            <div className="flex items-start gap-2">
              <Icon size={18} className="mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                {toast.title ? <div className="text-xs font-black uppercase tracking-wider">{toast.title}</div> : null}
                {toast.message ? <div className="text-xs mt-0.5">{toast.message}</div> : null}
              </div>
              <button
                type="button"
                onClick={() => onClose(toast.id)}
                className="opacity-70 hover:opacity-100 transition-opacity"
                aria-label="Chiudi toast"
              >
                <X size={14} />
              </button>
            </div>
          </div>
        );
      })}
    </div>
  );
};

export default AppToastStack;

