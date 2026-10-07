/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

vi.mock('../api', () => ({
  ackInnescoTimerScaduto: vi.fn(() => Promise.resolve({ ok: true })),
}));

import { ackInnescoTimerScaduto } from '../api';
import { TimerOverlay } from './TimerOverlay';

function mount(element) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(element);
  });
  return {
    host,
    unmount() {
      act(() => root.unmount());
      host.remove();
    },
  };
}

describe('TimerOverlay', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    localStorage.clear();
    vi.clearAllMocks();
  });

  it('mostra il countdown e lo sposta di angolo al tocco', () => {
    const endTime = Date.now() + 90_000;
    const { unmount } = mount(createElement(TimerOverlay, {
      activeTimers: {
        'innesco:4': {
          id: 'innesco:4',
          nome: 'Allarme',
          istanza: 'QR nord',
          endTime,
          alert_suono: true,
          messaggio_in_app: true,
        },
      },
      onRemove: () => {},
    }));

    const button = document.body.querySelector('button[aria-label*="Allarme"]');
    expect(button).toBeTruthy();
    expect(button.textContent).toMatch(/Allarme/);
    expect(button.textContent).toMatch(/QR nord/);
    expect(button.textContent).toMatch(/1:3/);
    const shell = button.parentElement;
    expect(shell.className).toContain('right-3');

    act(() => {
      button.click();
    });
    expect(button.parentElement.className).toContain('bottom-');
    expect(localStorage.getItem('kor35-timer-corner')).toBe('br');
    unmount();
  });

  it('alla scadenza mostra la scritta rossa finché non si preme Ok', async () => {
    const onRemove = vi.fn();
    const endTime = Date.now() - 2000;
    const { unmount } = mount(createElement(TimerOverlay, {
      activeTimers: {
        'innesco:7': {
          id: 'innesco:7',
          nome: 'Raid',
          istanza: 'Cancello est',
          endTime,
          scaduto: true,
          alert_suono: true,
          messaggio_in_app: true,
          source: 'innesco_timer',
        },
      },
      onRemove,
      personaggioId: 15,
      onLogout: () => {},
    }));

    const titolo = document.getElementById('timer-scaduto-titolo');
    expect(titolo).toBeTruthy();
    expect(titolo.textContent).toContain('Timer Raid scaduto!');
    expect(titolo.textContent).toContain('Cancello est');
    expect(titolo.className).toContain('text-red-600');
    expect(onRemove).not.toHaveBeenCalled();

    const ok = [...document.body.querySelectorAll('button')].find((el) => el.textContent === 'Ok');
    await act(async () => {
      ok.click();
    });

    expect(ackInnescoTimerScaduto).toHaveBeenCalledWith(
      expect.objectContaining({ personaggio_id: 15, innesco_id: '7' }),
      expect.any(Function),
    );
    expect(onRemove).toHaveBeenCalledWith('innesco:7');
    expect(document.getElementById('timer-scaduto-titolo')).toBeNull();
    unmount();
  });
});
