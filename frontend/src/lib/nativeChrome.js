/**
 * Chrome nativo Capacitor: status bar e inset di sistema.
 * Su Android 15+ setOverlaysWebView è ignorato (edge-to-edge forzato):
 * serve padding CSS basato su StatusBar.getInfo().height.
 */
import { StatusBar, Style } from '@capacitor/status-bar';
import { isNativeApp } from './nativePlatform';

const FALLBACK_SAFE_TOP_PX = 32;

function setSafeTopPx(px) {
  if (typeof document === 'undefined') return;
  const value = Math.max(0, Number(px) || 0);
  document.documentElement.style.setProperty('--kor-safe-top', `${value}px`);
}

async function applySafeTopFromStatusBar() {
  try {
    const info = await StatusBar.getInfo();
    if (info?.height && info.height > 0) {
      setSafeTopPx(info.height);
      return;
    }
  } catch {
    /* getInfo non disponibile */
  }
  setSafeTopPx(FALLBACK_SAFE_TOP_PX);
}

export async function setupNativeChrome() {
  if (!isNativeApp()) return;

  // Fallback subito: evita header sotto la status bar prima che getInfo risolva.
  setSafeTopPx(FALLBACK_SAFE_TOP_PX);

  try {
    // Android < 15: toglie overlay. Android 15+: no-op documentato.
    await StatusBar.setOverlaysWebView({ overlay: false });
  } catch (err) {
    console.warn('StatusBar.setOverlaysWebView failed:', err);
  }

  await applySafeTopFromStatusBar();

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
