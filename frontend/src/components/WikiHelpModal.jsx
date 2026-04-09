import React, { useState, useEffect } from 'react';
import { X, Loader2 } from 'lucide-react';
import { getWikiPage, getWikiImageUrl, getMediaUrl } from '../api';
import WikiRenderer from './WikiRenderer';

/**
 * Modal per visualizzare pagine wiki di aiuto/istruzioni
 * Ottimizzato per mobile ma funziona anche su desktop
 */
export default function WikiHelpModal({ isOpen, onClose, wikiSlug }) {
  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (isOpen && wikiSlug) {
      fetchPage();
    } else {
      // Reset quando si chiude
      setPageData(null);
      setError(null);
    }
  }, [isOpen, wikiSlug]);

  const fetchPage = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWikiPage(wikiSlug);
      setPageData(data);
    } catch (err) {
      console.error("Errore caricamento pagina wiki:", err);
      setError("Impossibile caricare la pagina di aiuto.");
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-0 md:p-4">
      {/* Overlay con backdrop blur */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Modal Container */}
      <div className="relative bg-white rounded-lg shadow-2xl w-full h-full md:h-auto md:max-h-[90vh] md:max-w-4xl flex flex-col animate-fadeIn">
        
        {/* Header */}
        <div className="flex items-center justify-between p-4 md:p-6 border-b bg-gradient-to-r from-indigo-50 to-blue-50 shrink-0">
          <h2 className="text-xl md:text-2xl font-bold text-gray-800 flex items-center gap-2">
            <span className="text-indigo-600">❓</span>
            {pageData?.titolo || 'Guida'}
          </h2>
          <button
            onClick={onClose}
            className="p-2 rounded-full hover:bg-gray-200 text-gray-600 hover:text-gray-800 transition-colors"
            aria-label="Chiudi"
          >
            <X size={24} />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <Loader2 size={48} className="text-indigo-600 animate-spin" />
              <p className="text-gray-500 font-medium">Caricamento guida...</p>
            </div>
          )}

          {error && (
            <div className="flex flex-col items-center justify-center py-20 gap-4">
              <div className="text-red-500 text-6xl">⚠️</div>
              <p className="text-gray-700 font-bold text-lg">{error}</p>
              <p className="text-gray-500 text-sm">La pagina potrebbe non essere ancora disponibile.</p>
            </div>
          )}

          {pageData && !loading && !error && (
            <div className="animate-fadeIn">
              {/* Immagine copertina se presente */}
              {pageData.immagine && (
                <div className="relative w-full h-48 md:h-64 mb-6 rounded-lg overflow-hidden shadow-lg">
                  <img
                    src={getWikiImageUrl(pageData.slug, 1200)}
                    alt={pageData.titolo}
                    className="w-full h-full object-cover"
                    style={{ objectPosition: `center ${pageData.banner_y ?? 50}%` }}
                    onError={(e) => { 
                      e.target.onerror = null; 
                      e.target.src = getMediaUrl(pageData.immagine); 
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/60 via-transparent to-transparent"></div>
                </div>
              )}

              {/* Contenuto */}
              <WikiRenderer content={pageData.contenuto} />
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="p-4 border-t bg-gray-50 shrink-0">
          <button
            onClick={onClose}
            className="w-full md:w-auto px-6 py-2 bg-indigo-600 hover:bg-indigo-700 text-white font-bold rounded-lg transition-colors shadow-md hover:shadow-lg"
          >
            Chiudi
          </button>
        </div>
      </div>
    </div>
  );
}
