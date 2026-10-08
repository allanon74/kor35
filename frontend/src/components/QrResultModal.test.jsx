/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement, useState } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  acquisisciItem: vi.fn(),
  richiediTransazione: vi.fn(),
  rubaOggetto: vi.fn(),
  createTransazioneAvanzata: vi.fn(),
  resolveMediaUrl: (url) => url || '',
  salvaDocumentoArchivio: vi.fn(),
  prendiDaInventarioQr: vi.fn(),
  fetchNegozioMercanteListino: vi.fn(),
  acquistaNegozioMercante: vi.fn(),
  vendiOggettoNegozioMercante: vi.fn(),
  restituisciPrestitoNegozioMercante: vi.fn(),
  previewVenditaNegozioMercante: vi.fn(),
  searchPersonaggi: vi.fn(),
  getBodySlots: () => [],
}));

vi.mock('../api', () => api);
vi.mock('./CharacterContext', () => ({
  useCharacter: () => ({
    selectedCharacterId: 7,
    selectedCharacterData: { nome: "Tamak'ti Emporio", crediti: 12, oggetti: [] },
    refreshCharacterData: vi.fn(),
  }),
}));
vi.mock('../hooks/useTimers', () => ({
  useTimers: () => ({ addTimer: vi.fn() }),
}));
vi.mock('../utils/toastBus', () => ({ emitToast: vi.fn() }));

import QrResultModal from './QrResultModal';

const DIECI_MINUTI = 10 * 60 * 1000;

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

function bottoneConTesto(testo) {
  return [...document.querySelectorAll('button')].find((nodo) => nodo.textContent.includes(testo));
}

afterEach(() => {
  document.body.innerHTML = '';
  vi.useRealTimers();
  vi.clearAllMocks();
});

describe('QrResultModal resta aperta', () => {
  it('il negozio non si chiude al mount, col fondale o con Escape', async () => {
    const onClose = vi.fn();
    const view = mount(createElement(QrResultModal, {
      data: {
        tipo_modello: 'negozio_mercante',
        qrcode_id: 'shop-inventurium',
        dati: { negozio_id: 3, nome: 'Inventurium', aperto: true, voci: [] },
      },
      onClose,
      onLogout: vi.fn(),
    }));

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 80));
    });

    expect(document.body.textContent).toContain('Inventurium');
    expect(document.body.textContent).toContain('Risultato Scansione');
    expect(document.querySelector('[data-headlessui-portal]')).toBeNull();
    expect(onClose).not.toHaveBeenCalled();

    const fondale = document.querySelector('.fixed.inset-0');
    await act(async () => {
      fondale?.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }));
      fondale?.dispatchEvent(new PointerEvent('pointerup', { bubbles: true }));
      fondale?.dispatchEvent(new MouseEvent('click', { bubbles: true }));
      document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    });
    expect(onClose).not.toHaveBeenCalled();

    const chiudiNegozio = document.querySelector('[aria-label="Chiudi negozio"]');
    expect(chiudiNegozio).toBeTruthy();
    await act(async () => {
      chiudiNegozio.click();
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    view.unmount();
  });

  it('dopo aver preso un oggetto o una tecnica la finestra resta aperta', async () => {
    api.acquisisciItem.mockResolvedValue({ success: 'Oggetto acquisito!' });
    const onClose = vi.fn();
    const view = mount(createElement(QrResultModal, {
      data: {
        tipo_modello: 'oggetto',
        qrcode_id: 9,
        dati: {
          qr_code_id: 9,
          nome: 'Scheggia',
          descrizione: 'Una scheggia',
          puo_acquisire_da_qr: true,
        },
      },
      onClose,
      onLogout: vi.fn(),
    }));

    await act(async () => {
      bottoneConTesto('Acquisisci').click();
    });
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 30));
    });
    expect(document.body.textContent).toContain('Oggetto acquisito!');

    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 2200));
    });
    expect(onClose).not.toHaveBeenCalled();
    expect(bottoneConTesto('Chiudi')).toBeTruthy();
    view.unmount();
  });

  it('si chiude da sola solo dopo 10 minuti', async () => {
    vi.useFakeTimers();
    const onClose = vi.fn();
    const view = mount(createElement(QrResultModal, {
      data: { tipo_modello: 'errore', qrcode_id: 'err-1', messaggio: 'QR non disponibile.' },
      onClose,
      onLogout: vi.fn(),
    }));

    await act(async () => {
      vi.advanceTimersByTime(DIECI_MINUTI - 1);
    });
    expect(onClose).not.toHaveBeenCalled();

    await act(async () => {
      vi.advanceTimersByTime(1);
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    view.unmount();
  });

  it('il negozio non si rimonta quando il genitore ridisegna', async () => {
    const onClose = vi.fn();
    const dati = { negozio_id: 3, nome: 'Inventurium', aperto: true, voci: [] };

    function Harness() {
      const [tick, setTick] = useState(0);
      return createElement(
        'div',
        null,
        createElement(
          'button',
          { type: 'button', onClick: () => setTick((n) => n + 1) },
          `ridisegna ${tick}`,
        ),
        createElement(QrResultModal, {
          data: { tipo_modello: 'negozio_mercante', qrcode_id: 'shop-inventurium', dati },
          onClose,
          onLogout: vi.fn(),
        }),
      );
    }

    const view = mount(createElement(Harness));
    await act(async () => {
      await new Promise((resolve) => setTimeout(resolve, 80));
    });
    const titolo = [...document.querySelectorAll('h2, [id]')].find((nodo) => nodo.textContent.includes('Inventurium'));
    expect(titolo).toBeTruthy();

    await act(async () => {
      bottoneConTesto('ridisegna').click();
    });
    await act(async () => {
      bottoneConTesto('ridisegna').click();
    });

    expect(titolo.isConnected).toBe(true);
    expect(document.body.textContent).toContain('Inventurium');
    expect(onClose).not.toHaveBeenCalled();
    view.unmount();
  });

  it('Chiudi è una chiusura deliberata', async () => {
    const onClose = vi.fn();
    const view = mount(createElement(QrResultModal, {
      data: { tipo_modello: 'testo', qrcode_id: 'txt-1', dati: { nome: 'Avviso', testo: 'Leggimi' } },
      onClose,
      onLogout: vi.fn(),
    }));
    expect(onClose).not.toHaveBeenCalled();
    await act(async () => {
      bottoneConTesto('Chiudi').click();
    });
    expect(onClose).toHaveBeenCalledTimes(1);
    view.unmount();
  });
});
