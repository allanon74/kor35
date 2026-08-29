import React, { useEffect, useMemo } from 'react';
import { Mail, MessageCircle, X } from 'lucide-react';
import { htmlToPlainText } from '../utils/htmlSanitizer';

/**
 * Toast in-app per notifiche realtime (messaggi, duelli, …).
 * Tema scuro allineato all'app; click apre la tab Messaggi.
 */
const NotificationPopup = ({ notification, onClose, onOpenMessages }) => {
  useEffect(() => {
    if (!notification) return undefined;
    const timer = setTimeout(() => onClose(), 8000);
    return () => clearTimeout(timer);
  }, [notification, onClose]);

  const plainText = useMemo(() => htmlToPlainText(notification?.testo), [notification?.testo]);

  if (!notification) return null;

  const handleOpen = () => {
    if (typeof onOpenMessages === 'function') onOpenMessages(notification);
    onClose();
  };

  return (
    <div className="fixed top-4 right-4 z-50 max-w-sm w-[min(100vw-2rem,24rem)] animate-slide-in-right">
      <div className="rounded-2xl border border-indigo-400/30 bg-gray-950/95 shadow-2xl shadow-indigo-950/40 backdrop-blur-md overflow-hidden ring-1 ring-white/10">
        <div className="flex items-stretch">
          <div className="w-1.5 bg-indigo-500 shrink-0" aria-hidden />
          <button
            type="button"
            onClick={handleOpen}
            className="flex-1 text-left p-4 hover:bg-white/5 transition-colors"
          >
            <div className="flex items-start gap-3">
              <div className="mt-0.5 rounded-full bg-indigo-600/30 p-2 text-indigo-300">
                <MessageCircle size={18} />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm font-semibold text-white truncate">
                  {notification.titolo || 'Nuovo messaggio'}
                </p>
                {plainText ? (
                  <p className="mt-1 text-sm text-gray-300 line-clamp-3">{plainText}</p>
                ) : null}
                {notification.mittente ? (
                  <p className="mt-2 text-[11px] uppercase tracking-wide text-gray-500">
                    Da: {notification.mittente}
                  </p>
                ) : null}
                <p className="mt-2 text-xs text-indigo-300/90 inline-flex items-center gap-1">
                  <Mail size={12} /> Apri messaggi
                </p>
              </div>
            </div>
          </button>
          <button
            type="button"
            className="self-start m-2 p-1.5 rounded-lg text-gray-500 hover:text-white hover:bg-white/10"
            onClick={(e) => {
              e.stopPropagation();
              onClose();
            }}
            aria-label="Chiudi"
          >
            <X size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

export default NotificationPopup;
