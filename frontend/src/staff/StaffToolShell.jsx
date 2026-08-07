import React from 'react';

/**
 * Shell layout unificato per i tool della dashboard staff.
 * Il main di StaffDashboard è p-0: lo shell fornisce padding e tipografia coerenti.
 *
 * fill=true → colonna full-height con body scrollabile (scommesse, personaggi, …)
 */

export const staffPageTitleClass = 'text-xl font-bold text-white tracking-tight';
export const staffMutedClass = 'text-sm text-gray-400';
export const staffPanelClass =
  'rounded-xl border border-gray-700 bg-gray-900/60 p-4';
export const staffPrimaryBtnClass =
  'inline-flex items-center gap-1.5 rounded-lg bg-violet-700 hover:bg-violet-600 px-3 py-1.5 text-sm font-bold text-white transition-colors';
export const staffSecondaryBtnClass =
  'inline-flex items-center gap-1.5 rounded-lg border border-gray-600 bg-gray-800 hover:bg-gray-700 px-3 py-1.5 text-sm font-semibold text-gray-200 transition-colors';
export const staffDangerBtnClass =
  'inline-flex items-center gap-1.5 rounded-lg bg-red-900/80 hover:bg-red-800 px-3 py-1.5 text-sm font-bold text-red-100 transition-colors';

export function StaffToolShell({
  children,
  className = '',
  fill = false,
  maxWidth = 'full',
}) {
  const maxCls =
    maxWidth === '4xl'
      ? 'max-w-4xl mx-auto'
      : maxWidth === '6xl'
        ? 'max-w-6xl mx-auto'
        : maxWidth === '3xl'
          ? 'max-w-3xl mx-auto'
          : '';

  if (fill) {
    return (
      <div
        className={`flex h-full min-h-0 flex-col bg-gray-900 text-gray-100 ${className}`}
      >
        {children}
      </div>
    );
  }

  return (
    <div className={`p-4 md:p-6 text-gray-100 ${maxCls} ${className}`.trim()}>
      {children}
    </div>
  );
}

/**
 * Header sticky per tool con sub-nav (fill mode) o header pagina standard.
 */
export function StaffToolHeader({
  title,
  description,
  icon,
  actions,
  onBackToList,
  backLabel = 'Torna alla lista',
  sticky = false,
  children,
}) {
  return (
    <div
      className={[
        'border-b border-gray-700 bg-gray-800/95 px-4 py-3',
        sticky ? 'sticky top-0 z-20 backdrop-blur-sm' : '',
      ]
        .filter(Boolean)
        .join(' ')}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3">
          {onBackToList ? (
            <button
              type="button"
              onClick={onBackToList}
              className="shrink-0 text-sm text-indigo-400 hover:text-indigo-300 hover:underline"
            >
              ← {backLabel}
            </button>
          ) : null}
          {icon ? <span className="shrink-0 text-violet-400">{icon}</span> : null}
          <div className="min-w-0">
            <h1 className={staffPageTitleClass}>{title}</h1>
            {description ? <p className={`mt-0.5 ${staffMutedClass}`}>{description}</p> : null}
          </div>
        </div>
        {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
      </div>
      {children}
    </div>
  );
}

/**
 * Sub-nav a pill coerente tra Scommesse / Carte / Personaggi / …
 * tabs: [{ id, label }] oppure array di stringhe
 */
export function StaffToolSubnav({ tabs, active, onChange, className = '' }) {
  const normalized = (tabs || []).map((t) =>
    typeof t === 'string' ? { id: t, label: t } : t
  );
  return (
    <div className={`mt-3 flex flex-wrap gap-2 ${className}`}>
      {normalized.map((t) => {
        const isActive = active === t.id;
        return (
          <button
            key={t.id}
            type="button"
            onClick={() => onChange?.(t.id)}
            className={`rounded-lg px-3 py-1.5 text-xs font-bold uppercase tracking-wide transition-colors ${
              isActive
                ? 'bg-indigo-600 text-white'
                : 'bg-gray-700 text-gray-300 hover:bg-gray-600'
            }`}
          >
            {t.label}
          </button>
        );
      })}
    </div>
  );
}

/**
 * Body scrollabile sotto header sticky (usare con StaffToolShell fill).
 */
export function StaffToolBody({ children, className = '' }) {
  return (
    <div className={`flex-1 min-h-0 overflow-y-auto p-4 md:p-6 ${className}`}>
      {children}
    </div>
  );
}

/**
 * Header pagina non-sticky (settings / form / list page).
 */
export function StaffToolPageTitle({ icon, title, description, actions, className = '' }) {
  return (
    <div className={`mb-5 flex flex-wrap items-start justify-between gap-3 ${className}`}>
      <div className="flex min-w-0 items-start gap-3">
        {icon ? <span className="mt-0.5 shrink-0 text-violet-400">{icon}</span> : null}
        <div className="min-w-0">
          <h2 className={staffPageTitleClass}>{title}</h2>
          {description ? <p className={`mt-0.5 ${staffMutedClass}`}>{description}</p> : null}
        </div>
      </div>
      {actions ? <div className="flex flex-wrap items-center gap-2 shrink-0">{actions}</div> : null}
    </div>
  );
}

export default StaffToolShell;
