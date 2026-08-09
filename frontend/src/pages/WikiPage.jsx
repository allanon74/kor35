import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import WikiRenderer from '../components/WikiRenderer';
import WikiPageEditorModal from '../components/wiki/WikiPageEditorModal';
import HomePage from '../components/HomePage';
import { getWikiPage, getWikiGlossario, getWikiImageUrl, getMediaUrl, getConfigurazioneSito } from '../api';
import { useCharacter } from '../components/CharacterContext';
import { EyeOff } from 'lucide-react';
import { putOfflineWikiPage, getOfflineWikiPage } from '../lib/offlineWikiDb';
import { OfflineConsultBanner } from '../components/OfflineConsultBanner';

export default function WikiPage({ slug: propSlug }) {
  const { slug } = useParams();
  const navigate = useNavigate();
  const currentSlug = propSlug || slug || 'home'; 
  
  const { isCampaignRedactor, isCampaignMaster } = useCharacter();
  const [siteConfig, setSiteConfig] = useState(null);
  const canEdit = (isCampaignRedactor || isCampaignMaster) && !siteConfig?.maintenance_mode;

  const [pageData, setPageData] = useState(null);
  const [wikiGlossary, setWikiGlossary] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [offlineMeta, setOfflineMeta] = useState(null);
  
  const [isEditorOpen, setEditorOpen] = useState(false);

  const fetchPage = async () => {
    setLoading(true);
    setError(null);
    setOfflineMeta(null);
    try {
      const [data, gloss, config] = await Promise.all([
        getWikiPage(currentSlug),
        getWikiGlossario().catch(() => []),
        getConfigurazioneSito().catch(() => null),
      ]);
      setPageData(data);
      setWikiGlossary(Array.isArray(gloss) ? gloss : []);
      setSiteConfig(config);
      putOfflineWikiPage(currentSlug, data).catch(() => {});
    } catch (err) {
      console.error("Errore fetch pagina:", err);
      try {
        const cached = await getOfflineWikiPage(currentSlug);
        if (cached?.page) {
          setPageData(cached.page);
          setOfflineMeta({ stored_at: cached.stored_at });
          setError(null);
          return;
        }
      } catch {
        /* ignore */
      }
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
      if (newSlug && newSlug !== currentSlug) {
          navigate(`/regolamento/${newSlug}`);
      } else {
          fetchPage();
      }
  };

  if (loading) return <div className="p-10 text-center text-gray-500 animate-pulse">Caricamento contenuto...</div>;

  if (error || !pageData) {
    return (
        <div className="max-w-4xl mx-auto mt-10 p-6 bg-white rounded shadow text-center">
            <h2 className="text-2xl font-bold text-gray-700 mb-2">404 - Pagina non trovata</h2>
            <p className="text-gray-500 mb-4">{error}</p>
            {canEdit && (
                <button 
                    onClick={() => setEditorOpen(true)}
                    className="bg-red-700 text-white px-4 py-2 rounded hover:bg-red-800"
                >
                    Crea pagina "{currentSlug}"
                </button>
            )}
            
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

  if (currentSlug === 'home') {
    return (
      <>
        {canEdit && (
          <div className="fixed top-20 right-4 z-50">
            <button 
              onClick={() => setEditorOpen(true)}
              className="flex items-center gap-2 bg-[var(--wiki-brand)] text-white px-4 py-2 rounded shadow-lg hover:bg-[var(--wiki-brand-hot)] font-bold text-sm opacity-70 hover:opacity-100 transition-opacity"
            >
              Modifica Pagina Home
            </button>
          </div>
        )}

        <HomePage pageData={pageData} siteConfig={siteConfig} />

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

  return (
    <div className="wiki-shell max-w-3xl mx-auto min-h-screen overflow-hidden relative group border-x border-stone-200/80">
        {offlineMeta && (
          <div className="px-4 pt-3">
            <OfflineConsultBanner isOfflineSnapshot storedAt={offlineMeta.stored_at} />
          </div>
        )}

        {pageData?.public === false && (
            <div className="bg-yellow-100 border-b border-yellow-300 text-yellow-800 px-4 py-2 flex items-center justify-center gap-2 font-bold text-sm">
                <EyeOff size={16} />
                <span>QUESTA PAGINA È UNA BOZZA (Visibile solo allo Staff)</span>
            </div>
        )}
        
        {canEdit && (
            <div className="absolute top-4 right-4 z-10 opacity-30 group-hover:opacity-100 transition-opacity">
                <button 
                    onClick={() => setEditorOpen(true)}
                    className="flex items-center gap-2 bg-[var(--wiki-brand)] text-white px-4 py-2 rounded shadow hover:bg-[var(--wiki-brand-hot)] font-bold text-sm"
                >
                    Modifica Pagina
                </button>
            </div>
        )}

        {pageData.immagine && (
            <div className="relative w-full h-48 md:h-64 lg:h-72 overflow-hidden">
                <img 
                    src={getWikiImageUrl(pageData.slug, 1200)}
                    srcSet={`${getWikiImageUrl(pageData.slug, 640)} 640w, ${getWikiImageUrl(pageData.slug, 960)} 960w, ${getWikiImageUrl(pageData.slug, 1200)} 1200w`}
                    sizes="100vw"
                    width={1200}
                    height={480}
                    loading="eager"
                    decoding="async"
                    onError={(e) => { e.target.onerror = null; e.target.src = getMediaUrl(pageData.immagine); e.target.removeAttribute('srcset'); }}
                    alt={pageData.titolo}
                    className="w-full h-full object-cover"
                    style={{ objectPosition: `center ${pageData.banner_y ?? 50}%` }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
                <div className="absolute bottom-0 left-0 p-4 md:p-8 text-white">
                    <h1 className="wiki-hero-brand text-2xl md:text-4xl drop-shadow-lg normal-case tracking-normal">{pageData.titolo}</h1>
                </div>
            </div>
        )}

        <article className="p-6 md:p-10 wiki-article-prose">
            {!pageData.immagine && (
                <h1 className="text-3xl md:text-4xl font-bold mb-8 text-[var(--wiki-brand)] border-b border-stone-300 pb-4">
                    {pageData.titolo}
                </h1>
            )}
            
            <WikiRenderer content={pageData.contenuto} glossaryEntries={wikiGlossary} />
        </article>

        {isEditorOpen && (
            <WikiPageEditorModal 
                initialData={pageData}
                onClose={() => setEditorOpen(false)}
                onSuccess={handleEditSuccess}
            />
        )}
    </div>
  );
}
