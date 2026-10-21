/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import StaffConsumabiliPersonaggioTab from './StaffConsumabiliPersonaggioTab';
import {
  staffPersonaggioAggiornaConsumabile,
  staffPersonaggioAggiungiConsumabile,
  staffPersonaggioCatalogoTessiture,
  staffPersonaggioRimuoviConsumabile,
} from '../../api';

vi.mock('../../api', () => ({
  staffPersonaggioCatalogoTessiture: vi.fn(),
  staffPersonaggioAggiungiConsumabile: vi.fn(),
  staffPersonaggioAggiornaConsumabile: vi.fn(),
  staffPersonaggioRimuoviConsumabile: vi.fn(),
}));

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
  });
}

function setSelect(select, value) {
  act(() => {
    const setter = Object.getOwnPropertyDescriptor(window.HTMLSelectElement.prototype, 'value').set;
    setter.call(select, value);
    select.dispatchEvent(new Event('change', { bubbles: true }));
  });
}

function setInput(input, value) {
  act(() => {
    const proto = input instanceof window.HTMLTextAreaElement
      ? window.HTMLTextAreaElement.prototype
      : window.HTMLInputElement.prototype;
    const setter = Object.getOwnPropertyDescriptor(proto, 'value').set;
    setter.call(input, value);
    input.dispatchEvent(new Event('input', { bubbles: true }));
  });
}

describe('consumabili staff personaggio', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('crea il numero richiesto di consumabili dalla tessitura scelta', async () => {
    staffPersonaggioCatalogoTessiture.mockResolvedValue([
      { id: 9, nome: 'Tinta di luna', livello: 2, aura: 'Luna' },
    ]);
    staffPersonaggioAggiungiConsumabile.mockResolvedValue({
      messaggio: 'Creati 4 consumabili.',
      consumabili: [],
    });
    const onUpdated = vi.fn();
    const view = mount(createElement(StaffConsumabiliPersonaggioTab, {
      detail: { id: 15, consumabili: [] },
      onLogout: vi.fn(),
      onUpdated,
      onError: vi.fn(),
    }));
    await flush();

    const select = view.host.querySelector('select');
    setSelect(select, '9');
    const numero = view.host.querySelector('[aria-label="Numero di consumabili"]');
    setInput(numero, '4');
    await flush();

    const crea = view.host.querySelector('[data-testid="crea-consumabili-tessitura"]');
    expect(crea.disabled).toBe(false);
    await act(async () => {
      crea.click();
    });

    expect(staffPersonaggioAggiungiConsumabile).toHaveBeenCalledWith(
      15,
      expect.objectContaining({ tessitura_id: 9, quantita: 4, utilizzi_rimanenti: 1 }),
      expect.any(Function),
    );
    expect(onUpdated).toHaveBeenCalled();
    view.unmount();
  });

  it('salva gli utilizzi e rimuove un consumabile esistente', async () => {
    staffPersonaggioCatalogoTessiture.mockResolvedValue([]);
    staffPersonaggioAggiornaConsumabile.mockResolvedValue({
      messaggio: 'aggiornato',
      consumabili: [{ id: 3, nome: 'Boccetta', utilizzi_rimanenti: 6, data_scadenza: '2026-12-01', scaduto: false }],
    });
    staffPersonaggioRimuoviConsumabile.mockResolvedValue({ messaggio: 'rimosso', consumabili: [] });
    vi.spyOn(window, 'confirm').mockReturnValue(true);
    const view = mount(createElement(StaffConsumabiliPersonaggioTab, {
      detail: {
        id: 15,
        consumabili: [{
          id: 3,
          nome: 'Boccetta',
          utilizzi_rimanenti: 2,
          data_scadenza: '2026-12-01',
          tessitura_nome: '',
          scaduto: false,
        }],
      },
      onLogout: vi.fn(),
      onUpdated: vi.fn(),
      onError: vi.fn(),
    }));
    await flush();

    setInput(view.host.querySelector('[aria-label="Utilizzi Boccetta"]'), '6');
    const salva = [...view.host.querySelectorAll('button')].find((b) => b.textContent === 'Salva');
    await act(async () => {
      salva.click();
    });
    expect(staffPersonaggioAggiornaConsumabile).toHaveBeenCalledWith(
      15,
      expect.objectContaining({ consumabile_id: 3, utilizzi_rimanenti: 6, data_scadenza: '2026-12-01' }),
      expect.any(Function),
    );

    const rimuovi = [...view.host.querySelectorAll('button')].find((b) => b.textContent === 'Rimuovi');
    await act(async () => {
      rimuovi.click();
    });
    expect(staffPersonaggioRimuoviConsumabile).toHaveBeenCalledWith(
      15, 3, 'Intervento staff consumabili', expect.any(Function),
    );
    view.unmount();
  });
});
