/**
 * Canale push unificato: FCM nativo in Capacitor, altrimenti Web Push (PWA/browser).
 */
import { activateWebPush, isWebPushSupported } from './webpush';
import { activateNativePush, isNativePushAvailable } from './nativePush';
import { isNativeApp } from './nativePlatform';

export function isDevicePushSupported() {
  if (isNativePushAvailable()) return true;
  return isWebPushSupported();
}

/**
 * @returns {Promise<
 *   | {ok: true, channel: 'fcm', token: string, platform: string}
 *   | {ok: true, channel: 'webpush', subscription: PushSubscription}
 *   | {ok: false, reason: string, message?: string}
 * >}
 */
export async function activateDevicePush() {
  if (isNativeApp()) {
    const native = await activateNativePush();
    if (!native.ok) return native;
    return {
      ok: true,
      channel: 'fcm',
      token: native.token,
      platform: native.platform,
    };
  }

  const web = await activateWebPush();
  if (!web.ok) return web;
  return {
    ok: true,
    channel: 'webpush',
    subscription: web.subscription,
  };
}
