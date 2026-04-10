import React, { useState } from 'react';
import IconaPunteggio, { getContrastColor } from './IconaPunteggio';
import { useCharacter } from './CharacterContext';
import ModelloAuraSelectionModal from './ModelloAuraSelectionModal';
import AuraTraitsModal from './AuraTraitsModal'; 
import { AlertTriangle, Crown } from 'lucide-react';

const PunteggioDisplay = ({ 
  punteggio, 
  value, 
  displayText = "abbr", 
  iconType = "inv_circle", 
  size = "m",
  className = "",
  readOnly = false, // <--- NUOVA PROP
  shadow = true,
  roundedClass = "rounded-lg",
}) => {
  // Safe destructuring nel caso useCharacter ritorni null (ospiti) o loading
  const context = useCharacter();
  const selectedCharacterData = context?.selectedCharacterData || null;
  const refreshCharacterData = context?.refreshCharacterData || (() => {});

  const [showModal, setShowModal] = useState(false);
  const [showTraitsModal, setShowTraitsModal] = useState(false);
  
  if (!punteggio || !punteggio.colore) {
    // Fallback elegante se mancano i dati (es. backend non manda l'oggetto completo)
    return (
      <div className={`flex items-center gap-1 p-1 bg-gray-200 rounded border border-gray-300 ${className}`}>
        {punteggio?.sigla && <span className="text-[10px] font-bold text-gray-500">{punteggio.sigla}</span>}
        <span className="text-[10px] font-semibold text-gray-400">N/A</span>
      </div>
    );
  }

  const textColor = getContrastColor(punteggio.colore);
  
  let iconMode = 'cerchio_inv';
  if (iconType === 'circle') iconMode = 'cerchio';
  if (iconType === 'raw') iconMode = 'raw'; 
  if (iconType === 'inv_circle') iconMode = 'cerchio_inv'; 
  if (iconType === 'none') iconMode = null;

  let textToShow = "";
  if (displayText === "abbr") {
    textToShow = punteggio.sigla ? punteggio.sigla.toUpperCase() : punteggio.nome;
  } else if (displayText === "name") {
    textToShow = punteggio.nome;
  }

  // Configurazione dimensioni (ho aggiunto 'badge' per uso in tabelle)
  const layoutConfig = {
    badge: { gap: 'gap-1', text: 'text-[9px]', val: 'hidden', p: 'p-0.5 px-1.5' }, // Compatto per badge
    xs: { gap: 'gap-1',    text: 'text-[9px]',     val: 'text-[10px]', p: 'p-0.5' },
    s:  { gap: 'gap-1.5',  text: 'text-[11px]',    val: 'text-xs',     p: 'p-1' },
    m:  { gap: 'gap-2.5',  text: 'text-sm',        val: 'text-lg',     p: 'p-1.5' },
    l:  { gap: 'gap-3.5',  text: 'text-base',      val: 'text-2xl',    p: 'p-2.5' },
    xl: { gap: 'gap-4',    text: 'text-xl',        val: 'text-4xl',    p: 'p-4' },
  };
  
  const layout = layoutConfig[size] || layoutConfig.m;
  const url = punteggio.icona_url || punteggio.icona;

  // --- LOGICA INTERATTIVA (Disabilitata se readOnly) ---
  const isAura = punteggio.tipo === 'AU';
  const hasModelsAvailable = punteggio.has_models;
  const userValue = parseInt(value) || 0;
  
  const selectedModelName = !readOnly && isAura && selectedCharacterData?.modelli_aura
      ? selectedCharacterData.modelli_aura.find(m => m.aura === punteggio.id)?.nome 
      : null;

  const needsSelection = !readOnly && isAura && userValue > 0 && hasModelsAvailable && !selectedModelName;
  // Aura innata (AIN): scelta razza solo dalla sezione dedicata in scheda, non dal tile aura
  const isAuraInnata = String(punteggio.sigla || '').toUpperCase() === 'AIN';
  const hasTraitsConfig =
    !readOnly &&
    !isAuraInnata &&
    punteggio.configurazione_livelli &&
    punteggio.configurazione_livelli.length > 0;

  const handleContainerClick = () => {
    if (readOnly) return;
    if (hasTraitsConfig) setShowTraitsModal(true);
  };

  return (
    <>
        <div 
          className={`flex items-center justify-between ${roundedClass} ${shadow ? 'shadow-sm' : ''} transition-all ${layout.p} ${className} 
            ${hasTraitsConfig ? 'cursor-pointer hover:brightness-110 relative group' : ''}
            ${readOnly ? 'cursor-default' : ''}`} 
          style={{ backgroundColor: punteggio.colore }}
          onClick={handleContainerClick}
        >
          <div className={`flex items-center ${layout.gap} min-w-0`}> 
            
            <div className="relative">
                {iconMode && url && (
                  <IconaPunteggio 
                    url={url} 
                    color={punteggio.colore} 
                    mode={iconMode} 
                    size={size === 'badge' ? 'xs' : size} // Badge usa icone piccole
                    className="shrink-0" 
                  />
                )}
                {hasTraitsConfig && (
                    <div className="absolute -top-1 -right-1 bg-amber-500 rounded-full p-0.5 border border-black/50 shadow-sm">
                        <Crown size={8} className="text-white" fill="currentColor" />
                    </div>
                )}
            </div>
            
            <div className="flex flex-col min-w-0 justify-center">
                {textToShow && (
                  <span 
                    className={`font-bold uppercase tracking-wider ${layout.text} truncate whitespace-nowrap leading-tight`} 
                    style={{ color: textColor }}
                  >
                    {textToShow}
                  </span>
                )}

                {needsSelection && (
                    <button
                        onClick={(e) => { e.stopPropagation(); setShowModal(true); }}
                        className="mt-0.5 flex items-center gap-1 text-[10px] bg-red-600 text-white px-1.5 py-0.5 rounded animate-pulse hover:bg-red-500 font-bold uppercase tracking-wider border border-white/20 shadow-sm w-max"
                    >
                        <AlertTriangle size={10} /> Scegli!
                    </button>
                )}

                {selectedModelName && (
                    <span 
                        className="text-[10px] opacity-90 font-mono uppercase tracking-tight block leading-none mt-0.5" 
                        style={{ color: textColor }}
                    >
                        {selectedModelName}
                    </span>
                )}
            </div>
          </div>
          
          {/* Valore numerico (nascosto se size='badge' o value è null) */}
          {value !== null && value !== undefined && layout.val !== 'hidden' && (
            <span 
              className={`font-bold font-mono ${layout.val} shrink-0 ml-2 whitespace-nowrap`} 
              style={{ color: textColor }}
            >
              {value}
            </span>
          )}
        </div>

        {showModal && (
            <ModelloAuraSelectionModal 
                aura={punteggio} 
                onClose={() => setShowModal(false)} 
            />
        )}

        {showTraitsModal && (
            <AuraTraitsModal 
                aura={punteggio}
                personaggio={selectedCharacterData}
                currentValue={userValue} 
                onClose={() => setShowTraitsModal(false)}
                onUpdateCharacter={refreshCharacterData} 
            />
        )}
    </>
  );
};

export default PunteggioDisplay;