import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import WikiRenderer from '../components/WikiRenderer';
import WikiPageEditorModal from '../components/wiki/WikiPageEditorModal'; // Importiamo il modale
import HomePage from '../components/HomePage'; // Importiamo il componente HomePage speciale
import { getWikiPage, getWikiImageUrl, getMediaUrl } from '../api';
import { useCharacter } from '../components/CharacterContext'; // Per i permessi
import { EyeOff } from 'lucide-react';

export default function WikiPage({ slug: propSlug }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const currentSlug = propSlug || slug || 'home'; 
  
  // Recuperiamo i permessi
  // Nota: controlliamo isStaff all'interno del token/context
  const { isStaff, isMaster } = useCharacter(); 
  const canEdit = isStaff || isMaster; // Definisci chi può editare

  const [pageData, setPageData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Stato per il modale di modifica
  const [isEditorOpen, setEditorOpen] = useState(false);

  // Funzione di caricamento (estratta per poter ricaricare dopo l'edit)
  const fetchPage = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWikiPage(currentSlug);
      setPageData(data);
    } catch (err) {
      console.error("Errore fetch pagina:", err);
      setError("Pagina non trovata.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPage();
  }, [currentSlug]);

  const handleEditSuccess = (newSlug) => {
      setEditorOpen(false);
      // Se lo slug è cambiato, navighiamo alla nuova URL
      if (newSlug && newSlug !== currentSlug) {
          navigate(`/regolamento/${newSlug}`);
      } else {
          // Altrimenti ricarichiamo i dati della pagina corrente
          fetchPage();
      }
  };

  if (loading) return <div className="p-10 text-center text-gray-500 animate-pulse">Caricamento contenuto...</div>;

  if (error || !pageData) {
    return (
        <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded shadow text-center">
            <h2 className="text-2xl font-bold text-gray-700 mb-2">404 - Pagina non trovata</h2>
            <p className="text-gray-500 mb-4">{error}</p>
            {/* Se siamo staff, offriamo di creare la pagina qui */}
            {canEdit && (
                <button 
                    onClick={() => setEditorOpen(true)}
                    className="bg-red-700 text-white px-4 py-2 rounded hover:bg-red-800"
                >
                    Crea pagina "{currentSlug}"
                </button>
            )}
            
            {/* Modale Creazione su 404 */}
            {isEditorOpen && (
                <WikiPageEditorModal 
                    initialData={{ title: currentSlug, slug: currentSlug }}
                    onClose={() => setEditorOpen(false)}
                    onSuccess={handleEditSuccess}
                />
            )}
        </div>
    );
  }

  // Se lo slug è "home", usa il layout speciale HomePage
  if (currentSlug === 'home') {
    return (
      <>
        {/* PULSANTE MODIFICA (Visibile solo a Staff/Master) */}
        {canEdit && (
          <div className="fixed top-20 right-4 z-50">
            <button 
              onClick={() => setEditorOpen(true)}
              className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded shadow-lg hover:bg-indigo-700 font-bold text-sm opacity-70 hover:opacity-100 transition-opacity"
            >
              ✏️ Modifica Pagina Home
            </button>
          </div>
        )}

        {/* Componente HomePage speciale */}
        <HomePage pageData={pageData} />

        {/* MODALE EDITOR */}
        {isEditorOpen && (
          <WikiPageEditorModal 
            initialData={pageData}
            onClose={() => setEditorOpen(false)}
            onSuccess={handleEditSuccess}
          />
        )}
      </>
    );
  }

  // Layout standard per tutte le altre pagine
  return (
    <div className="max-w-5xl mx-auto bg-white min-h-screen shadow-sm md:rounded-lg overflow-hidden relative group">

        {/* --- BANNER BOZZA (NUOVO) --- */}
        {pageData?.public === false && (
            <div className="bg-yellow-100 border-b border-yellow-300 text-yellow-800 px-4 py-2 flex items-center justify-center gap-2 font-bold text-sm">
                <EyeOff size={16} />
                <span>QUESTA PAGINA È UNA BOZZA (Visibile solo allo Staff)</span>
            </div>
        )}
        
        {/* PULSANTE MODIFICA (Visibile solo a Staff/Master) */}
        {canEdit && (
            <div className="absolute top-4 right-4 z-10 opacity-30 group-hover:opacity-100 transition-opacity">
                <button 
                    onClick={() => setEditorOpen(true)}
                    className="flex items-center gap-2 bg-indigo-600 text-white px-4 py-2 rounded shadow hover:bg-indigo-700 font-bold text-sm"
                >
                    ✏️ Modifica Pagina
                </button>
            </div>
        )}

        {/* Immagine Copertina */}
        {pageData.immagine && (
            <div className="relative w-full h-48 md:h-64 lg:h-80 overflow-hidden shadow-md">
                <img 
                    // Richiedi larghezza 1200px (buon compromesso desktop/mobile)
                    src={getWikiImageUrl(pageData.slug, 1200)} 
                    
                    // Fallback: se l'API custom fallisce per qualche motivo, usa l'url originale
                    onError={(e) => { e.target.onerror = null; e.target.src = getMediaUrl(pageData.immagine); }}
                    
                    alt={pageData.titolo}
                    className="w-full h-full object-cover"
                    
                    // Applica la posizione salvata (default 50% se manca)
                    style={{ objectPosition: `center ${pageData.banner_y ?? 50}%` }}
                />
                
                {/* Gradiente per leggere il titolo */}
                <div className="absolute inset-0 bg-linear-to-t from-black/80 via-transparent to-transparent"></div>
                
                <div className="absolute bottom-0 left-0 p-4 md:p-8 text-white">
                    <h1 className="text-3xl md:text-5xl font-bold drop-shadow-lg">{pageData.titolo}</h1>
                </div>
            </div>
        )}

        <div className="p-6 md:p-10">
            {/* Titolo se non c'è immagine */}
            {!pageData.immagine && (
                <h1 className="text-3xl md:text-4xl font-bold mb-8 text-red-900 border-b pb-4 flex justify-between items-center">
                    {pageData.titolo}
                </h1>
            )}
            
            {/* Contenuto */}
            <WikiRenderer content={pageData.contenuto} />
        </div>

        {/* MODALE EDITOR */}
        {isEditorOpen && (
            <WikiPageEditorModal 
                initialData={pageData} // Passiamo i dati attuali per popolare il form
                onClose={() => setEditorOpen(false)}
                onSuccess={handleEditSuccess}
            />
        )}
    </div>
  );
}