import React, { useEffect, useState } from 'react';
import { Share2, MessageCircle, Instagram, Facebook, Youtube, Mail, Twitter, AlertCircle } from 'lucide-react';
import { getLinkSocial } from '../../api';

/**
 * Widget Social - Mostra i link social dell'associazione dal database
 * I link sono modificabili tramite l'admin Django in "Link Social"
 */
export default function WidgetSocial() {
  const [socialLinks, setSocialLinks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    getLinkSocial()
      .then(res => {
        setSocialLinks(res);
        setLoading(false);
      })
      .catch(err => {
        console.error('Errore caricamento link social:', err);
        setError(true);
        setLoading(false);
      });
  }, []);

  // Mappa dei tipi social alle icone e colori
  const socialConfig = {
    whatsapp: { icon: MessageCircle, color: 'bg-green-500 hover:bg-green-600' },
    instagram: { icon: Instagram, color: 'bg-pink-500 hover:bg-pink-600' },
    facebook: { icon: Facebook, color: 'bg-blue-600 hover:bg-blue-700' },
    youtube: { icon: Youtube, color: 'bg-red-600 hover:bg-red-700' },
    twitter: { icon: Twitter, color: 'bg-sky-500 hover:bg-sky-600' },
    email: { icon: Mail, color: 'bg-gray-600 hover:bg-gray-700' },
    discord: { icon: MessageCircle, color: 'bg-indigo-600 hover:bg-indigo-700' },
    telegram: { icon: MessageCircle, color: 'bg-blue-500 hover:bg-blue-600' },
    altro: { icon: Share2, color: 'bg-gray-500 hover:bg-gray-600' },
  };

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
        <div className="animate-pulse space-y-4">
          <div className="h-6 bg-gray-200 rounded w-1/3"></div>
          <div className="space-y-3">
            <div className="h-16 bg-gray-100 rounded"></div>
            <div className="h-16 bg-gray-100 rounded"></div>
            <div className="h-16 bg-gray-100 rounded"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6 border border-red-200">
        <div className="flex items-center gap-3 text-red-600">
          <AlertCircle size={24} />
          <p>Errore nel caricamento dei link social</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200">
      <div className="flex items-center gap-3 mb-4 pb-3 border-b border-gray-200">
        <Share2 className="text-red-700" size={28} />
        <h3 className="text-xl font-bold text-gray-800">Seguici</h3>
      </div>
      
      {socialLinks.length === 0 ? (
        <div className="text-center py-8 text-gray-500">
          <Share2 size={48} className="mx-auto mb-3 text-gray-300" />
          <p className="font-medium">Nessun link social configurato</p>
          <p className="text-sm mt-1">Aggiungi i link tramite l'admin Django</p>
        </div>
      ) : (
        <div className="space-y-3">
          <p className="text-sm text-gray-600 mb-4">
            Resta aggiornato sulle nostre attività e unisciti alla community!
          </p>
          
          <div className="grid gap-3">
            {socialLinks.map((social) => {
              const config = socialConfig[social.tipo] || socialConfig['altro'];
              const IconComponent = config.icon;
              const isEmail = social.tipo === 'email';
              
              return (
                <a
                  key={social.id}
                  href={social.url}
                  target={!isEmail ? '_blank' : undefined}
                  rel={!isEmail ? 'noopener noreferrer' : undefined}
                  className={`flex items-center gap-4 p-4 rounded-lg text-white transition-all transform hover:scale-105 shadow-sm hover:shadow-md ${config.color}`}
                >
                  <div className="flex-shrink-0 bg-white/20 p-2 rounded-lg">
                    <IconComponent size={24} />
                  </div>
                  <div className="flex-1">
                    <div className="font-semibold">{social.tipo_display}</div>
                    <div className="text-xs opacity-90">
                      {social.descrizione || social.nome_visualizzato}
                    </div>
                  </div>
                  <svg 
                    className="w-5 h-5 opacity-70" 
                    fill="none" 
                    strokeLinecap="round" 
                    strokeLinejoin="round" 
                    strokeWidth="2" 
                    viewBox="0 0 24 24" 
                    stroke="currentColor"
                  >
                    <path d="M9 5l7 7-7 7"></path>
                  </svg>
                </a>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
