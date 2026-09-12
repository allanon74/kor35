/**
 * Rilevamento shell Capacitor (Android nativo) vs browser/PWA.
 * Non importare plugin nativi qui: solo @capacitor/core, sicuro anche sul web.
 */
import { Capacitor } from '@capacitor/core';

/** True se l'UI gira dentro la WebView Capacitor (APK), non nel browser. */
export function isNativeApp() {
  try {
    return Capacitor.isNativePlatform();
  } catch {
    return false;
  }
}

/** 'android' | 'ios' | 'web' */
export function getNativePlatform() {
  try {
    return Capacitor.getPlatform();
  } catch {
    return 'web';
  }
}

export function isNativeAndroid() {
  return isNativeApp() && getNativePlatform() === 'android';
}

/**
 * Marker DOM/CSS per stili o debug (data-kor35-native="android").
 * Idempotente.
 */
export function applyNativePlatformMarker() {
  if (typeof document === 'undefined') return;
  const platform = getNativePlatform();
  const root = document.documentElement;
  root.dataset.kor35Platform = platform;
  if (isNativeApp()) {
    root.dataset.kor35Native = platform;
  } else {
    delete root.dataset.kor35Native;
  }
}
