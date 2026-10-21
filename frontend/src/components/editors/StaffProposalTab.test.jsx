/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  staffGetProposteInValutazione: vi.fn(),
  staffRifiutaProposta: vi.fn(),
  staffApprovaProposta: vi.fn(),
  staffRegistraNotaProposta: vi.fn(),
  getEventi: vi.fn(),
  resolveMediaUrl: (url) => url || '',
}));

vi.mock('../../api', () => api);
vi.mock('../MissioneResolvePicker', () => ({ default: () => null }));
vi.mock('./SearchableSelect', () => ({ default: () => null }));
vi.mock('../RichTextEditor', () => ({
  default: function EditorStub({ value, onChange, placeholder, ariaLabel }) {
    return createElement('textarea', {
      'aria-label': ariaLabel || 'Nuova nota master',
      value: value || '',
      placeholder,
      onChange: (event) => onChange(event.target.value),
    });
  },
}));
vi.mock('../RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', null, content);
  },
}));

import StaffProposalTab from './StaffProposalTab';

const PROPOSTA = {
  id: 9,
  tipo: 'TES',
  nome: 'Soffio',
  stato: 'VALUTAZIONE',
  livello: 2,
  personaggio: 4,
  personaggio_nome: 'Ada',
  giocatore_nome: 'Lia',
  descrizione: '<p>Il ragionamento del giocatore.</p>',
  note_staff: '<p>Vecchia nota che non deve restare nel campo.</p>',
  note_log: [
    {
      id: 'invio',
      origine: 'INVIO',
      testo: 'Inviata per approvazione',
      creata_il: '2026-10-21T16:00:00Z',
    },
    {
      id: 'staff',
      origine: 'STAFF',
      testo: '<p>Vecchia nota che non deve restare nel campo.</p>',
      creata_il: '2026-10-21T18:00:00Z',
    },
  ],
  componenti: [
    {
      valore: 2,
      caratteristica: { id: 3, nome: 'Destrezza', sigla: 'DES' },
      mattone_nome: 'Soffio (DES)',
      mattone: {
        id: 4,
        nome: 'Soffio',
        colore: '#135cd1',
        tipo_display: 'Mattone',
        descrizione_mattone: '<p>Scalda il metallo.</p>',
        aura: { nome: 'Fuoco' },
        caratteristica_associata: { nome: 'Destrezza', sigla: 'DES' },
      },
    },
  ],
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

async function flush() {
  await act(async () => {
    await Promise.resolve();
    await Promise.resolve();
  });
}

describe('StaffProposalTab note e mattoni', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('mostra l\'ultima nota fuori dal campo, lo storico al click e la scheda del mattone', async () => {
    api.staffGetProposteInValutazione.mockResolvedValue([PROPOSTA]);
    api.getEventi.mockResolvedValue([]);
    const view = mount(createElement(StaffProposalTab, { onLogout: () => {} }));
    await flush();

    const valuta = [...document.body.querySelectorAll('button')].find((button) => button.textContent.includes('Valuta'));
    expect(valuta).toBeTruthy();
    act(() => {
      valuta.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });

    const campo = document.body.querySelector('textarea[aria-label="Nuova nota master"]');
    expect(campo).toBeTruthy();
    expect(campo.value).toBe('');
    expect(document.body.textContent).toContain('Vecchia nota che non deve restare nel campo.');
    expect(document.body.textContent).not.toContain('Inviata per approvazione');

    const storico = [...document.body.querySelectorAll('button')].find((button) => button.textContent.includes('Ultima nota'));
    act(() => {
      storico.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).toContain('Inviata per approvazione');

    const info = document.body.querySelector('button[aria-label="Mostra descrizione di Soffio"]');
    expect(info).toBeTruthy();
    act(() => {
      info.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).toContain('Scalda il metallo.');

    const chiudi = document.body.querySelector('[aria-label="Chiudi Soffio"]');
    act(() => {
      chiudi.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).not.toContain('Scalda il metallo.');

    const registra = [...document.body.querySelectorAll('button')].find((button) => button.textContent.includes('Registra nota'));
    expect(registra.disabled).toBe(true);

    view.unmount();
  });
});
