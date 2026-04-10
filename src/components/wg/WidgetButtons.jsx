import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { getWidgetButtons } from '../../api';
import * as LucideIcons from 'lucide-react';

/**
 * Widget Pulsanti Configurabili
 * Renderizza una griglia di pulsanti configurabili con link a pagine wiki o app
 */

// Preset di colori disponibili
const COLOR_PRESETS = {
  indigo_purple: {
    name: 'Indaco-Viola',
    gradient: 'from-indigo-500 to-purple-600',
    border: 'border-indigo-200',
    bg: 'from-indigo-50 to-purple-50',
    icon: 'bg-indigo-500',
    text: 'text-indigo-500'
  },
  red_orange: {
    name: 'Rosso-Arancio',
    gradient: 'from-red-600 to-orange-600',
    border: 'border-red-200',
    bg: 'from-red-50 to-orange-50',
    icon: 'bg-red-500',
    text: 'text-red-500'
  },
  emerald_teal: {
    name: 'Smeraldo-Verde Acqua',
    gradient: 'from-emerald-500 to-teal-600',
    border: 'border-emerald-200',
    bg: 'from-emerald-50 to-teal-50',
    icon: 'bg-emerald-500',
    text: 'text-emerald-500'
  },
  blue_indigo: {
    name: 'Blu-Indaco',
    gradient: 'from-blue-500 to-indigo-600',
    border: 'border-blue-200',
    bg: 'from-blue-50 to-indigo-50',
    icon: 'bg-blue-500',
    text: 'text-blue-500'
  },
  pink_rose: {
    name: 'Rosa-Rosa Intenso',
    gradient: 'from-pink-500 to-rose-600',
    border: 'border-pink-200',
    bg: 'from-pink-50 to-rose-50',
    icon: 'bg-pink-500',
    text: 'text-pink-500'
  },
  amber_orange: {
    name: 'Ambra-Arancio',
    gradient: 'from-amber-500 to-orange-600',
    border: 'border-amber-200',
    bg: 'from-amber-50 to-orange-50',
    icon: 'bg-amber-500',
    text: 'text-amber-500'
  },
  cyan_blue: {
    name: 'Ciano-Blu',
    gradient: 'from-cyan-500 to-blue-600',
    border: 'border-cyan-200',
    bg: 'from-cyan-50 to-blue-50',
    icon: 'bg-cyan-500',
    text: 'text-cyan-500'
  },
  violet_purple: {
    name: 'Viola-Porpora',
    gradient: 'from-violet-500 to-purple-600',
    border: 'border-violet-200',
    bg: 'from-violet-50 to-purple-50',
    icon: 'bg-violet-500',
    text: 'text-violet-500'
  },
  slate_gray: {
    name: 'Ardesia-Grigio',
    gradient: 'from-slate-600 to-gray-700',
    border: 'border-slate-200',
    bg: 'from-slate-50 to-gray-50',
    icon: 'bg-slate-600',
    text: 'text-slate-600'
  },
  lime_green: {
    name: 'Lime-Verde',
    gradient: 'from-lime-500 to-green-600',
    border: 'border-lime-200',
    bg: 'from-lime-50 to-green-50',
    icon: 'bg-lime-500',
    text: 'text-lime-500'
  }
};

// Dimensioni disponibili
const SIZE_PRESETS = {
  small: {
    name: 'Piccolo',
    padding: 'p-4',
    iconSize: 24,
    iconPadding: 'p-3',
    titleSize: 'text-lg',
    descSize: 'text-xs',
    subtextSize: 'text-xs'
  },
  medium: {
    name: 'Medio',
    padding: 'p-5',
    iconSize: 28,
    iconPadding: 'p-3',
    titleSize: 'text-xl',
    descSize: 'text-sm',
    subtextSize: 'text-sm'
  },
  large: {
    name: 'Grande',
    padding: 'p-6',
    iconSize: 32,
    iconPadding: 'p-3',
    titleSize: 'text-2xl',
    descSize: 'text-base',
    subtextSize: 'text-sm'
  }
};

// Stili dei pulsanti
const BUTTON_STYLES = {
  gradient: 'gradient', // Stile grande con gradiente (tipo home top)
  light: 'light'        // Stile più piccolo con sfondo chiaro (tipo home bottom)
};

/**
 * Versione per slot wiki: riceve navigate e usa <a> al posto di <Link>
 * (createRoot monta fuori dal Router, quindi useNavigate/Link non sono disponibili)
 */
export function WidgetButtonsSlot({ id, navigate }) {
  return <WidgetButtonsCore id={id} navigate={navigate} useAnchorLinks={true} />;
}

function WidgetButtonsCore({ id, navigate, useAnchorLinks }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const result = await getWidgetButtons(id);
        setData(result);
      } catch (error) {
        console.error('Errore caricamento widget buttons:', error);
      } finally {
        setLoading(false);
      }
    };

    if (id) fetchData();
  }, [id]);

  if (loading) {
    return (
      <div className="w-full py-8 text-center">
        <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
      </div>
    );
  }

  if (!data || !data.buttons || data.buttons.length === 0) {
    return (
      <div className="text-center text-gray-500 text-sm p-4 bg-gray-50 rounded-lg border border-gray-200">
        Nessun pulsante configurato
      </div>
    );
  }

  const handleButtonClick = (button, e) => {
    if (button.link_type === 'app' && button.app_route && navigate) {
      e.preventDefault();
      navigate(button.app_route);
    }
  };

  const renderButton = (button, index) => {
    const colorPreset = COLOR_PRESETS[button.color_preset] || COLOR_PRESETS.indigo_purple;
    const sizePreset = SIZE_PRESETS[button.size] || SIZE_PRESETS.medium;
    const style = button.style || BUTTON_STYLES.gradient;

    // Recupera l'icona da lucide-react
    const Icon = button.icon && LucideIcons[button.icon] ? LucideIcons[button.icon] : null;

    // Determina il link
    const linkTo = button.link_type === 'wiki' 
      ? `/regolamento/${button.wiki_slug}` 
      : button.app_route || '#';

    // Stile Gradient (tipo pulsanti grandi home)
    if (style === BUTTON_STYLES.gradient) {
      const content = (
        <>
          <div className="relative z-10">
            <div className="flex items-center gap-3 mb-3">
              {Icon && (
                <div className={`bg-white/20 ${sizePreset.iconPadding} rounded-lg`}>
                  <Icon size={sizePreset.iconSize} />
                </div>
              )}
              <h2 className={`${sizePreset.titleSize} font-bold`}>{button.title}</h2>
            </div>
            {button.description && (
              <p className={`text-white/90 mb-2 ${sizePreset.descSize}`}>
                {button.description}
              </p>
            )}
            {button.subtext && (
              <p className={`${sizePreset.subtextSize} text-white/75`}>
                {button.subtext}
              </p>
            )}
          </div>
          <div className="absolute top-0 right-0 w-32 h-32 bg-white opacity-10 rounded-full -mr-16 -mt-16 group-hover:scale-150 transition-transform"></div>
        </>
      );

      const className = `group relative overflow-hidden bg-linear-to-br ${colorPreset.gradient} text-white rounded-xl ${sizePreset.padding} shadow-lg hover:shadow-2xl transition-all transform hover:scale-105`;

      if (button.link_type === 'wiki') {
        if (useAnchorLinks) {
          return (
            <a key={index} href={linkTo} className={className}>
              {content}
            </a>
          );
        }
        return (
          <Link key={index} to={linkTo} className={className}>
            {content}
          </Link>
        );
      } else {
        return (
          <button
            key={index}
            onClick={(e) => handleButtonClick(button, e)}
            className={`${className} text-left w-full`}
          >
            {content}
          </button>
        );
      }
    }

    // Stile Light (tipo pulsanti piccoli home)
    if (style === BUTTON_STYLES.light) {
      const content = (
        <>
          {Icon && (
            <div className={`${colorPreset.icon} text-white ${sizePreset.iconPadding} rounded-lg group-hover:scale-110 transition-transform`}>
              <Icon size={sizePreset.iconSize} />
            </div>
          )}
          <div className="flex-1">
            <h3 className={`${sizePreset.titleSize} font-bold text-gray-800 mb-1`}>
              {button.title}
            </h3>
            {button.description && (
              <p className={`${sizePreset.descSize} text-gray-600`}>
                {button.description}
              </p>
            )}
          </div>
          <svg 
            className={`w-6 h-6 ${colorPreset.text} group-hover:translate-x-1 transition-transform`}
            fill="none" 
            strokeLinecap="round" 
            strokeLinejoin="round" 
            strokeWidth="2" 
            viewBox="0 0 24 24" 
            stroke="currentColor"
          >
            <path d="M9 5l7 7-7 7"></path>
          </svg>
        </>
      );

      const className = `flex items-center gap-4 ${sizePreset.padding} bg-linear-to-r ${colorPreset.bg} border-2 ${colorPreset.border} rounded-lg hover:shadow-lg transition-all group`;

      if (button.link_type === 'wiki') {
        if (useAnchorLinks) {
          return (
            <a key={index} href={linkTo} className={className}>
              {content}
            </a>
          );
        }
        return (
          <Link key={index} to={linkTo} className={className}>
            {content}
          </Link>
        );
      } else {
        return (
          <button
            key={index}
            onClick={(e) => handleButtonClick(button, e)}
            className={`${className} text-left w-full`}
          >
            {content}
          </button>
        );
      }
    }

    return null;
  };

  // Distribuzione dei pulsanti su più righe in modo uniforme
  const buttonsCount = data.buttons.length;
  let columns = 1;
  
  if (buttonsCount === 1) columns = 1;
  else if (buttonsCount === 2) columns = 2;
  else if (buttonsCount === 3) columns = 3;
  else if (buttonsCount === 4) columns = 2;
  else if (buttonsCount === 5) columns = 3;
  else if (buttonsCount === 6) columns = 3;
  else if (buttonsCount >= 7) columns = 3;

  return (
    <div className={`grid md:grid-cols-${columns} gap-4 my-6`}>
      {data.buttons.map((button, index) => renderButton(button, index))}
    </div>
  );
}

export default function WidgetButtons({ id }) {
  const navigate = useNavigate();
  return <WidgetButtonsCore id={id} navigate={navigate} useAnchorLinks={false} />;
}

// Export dei preset per uso in altri componenti (es. modal di configurazione)
export { COLOR_PRESETS, SIZE_PRESETS, BUTTON_STYLES };
