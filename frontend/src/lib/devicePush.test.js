import { describe, expect, it, vi, beforeEach } from 'vitest';

describe('devicePush', () => {
  beforeEach(() => {
    vi.resetModules();
  });

  it('in app nativa preferisce il canale FCM', async () => {
    vi.doMock('./nativePlatform', () => ({
      isNativeApp: () => true,
      getNativePlatform: () => 'android',
    }));
    vi.doMock('./nativePush', () => ({
      isNativePushAvailable: () => true,
      activateNativePush: async () => ({
        ok: true,
        token: 'fcm-token-test',
        platform: 'android',
      }),
    }));
    vi.doMock('./webpush', () => ({
      isWebPushSupported: () => true,
      activateWebPush: async () => ({
        ok: true,
        subscription: { endpoint: 'https://web.example' },
      }),
    }));
    const { activateDevicePush, isDevicePushSupported } = await import('./devicePush');
    expect(isDevicePushSupported()).toBe(true);
    await expect(activateDevicePush()).resolves.toEqual({
      ok: true,
      channel: 'fcm',
      token: 'fcm-token-test',
      platform: 'android',
    });
  });

  it('nel browser usa web push', async () => {
    vi.doMock('./nativePlatform', () => ({
      isNativeApp: () => false,
      getNativePlatform: () => 'web',
    }));
    vi.doMock('./nativePush', () => ({
      isNativePushAvailable: () => false,
      activateNativePush: async () => ({ ok: false, reason: 'unsupported' }),
    }));
    vi.doMock('./webpush', () => ({
      isWebPushSupported: () => true,
      activateWebPush: async () => ({
        ok: true,
        subscription: { endpoint: 'https://web.example' },
      }),
    }));
    const { activateDevicePush } = await import('./devicePush');
    const result = await activateDevicePush();
    expect(result.ok).toBe(true);
    expect(result.channel).toBe('webpush');
    expect(result.subscription.endpoint).toBe('https://web.example');
  });
});
