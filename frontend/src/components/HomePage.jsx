import React from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Sparkles, LogIn, Scroll, BookOpen, Users, Calendar, Share2 } from 'lucide-react';
import { useCharacter } from './CharacterContext';
import { getMediaUrl } from '../api';
import WidgetChiSiamo from './wg/WidgetChiSiamo';
import WidgetEventi from './wg/WidgetEventi';
import WidgetSocial from './wg/WidgetSocial';

/**
 * HomePage - Layout speciale per la pagina home della Wiki
 * Mostra un layout a griglia con pulsanti e widget personalizzati
 */
export default function HomePage({ pageData }) {
  const navigate = useNavigate();
  const { character } = useCharacter();
  const isLogged = !!character;

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

          {/* Pulsante "Veterano? Accedi al Profilo" */}
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

        {/* SEZIONE WIDGET: CHI SIAMO, EVENTI, SOCIAL */}
        <div className="grid md:grid-cols-3 gap-6">
          
          {/* Widget Chi Siamo */}
          <div className="md:col-span-1">
            <WidgetChiSiamo />
          </div>

          {/* Widget Eventi */}
          <div className="md:col-span-1">
            <WidgetEventi />
          </div>

          {/* Widget Social */}
          <div className="md:col-span-1">
            <WidgetSocial />
          </div>
        </div>

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
