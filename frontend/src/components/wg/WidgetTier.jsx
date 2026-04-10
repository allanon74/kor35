import React, { useEffect, useState } from 'react';
import { getWikiTier } from '../../api';
import AbilitaTable from '../wiki/AbilitaTable';
import { CHROMATIC_STYLES } from '../../utils/chromaticStyles';

/** Costruisce la stringa CSS per il gradiente (135deg) da una lista di colori hex */
function gradientStyle(colors) {
  if (!Array.isArray(colors) || colors.length === 0) return null;
  const list = colors.filter(c => c && String(c).trim());
  if (list.length === 0) return null;
  if (list.length === 1) return list[0];
  return `linear-gradient(135deg, ${list.join(', ')})`;
}

/** Ritorna true se il colore (hex) è "scuro" in base alla luminanza approssimata */
function isColorDark(hex) {
  if (!hex) return false;
  const clean = String(hex).trim().replace('#', '');
  if (clean.length !== 6) return false;
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);
  // luminanza percettiva semplice
  const luminance = 0.299 * r + 0.587 * g + 0.114 * b;
  return luminance < 150; // soglia empirica: <150 consideriamo sfondo scuro
}

/** Valuta l'insieme dei colori del gradiente per decidere se il risultato è "scuro" */
function isGradientDark(colors) {
  if (!Array.isArray(colors) || colors.length === 0) return false;
  const valid = colors
    .map(c => String(c).trim())
    .filter(c => c);
  if (valid.length === 0) return false;
  const darkCount = valid.filter(isColorDark).length;
  // Se la maggioranza dei colori è scura, consideriamo il gradiente scuro
  return darkCount >= valid.length / 2;
}

export default function WidgetTier({ id }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isAbilitiesOpen, setIsAbilitiesOpen] = useState(false);

  useEffect(() => {
    getWikiTier(id)
       .then(res => setData(res))
       .catch(err => {
         console.error(`Errore caricamento Tier #${id}:`, err);
         setError(true);
       });
  }, [id]);

  useEffect(() => {
    if (!data) return;
    setIsAbilitiesOpen(data.abilities_collapsed_by_default === false);
  }, [data]);

  if (error) return <div className="text-red-500 text-xs border border-red-300 p-2 rounded bg-red-50">Tier #{id} non disponibile.</div>;
  if (!data) return <div className="animate-pulse h-20 bg-gray-200 rounded my-4"></div>;

  const sortedList = [...(data.abilita || [])].sort((a, b) => 
    (a.nome || '').localeCompare(b.nome || '')
  );

  const soloLista = data?.abilities_solo_list === true;

  const gradientColors = Array.isArray(data.gradient_colors) ? data.gradient_colors : [];
  const useGradient = gradientColors.length > 0;
  const gradientBg = useGradient ? gradientStyle(gradientColors) : null;
  const style = CHROMATIC_STYLES[data.color_style] || CHROMATIC_STYLES.default;

  const gradientIsDark = useGradient ? isGradientDark(gradientColors) : false;
  const gradientHeaderTextColor = gradientIsDark ? '#ffffff' : '#111827';

  const headerStyle = gradientBg
    ? { background: gradientBg, color: gradientHeaderTextColor }
    : { background: style.headerBgColor, color: style.headerTextColor };
  const headerClass = 'p-3 md:p-4 flex flex-row justify-between items-center gap-2 rounded-t-lg';

  const bodyStyle = gradientBg ? undefined : { color: style.bodyTextColor };
  const bodyClass = gradientBg
    ? 'w-full p-2 text-gray-800 bg-gray-50'
    : `w-full bg-gradient-to-b ${style.bg} ${style.text} p-2`;

  const borderClass = gradientBg ? 'border-gray-300' : style.border;
  const descStyle = gradientBg ? undefined : { color: style.bodyTextColor };
  const descClass = gradientBg
    ? 'p-3 md:p-4 text-xs md:text-sm border-b border-gray-200 italic prose prose-sm max-w-none wrap-break-words text-gray-800 bg-gray-50'
    : `p-3 md:p-4 bg-gradient-to-b ${style.bg} ${style.text} text-xs md:text-sm border-b ${style.border} italic prose prose-sm max-w-none wrap-break-words`;

  return (
    <div className={`wiki-widget-tier my-6 w-full max-w-full border ${borderClass} rounded-lg bg-white shadow-sm break-inside-avoid overflow-hidden`}>
        {/* HEADER DEL TIER: stili inline per contrasto (chiaro su scuro, scuro su chiaro) e per evitare override da .prose */}
        <div className={`wiki-widget-tier__header ${headerClass}`} style={headerStyle}>
            <div className="flex flex-col">
                <h3 className="text-base md:text-xl font-bold uppercase tracking-wider leading-tight">{data.nome}</h3>
                {data.costo && (
                  <span className="text-[10px] md:text-xs opacity-80 px-2 py-0.5 rounded mt-1 self-start bg-black/20">
                    Costo Base: {data.costo}
                  </span>
                )}
            </div>
            <div className="text-xl md:text-2xl opacity-20 select-none">📊</div>
        </div>

        {/* DESCRIZIONE TIER */}
        {data.descrizione && (
            <div
              className={descClass}
              style={descStyle}
              dangerouslySetInnerHTML={{ __html: data.descrizione }}
            />
        )}

        {/* GRIGLIA ABILITÀ: collapsible se data.abilities_collapsible, aperto/chiuso da data.abilities_collapsed_by_default */}
        {data.abilities_collapsible !== false ? (
          <details
            className={bodyClass}
            style={bodyStyle}
            open={isAbilitiesOpen}
            onToggle={(e) => setIsAbilitiesOpen(e.currentTarget.open)}
          >
            <summary className="cursor-pointer font-semibold py-2 px-3 list-none flex items-center gap-2 [&::-webkit-details-marker]:hidden">
              <span>Abilità</span>
              <em className="font-normal text-xs opacity-80">
                {isAbilitiesOpen ? '(clicca qui per nascondere)' : '(clicca qui per espandere)'}
              </em>
            </summary>
            <div className="pt-0 px-2 pb-2">
              <AbilitaTable
                list={sortedList}
                soloList={soloLista}
                chromaticStyle={
                  gradientBg
                    ? { 
                        ...style, 
                        text: gradientIsDark ? 'text-gray-100' : 'text-gray-800',
                        icon: gradientIsDark ? 'bg-gray-200' : 'bg-gray-500',
                        headerStyle: { background: gradientBg, color: gradientHeaderTextColor }
                      }
                    : style
                }
              />
            </div>
          </details>
        ) : (
          <div className={bodyClass} style={bodyStyle}>
            <AbilitaTable
              list={sortedList}
              soloList={soloLista}
              chromaticStyle={
                gradientBg
                  ? { 
                      ...style, 
                      text: gradientIsDark ? 'text-gray-100' : 'text-gray-800',
                      icon: gradientIsDark ? 'bg-gray-200' : 'bg-gray-500',
                      headerStyle: { background: gradientBg, color: gradientHeaderTextColor }
                    }
                  : style
              }
            />
          </div>
        )}
    </div>
  );
}