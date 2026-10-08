/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  staffGetRandomQrPools: vi.fn(),
  staffCreateRandomQrPool: vi.fn(),
  staffUpdateRandomQrPool: vi.fn(),
  staffDeleteRandomQrPool: vi.fn(),
  staffRandomQrPoolAddQr: vi.fn(),
  staffRandomQrPoolRemoveQr: vi.fn(),
  staffCreateRandomQrPoolEffect: vi.fn(),
  staffUpdateRandomQrPoolEffect: vi.fn(),
  staffDeleteRandomQrPoolEffect: vi.fn(),
  staffGetSerieCollezioni: vi.fn(),
  staffGetNodi: vi.fn(),
  staffGetMinigiocoPatterns: vi.fn(),
  staffGetManifesti: vi.fn(),
  staffGetOggettiBase: vi.fn(),
  staffGetTessiture: vi.fn(),
  staffGetInfusioni: vi.fn(),
  staffGetCerimoniali: vi.fn(),
  staffGetNegoziMercante: vi.fn(),
  staffGetInventari: vi.fn(),
}));

vi.mock('../../api', () => api);
vi.mock('../StaffQrTab', () => ({
  default: function StaffQrTabStub({ autoStart }) {
    return createElement(
      'div',
      { 'data-testid': 'staff-qr-tab-stub', 'data-autostart': autoStart ? 'true' : 'false' },
      'scanner stub',
    );
  },
}));

import RandomQrPoolManager from './RandomQrPoolManager';

const POOL = {
  id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
  nome: 'Casse bosco',
  attivo: true,
  cooldown_attivo: false,
  cooldown_minuti_min: 5,
  cooldown_minuti_max: 25,
  memberships: [],
  effetti: [],
  qr_count: 0,
  effetti_count: 0,
};

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

async function waitFor(predicate, { timeout = 2500 } = {}) {
  const start = Date.now();
  while (Date.now() - start < timeout) {
    if (predicate()) return;
    await act(async () => {
      await new Promise((r) => setTimeout(r, 20));
    });
  }
  throw new Error('timeout waiting for condition');
}

describe('RandomQrPoolManager scan overlay e cooldown', () => {
  afterEach(() => {
    document.body.querySelectorAll('[data-testid="pool-qr-scan-overlay"]').forEach((el) => el.remove());
    document.body.querySelectorAll('[data-testid="staff-editor-modal"]').forEach((el) => el.remove());
  });

  beforeEach(() => {
    Object.values(api).forEach((fn) => fn.mockReset());
    api.staffGetRandomQrPools.mockResolvedValue([POOL]);
    api.staffGetSerieCollezioni.mockResolvedValue([]);
    api.staffGetNodi.mockResolvedValue([]);
    api.staffGetMinigiocoPatterns.mockResolvedValue([]);
    api.staffGetManifesti.mockResolvedValue([]);
    api.staffGetOggettiBase.mockResolvedValue([]);
    api.staffGetTessiture.mockResolvedValue([]);
    api.staffGetInfusioni.mockResolvedValue([]);
    api.staffGetCerimoniali.mockResolvedValue([]);
    api.staffGetNegoziMercante.mockResolvedValue([]);
    api.staffGetInventari.mockResolvedValue([]);
  });

  it('sulla tab QR mostra il cooldown e apre lo scanner in portal sopra il modal', async () => {
    const { host, unmount } = mount(createElement(RandomQrPoolManager, { onLogout: vi.fn() }));

    await waitFor(() => host.textContent.includes('Casse bosco'));

    const editBtn = host.querySelector('button[title="Modifica"]');
    expect(editBtn).toBeTruthy();
    await act(async () => {
      editBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const modal = document.body.querySelector('[data-testid="staff-editor-modal"]');
    expect(modal).toBeTruthy();
    expect(modal.className).toContain('z-[100]');
    expect(modal.textContent).toContain('Tempo prima di riscansionare (cooldown)');

    const qrTab = Array.from(modal.querySelectorAll('button')).find((b) => /^\s*QR\b/.test(b.textContent || ''));
    expect(qrTab).toBeTruthy();
    await act(async () => {
      qrTab.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const cooldownOnQr = modal.querySelector('[data-testid="pool-cooldown-fields"]');
    expect(cooldownOnQr).toBeTruthy();
    expect(cooldownOnQr.textContent).toContain('Attiva attesa tra una scansione e la successiva');
    expect(cooldownOnQr.textContent).toContain('Minuti min');
    expect(cooldownOnQr.textContent).toContain('Minuti max');

    const scanBtn = modal.querySelector('[data-testid="pool-qr-scan-button"]');
    expect(scanBtn).toBeTruthy();
    expect(document.body.querySelector('[data-testid="pool-qr-scan-overlay"]')).toBeNull();

    await act(async () => {
      scanBtn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const overlay = document.body.querySelector('[data-testid="pool-qr-scan-overlay"]');
    expect(overlay).toBeTruthy();
    expect(overlay.className).toContain('z-[140]');
    expect(overlay.className).toContain('fixed');
    expect(modal.contains(overlay)).toBe(false);
    expect(host.contains(overlay)).toBe(false);
    expect(overlay.querySelector('[data-testid="staff-qr-tab-stub"]')?.getAttribute('data-autostart')).toBe('true');

    unmount();
  });
});
