/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

const api = vi.hoisted(() => ({
  getProposte: vi.fn(),
}));

vi.mock('../api', () => api);
vi.mock('./CharacterContext', () => ({
  useCharacter: () => ({ selectedCharacterId: 7 }),
}));
vi.mock('./ProposalEditorModal', () => ({
  default: function EditorStub() {
    return null;
  },
}));
vi.mock('./RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', { 'data-testid': 'note-staff' }, content);
  },
}));

import ProposalManager from './ProposalManager';

const PROPOSTE = [
  {
    id: 1,
    tipo: 'TES',
    stato: 'VALUTAZIONE',
    nome: 'Soffio in coda',
    personaggio_nome: 'PG Nascosto',
    livello: 2,
    aura_details: { nome: 'Fuoco', colore: '#f00' },
    note_staff: '',
  },
  {
    id: 2,
    tipo: 'TES',
    stato: 'BOZZA',
    nome: 'Soffio da rivedere',
    personaggio_nome: 'PG Nascosto',
    livello: 2,
    aura_details: { nome: 'Fuoco', colore: '#f00' },
    note_staff: '<p>Manca il ragionamento sui mattoni.</p>',
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

describe('ProposalManager', () => {
  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  it('tiene la proposta rifiutata nelle bozze, con il nome della tecnica e le note', async () => {
    api.getProposte.mockResolvedValue(PROPOSTE);
    const view = mount(createElement(ProposalManager, { type: 'Tessitura', onClose: () => {} }));
    await flush();

    const testo = view.host.textContent;
    expect(testo).toContain('Soffio da rivedere');
    expect(testo).toContain('Soffio in coda');
    expect(testo).not.toContain('PG Nascosto');
    expect(testo).toContain('Manca il ragionamento sui mattoni.');
    expect(testo).toContain('Bozza da rivedere');
    expect(testo).toContain('In valutazione');

    const bozze = view.host.querySelector('[aria-label="Bozze"]');
    const coda = view.host.querySelector('[aria-label="In valutazione"]');
    expect(bozze.textContent).toContain('Soffio da rivedere');
    expect(bozze.textContent).not.toContain('Soffio in coda');
    expect(coda.textContent).toContain('Soffio in coda');
    expect(coda.textContent).not.toContain('Soffio da rivedere');

    view.unmount();
  });
});
