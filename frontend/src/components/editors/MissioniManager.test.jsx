/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  getMissioni: vi.fn(),
  getMissione: vi.fn(),
  createMissione: vi.fn(),
  updateMissione: vi.fn(),
  deleteMissione: vi.fn(),
  getEventiOpzioni: vi.fn(),
  staffGetKorps: vi.fn(),
  getMissioniProposte: vi.fn(),
  accettaMissioneProposta: vi.fn(),
  rifiutaMissioneProposta: vi.fn(),
  getMissioniEventoAttivo: vi.fn(),
  getMissioniEventoTasks: vi.fn(),
  setMissioneAttivaEvento: vi.fn(),
  getMissioniEventoPartecipanti: vi.fn(),
  assegnaMissioneRisoluzione: vi.fn(),
}));

vi.mock('../../api', () => api);

import MissioniManager from './MissioniManager';

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

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
    await Promise.resolve();
  });
}

function clickTab(host, label) {
  const btn = [...host.querySelectorAll('button')].find((node) => node.textContent.trim() === label);
  expect(btn).toBeTruthy();
  return act(async () => {
    btn.click();
  });
}

describe('MissioniManager schede', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('tiene catalogo, soluzioni e stato su schede diverse', async () => {
    api.getMissioni.mockResolvedValue([{ id: 't1', titolo: 'Relitto', tipo_risoluzione: 'MANUALE', attiva: true }]);
    api.getMissioniProposte.mockResolvedValue([]);
    api.getMissioniEventoAttivo.mockResolvedValue({ attivo: false });

    const view = mount(createElement(MissioniManager, {}));
    await flush();

    expect(view.host.textContent).toContain('Catalogo task');
    expect(view.host.textContent).toContain('Relitto');
    expect(view.host.textContent).not.toContain('Nessuna soluzione in attesa');
    expect(view.host.textContent).not.toContain('Nessun evento in corso');

    await clickTab(view.host, 'Soluzioni');
    await flush();
    expect(view.host.textContent).toContain('Nessuna soluzione in attesa');
    expect(view.host.textContent).not.toContain('Catalogo task');

    await clickTab(view.host, 'Stato task evento');
    await flush();
    expect(view.host.textContent).toContain('Nessun evento in corso');
    expect(api.getMissioniEventoTasks).not.toHaveBeenCalled();

    view.unmount();
  });

  it('con evento in corso accredita task e personaggio senza chiedere l\'evento', async () => {
    api.getMissioni.mockImplementation(async (params) => {
      if (params?.evento) {
        return [{
          id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
          titolo: 'As Miranda Comands',
          reward_crediti: '15.00',
          reward_prestigio: 2,
        }];
      }
      return [];
    });
    api.getMissioniEventoAttivo.mockResolvedValue({ attivo: true, id: 3, titolo: 'All\'Ombra dei Sette Alberi' });
    api.getMissioniEventoPartecipanti.mockResolvedValue({
      evento_id: 3,
      in_corso: true,
      chiuso: false,
      partecipanti: [{ id: 9, nome: 'Nyxen' }],
    });
    api.assegnaMissioneRisoluzione.mockResolvedValue({
      personaggio_nome: 'Nyxen',
      reward_crediti: '15.00',
      reward_prestigio: 2,
    });

    const view = mount(createElement(MissioniManager, {}));
    await flush();
    await clickTab(view.host, 'Soluzione manuale');
    await flush();
    await flush();

    expect(view.host.textContent).toContain('All\'Ombra dei Sette Alberi');
    expect(view.host.textContent).not.toContain('Evento da accreditare');

    const selects = view.host.querySelectorAll('select');
    expect(selects.length).toBe(2);
    await act(async () => {
      selects[0].value = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
      selects[0].dispatchEvent(new Event('change', { bubbles: true }));
      selects[1].value = '9';
      selects[1].dispatchEvent(new Event('change', { bubbles: true }));
    });
    const area = view.host.querySelector('textarea');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(area, 'Consegnato il dispaccio.');
      area.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const invia = [...view.host.querySelectorAll('button')].find((node) => node.textContent.includes('Accredita soluzione'));
    await act(async () => {
      invia.click();
    });
    await flush();

    expect(api.assegnaMissioneRisoluzione).toHaveBeenCalledWith({
      missione_id: 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee',
      evento_id: 3,
      personaggio_id: 9,
      note: 'Consegnato il dispaccio.',
    }, undefined);
    expect(view.host.textContent).toContain('Soluzione accreditata a Nyxen');
    view.unmount();
  });

  it('a evento chiuso chiede quale evento accreditare', async () => {
    api.getMissioni.mockResolvedValue([]);
    api.getMissioniEventoAttivo.mockResolvedValue({ attivo: false });
    api.getEventiOpzioni.mockResolvedValue([
      { id: 8, titolo: 'Evento passato', in_corso: false, chiuso: true },
      { id: 9, titolo: 'Mai partito', in_corso: false, chiuso: false },
    ]);

    const view = mount(createElement(MissioniManager, {}));
    await flush();
    await clickTab(view.host, 'Soluzione manuale');
    await flush();
    await flush();

    expect(view.host.textContent).toContain('Evento da accreditare');
    const select = view.host.querySelector('select');
    const labels = [...select.options].map((opt) => opt.textContent);
    expect(labels).toContain('Evento passato');
    expect(labels).not.toContain('Mai partito');
    view.unmount();
  });
});
