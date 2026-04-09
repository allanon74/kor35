import React, { useEffect } from 'react';

const NotificationPopup = ({ notification, onClose }) => {
  if (!notification) return null;

  // Chiudi automaticamente dopo 10 secondi (10000 ms)
  useEffect(() => {
    const timer = setTimeout(() => {
      onClose();
    }, 10000); // <--- MODIFICATO: Durata più lunga
    return () => clearTimeout(timer);
  }, [notification, onClose]);

  return (
    <div className="fixed top-5 right-5 z-50 max-w-sm w-full bg-white shadow-lg rounded-lg pointer-events-auto ring-1 ring-black ring-opacity-5 overflow-hidden animate-slide-in-right">
      <div className="p-4">
        <div className="flex items-start">
          <div className="shrink-0">
            <svg className="h-6 w-6 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9" />
            </svg>
          </div>
          <div className="ml-3 w-0 flex-1 pt-0.5">
            <p className="text-sm font-medium text-gray-900">
              {notification.titolo}
            </p>
            
            {/* MODIFICA QUI: Renderizza HTML invece di testo puro */}
            <div 
                className="mt-1 text-sm text-gray-500"
                dangerouslySetInnerHTML={{ __html: notification.testo }}
            />
            
            <p className="mt-1 text-xs text-gray-400">
                Da: {notification.mittente}
            </p>
          </div>
          <div className="ml-4 shrink-0 flex">
            <button
              className="bg-white rounded-md inline-flex text-gray-400 hover:text-gray-500 focus:outline-none"
              onClick={onClose}
            >
              <span className="sr-only">Chiudi</span>
              <svg className="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

export default NotificationPopup;