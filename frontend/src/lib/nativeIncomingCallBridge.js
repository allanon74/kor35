/**
 * Bridge Capacitor: push FCM + App resume → deep-link chiamate vocali.
 */
import { App } from '@capacitor/app';
import { isNativeApp } from './nativePlatform';
import { attachNativePushListeners } from './nativePush';
import {
  dispatchCallWake,
  isIncomingCallPayload,
  parseCallDeepLink,
  parseCallPushPayload,
} from './callDeepLink';

let started = false;
let cleanups = [];

function wakeFromParsed(parsed) {
  if (!isIncomingCallPayload(parsed) && !parsed?.callId) return;
  dispatchCallWake({
    callId: parsed.callId,
    action: parsed.action,
    url: parsed.url,
  });
}

function consumeLocationDeepLink() {
  if (typeof window === 'undefined') return;
  const parsed = parseCallDeepLink(window.location);
  if (parsed.callId || (parsed.action && String(parsed.action).startsWith('VOCE_'))) {
    wakeFromParsed({ ...parsed, category: parsed.category || 'chiamate' });
  }
}

async function consumeLaunchUrl() {
  try {
    const result = await App.getLaunchUrl();
    const url = result?.url;
    if (!url) return;
    const parsed = parseCallDeepLink(url);
    if (parsed.callId || parsed.action) {
      wakeFromParsed({ ...parsed, category: 'chiamate' });
    }
  } catch {
    /* plugin non pronto / web */
  }
}

/**
 * Avvia i listener una sola volta (idempotente).
 * @returns {Promise<() => void>}
 */
export async function startNativeIncomingCallBridge() {
  if (typeof window === 'undefined') return () => {};
  if (started) {
    return () => stopNativeIncomingCallBridge();
  }
  started = true;
  cleanups = [];

  // Deep-link già presente nell'URL (tap notifica / cold start WebView).
  consumeLocationDeepLink();

  // PWA: messaggio dallo service worker
  const onSwMessage = (event) => {
    const data = event?.data;
    if (!data || typeof data !== 'object') return;
    if (data.type === 'kor35:open-url' && data.url) {
      const parsed = parseCallDeepLink(data.url);
      if (parsed.callId || parsed.action) {
        wakeFromParsed({ ...parsed, category: 'chiamate' });
        return;
      }
      if (String(data.url).includes('tab=messaggi')) {
        window.dispatchEvent(new CustomEvent('kor35:open-messaggi'));
      }
      return;
    }
    if (data.type === 'kor35:voce-wake' || data.type === 'kor35:call-wake') {
      wakeFromParsed(parseCallPushPayload(data.payload || data));
    }
  };
  if (navigator?.serviceWorker?.addEventListener) {
    navigator.serviceWorker.addEventListener('message', onSwMessage);
    cleanups.push(() => navigator.serviceWorker.removeEventListener('message', onSwMessage));
  }

  if (!isNativeApp()) {
    return () => stopNativeIncomingCallBridge();
  }

  await consumeLaunchUrl();

  const appUrlSub = await App.addListener('appUrlOpen', (event) => {
    const parsed = parseCallDeepLink(event?.url || '');
    wakeFromParsed({ ...parsed, category: parsed.category || 'chiamate' });
  });
  cleanups.push(() => appUrlSub.remove().catch(() => {}));

  const stateSub = await App.addListener('appStateChange', ({ isActive }) => {
    if (!isActive) return;
    // Al ritorno in foreground: se c'è ancora una chiamata ringing, il provider rifà fetch.
    window.dispatchEvent(new CustomEvent('kor35:voce-wake', { detail: { reason: 'app-resume' } }));
    consumeLocationDeepLink();
  });
  cleanups.push(() => stateSub.remove().catch(() => {}));

  const detachPush = await attachNativePushListeners({
    onNotification: (notification) => {
      const parsed = parseCallPushPayload(notification);
      if (isIncomingCallPayload(parsed)) {
        // Foreground: risveglia subito l'overlay (oltre alla notifica di sistema).
        wakeFromParsed(parsed);
      }
    },
    onAction: (event) => {
      const parsed = parseCallPushPayload(event?.notification || event);
      wakeFromParsed(parsed);
    },
  });
  cleanups.push(detachPush);

  return () => stopNativeIncomingCallBridge();
}

export function stopNativeIncomingCallBridge() {
  const list = cleanups.slice();
  cleanups = [];
  started = false;
  list.forEach((fn) => {
    try {
      fn();
    } catch {
      /* ignore */
    }
  });
}
