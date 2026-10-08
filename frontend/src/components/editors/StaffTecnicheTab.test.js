/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import StaffTecnicheTab from './StaffTecnicheTab';
import {
  staffPersonaggioAssegnaTecnica,
  staffPersonaggioCatalogoTecniche,
  staffPersonaggioRimuoviTecnica,
} from '../../api';

vi.mock('../../api', () => ({
  staffPersonaggioCatalogoTecniche: vi.fn(),
  staffPersonaggioAssegnaTecnica: vi.fn(),
  staffPersonaggioRimuoviTecnica: vi.fn(),
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

describe('StaffTecnicheTab', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('mostra le possedute e assegna in omaggio dal catalogo', async () => {
    staffPersonaggioCatalogoTecniche.mockResolvedValue([
      { id: 7, nome: 'Brace', livello: 1, aura: 'Fuoco', non_acquistabile: false },
    ]);
    staffPersonaggioAssegnaTecnica.mockResolvedValue({ infusioni_possedute: [] });
    const onUpdated = vi.fn();
    const detail = {
      id: 42,
      infusioni_possedute: [
        { id: 3, nome: 'Fiamma nota', livello: 2, aura: 'Sacra', costo_crediti_pagato: '12.00' },
      ],
      cerimoniali_posseduti: [],
      tessiture_possedute: [],
    };

    const { host, unmount } = mount(
      createElement(StaffTecnicheTab, { detail, onLogout: () => {}, onUpdated, onError: () => {} }),
    );

    await act(async () => {
      await Promise.resolve();
    });

    expect(host.textContent).toContain('Fiamma nota');
    expect(host.textContent).toContain('pagati 12.00 CR');
    expect(staffPersonaggioCatalogoTecniche).toHaveBeenCalledWith(42, 'infusione', expect.any(Function));

    const select = host.querySelector('select');
    expect(select).toBeTruthy();
    await act(async () => {
      select.value = '7';
      select.dispatchEvent(new Event('change', { bubbles: true }));
    });

    const omaggio = host.querySelector('input[type="checkbox"]');
    await act(async () => {
      omaggio.click();
    });

    const assegnaBtn = [...host.querySelectorAll('button')].find((b) => b.textContent === 'Assegna');
    expect(assegnaBtn.disabled).toBe(false);
    await act(async () => {
      assegnaBtn.click();
    });
    await act(async () => {
      await Promise.resolve();
    });

    expect(staffPersonaggioAssegnaTecnica).toHaveBeenCalledWith(
      42,
      expect.objectContaining({ tipo: 'infusione', tecnicaId: 7, omaggio: true }),
      expect.any(Function),
    );
    expect(onUpdated).toHaveBeenCalled();
    expect(staffPersonaggioRimuoviTecnica).not.toHaveBeenCalled();
    unmount();
  });

  it('passa ai cerimoniali e mostra lo stato vuoto', async () => {
    staffPersonaggioCatalogoTecniche.mockResolvedValue([]);
    const detail = {
      id: 9,
      infusioni_possedute: [{ id: 1, nome: 'X', livello: 0, costo_crediti_pagato: '0.00' }],
      cerimoniali_posseduti: [],
      tessiture_possedute: [],
    };
    const { host, unmount } = mount(
      createElement(StaffTecnicheTab, { detail, onLogout: () => {}, onUpdated: () => {}, onError: () => {} }),
    );
    const cer = [...host.querySelectorAll('button')].find((b) => b.textContent.includes('Cer'));
    await act(async () => {
      cer.click();
    });
    expect(host.textContent).toContain('Nessun cerimoniale posseduto.');
    expect(staffPersonaggioCatalogoTecniche).toHaveBeenCalledWith(9, 'cerimoniale', expect.any(Function));
    unmount();
  });
});