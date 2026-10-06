/**
 * @vitest-environment jsdom
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  staffGetTipiCarriera: vi.fn(),
  staffGetCarriere: vi.fn(),
  staffCreateCarriera: vi.fn(),
  staffUpdateCarriera: vi.fn(),
  staffDeleteCarriera: vi.fn(),
  staffGetCariche: vi.fn(),
  staffCreateCarica: vi.fn(),
  staffUpdateCarica: vi.fn(),
  staffDeleteCarica: vi.fn(),
  staffGetCarriereMemberships: vi.fn(),
  staffCreateCarriereMembership: vi.fn(),
  staffUpdateCarriereMembership: vi.fn(),
  staffDeleteCarriereMembership: vi.fn(),
  staffGetCarrieraTiersSelezionabili: vi.fn(),
  getPersonaggiEditList: vi.fn(),
  staffGetAbilitaListAll: vi.fn(),
}));

vi.mock('../../api', () => api);

import CarriereKorpsManager from './CarriereKorpsManager';

const TIPO_KORP = { id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeee1', codice: 'korp', nome: 'KORP' };
const TIPO_PROF = { id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeee2', codice: 'professione', nome: 'Professione' };

function emptyApis() {
  api.staffGetTipiCarriera.mockResolvedValue([TIPO_KORP, TIPO_PROF]);
  api.staffGetCarriere.mockResolvedValue([]);
  api.staffGetCariche.mockResolvedValue([]);
  api.staffGetCarriereMemberships.mockResolvedValue([]);
  api.getPersonaggiEditList.mockResolvedValue([]);
  api.staffGetCarrieraTiersSelezionabili.mockResolvedValue([
    { id: 11, nome: 'Combattente', tipo: 'T2' },
    { id: 12, nome: 'Supporto', tipo: 'T3' },
  ]);
  api.staffGetAbilitaListAll.mockResolvedValue([{ id: 99, nome: 'Sconto forgiatura' }]);
}

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

function clickButtonByText(root, text) {
  const btn = [...root.querySelectorAll('button')].find((el) => el.textContent.includes(text));
  if (!btn) throw new Error(`button not found: ${text}`);
  act(() => {
    btn.dispatchEvent(new MouseEvent('click', { bubbles: true }));
  });
}

describe('CarriereKorpsManager form staff', () => {
  beforeEach(() => {
    emptyApis();
  });

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('apre la maschera carriera con etichette e distinzione cataloghi vs livello wiki', async () => {
    const { unmount } = mount(createElement(CarriereKorpsManager, { onLogout: vi.fn() }));
    await waitFor(() => document.body.textContent.includes('Carriere, KORP e cariche'));
    clickButtonByText(document.body, 'Nuova carriera');
    await waitFor(() => document.body.querySelector('[data-testid="carriera-edit-form"]'));
    const form = document.body.querySelector('[data-testid="carriera-edit-form"]');
    expect(form.textContent).toContain('Nome');
    expect(form.textContent).toContain('Livello in wiki');
    expect(form.textContent).toContain('Cataloghi di abilità sbloccabili');
    expect(form.textContent).toContain('Non è una lista di abilità');
    expect(form.textContent).toContain('Bonus crediti evento');
    expect(form.textContent).not.toContain('Fattore crediti delle task');
    unmount();
  });

  it('mostra i moltiplicatori task solo per tipo KORP', async () => {
    api.staffGetCarriere.mockResolvedValue([
      {
        id: 1,
        nome: 'Sicurezza',
        tipo: 'T3',
        tipo_carriera: TIPO_KORP.id,
        tipo_carriera_codice: 'korp',
        tipo_carriera_nome: 'KORP',
        bonus_crediti_evento: 0,
        fattore_task_crediti: 2,
        fattore_task_prestigio: 1,
        tiers_sblocco_dettaglio: [{ id: 11, nome: 'Combattente', tipo: 'T2' }],
        abilita_default_dettaglio: [],
      },
    ]);
    const { unmount } = mount(createElement(CarriereKorpsManager, { onLogout: vi.fn() }));
    await waitFor(() => document.body.textContent.includes('Sicurezza'));
    act(() => {
      document.body.querySelector('button[title="Modifica"]').dispatchEvent(
        new MouseEvent('click', { bubbles: true }),
      );
    });
    await waitFor(() => document.body.querySelector('[data-testid="carriera-edit-form"]'));
    const form = document.body.querySelector('[data-testid="carriera-edit-form"]');
    expect(form.textContent).toContain('Catalogo T2');
    expect(form.textContent).toContain('Combattente');
    expect(form.textContent).toContain('Fattore crediti delle task');
    expect(form.textContent).toContain('Sottoscrive contratti');
    unmount();
  });

  it('apre carica e appartenenza con didascalie dei campi numerici', async () => {
    const { unmount } = mount(createElement(CarriereKorpsManager, { onLogout: vi.fn() }));
    await waitFor(() => document.body.textContent.includes('Cariche'));
    clickButtonByText(document.body, 'Cariche');
    await waitFor(() => document.body.textContent.includes('Nuova carica'));
    clickButtonByText(document.body, 'Nuova carica');
    await waitFor(() => document.body.querySelector('[data-testid="carica-edit-form"]'));
    const carica = document.body.querySelector('[data-testid="carica-edit-form"]');
    expect(carica.textContent).toContain('Nome carica');
    expect(carica.textContent).toContain('Bonus stipendio evento');
    expect(carica.textContent).toContain('Bonus slot contratto');
    expect(carica.textContent).toContain('Dipartimenti');
    act(() => {
      document.body.querySelector('[aria-label="Chiudi"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    clickButtonByText(document.body, 'Appartenenze');
    await waitFor(() => document.body.textContent.includes('Nuova appartenenza'));
    clickButtonByText(document.body, 'Nuova appartenenza');
    await waitFor(() => document.body.querySelector('[data-testid="membership-edit-form"]'));
    const mem = document.body.querySelector('[data-testid="membership-edit-form"]');
    expect(mem.textContent).toContain('Personaggio');
    expect(mem.textContent).toContain('Data inizio');
    expect(mem.textContent).toContain('Data fine');
    expect(mem.textContent).toContain('Carica visibile su InstaFame');
    unmount();
  });
});
