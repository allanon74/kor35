import React, { useLayoutEffect } from 'react';
import { createPortal } from 'react-dom';

/**
 * Shell layout unificato per i tool della dashboard staff.
 * Il main di StaffDashboard è p-0: lo shell fornisce padding e tipografia coerenti.
 *
 * fill=true → colonna full-height con body scrollabile (scommesse, personaggi, …)
 *
 * Responsive (obbligatorio): ogni tool deve funzionare sia su PC (≥lg) sia su telefono.
 * Vedi `.cursor/rules/responsive-ui.mdc` e `.cursorrules` §3.
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

/**
 * Backdrop overlay staff/mobile-safe:
 * scroll sul backdrop + sheet dal basso su telefono (evita modali centrati tagliati).
 */
export const staffModalBackdropClass =
  'fixed inset-0 z-[100] overflow-y-auto overscroll-contain bg-black/80 backdrop-blur-sm';
export const staffModalCenterClass =
  'flex min-h-full items-end sm:items-center justify-center p-0 sm:p-4';
export const staffModalPanelClass =
  'w-full max-h-[min(94vh,100dvh)] overflow-y-auto rounded-t-2xl sm:rounded-xl border border-gray-600 bg-gray-900 shadow-2xl min-w-0';

/**
 * Dopo lista lunga → edit: il main staff resta scrollato e l'editor "finisce fuori schermo".
 * Chiamare all'apertura di editor/modali (StaffEditorHeader / StaffEditorModal lo fanno già).
 */
export function scrollStaffMainToTop() {
  if (typeof document === 'undefined') return;
  const main = document.querySelector('[data-staff-main]');
  if (main) {
    main.scrollTop = 0;
  }
  document.querySelectorAll('main.overflow-y-auto').forEach((el) => {
    el.scrollTop = 0;
  });
  document.querySelectorAll('[data-staff-fullscreen-scroll]').forEach((el) => {
    el.scrollTop = 0;
  });
  if (typeof window !== 'undefined') {
    window.scrollTo(0, 0);
  }
}

/**
 * Editor catalogo a schermo intero (portal su body).
 * Su telefono evita che Infusioni/Tessiture/… restino imprigionati nello scroll del main staff.
 */
export function StaffFullscreenEditor({
  open = true,
  onBack,
  backLabel = 'Torna alla lista',
  subHeader = null,
  children,
  className = '',
}) {
  useLayoutEffect(() => {
    if (!open) return undefined;
    scrollStaffMainToTop();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => {
      document.body.style.overflow = previousOverflow;
    };
  }, [open]);

  if (!open || typeof document === 'undefined') return null;

  return createPortal(
    <div
      data-testid="staff-fullscreen-editor"
      className={`fixed inset-0 z-[110] flex flex-col bg-gray-950 text-gray-100 ${className}`.trim()}
      style={{ height: '100dvh', maxHeight: '100dvh' }}
      role="dialog"
      aria-modal="true"
    >
      {onBack ? (
        <div className="shrink-0 flex items-center gap-2 border-b border-gray-800 bg-gray-950/95 px-3 py-2 pt-[max(0.5rem,var(--kor-safe-top))]">
          <button
            type="button"
            onClick={onBack}
            className="min-h-11 px-3 rounded-lg text-sm font-bold text-amber-400 hover:text-amber-300 hover:bg-amber-500/10"
          >
            ← {backLabel}
          </button>
        </div>
      ) : null}
      {subHeader ? (
        <div className="shrink-0 min-w-0 border-b border-gray-800 bg-gray-950">
          {subHeader}
        </div>
      ) : null}
      <div
        data-staff-fullscreen-scroll
        className="flex-1 min-h-0 min-w-0 overflow-y-auto overflow-x-hidden overscroll-contain px-2 sm:px-4 py-3"
      >
        {children}
      </div>
    </div>,
    document.body,
  );
}

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
    <div className={`min-w-0 p-2 sm:p-4 md:p-6 text-gray-100 ${maxCls} ${className}`.trim()}>
      {children}
    </div>
  );
}

/** Pannello form staff: niente max-height interno (su telefono combatte con lo scroll della dashboard). */
export const staffEditorShellClass =
  'bg-gray-800 p-3 sm:p-5 lg:p-6 rounded-xl space-y-4 sm:space-y-6 mx-auto min-w-0 w-full max-w-full overflow-x-hidden text-white shadow-2xl border border-gray-700 pb-40 lg:pb-6';

/**
 * Header editor: su telefono solo il titolo; Salva/Annulla restano in barra fissa in basso
 * (portale su document.body: evita clipping da overflow/transform degli antenati staff).
 * Su desktop titolo e azioni restano sulla stessa riga.
 * All'apertura riporta lo scroll del main staff in cima (lista → edit).
 */
export function StaffEditorHeader({
  title,
  titleClassName = 'text-indigo-400',
  actions,
  sticky = false,
}) {
  useLayoutEffect(() => {
    scrollStaffMainToTop();
  }, []);

  const mobileFooter =
    actions && typeof document !== 'undefined'
      ? createPortal(
          <div
            data-testid="staff-editor-mobile-footer"
            className="lg:hidden fixed inset-x-0 bottom-0 z-[130] border-t border-gray-700 bg-gray-950/95 px-3 pt-2 backdrop-blur-sm pb-[max(0.75rem,var(--kor-safe-bottom))]"
          >
            {actions}
          </div>,
          document.body,
        )
      : null;

  return (
    <>
      <div
        data-staff-editor-header
        className={[
          'flex min-w-0 flex-col gap-3 border-b border-gray-700 pb-4 lg:flex-row lg:items-start lg:justify-between',
          sticky ? 'sticky top-0 z-10 bg-gray-800 pt-1' : '',
        ]
          .filter(Boolean)
          .join(' ')}
      >
        <h2 className={`min-w-0 break-words text-lg font-bold uppercase tracking-tighter sm:text-xl ${titleClassName}`}>
          {title}
        </h2>
        <div className="hidden min-w-0 lg:block lg:w-auto lg:shrink-0">{actions}</div>
      </div>
      {mobileFooter}
    </>
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
