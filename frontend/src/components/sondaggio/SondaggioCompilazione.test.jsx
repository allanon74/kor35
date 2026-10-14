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

  it('invia il livello scelto sulle stelle', () => {
    const conStelle = {
      ...sondaggio,
      domande: [
        ...sondaggio.domande,
        {
          id: 'entry.9',
          titolo: 'Come valuti le missioni',
          tipo: 'valutazione',
          obbligatoria: true,
          supportata: true,
          opzioni: ['1', '2', '3', '4', '5'],
          scala_min: 1,
          scala_max: 5,
        },
      ],
    };
    const onInvia = vi.fn();
    const { host, unmount } = mount(createElement(SondaggioCompilazione, { sondaggio: conStelle, onInvia }));
    const input = host.querySelector('input[type="text"]');
    const radio = host.querySelector('input[value="Tank"]');
    const stella = host.querySelector('button[aria-label="4 su 5"]');
    act(() => {
      const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
      setter.call(input, 'Ada');
      input.dispatchEvent(new Event('input', { bubbles: true }));
      radio.click();
      stella.click();
    });
    act(() => {
      host.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(onInvia).toHaveBeenCalledWith({ 'entry.1': 'Ada', 'entry.2': 'Tank', 'entry.9': '4' });
    expect(host.textContent).not.toContain('solo sul modulo Google');
    unmount();
  });

  it('invia una scelta per ogni riga della griglia', () => {
    const conGriglia = {
      ...sondaggio,
      domande: [
        {
          id: 'griglia.1',
          titolo: 'Come valuti le missioni legate ai voli della Mist Glider?',
          tipo: 'griglia',
          obbligatoria: true,
          supportata: true,
          opzioni: ['Scadente', 'Buono', 'Ottimo'],
          righe: [
            { id: 'entry.11', titolo: 'Divertimento', obbligatoria: true, opzioni: ['Scadente', 'Buono', 'Ottimo'] },
            { id: 'entry.12', titolo: 'Immersione', obbligatoria: true, opzioni: ['Scadente', 'Buono', 'Ottimo'] },
          ],
        },
      ],
    };
    const onInvia = vi.fn();
    const { host, unmount } = mount(createElement(SondaggioCompilazione, { sondaggio: conGriglia, onInvia }));
    act(() => {
      host.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(onInvia).not.toHaveBeenCalled();
    expect(host.textContent).toContain('Divertimento');
    const bottoni = host.querySelectorAll('button[type="button"]');
    const buono = [...bottoni].find((nodo) => nodo.textContent === 'Buono');
    const ottimo = [...bottoni].filter((nodo) => nodo.textContent === 'Ottimo');
    act(() => {
      buono.click();
      ottimo[1].click();
    });
    act(() => {
      host.querySelector('form').dispatchEvent(new Event('submit', { bubbles: true, cancelable: true }));
    });
    expect(onInvia).toHaveBeenCalledWith({ 'entry.11': 'Buono', 'entry.12': 'Ottimo' });
    expect(host.textContent).not.toContain('solo sul modulo Google');
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
