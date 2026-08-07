import React from 'react';

/**
 * Shell layout unificato per le tab giocatore (personaggi / play).
 *
 * width:
 *  - sheet  → scheda PG (Home)
 *  - wide   → liste tecniche / inventari
 *  - narrow → contenuto centrato stretto
 *  - full   → full-bleed con padding standard
 *  - hud    → Game / HUD densi (padding ridotto)
 */

const WIDTH_CLASS = {
  sheet: 'max-w-4xl',
  wide: 'max-w-6xl',
  narrow: 'max-w-3xl',
  full: 'max-w-none',
  hud: 'max-w-none',
};

const PAD_CLASS = {
  sheet: 'px-4 py-4',
  wide: 'px-4 py-4',
  narrow: 'px-4 py-4',
  full: 'px-4 py-4',
  hud: 'px-2 pt-2',
};

export function PlayerTabShell({
  children,
  width = 'wide',
  className = '',
  safeBottom = true,
  animate = false,
}) {
  const widthCls = WIDTH_CLASS[width] || WIDTH_CLASS.wide;
  const padCls = PAD_CLASS[width] || PAD_CLASS.wide;
  return (
    <div
      className={[
        'w-full mx-auto text-gray-100',
        padCls,
        widthCls,
        safeBottom ? 'pb-safe-tab' : '',
        animate ? 'animate-fadeIn' : '',
        className,
      ]
        .filter(Boolean)
        .join(' ')}
    >
      {children}
    </div>
  );
}

/**
 * Titolo pagina tab: icona + titolo + sottotitolo + azioni a destra.
 */
export function PlayerTabHeader({ icon, title, subtitle, actions, className = '' }) {
  return (
    <header
      className={`mb-5 flex flex-wrap items-start justify-between gap-3 ${className}`}
    >
      <div className="min-w-0 flex items-start gap-2">
        {icon ? <span className="mt-0.5 shrink-0 text-indigo-400">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-white tracking-tight">{title}</h2>
          {subtitle ? (
            <p className="mt-0.5 text-sm text-gray-400 leading-snug">{subtitle}</p>
          ) : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
    </header>
  );
}

/**
 * Strip risorse (PC / CR / custom) usata da Abilità, Tessiture, Infusioni, …
 */
export function PlayerResourceStrip({ children, className = '' }) {
  return (
    <div
      className={`mb-5 flex justify-between items-center bg-gray-800 p-3 rounded-lg border border-gray-700 shadow-sm max-w-3xl mx-auto ${className}`}
    >
      {children}
    </div>
  );
}

/**
 * Contenuto lista/tecnica ristretto al centro sotto lo shell wide.
 */
export function PlayerContentNarrow({ children, className = '' }) {
  return <div className={`max-w-3xl mx-auto ${className}`}>{children}</div>;
}

export default PlayerTabShell;
