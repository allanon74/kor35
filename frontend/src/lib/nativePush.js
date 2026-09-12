/**
 * Push nativo Android (FCM) via @capacitor/push-notifications.
 * Usato solo dentro la shell Capacitor; sul web resta web push (VAPID).
 */
import { PushNotifications } from '@capacitor/push-notifications';
import { isNativeApp, getNativePlatform } from './nativePlatform';

const REGISTRATION_TIMEOUT_MS = 20000;

export function isNativePushAvailable() {
  return isNativeApp();
}

/**
 * Richiede permesso, registra FCM e restituisce il device token.
 * @returns {Promise<{ok: true, token: string, platform: string} | {ok: false, reason: string, message?: string}>}
 */
export async function activateNativePush() {
  if (!isNativePushAvailable()) {
    return {
      ok: false,
      reason: 'unsupported',
      message: 'Push nativo disponibile solo nell\'app Android KOR35.',
    };
  }

  try {
    let perm = await PushNotifications.checkPermissions();
    if (perm.receive !== 'granted') {
      perm = await PushNotifications.requestPermissions();
    }
    if (perm.receive !== 'granted') {
      return {
        ok: false,
        reason: perm.receive === 'denied' ? 'denied' : 'dismissed',
        message:
          perm.receive === 'denied'
            ? 'Permesso notifiche negato. Abilitalo dalle impostazioni Android dell\'app KOR35.'
            : 'Richiesta notifiche annullata.',
      };
    }

    return await new Promise((resolve) => {
      let settled = false;
      const finish = (value) => {
        if (settled) return;
        settled = true;
        clearTimeout(timer);
        regHandle.then((h) => h.remove()).catch(() => {});
        errHandle.then((h) => h.remove()).catch(() => {});
        resolve(value);
      };

      const regHandle = PushNotifications.addListener('registration', (event) => {
        const token = String(event?.value || '').trim();
        if (!token) {
          finish({
            ok: false,
            reason: 'error',
            message: 'Token FCM vuoto dalla registrazione nativa.',
          });
          return;
        }
        finish({
          ok: true,
          token,
          platform: getNativePlatform(),
        });
      });

      const errHandle = PushNotifications.addListener('registrationError', (event) => {
        finish({
          ok: false,
          reason: 'error',
          message: event?.error || 'Registrazione FCM fallita.',
        });
      });

      const timer = setTimeout(() => {
        finish({
          ok: false,
          reason: 'timeout',
          message:
            'Timeout registrazione FCM. Verifica google-services.json e rete sul dispositivo.',
        });
      }, REGISTRATION_TIMEOUT_MS);

      PushNotifications.register().catch((error) => {
        finish({
          ok: false,
          reason: 'error',
          message: error?.message || 'Impossibile avviare la registrazione FCM.',
        });
      });
    });
  } catch (error) {
    console.error('Native push activation error:', error);
    return {
      ok: false,
      reason: 'error',
      message: error?.message || 'Impossibile attivare le notifiche native.',
    };
  }
}

/**
 * Listener per tap su notifica / payload in foreground.
 * Utile per deep-link chiamate vocali (VOCE_*) nelle iterazioni successive.
 * @returns {Promise<() => void>} cleanup
 */
export async function attachNativePushListeners({ onNotification, onAction } = {}) {
  if (!isNativePushAvailable()) return () => {};

  const received = await PushNotifications.addListener(
    'pushNotificationReceived',
    (notification) => {
      onNotification?.(notification);
    }
  );
  const action = await PushNotifications.addListener(
    'pushNotificationActionPerformed',
    (event) => {
      onAction?.(event);
    }
  );

  return () => {
    received.remove().catch(() => {});
    action.remove().catch(() => {});
  };
}
