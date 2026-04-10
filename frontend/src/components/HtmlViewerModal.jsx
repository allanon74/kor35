import React from 'react';

// Icona per il pulsante di chiusura (da lucide-react)
const X = (props) => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    width="24"
    height="24"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    {...props}
  >
    <path d="M18 6 6 18" />
    <path d="m6 6 12 12" />
  </svg>
);

const HtmlViewerModal = ({ htmlContent, onClose }) => {
  if (!htmlContent) {
    return null;
  }

  return (
    // Overlay scuro che copre l'intera pagina
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-75 p-4">
      
      {/* Contenitore della modale */}
      <div className="flex flex-col w-full h-full max-w-4xl max-h-[90vh] bg-gray-800 rounded-lg shadow-2xl overflow-hidden">
        
        {/* Header della modale */}
        <div className="flex items-center justify-between p-4 border-b border-gray-700">
          <h2 className="text-xl font-bold text-white">Risultato Scansione</h2>
          <button
            onClick={onClose}
            className="p-2 text-gray-400 rounded-full hover:bg-gray-700 hover:text-white focus:outline-none focus:ring-2 focus:ring-indigo-500"
            aria-label="Chiudi"
          >
            <X className="w-6 h-6" />
          </button>
        </div>

        {/* Contenuto (iframe) */}
        <div className="grow p-4 bg-white overflow-auto">
          <iframe
            srcDoc={htmlContent}
            title="Contenuto QR"
            className="w-full h-full border-0"
            sandbox="allow-scripts allow-same-origin" // Aggiunge un po' di sicurezza
          />
        </div>

        {/* Footer con pulsante di chiusura (utile per mobile) */}
        <div className="p-4 border-t border-gray-700 text-center">
           <button
            onClick={onClose}
            className="px-6 py-2 font-bold text-white bg-indigo-600 rounded-md shadow-lg hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
};

export default HtmlViewerModal;

