/**
 * Deep-link SSO Arcana Domine nella shell Capacitor.
 * Se il flusso OAuth finisce su Chrome, un intent https://…/login?arcana_ticket=…
 * (o kor35://login?…) può riaprire l'app; qui portiamo la WebView su quell'URL.
 */
import { App } from '@capacitor/app';
import { isNativeApp } from './nativePlatform';

let started = false;
let removeListener = null;

function loginUrlFromAppOpen(url) {
  if (!url || typeof url !== 'string') return null;
  try {
    if (url.startsWith('kor35://')) {
      const u = new URL(url.replace('kor35://', 'https://kor35.local/'));
      const ticket = u.searchParams.get('arcana_ticket');
      const err = u.searchParams.get('arcana_error');
      if (!ticket && !err) return null;
      const q = new URLSearchParams();
      if (ticket) q.set('arcana_ticket', ticket);
      if (err) q.set('arcana_error', err);
      return `/login?${q.toString()}`;
    }
    const u = new URL(url);
    if (!u.pathname.startsWith('/login')) return null;
    if (!u.searchParams.get('arcana_ticket') && !u.searchParams.get('arcana_error')) {
      return null;
    }
    return `${u.pathname}${u.search}`;
  } catch {
    return null;
  }
}

function navigateToLogin(pathWithQuery) {
  if (typeof window === 'undefined' || !pathWithQuery) return;
  const target = pathWithQuery.startsWith('/') ? pathWithQuery : `/${pathWithQuery}`;
  if (`${window.location.pathname}${window.location.search}` === target) return;
  window.location.assign(target);
}

/**
 * @returns {Promise<() => void>}
 */
export async function startNativeArcanaSsoBridge() {
  if (typeof window === 'undefined') return () => {};
  if (started) return () => stopNativeArcanaSsoBridge();
  started = true;

  if (!isNativeApp()) {
    return () => stopNativeArcanaSsoBridge();
  }

  try {
    const launch = await App.getLaunchUrl();
    const fromLaunch = loginUrlFromAppOpen(launch?.url);
    if (fromLaunch) navigateToLogin(fromLaunch);
  } catch {
    /* plugin non pronto */
  }

  const handle = await App.addListener('appUrlOpen', (event) => {
    const path = loginUrlFromAppOpen(event?.url);
    if (path) navigateToLogin(path);
  });
  removeListener = () => {
    handle.remove().catch(() => {});
  };

  return () => stopNativeArcanaSsoBridge();
}

export function stopNativeArcanaSsoBridge() {
  if (removeListener) {
    try {
      removeListener();
    } catch {
      /* ignore */
    }
  }
  removeListener = null;
  started = false;
}

/** Solo test */
export const _test = { loginUrlFromAppOpen };
