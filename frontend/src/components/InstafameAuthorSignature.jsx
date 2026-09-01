import React from 'react';

/**
 * Firma social del personaggio (banner + testo) sotto post e articoli rubrica.
 */
export default function InstafameAuthorSignature({
  testo = '',
  bannerUrl = null,
  className = '',
  compact = false,
  light = false,
}) {
  const testoPulito = String(testo || '').trim();
  if (!testoPulito && !bannerUrl) return null;

  const borderClass = light ? 'border-gray-200' : 'border-white/10';
  const textClass = light ? 'text-gray-600' : 'text-gray-400';

  return (
    <div className={`mt-3 pt-3 border-t ${borderClass} ${className}`}>
      {bannerUrl ? (
        <img
          src={bannerUrl}
          alt=""
          className={`w-full object-cover rounded-lg mb-2 ${compact ? 'max-h-16' : 'max-h-28'}`}
        />
      ) : null}
      {testoPulito ? (
        <p className={`whitespace-pre-wrap leading-relaxed ${textClass} ${compact ? 'text-xs' : 'text-sm'}`}>
          {testoPulito}
        </p>
      ) : null}
    </div>
  );
}
