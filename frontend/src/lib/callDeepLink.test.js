import { describe, expect, it, vi, afterEach } from 'vitest';
import {
  dispatchCallWake,
  isIncomingCallPayload,
  parseCallDeepLink,
  parseCallPushPayload,
} from './callDeepLink';

describe('callDeepLink', () => {
  it('parse URL con call e voce', () => {
    const parsed = parseCallDeepLink(
      '/?tab=messaggi&call=11111111-2222-3333-4444-555555555555&voce=VOCE_INVITO'
    );
    expect(parsed.callId).toBe('11111111-2222-3333-4444-555555555555');
    expect(parsed.action).toBe('VOCE_INVITO');
  });

  it('parse payload FCM data', () => {
    const parsed = parseCallPushPayload({
      data: {
        category: 'chiamate',
        call_id: 'abc-1',
        action: 'VOCE_INVITO',
        url: '/?tab=messaggi&call=abc-1&voce=VOCE_INVITO',
        head: 'Chiamata vocale',
        body: 'Alice ti sta chiamando.',
      },
    });
    expect(parsed.callId).toBe('abc-1');
    expect(parsed.action).toBe('VOCE_INVITO');
    expect(parsed.category).toBe('chiamate');
    expect(isIncomingCallPayload(parsed)).toBe(true);
  });

  it('payload messaggi generico non è incoming call', () => {
    const parsed = parseCallPushPayload({
      data: { category: 'messaggi', url: '/?tab=messaggi', head: 'Msg' },
    });
    expect(isIncomingCallPayload(parsed)).toBe(false);
  });
});

describe('dispatchCallWake', () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('emette open-messaggi e voce-wake', () => {
    const spy = vi.spyOn(window, 'dispatchEvent');
    dispatchCallWake({ callId: 'c1', action: 'VOCE_INVITO' });
    const types = spy.mock.calls.map((c) => c[0]?.type);
    expect(types).toContain('kor35:open-messaggi');
    expect(types).toContain('kor35:voce-wake');
    expect(types).toContain('kor35:voce');
  });
});

describe('applyPushNotificationAction', () => {
  afterEach(() => {
    vi.restoreAllMocks();
    sessionStorage.clear();
  });

  it('messaggio apre solo tab messaggi', async () => {
    const { applyPushNotificationAction } = await import('./callDeepLink');
    const spy = vi.spyOn(window, 'dispatchEvent');
    applyPushNotificationAction({
      data: { category: 'messaggi', url: '/?tab=messaggi', head: 'Ciao' },
    });
    const types = spy.mock.calls.map((c) => c[0]?.type);
    expect(types).toContain('kor35:open-messaggi');
    expect(types).not.toContain('kor35:voce-wake');
  });

  it('persist+consume ripristina azione pending', async () => {
    const {
      persistPendingPushAction,
      consumePendingPushAction,
    } = await import('./callDeepLink');
    const spy = vi.spyOn(window, 'dispatchEvent');
    persistPendingPushAction({
      data: { category: 'messaggi', url: '/?tab=messaggi' },
    });
    expect(consumePendingPushAction()).toBe(true);
    expect(spy.mock.calls.map((c) => c[0]?.type)).toContain('kor35:open-messaggi');
    expect(consumePendingPushAction()).toBe(false);
  });
});
