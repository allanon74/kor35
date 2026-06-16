const VAPID_PUBLIC_KEY =
  'BIOIApSIeJdV1tp5iVxyLtm8KzM43_AQWV2ymS4iMjkIG1R5g399o6WRdZJY-xcUBZPyJ7EFRVgWqlbalOkGSYw';

/** Abilitato di default; imposta VITE_WEBPUSH_ENABLED=false per disattivare. */
export function isWebPushEnabled() {
  return String(import.meta.env.VITE_WEBPUSH_ENABLED ?? 'true').toLowerCase() !== 'false';
}

export function isWebPushSupported() {
  if (!isWebPushEnabled()) return false;
  if (!window.isSecureContext) return false;
  return (
    'serviceWorker' in navigator &&
    'PushManager' in window &&
    'Notification' in window
  );
}

function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, '+').replace(/_/g, '/');
  const rawData = window.atob(base64);
  const outputArray = new Uint8Array(rawData.length);
  for (let i = 0; i < rawData.length; ++i) {
    outputArray[i] = rawData.charCodeAt(i);
  }
  return outputArray;
}

async function ensureServiceWorkerRegistration() {
  const existing = await navigator.serviceWorker.getRegistration('/');
  if (existing) return existing;
  return navigator.serviceWorker.register('/sw.js', { scope: '/' });
}

/**
 * Richiede permesso, registra il service worker e crea/recupera la subscription push.
 * @returns {Promise<{ok: true, subscription: PushSubscription} | {ok: false, reason: string, message?: string}>}
 */
export async function activateWebPush() {
  if (!isWebPushSupported()) {
    if (!window.isSecureContext) {
      return {
        ok: false,
        reason: 'insecure',
        message: 'Le notifiche push richiedono HTTPS (o localhost).',
      };
    }
    return {
      ok: false,
      reason: 'unsupported',
      message: 'Il browser non supporta le notifiche push.',
    };
  }

  const permission = await Notification.requestPermission();
  if (permission !== 'granted') {
    return {
      ok: false,
      reason: permission === 'denied' ? 'denied' : 'dismissed',
      message:
        permission === 'denied'
          ? 'Permesso negato. Abilita le notifiche dalle impostazioni del sito in Chrome.'
          : 'Richiesta annullata.',
    };
  }

  try {
    const registration = await ensureServiceWorkerRegistration();
    await navigator.serviceWorker.ready;

    let subscription = await registration.pushManager.getSubscription();
    if (!subscription) {
      subscription = await registration.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlBase64ToUint8Array(VAPID_PUBLIC_KEY),
      });
    }

    return { ok: true, subscription };
  } catch (error) {
    console.error('WebPush activation error:', error);
    return {
      ok: false,
      reason: 'error',
      message: error?.message || 'Impossibile attivare le notifiche push.',
    };
  }
}
