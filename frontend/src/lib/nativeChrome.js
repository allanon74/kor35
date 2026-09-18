/**
 * Chrome nativo Capacitor: stile delle barre di sistema.
 *
 * Gli inset (safe area) NON si gestiscono qui: su Android 15+ il plugin core
 * SystemBars inietta `--safe-area-inset-*` nella pagina e il CSS li usa via
 * `--kor-safe-top` / `--kor-safe-bottom`. Nessun padding nativo, nessuna
 * striscia vuota sopra la UI.
 */
import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeApp } from './nativePlatform';

export async function setupNativeChrome() {
  if (!isNativeApp()) return;

  try {
    await StatusBar.setStyle({ style: Style.Dark });
  } catch {
    /* alcuni OEM non supportano lo style */
  }

  try {
    // Non disponibile su Android 15+ (edge-to-edge forzato).
    await StatusBar.setBackgroundColor({ color: '#111827' });
  } catch {
    /* ignore */
  }
}
