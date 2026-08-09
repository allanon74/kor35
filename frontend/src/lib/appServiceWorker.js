/**
 * Registrazione Service Worker per shell PWA / offline (indipendente dal push).
 */

let registrationPromise = null;

export async function ensureAppServiceWorker() {
  if (typeof window === 'undefined' || !('serviceWorker' in navigator)) {
    return null;
  }
  if (!window.isSecureContext) {
    return null;
  }
  if (!registrationPromise) {
    registrationPromise = (async () => {
      const existing = await navigator.serviceWorker.getRegistration('/');
      if (existing) return existing;
      return navigator.serviceWorker.register('/sw.js', { scope: '/' });
    })().catch((err) => {
      registrationPromise = null;
      console.warn('KOR35 SW registration failed:', err);
      return null;
    });
  }
  return registrationPromise;
}
