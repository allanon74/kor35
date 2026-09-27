/** Viewport kiosk 7" 800×480 (Raspberry Pi 4 + touch). */

const QUERY = () => new URLSearchParams(window.location.search);

export function viewportForced800() {
  return QUERY().get('viewport') === '800x480';
}

export function viewportMatches800() {
  if (typeof window === 'undefined' || !window.matchMedia) return false;
  return window.matchMedia('(max-width: 860px) and (max-height: 540px)').matches;
}

export function isCompact800() {
  return viewportForced800() || viewportMatches800();
}

/** Classe sul documento: layout compatto e, su monitor grandi, cornice 800×480. */
export function applyViewportClass() {
  const root = document.documentElement;
  const forced = viewportForced800();
  const compact = forced || viewportMatches800();
  root.classList.toggle('viewport-800', compact);
  const frame = forced && window.innerWidth >= 900 && window.innerHeight >= 560;
  root.classList.toggle('viewport-800-frame', frame);
  return compact;
}

export function fromStation() {
  return QUERY().get('from') === 'station';
}

/** Navigazione piena: SCREEN_MODE è letto al caricamento della pagina. */
export function navigateScreen(screen) {
  const params = QUERY();
  if (screen === 'station') {
    params.set('screen', 'station');
    params.delete('from');
  } else {
    params.set('screen', screen);
    params.set('from', 'station');
  }
  params.delete('preview');
  params.delete('tab');
  window.location.search = params.toString();
}

export function initialTab(allowed, fallback) {
  const tab = QUERY().get('tab') || '';
  return allowed.includes(tab) ? tab : fallback;
}
