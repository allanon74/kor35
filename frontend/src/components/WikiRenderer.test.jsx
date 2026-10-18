/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import { MemoryRouter } from 'react-router-dom';
import { CharacterContext } from './CharacterContext';
import { mergeGiocoEventoStato } from '../utils/giocoEventoStato';

vi.mock('./wg/WidgetTier', async () => {
  const React = await import('react');
  const { CharacterContext: Ctx } = await import('./CharacterContext');
  return {
    default: function MockWidgetTier({ id }) {
      const ctx = React.useContext(Ctx);
      const [n, setN] = React.useState(0);
      return React.createElement(
        'button',
        {
          type: 'button',
          'data-widget-tier': id,
          onClick: () => setN((v) => v + 1),
        },
        `${ctx?.marker ?? ''}:${n}`,
      );
    },
  };
});

import WikiRenderer from './WikiRenderer';

const PAGINA = [
  '<p id="lettura">Il medico di bordo conosce le infusioni.</p>',
  '<details id="sezione-medico"><summary>Medico</summary><div>Testo della professione</div></details>',
  '{{WIDGET_TIER:medici}}',
].join('');

const GLOSSARIO = [{
  sync_id: 'gloss-medico',
  nome: 'Medico',
  dichiarazione: 'medico',
  descrizione: '<p>Cura</p>',
}];

function Harness({ marker, content, glossaryEntries }) {
  return createElement(
    MemoryRouter,
    null,
    createElement(
      CharacterContext.Provider,
      { value: { marker, punteggiList: [] } },
      createElement(WikiRenderer, { content, glossaryEntries }),
    ),
  );
}

function mount(element) {
  const host = document.createElement('div');
  document.body.appendChild(host);
  const root = createRoot(host);
  act(() => {
    root.render(element);
  });
  return {
    host,
    rerender(next) {
      act(() => {
        root.render(next);
      });
    },
    unmount() {
      act(() => root.unmount());
      host.remove();
    },
  };
}

describe('mergeGiocoEventoStato', () => {
  const prev = {
    evento_aperto: false,
    evento_titolo: null,
    azioni_live_abilitate: false,
    bypass_evento_gate: false,
    transazioni_giocatore_abilitate: false,
    nodo_scan_abilitato: true,
    allibratore_codici_abilitati: false,
  };

  it('mantiene lo stesso oggetto se il poll non cambia nulla', () => {
    const next = mergeGiocoEventoStato(prev, {
      evento_aperto: 0,
      nodo_scan_abilitato: 1,
    });
    expect(next).toBe(prev);
  });

  it('sostituisce lo stato solo quando un flag cambia', () => {
    const next = mergeGiocoEventoStato(prev, { evento_aperto: true, evento_titolo: 'Bosco' });
    expect(next).not.toBe(prev);
    expect(next.evento_aperto).toBe(true);
    expect(next.evento_titolo).toBe('Bosco');
    expect(next.nodo_scan_abilitato).toBe(false);
  });
});

describe('WikiRenderer', () => {
  let view;

  afterEach(() => {
    view?.unmount();
    view = undefined;
    document.body.innerHTML = '';
  });

  it('non ricostruisce la pagina quando cambia solo il contesto personaggio', () => {
    view = mount(createElement(Harness, {
      marker: 'prima',
      content: PAGINA,
      glossaryEntries: GLOSSARIO,
    }));

    const paragrafo = view.host.querySelector('#lettura');
    const sezione = view.host.querySelector('#sezione-medico');
    expect(paragrafo).toBeTruthy();
    expect(view.host.querySelector('[data-widget-tier="medici"]').textContent).toBe('prima:0');

    sezione.open = true;
    const bottone = view.host.querySelector('[data-widget-tier="medici"]');
    act(() => {
      bottone.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(bottone.textContent).toBe('prima:1');

    view.rerender(createElement(Harness, {
      marker: 'dopo',
      content: PAGINA,
      glossaryEntries: GLOSSARIO.map((entry) => ({ ...entry })),
    }));

    expect(view.host.querySelector('#lettura')).toBe(paragrafo);
    expect(view.host.querySelector('#sezione-medico').open).toBe(true);
    expect(view.host.querySelector('[data-widget-tier="medici"]').textContent).toBe('dopo:1');
  });

  it('rimonta i widget solo se cambia il contenuto della pagina', () => {
    view = mount(createElement(Harness, { marker: 'prima', content: PAGINA, glossaryEntries: [] }));
    const bottone = view.host.querySelector('[data-widget-tier="medici"]');
    act(() => {
      bottone.dispatchEvent(new MouseEvent('click', { bubbles: true }));
    });
    expect(view.host.querySelector('[data-widget-tier="medici"]').textContent).toBe('prima:1');

    view.rerender(createElement(Harness, {
      marker: 'prima',
      content: '<p id="lettura">Altra pagina</p>{{WIDGET_TIER:medici}}',
      glossaryEntries: [],
    }));

    expect(view.host.querySelector('#lettura').textContent).toBe('Altra pagina');
    expect(view.host.querySelector('[data-widget-tier="medici"]').textContent).toBe('prima:0');
  });
});
