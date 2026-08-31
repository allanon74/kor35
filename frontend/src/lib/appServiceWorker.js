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
      if (existing) {
        // Senza update() il browser ricontrolla /sw.js solo ogni ~24h: dopo un deploy
        // la vecchia precache continuerebbe a servire il bundle superato.
        // Sull'edge offline la richiesta fallisce: è previsto, si resta sul worker attivo.
        existing.update().catch(() => {});
        return existing;
      }
      return navigator.serviceWorker.register('/sw.js', {
        scope: '/',
        updateViaCache: 'none',
      });
    })().catch((err) => {
      registrationPromise = null;
      console.warn('KOR35 SW registration failed:', err);
      return null;
    });
  }
  return registrationPromise;
}
