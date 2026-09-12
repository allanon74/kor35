import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest';

describe('nativePlatform', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  afterEach(() => {
    vi.doUnmock('@capacitor/core');
    delete document.documentElement.dataset.kor35Platform;
    delete document.documentElement.dataset.kor35Native;
  });

  it('su web riporta isNativeApp=false e platform=web', async () => {
    vi.doMock('@capacitor/core', () => ({
      Capacitor: {
        isNativePlatform: () => false,
        getPlatform: () => 'web',
      },
    }));
    const mod = await import('./nativePlatform');
    expect(mod.isNativeApp()).toBe(false);
    expect(mod.isNativeAndroid()).toBe(false);
    expect(mod.getNativePlatform()).toBe('web');
    mod.applyNativePlatformMarker();
    expect(document.documentElement.dataset.kor35Platform).toBe('web');
    expect(document.documentElement.dataset.kor35Native).toBeUndefined();
  });

  it('su Android Capacitor marca il DOM', async () => {
    vi.doMock('@capacitor/core', () => ({
      Capacitor: {
        isNativePlatform: () => true,
        getPlatform: () => 'android',
      },
    }));
    const mod = await import('./nativePlatform');
    expect(mod.isNativeApp()).toBe(true);
    expect(mod.isNativeAndroid()).toBe(true);
    mod.applyNativePlatformMarker();
    expect(document.documentElement.dataset.kor35Native).toBe('android');
  });
});
