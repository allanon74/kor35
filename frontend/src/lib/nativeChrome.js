/**
 * Chrome nativo Capacitor: status bar e inset di sistema.
 * Evita che header/pulsanti finiscano sotto la barra notifiche Android.
 */
import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeApp } from './nativePlatform';

export async function setupNativeChrome() {
  if (!isNativeApp()) return;

  try {
    // WebView sotto la status bar (non overlay): i tap sull'header funzionano.
    await StatusBar.setOverlaysWebView({ overlay: false });
  } catch (err) {
    console.warn('StatusBar.setOverlaysWebView failed:', err);
  }

  try {
    await StatusBar.setStyle({ style: Style.Dark });
  } catch {
    /* alcuni OEM non supportano lo style */
  }

  try {
    await StatusBar.setBackgroundColor({ color: '#111827' });
  } catch {
    /* ignore */
  }
}
