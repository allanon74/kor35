import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, LogIn, Scroll, BookOpen, Download } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { getMediaUrl, getPublicWikiManualeList, getWikiManualeLatestPdfUrl } from '../api';
import WidgetChiSiamo from './wg/WidgetChiSiamo';
import WidgetEventi from './wg/WidgetEventi';
import WidgetSocial from './wg/WidgetSocial';

/**
 * HomePage - Layout speciale per la pagina home della Wiki
 * Mostra un layout a griglia con pulsanti e widget personalizzati
 */
export default function HomePage({ pageData, siteConfig }) {
  const navigate = useNavigate();
  const { character, isAdmin } = useCharacter();
  const [wikiManuale, setWikiManuale] = useState([]);
  const isLogged = !!character;

  useEffect(() => {
    let cancelled = false;
    getPublicWikiManualeList()
      .then((data) => {
        if (!cancelled && Array.isArray(data)) {
          setWikiManuale(data.filter((m) => m.ultimo_generato_at && m.download_url));
        }
      })
      .catch(() => {});
    return () => { cancelled = true; };
  }, []);
  const isMaintenanceMode = !!siteConfig?.maintenance_mode;
  const maintenanceMessage = String(siteConfig?.maintenance_public_message || '').trim();

  // Gestisce il click sul pulsante "Veterano"
  const handleVeteranoClick = () => {
    if (isLogged) {
      // Se già loggato, vai alla sezione app
      navigate('/app');
    } else {
      // Altrimenti vai al login
      navigate('/login');
    }
  };

  return (
    <div className="max-w-7xl mx-auto bg-white min-h-screen">
      
      {/* HEADER - Immagine e Titolo (se presenti nei dati della pagina) */}
      {pageData?.immagine && (
        <div className="relative w-full h-64 md:h-80 lg:h-96 overflow-hidden shadow-md">
          <img 
            src={getMediaUrl(pageData.immagine)}
            alt={pageData.titolo}
            className="w-full h-full object-cover"
            style={{ objectPosition: `center ${pageData.banner_y ?? 50}%` }}
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent"></div>
          <div className="absolute bottom-0 left-0 p-6 md:p-10 text-white">
            <h1 className="text-4xl md:text-6xl font-bold drop-shadow-lg">{pageData.titolo}</h1>
          </div>
        </div>
      )}

      <div className="p-6 md:p-10">
        {/* Titolo se non c'è immagine */}
        {!pageData?.immagine && pageData?.titolo && (
          <h1 className="text-4xl md:text-5xl font-bold mb-8 text-red-900 border-b pb-4">
            {pageData.titolo}
          </h1>
        )}

        {/* SEZIONE PULSANTI PRINCIPALI */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          
          {/* Pulsante "Sei Nuovo? Scopri!" */}
          <Link
            to="/regolamento/nuovo"
            className="group relative overflow-hidden bg-gradient-to-br from-indigo-500 to-purple-600 text-white rounded-xl p-6 shadow-lg hover:shadow-2xl transition-all transform hover:scale-105"
          >
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="bg-white/20 p-3 rounded-lg">
                  <Sparkles size={32} />
                </div>
                <h2 className="text-2xl font-bold">Sei Nuovo?</h2>
              </div>
              <p className="text-white/90 mb-2">
                Scopri il mondo di KOR35
              </p>
              <p className="text-sm text-white/75">
                Inizia la tua avventura da qui →
              </p>
            </div>
            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform"></div>
          </Link>

          <button
            onClick={handleVeteranoClick}
            className="group relative overflow-hidden bg-gradient-to-br from-red-600 to-orange-600 text-white rounded-xl p-6 shadow-lg hover:shadow-2xl transition-all transform hover:scale-105 text-left"
          >
            <div className="relative z-10">
              <div className="flex items-center gap-3 mb-3">
                <div className="bg-white/20 p-3 rounded-lg">
                  <LogIn size={32} />
                </div>
                <h2 className="text-2xl font-bold">Veterano?</h2>
              </div>
              <p className="text-white/90 mb-2">
                {isLogged ? 'Accedi alla tua area riservata' : 'Accedi al tuo profilo'}
              </p>
              <p className="text-sm text-white/75">
                {isLogged ? 'Vai all\'app →' : 'Effettua il login →'}
              </p>
            </div>
            <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform"></div>
          </button>

        </div>

        {isMaintenanceMode && (
          <div className="mb-8 rounded-xl border border-amber-500/40 bg-amber-950/30 p-5 text-amber-100">
            <h3 className="text-lg font-black mb-1">Maintenance mode attiva</h3>
            <p className="text-sm opacity-95 mb-3">
              {maintenanceMessage || 'Il sistema e temporaneamente in manutenzione.'}
            </p>
            {isAdmin && (
              <button
                type="button"
                onClick={() => navigate('/app/maintenance')}
                className="px-4 py-2 rounded-lg bg-amber-500 text-gray-900 font-bold hover:bg-amber-400"
              >
                Apri console maintenance
              </button>
            )}
          </div>
        )}

        {/* SEZIONE AMBIENTAZIONE E REGOLAMENTO */}
        <div className="grid md:grid-cols-2 gap-4 mb-8">
          
          {/* Pulsante Ambientazione */}
          <Link
            to="/regolamento/ambientazione"
            className="flex items-center gap-4 p-6 bg-gradient-to-r from-emerald-50 to-teal-50 border-2 border-emerald-200 rounded-lg hover:shadow-lg transition-all group"
          >
            <div className="bg-emerald-500 text-white p-4 rounded-lg group-hover:scale-110 transition-transform">
              <Scroll size={32} />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-gray-800 mb-1">Ambientazione</h3>
              <p className="text-sm text-gray-600">Esplora il mondo e la storia</p>
            </div>
            <svg 
              className="w-6 h-6 text-emerald-500 group-hover:translate-x-1 transition-transform" 
              fill="none" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth="2" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path d="M9 5l7 7-7 7"></path>
            </svg>
          </Link>

          {/* Pulsante Regolamento */}
          <Link
            to="/regolamento/regolamento"
            className="flex items-center gap-4 p-6 bg-gradient-to-r from-blue-50 to-indigo-50 border-2 border-blue-200 rounded-lg hover:shadow-lg transition-all group"
          >
            <div className="bg-blue-500 text-white p-4 rounded-lg group-hover:scale-110 transition-transform">
              <BookOpen size={32} />
            </div>
            <div className="flex-1">
              <h3 className="text-xl font-bold text-gray-800 mb-1">Regolamento</h3>
              <p className="text-sm text-gray-600">Leggi le regole del gioco</p>
            </div>
            <svg 
              className="w-6 h-6 text-blue-500 group-hover:translate-x-1 transition-transform" 
              fill="none" 
              strokeLinecap="round" 
              strokeLinejoin="round" 
              strokeWidth="2" 
              viewBox="0 0 24 24" 
              stroke="currentColor"
            >
              <path d="M9 5l7 7-7 7"></path>
            </svg>
          </Link>
        </div>

        {wikiManuale.length > 0 && (
          <div className="mb-8 space-y-3">
            <h3 className="text-sm font-black uppercase tracking-widest text-gray-500">Manuali PDF</h3>
            <div className="grid gap-3 md:grid-cols-2">
              {wikiManuale.map((m) => (
                <a
                  key={m.slug}
                  href={getWikiManualeLatestPdfUrl(m.slug)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="group relative overflow-hidden bg-gradient-to-r from-red-800 to-rose-900 text-white rounded-xl p-5 shadow-lg hover:shadow-2xl transition-all"
                  title={`Scarica ${m.titolo}`}
                >
                  <div className="relative z-10 flex items-center gap-4">
                    <div className="bg-white/25 p-2.5 rounded-lg shrink-0">
                      <Download size={24} />
                    </div>
                    <div className="min-w-0">
                      <h4 className="text-lg font-black leading-tight">{m.titolo}</h4>
                      {m.sottotitolo && (
                        <p className="text-sm text-white/80 mt-0.5 line-clamp-2">{m.sottotitolo}</p>
                      )}
                    </div>
                    <span className="ml-auto text-xs font-bold text-white/70 group-hover:text-white">PDF →</span>
                  </div>
                </a>
              ))}
            </div>
          </div>
        )}

        {/* SEZIONE WIDGET: CHI SIAMO ED EVENTI */}
        <div className="grid md:grid-cols-2 gap-6 mb-6">
          <WidgetChiSiamo />
          <WidgetEventi />
        </div>

        {/* SEGUICI — larghezza piena sotto Chi Siamo ed Eventi */}
        <WidgetSocial />

        {/* Footer informativo */}
        <div className="mt-10 pt-6 border-t border-gray-200">
          <p className="text-center text-sm text-gray-500 italic">
            Benvenuto su KOR35 - Dove l'avventura prende vita
          </p>
        </div>
      </div>
    </div>
  );
}
