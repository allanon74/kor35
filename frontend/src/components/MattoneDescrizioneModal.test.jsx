/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';

vi.mock('../api', () => ({
  resolveMediaUrl: (url) => url || '',
}));

vi.mock('./RichHtml', () => ({
  default: function RichHtmlStub({ content }) {
    return createElement('div', null, content);
  },
}));

import { MattoneInfoButton } from './MattoneDescrizioneModal';

const MATTONE = {
  id: 4,
  nome: 'Soffio',
  sigla: 'SOF',
  colore: '#135cd1',
  tipo_display: 'Mattone',
  descrizione_mattone: '<p>Un soffio che scalda il metallo.</p>',
  aura: { nome: 'Fuoco' },
  caratteristica_associata: { nome: 'Destrezza', sigla: 'DES' },
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

describe('MattoneInfoButton', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('apre la descrizione wiki e la chiude toccando il mattone', () => {
    const view = mount(createElement(MattoneInfoButton, { mattone: MATTONE }));
    expect(document.body.textContent).not.toContain('Un soffio che scalda il metallo.');

    const apri = view.host.querySelector('button');
    act(() => {
      apri.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).toContain('Un soffio che scalda il metallo.');
    expect(document.body.textContent).toContain('Soffio');
    expect(document.body.textContent).toContain('Tocca il mattone per chiudere');

    const chiudiMattone = document.body.querySelector('[aria-label="Chiudi Soffio"]');
    expect(chiudiMattone).toBeTruthy();
    act(() => {
      chiudiMattone.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(document.body.textContent).not.toContain('Un soffio che scalda il metallo.');
    view.unmount();
  });
});
