/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import SondaggioCompilazione from './SondaggioCompilazione';

const sondaggio = {
  id: 's1',
  titolo: 'Chiusura',
  descrizione: 'Due minuti.',
  gia_risposto: false,
  consenti_modifica: false,
  domande: [
    {
      id: 'entry.1',
      titolo: 'Nome',
      tipo: 'testo_breve',
      obbligatoria: true,
      supportata: true,
      opzioni: [],
    },
    {
      id: 'entry.2',
      titolo: 'Ruolo',
      tipo: 'scelta_singola',
      obbligatoria: true,
      supportata: true,
      opzioni: ['Tank', 'Healer'],
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

describe('SondaggioCompilazione', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('blocca l\'invio se manca una risposta obbligatoria', () => {
    const onInvia = vi.fn();
    const { host, unmount } = mount(createElement(SondaggioCompilazione, { sondaggio, onInvia }));
    const form = host.querySelector('form');
    act(() => {
      form.dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(onInvia).not.toHaveBeenCalled();
    expect(host.textContent).toContain('Rispondi a «Nome»');
    unmount();
  });

  it('invia testo e scelta singola', () => {
    const onInvia = vi.fn();
    const { host, unmount } = mount(createElement(SondaggioCompilazione, { sondaggio, onInvia }));
    const input = host.querySelector('input[type="text"]');
    const radio = host.querySelector('input[value="Healer"]');
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'Ada');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      radio.click();
    });
    act(() => {
      host.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(onInvia).toHaveBeenCalledWith({ 'entry.1': 'Ada', 'entry.2': 'Healer' });
    unmount();
  });

  it('mostra la risposta già inviata senza richiedere un nuovo invio', () => {
    const compilato = {
      ...sondaggio,
      gia_risposto: true,
      mia_risposta: { 'entry.1': 'Ada', 'entry.2': 'Tank' },
    };
    const { host, unmount } = mount(createElement(SondaggioCompilazione, { sondaggio: compilato, onInvia: vi.fn() }));
    expect(host.textContent).toContain('Risposta registrata');
    expect(host.textContent).toContain('Ada');
    expect(host.querySelector('form')).toBeNull();
    unmount();
  });
});
