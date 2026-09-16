/**
 * Chrome nativo Capacitor: stile status/navigation bar.
 *
 * Su Android 15+ (targetSdk ≥ 35) gli inset li gestisce MainActivity
 * (padding nativo sul layout bridge). Qui NON impostiamo --kor-safe-top
 * da StatusBar.getInfo(): eviterebbe/raddoppierebbe il padding nativo.
 * La PWA continua a usare env(safe-area-inset-*).
 */
import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeAndroid, isNativeApp } from './nativePlatform';

export async function setupNativeChrome() {
  if (!isNativeApp()) return;

  // MainActivity padda già la WebView: azzera il token CSS usato dall'header.
  if (isNativeAndroid() && typeof document !== 'undefined') {
    document.documentElement.style.setProperty('--kor-safe-top', '0px');
    document.documentElement.dataset.kor35NativeInsets = 'activity';
  }

  try {
    // Android < 15: utile. Android 15+: no-op documentato.
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
    // Non disponibile su Android 15+.
    await StatusBar.setBackgroundColor({ color: '#111827' });
  } catch {
    /* ignore */
  }
}
