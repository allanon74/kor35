/**
 * @vitest-environment jsdom
 *
 * Il cambio sottoscheda inventario non deve aspettare un altro aggiornamento
 * di MainPage (poll Tasks, messaggi, …): la vista nuova è nel render del click.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';

vi.mock('../api', () => ({
  getPilotNavigationConfig: vi.fn(() => Promise.resolve({})),
  fetchAuthenticated: vi.fn(() => Promise.resolve({})),
  fetchStaffMessages: vi.fn(() => Promise.resolve([])),
  socialGetNotifications: vi.fn(() => Promise.resolve([])),
  getArcanaPasswordStatus: vi.fn(() => Promise.resolve({})),
  normCampaignSlug: (slug) => slug || '',
  getQrCodeData: vi.fn(() => Promise.resolve({})),
  pilotSubsystemRepair: vi.fn(() => Promise.resolve({})),
  pilotSubsystemRecharge: vi.fn(() => Promise.resolve({})),
  pilotSubsystemSabota: vi.fn(() => Promise.resolve({})),
  carteGetStato: vi.fn(() => Promise.resolve({})),
  getMissioniEventoAttivo: vi.fn(() => Promise.resolve({ attivo: false })),
  contrattiGetAccesso: vi.fn(() => Promise.resolve({})),
  getPoolPgGiocatoreVisibili: vi.fn(() => Promise.resolve([])),
  sondaggiGetStato: vi.fn(() => Promise.resolve({})),
}));

vi.mock('./CharacterContext', () => ({
  useCharacter: () => ({
    personaggiList: [{ id: 7, nome: 'Prova' }],
    selectedCharacterId: 7,
    preferredCharacterId: 7,
    selectedCharacterData: { id: 7, nome: 'Prova', oggetti: [], impostazioni_ui: {} },
    refreshCharacterData: vi.fn(),
    punteggiList: [],
    activeTimers: [],
    removeTimerState: vi.fn(),
    refreshActiveTimers: vi.fn(),
    selectCharacter: vi.fn(),
    setPreferredCharacter: vi.fn(),
    fetchPersonaggi: vi.fn(),
    isLoading: false,
    isAdmin: false,
    viewAll: false,
    toggleViewAll: vi.fn(),
    adminPendingCount: 0,
    unreadCount: 0,
    campaigns: [],
    activeCampaign: 'kor35',
    changeActiveCampaign: vi.fn(),
    isCampaignMaster: false,
    isCampaignStaffer: false,
    isCampaignHeadMaster: false,
    canSeeStaffCompiti: false,
    canAccessModulo: () => false,
  }),
}));

vi.mock('./StaffCompitiWidget', () => ({
  useMieiStaffCompiti: () => ({ aperti: [] }),
}));

vi.mock('../hooks/useSharedNowTs', () => ({
  useSharedNowTs: () => 0,
}));

vi.mock('../lib/webpush', () => ({ isWebPushEnabled: () => false }));
vi.mock('../lib/appServiceWorker', () => ({ ensureAppServiceWorker: vi.fn() }));
vi.mock('../lib/callDeepLink', () => ({ consumePendingPushAction: vi.fn() }));
vi.mock('../utils/toastBus', () => ({ emitToast: vi.fn(), onToast: () => () => {} }));

vi.mock('./GameTab.jsx', () => ({ default: () => null }));
vi.mock('./JobRequestsWidget.jsx', () => ({ default: () => null }));
vi.mock('./RazzaCollapsible', () => ({ default: () => null, stripRazzaPrefix: (n) => n }));
vi.mock('./TimerOverlay', () => ({ TimerOverlay: () => null }));
vi.mock('./PasswordChangeModal.jsx', () => ({ default: () => null }));
vi.mock('./AppToastStack.jsx', () => ({ default: () => null }));
vi.mock('./WikiHelpModal.jsx', () => ({ default: () => null }));
vi.mock('./QrResultModal.jsx', () => ({ default: () => null }));
vi.mock('./minigioco/MinigiocoModal.jsx', () => ({ default: () => null }));

vi.mock('./InventoryTab.jsx', () => ({
  default: function InventoryTabStub({ vista, onVistaChange }) {
    return createElement(
      'div',
      null,
      createElement('p', { 'data-testid': 'vista-inventario' }, vista || ''),
      createElement(
        'button',
        { type: 'button', onClick: () => onVistaChange?.('consumabili') },
        'Vai ai consumabili',
      ),
      createElement(
        'button',
        { type: 'button', onClick: () => onVistaChange?.('serie') },
        'Vai alle serie',
      ),
    );
  },
}));

import MainPage from './MainPage.jsx';

function mount() {
  window.history.replaceState({}, '', '/app/play?tab=inventario');
  sessionStorage.setItem('kor35_main_active_tab', 'inventario');
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(
      createElement(
        MemoryRouter,
        { initialEntries: ['/app/play?tab=inventario'] },
        createElement(MainPage, {
          token: 't',
          onLogout: () => {},
          onSwitchToMaster: () => {},
        }),
      ),
    );
  });
  return {
    host,
    unmount() {
      act(() => root.unmount());
      host.remove();
    },
  };
}

function vistaNode() {
  return document.querySelector('[data-testid="vista-inventario"]');
}

afterEach(() => {
  document.body.innerHTML = '';
  sessionStorage.clear();
  vi.clearAllMocks();
});

describe('cambio scheda inventario', () => {
  it('mostra la sottoscheda nel render del click, senza attendere un altro aggiornamento', async () => {
    const view = mount();
    await act(async () => {
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(vistaNode()?.textContent).toBe('physical');

    const consumabili = [...document.querySelectorAll('button')].find((nodo) =>
      nodo.textContent.includes('Vai ai consumabili'),
    );
    expect(consumabili).toBeTruthy();

    await act(async () => {
      consumabili.click();
    });

    expect(vistaNode()?.textContent).toBe('consumabili');

    const serie = [...document.querySelectorAll('button')].find((nodo) =>
      nodo.textContent.includes('Vai alle serie'),
    );
    await act(async () => {
      serie.click();
    });
    expect(vistaNode()?.textContent).toBe('serie');

    view.unmount();
  });
});
