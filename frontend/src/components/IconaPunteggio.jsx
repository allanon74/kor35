import React, { useState } from 'react';
import { resolveMediaUrl } from '../api';

// Helper per il contrasto (ROBUSTO: gestisce anche hex a 3 cifre)
export const getContrastColor = (hexColor) => {
  if (!hexColor) return 'white';
  try {
    let hex = hexColor.replace('#', '');
    if (hex.length === 3) {
      hex = hex.split('').map((c) => c + c).join('');
    }
    const r = parseInt(hex.substring(0, 2), 16);
    const g = parseInt(hex.substring(2, 4), 16);
    const b = parseInt(hex.substring(4, 6), 16);

    if (isNaN(r) || isNaN(g) || isNaN(b)) return 'white';

    const luminanza = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
    return luminanza > 0.5 ? 'black' : 'white';
  } catch (e) {
    return 'white';
  }
};

/** SVG icone punteggio: silhouette bianca/nera via filter (come AbilitaTable / WidgetMattoni). */
export const contrastIconFilter = (hexColor) => {
  const contrast = getContrastColor(hexColor);
  return contrast === 'white' ? 'brightness(0) invert(1)' : 'brightness(0)';
};

const FallbackGlyph = ({ text, boxClass, className, color }) => (
  <div
    className={`flex items-center justify-center shrink-0 font-bold uppercase leading-none ${boxClass} ${className}`}
    style={{ color: getContrastColor(color) }}
    aria-hidden="true"
  >
    {String(text || '?').slice(0, 1)}
  </div>
);

const IconaPunteggio = ({
  url,
  color = '#000000',
  mode = 'normal',
  size = 'm',
  className = '',
  fallbackText = '',
}) => {
  const [failed, setFailed] = useState(false);

  const sizeMap = {
    xs: 'w-[18px] h-[18px]',
    s: 'w-7 h-7',
    m: 'w-11 h-11',
    l: 'w-[4.5rem] h-[4.5rem]',
    xl: 'w-28 h-28',
  };

  const iconSizeMap = {
    xs: 'w-[14px] h-[14px]',
    s: 'w-[18px] h-[18px]',
    m: 'w-7 h-7',
    l: 'w-11 h-11',
    xl: 'w-20 h-20',
  };

  const containerSize = sizeMap[size] || sizeMap.m;
  const iconSize = iconSizeMap[size] || iconSizeMap.m;

  if (!url || failed) {
    if (!fallbackText) return null;
    return <FallbackGlyph text={fallbackText} boxClass={containerSize} className={className} color={color} />;
  }

  const fullUrl = resolveMediaUrl(url) || url;
  const contrastFilter = contrastIconFilter(color);

  const renderImg = (imgClass, withContrastFilter = true) => (
    <img
      src={fullUrl}
      alt=""
      className={`object-contain ${imgClass}`}
      style={withContrastFilter ? { filter: contrastFilter } : undefined}
      onError={() => setFailed(true)}
    />
  );

  if (mode === 'raw') {
    return (
      <div className={`flex items-center justify-center shrink-0 ${containerSize} ${className}`}>
        <img
          src={fullUrl}
          alt=""
          className="w-full h-full object-contain"
          onError={() => setFailed(true)}
        />
      </div>
    );
  }

  if (mode === 'glyph' || mode === 'mask' || mode === 'normal') {
    return (
      <div className={`flex items-center justify-center shrink-0 ${containerSize} ${className}`}>
        {renderImg('w-full h-full')}
      </div>
    );
  }

  if (mode === 'cerchio') {
    const containerBg = getContrastColor(color) === 'white' ? '#1f2937' : '#f3f4f6';
    return (
      <div
        className={`flex items-center justify-center shrink-0 shadow-sm ${containerSize} ${className}`}
        style={{ backgroundColor: containerBg, borderRadius: '50%' }}
      >
        {renderImg(`${iconSize}`, false)}
      </div>
    );
  }

  if (mode === 'cerchio_inv') {
    return (
      <div
        className={`flex items-center justify-center shrink-0 shadow-sm ${containerSize} ${className}`}
        style={{ backgroundColor: color, borderRadius: '50%' }}
      >
        {renderImg(iconSize)}
      </div>
    );
  }

  return (
    <div className={`flex items-center justify-center shrink-0 ${containerSize} ${className}`}>
      {renderImg('w-full h-full')}
    </div>
  );
};

export default IconaPunteggio;
