/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import StaffInventarioInfusionePanel from './StaffInventarioInfusionePanel';
import CreaIstanzaInfusioneModal from './CreaIstanzaInfusioneModal';
import {
  staffCreaIstanzaDaInfusione,
  staffGetInfusioni,
  staffGetPersonaggi,
  staffGetPersonaggioDetail,
  staffPersonaggioCreaOggettoDaInfusione,
  staffPersonaggioMontaPotenziamento,
} from '../../api';

vi.mock('../../api', () => ({
  staffGetInfusioni: vi.fn(),
  staffPersonaggioCreaOggettoDaInfusione: vi.fn(),
  staffPersonaggioMontaPotenziamento: vi.fn(),
  staffCreaIstanzaDaInfusione: vi.fn(),
  staffGetPersonaggi: vi.fn(),
  staffGetPersonaggioDetail: vi.fn(),
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

describe('inventario staff da infusione', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('obbliga lo slot libero per mutazione e lo invia', async () => {
    staffGetInfusioni.mockResolvedValue([
      {
        id: 7,
        nome: 'Pelle di pietra',
        tipo_risultato: 'AUM',
        slot_corpo_permessi: 'HD1,TR1',
      },
    ]);
    staffPersonaggioCreaOggettoDaInfusione.mockResolvedValue({ detail: 'creata' });
    const onMessage = vi.fn();
    const onReload = vi.fn();
    const view = mount(createElement(StaffInventarioInfusionePanel, {
      personaggioId: 4,
      oggetti: [
        { id: 1, nome: 'Pelle vecchia', tipo_oggetto: 'MUT', slot_corpo: 'HD1', is_equipaggiato: true, potenziamenti: [] },
        { id: 2, nome: 'Lama', tipo_oggetto: 'FIS', potenziamenti: [] },
      ],
      onLogout: vi.fn(),
      onMessage,
      onReload,
    }));
    await flush();

    const selects = view.host.querySelectorAll('select');
    setSelect(selects[0], '7');
    await flush();

    expect(view.host.textContent).toContain('Slot corporeo libero');
    const slotSelect = [...view.host.querySelectorAll('select')].find((el) =>
      [...el.options].some((opt) => opt.value === 'HD1')
    );
    const hd1 = [...slotSelect.options].find((opt) => opt.value === 'HD1');
    const tr1 = [...slotSelect.options].find((opt) => opt.value === 'TR1');
    expect(hd1.disabled).toBe(true);
    expect(tr1.disabled).toBe(false);
    const crea = [...view.host.querySelectorAll('button')].find((b) => b.textContent.includes('Crea istanza da infusione'));
    expect(crea.disabled).toBe(true);

    setSelect(slotSelect, 'TR1');
    await flush();
    expect(crea.disabled).toBe(false);
    await act(async () => {
      crea.click();
    });
    expect(staffPersonaggioCreaOggettoDaInfusione).toHaveBeenCalledWith(
      4,
      expect.objectContaining({ infusione_id: 7, slot_corpo: 'TR1' }),
      expect.any(Function),
    );
    expect(onReload).toHaveBeenCalled();
    view.unmount();
  });

  it('monta d\'ufficio materia e oggetto dello stesso inventario', async () => {
    staffGetInfusioni.mockResolvedValue([]);
    staffPersonaggioMontaPotenziamento.mockResolvedValue({ detail: 'montata' });
    const view = mount(createElement(StaffInventarioInfusionePanel, {
      personaggioId: 4,
      oggetti: [
        { id: 9, nome: 'Scheggia', tipo_oggetto: 'MAT', potenziamenti: [] },
        { id: 2, nome: 'Lama', tipo_oggetto: 'FIS', potenziamenti: [] },
      ],
      motivo: 'Plot',
      onLogout: vi.fn(),
      onMessage: vi.fn(),
      onReload: vi.fn(),
    }));
    await flush();
    const selects = view.host.querySelectorAll('select');
    const materia = [...selects].find((el) => [...el.options].some((opt) => opt.value === '9'));
    const host = [...selects].find((el) => [...el.options].some((opt) => opt.textContent.includes('Lama')));
    setSelect(materia, '9');
    setSelect(host, '2');
    const monta = [...view.host.querySelectorAll('button')].find((b) => b.textContent.includes("Monta d'ufficio"));
    expect(monta.disabled).toBe(false);
    await act(async () => {
      monta.click();
    });
    expect(staffPersonaggioMontaPotenziamento).toHaveBeenCalledWith(4, 9, 2, 'Plot', expect.any(Function));
    view.unmount();
  });
});

describe('modale istanza da infusioni', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('crea senza personaggio', async () => {
    staffCreaIstanzaDaInfusione.mockResolvedValue({ detail: 'Istanza creata, senza personaggio.' });
    const onCreated = vi.fn();
    const view = mount(createElement(CreaIstanzaInfusioneModal, {
      open: true,
      infusione: { id: 3, nome: 'Scheggia', tipo_risultato: 'POT' },
      onClose: vi.fn(),
      onLogout: vi.fn(),
      onCreated,
    }));
    const salva = [...document.body.querySelectorAll('button')].find((b) => b.textContent === 'Crea istanza');
    await act(async () => {
      salva.click();
    });
    expect(staffCreaIstanzaDaInfusione).toHaveBeenCalledWith(
      3,
      expect.objectContaining({ personaggio_id: null }),
      expect.any(Function),
    );
    expect(onCreated).toHaveBeenCalled();
    expect(staffGetPersonaggi).not.toHaveBeenCalled();
    view.unmount();
  });

  it('con personaggio e aumento chiede uno slot libero', async () => {
    vi.useFakeTimers();
    staffGetPersonaggi.mockResolvedValue({ results: [{ id: 8, nome: 'Ada' }] });
    staffGetPersonaggioDetail.mockResolvedValue({
      id: 8,
      nome: 'Ada',
      oggetti_inventario: [],
    });
    staffCreaIstanzaDaInfusione.mockResolvedValue({ detail: 'installata' });
    const view = mount(createElement(CreaIstanzaInfusioneModal, {
      open: true,
      infusione: { id: 11, nome: 'Occhio', tipo_risultato: 'AUM', slot_corpo_permessi: 'HD2' },
      onClose: vi.fn(),
      onLogout: vi.fn(),
      onCreated: vi.fn(),
    }));
    const input = document.body.querySelector('input');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'Ad');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      await vi.advanceTimersByTimeAsync(350);
    });
    const scelta = [...document.body.querySelectorAll('button')].find((b) => b.textContent.includes('Ada'));
    expect(scelta).toBeTruthy();
    await act(async () => {
      scelta.click();
      await Promise.resolve();
      await Promise.resolve();
    });
    expect(document.body.textContent).toContain('Slot corporeo libero');
    const slotSelect = [...document.body.querySelectorAll('select')].find((el) =>
      [...el.options].some((opt) => opt.value === 'HD2')
    );
    const hd1 = [...slotSelect.options].find((opt) => opt.value === 'HD1');
    expect(hd1.disabled).toBe(true);
    setSelect(slotSelect, 'HD2');
    const salva = [...document.body.querySelectorAll('button')].find((b) => b.textContent === 'Crea istanza');
    await act(async () => {
      salva.click();
    });
    expect(staffCreaIstanzaDaInfusione).toHaveBeenCalledWith(
      11,
      expect.objectContaining({ personaggio_id: 8, slot_corpo: 'HD2' }),
      expect.any(Function),
    );
    vi.useRealTimers();
    view.unmount();
  });
});
