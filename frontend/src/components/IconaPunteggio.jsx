import React from 'react';
import { resolveMediaUrl } from '../api';

// Helper per il contrasto (ROBUSTO: gestisce anche hex a 3 cifre)
export const getContrastColor = (hexColor) => {
  if (!hexColor) return 'white';
  try {
    let hex = hexColor.replace('#', '');
    // Espande la notazione breve (es. "fff" -> "ffffff")
    if (hex.length === 3) {
        hex = hex.split('').map(c => c + c).join('');
    }
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);
    
    // Se il parsing fallisce (NaN), ritorna bianco per sicurezza
    if (isNaN(r) || isNaN(g) || isNaN(b)) return 'white';

    const luminanza = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminanza > 0.5 ? 'black' : 'white';
  } catch (e) {
    return 'white';
  }
};

const IconaPunteggio = ({ url, color = '#000000', mode = 'normal', size = 'm', className = '' }) => {
  if (!url) return null;

  const fullUrl = resolveMediaUrl(url) || url;

  const contrastColor = getContrastColor(color);

  // --- DIMENSIONI INTERMEDIE ---
  const sizeMap = {
    xs: 'w-4.5 h-4.5', // 18px
    s:  'w-7 h-7',     // 28px
    m:  'w-11 h-11',   // 44px
    l:  'w-[4.5rem] h-[4.5rem]', // 72px
    xl: 'w-28 h-28',   // 112px
  };

  const iconSizeMap = {
    xs: 'w-3 h-3',
    s:  'w-4.5 h-4.5',
    m:  'w-7 h-7',
    l:  'w-11 h-11',
    xl: 'w-20 h-20',
  };

  const containerSize = sizeMap[size] || sizeMap.m;
  const iconSize = iconSizeMap[size] || iconSizeMap.m;

  let containerBg = 'transparent';
  let iconFill = color; 
  let borderRadius = '0';
  let isRaw = false;

  if (mode === 'raw') {
      isRaw = true;
  } else if (mode === 'normal') {
      iconFill = color;
  } else if (mode === 'cerchio') {
      containerBg = contrastColor === 'white' ? '#1f2937' : '#f3f4f6';
      iconFill = color;
      borderRadius = '50%';
  } else if (mode === 'cerchio_inv') {
      containerBg = color;
      iconFill = contrastColor; // Qui usa il colore calcolato (Bianco/Nero)
      borderRadius = '50%';
  }

  if (isRaw) {
    return (
      <div className={`flex items-center justify-center shrink-0 ${containerSize} ${className}`}>
         <img 
            src={fullUrl} 
            alt="" 
            className="w-full h-full object-contain"
            onError={(e) => e.target.style.display = 'none'} 
         />
      </div>
    );
  }

  return (
    <div 
      className={`flex items-center justify-center shrink-0 shadow-sm ${containerSize} ${className}`}
      style={{ backgroundColor: containerBg, borderRadius }}
    >
      <div className={`${iconSize} relative overflow-hidden`}>
         <img 
            src={fullUrl} 
            alt="" 
            className="w-full h-full object-contain"
            style={{
               transform: 'translateX(-1000px)',
               filter: `drop-shadow(1000px 0 0 ${iconFill})`
            }}
            onError={(e) => e.target.style.display = 'none'}
         />
      </div>
    </div>
  );
};

export default IconaPunteggio;