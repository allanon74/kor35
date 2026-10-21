/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const personaggio = vi.hoisted(() => ({
  id: 7,
  punteggi_base: { Fuoco: 3, Destrezza: 4 },
  bonus_caratteristica_contestuali: [],
  modelli_aura: [],
}));

const api = vi.hoisted(() => ({
  createProposta: vi.fn(),
  updateProposta: vi.fn(),
  sendProposta: vi.fn(),
  deleteProposta: vi.fn(),
  getAllPunteggi: vi.fn(),
  getMattoniAura: vi.fn(),
  getClassiOggetto: vi.fn(),
  resolveMediaUrl: (url) => url || '',
}));

vi.mock('../api', () => api);
vi.mock('./CharacterContext', () => ({
  useCharacter: () => ({
    selectedCharacterId: 7,
    selectedCharacterData: personaggio,
  }),
}));
vi.mock('./RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', null, content);
  },
}));

import ProposalEditorModal from './ProposalEditorModal';

const MATTONE = {
  id: 4,
  nome: 'Soffio',
  sigla: 'SOF',
  colore: '#135cd1',
  tipo_display: 'Mattone',
  descrizione_mattone: '<p>Scalda il metallo del giocatore.</p>',
  aura: { nome: 'Fuoco' },
  caratteristica_associata: { id: 3, nome: 'Destrezza', sigla: 'DES' },
};

function mount(element) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(element);
  });
  return {
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

describe('ProposalEditorModal', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('mostra l\'ultima nota e la descrizione dei mattoni selezionabili', async () => {
    api.getAllPunteggi.mockResolvedValue([
      { id: 10, tipo: 'AU', nome: 'Fuoco', sigla: 'FUO', permette_tessiture: true, aure_infusione_consentite: [10] },
      { id: 3, tipo: 'CA', nome: 'Destrezza', sigla: 'DES' },
    ]);
    api.getMattoniAura.mockResolvedValue({
      mattoni: [MATTONE],
      obbligatorie_caratteristica_ids: [],
    });

    const view = mount(createElement(ProposalEditorModal, {
      type: 'Tessitura',
      onClose: () => {},
      onRefresh: () => {},
      proposal: {
        id: 1,
        stato: 'BOZZA',
        nome: 'Soffio di brace',
        aura: 10,
        descrizione: 'testo',
        note_staff: '<p>Vecchia nota staff.</p>',
        note_log: [
          { id: 'invio', origine: 'INVIO', testo: 'Inviata per approvazione', creata_il: '2026-10-21T16:00:00Z' },
          { id: 'staff', origine: 'STAFF', testo: '<p>Vecchia nota staff.</p>', creata_il: '2026-10-21T18:00:00Z' },
        ],
        componenti: [],
      },
    }));
    await flush();

    expect(document.body.textContent).toContain('Vecchia nota staff.');
    expect(document.body.textContent).not.toContain('Inviata per approvazione');

    const info = document.body.querySelector('button[aria-label="Mostra descrizione di Soffio"]');
    expect(info).toBeTruthy();
    act(() => {
      info.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).toContain('Scalda il metallo del giocatore.');

    act(() => {
      document.body.querySelector('[aria-label="Chiudi Soffio"]').dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).not.toContain('Scalda il metallo del giocatore.');
    view.unmount();
  });
});
