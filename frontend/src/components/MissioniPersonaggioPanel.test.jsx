/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  getMissioniMie: vi.fn(),
  proponiSoluzioneMissione: vi.fn(),
}));

vi.mock('../api', () => api);
vi.mock('./RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', { 'data-testid': 'descrizione-completa' }, content);
  },
}));

import MissioniPersonaggioPanel, { SOLUZIONE_DISCLAIMER } from './MissioniPersonaggioPanel';

const ROWS = [
  {
    id: 'task-aperta',
    titolo: 'Duello Leale',
    descrizione: 'Testo completo della task che non deve restare troncato dopo il click.',
    tipo_risoluzione: 'MANUALE',
    allineamento: 'LUMINOSA',
    reward_crediti: '10.00',
    reward_prestigio: 2,
    svolta: false,
    effettuabile: true,
    evento_soluzione_id: 3,
    eventi_ids: [3],
    proposta: null,
    is_korp_bonus: false,
  },
  {
    id: 'task-fatta',
    titolo: 'Studio sulla Fiamma Sacra',
    descrizione: 'Già svolta.',
    tipo_risoluzione: 'QUEST',
    allineamento: 'OSCURA',
    reward_crediti: '0.00',
    reward_prestigio: 1,
    svolta: true,
    effettuabile: false,
    eventi_ids: [3],
    proposta: { id: 'p1', stato: 'ACCETTATA', testo: 'Ho acceso la fiamma.', messaggio_rifiuto: '' },
    is_korp_bonus: false,
  },
];

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

describe('MissioniPersonaggioPanel', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('apre la descrizione, nasconde luminosa/oscura e tiene le completate', async () => {
    api.getMissioniMie.mockResolvedValue(ROWS);
    const view = mount(createElement(MissioniPersonaggioPanel, {
      personaggioId: 7,
      personaggioNome: 'Nyxen',
      standalone: true,
    }));
    await flush();

    expect(view.host.textContent).toContain('Duello Leale');
    expect(view.host.textContent).toContain('Studio sulla Fiamma Sacra');
    expect(view.host.textContent).toContain('Completate');
    expect(view.host.textContent).not.toMatch(/Luminosa|Oscura/);

    const apri = [...view.host.querySelectorAll('button')].find((btn) => btn.textContent.includes('Duello Leale'));
    expect(apri).toBeTruthy();
    await act(async () => {
      apri.click();
    });

    expect(view.host.querySelector('[data-testid="descrizione-completa"]').textContent)
      .toContain('Testo completo della task');
    expect(view.host.textContent).toContain(SOLUZIONE_DISCLAIMER);
    expect(view.host.querySelector('textarea')).toBeTruthy();

    view.unmount();
  });

  it('invia la soluzione della task aperta', async () => {
    api.getMissioniMie.mockResolvedValue(ROWS);
    api.proponiSoluzioneMissione.mockResolvedValue({ id: 'new', stato: 'IN_ATTESA' });
    const view = mount(createElement(MissioniPersonaggioPanel, { personaggioId: 7 }));
    await flush();

    const apri = [...view.host.querySelectorAll('button')].find((btn) => btn.textContent.includes('Duello Leale'));
    await act(async () => {
      apri.click();
    });
    const area = view.host.querySelector('textarea');
    await act(async () => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLTextAreaElement.prototype, 'value').set;
      setter.call(area, 'Ho duellato e non ho ricevuto il premio.');
      area.dispatchEvent(new Event('input', { bubbles: true }));
    });
    const invia = [...view.host.querySelectorAll('button')].find((btn) => btn.textContent.includes('Invia soluzione'));
    await act(async () => {
      invia.click();
    });
    await flush();

    expect(api.proponiSoluzioneMissione).toHaveBeenCalledWith({
      missione_id: 'task-aperta',
      evento_id: 3,
      personaggio_id: 7,
      testo: 'Ho duellato e non ho ricevuto il premio.',
    }, undefined);
    view.unmount();
  });
});
