/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

vi.mock('./RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', null, content);
  },
}));

import NotePropostaElenco from './NotePropostaElenco';

const PROPOSTA = {
  note_staff: '',
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
      testo: '<p>Manca il ragionamento sui mattoni.</p>',
      creata_il: '2026-10-21T18:30:00Z',
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

describe('NotePropostaElenco', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('mostra l\'ultima nota e apre lo storico al click', () => {
    const view = mount(createElement(NotePropostaElenco, { proposta: PROPOSTA }));
    const testo = view.host.textContent;
    expect(testo).toContain('Ultima nota');
    expect(testo).toContain('Manca il ragionamento sui mattoni.');
    expect(testo).not.toContain('Inviata per approvazione');

    const pulsante = view.host.querySelector('button');
    act(() => {
      pulsante.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(view.host.textContent).toContain('Inviata per approvazione');
    expect(view.host.textContent).toContain('Manca il ragionamento sui mattoni.');

    act(() => {
      pulsante.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(view.host.textContent).not.toContain('Inviata per approvazione');
    view.unmount();
  });

  it('usa la nota staff legacy se lo storico non è ancora arrivato', () => {
    const view = mount(createElement(NotePropostaElenco, {
      proposta: { note_staff: '<p>Sistema il testo.</p>', note_log: [] },
    }));
    expect(view.host.textContent).toContain('Sistema il testo.');
    view.unmount();
  });
});
