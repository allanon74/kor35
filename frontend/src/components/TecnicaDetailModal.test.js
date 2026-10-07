/**
 * @vitest-environment jsdom
 */
import { afterEach, describe, expect, it } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import TecnicaDetailModal from './TecnicaDetailModal';

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

const infusione = {
  nome: 'Lama di vetro',
  livello: 2,
  testo: '<p>Taglia.</p>',
  costo_pieno: 200,
  costo_effettivo: 200,
  costo_realizzazione: 300,
  tempo_realizzazione_secondi: 180,
  costi_attivazione: [],
  componenti: [],
};

describe('TecnicaDetailModal realizzazione infusione', () => {
  afterEach(() => {
    document.body.innerHTML = '';
  });

  it('mostra costo e tempo per realizzare l oggetto', () => {
    const { host, unmount } = mount(createElement(TecnicaDetailModal, {
      tecnica: infusione,
      type: 'Infusione',
      onClose: () => {},
    }));

    expect(host.textContent).toMatch(/Realizzazione oggetto/);
    expect(host.textContent).toMatch(/300 CR/);
    expect(host.textContent).toMatch(/3 min/);
    expect(host.textContent).toMatch(/200 CR/);
    unmount();
  });

  it('non mostra la realizzazione sulle tessiture', () => {
    const { host, unmount } = mount(createElement(TecnicaDetailModal, {
      tecnica: { ...infusione, nome: 'Sigillo' },
      type: 'Tessitura',
      onClose: () => {},
    }));

    expect(host.textContent).not.toMatch(/Realizzazione oggetto/);
    expect(host.textContent).not.toMatch(/300 CR/);
    unmount();
  });

  it('resta usabile su viewport stretta', () => {
    const { host, unmount } = mount(createElement(TecnicaDetailModal, {
      tecnica: infusione,
      type: 'Infusione',
      onClose: () => {},
    }));

    const pannello = host.querySelector('.overflow-y-auto');
    expect(pannello).toBeTruthy();
    expect(pannello.className).toContain('max-h-[92vh]');
    const titolo = [...host.querySelectorAll('h3')].find((nodo) =>
      nodo.textContent?.includes('Realizzazione oggetto')
    );
    const blocco = titolo?.nextElementSibling;
    expect(blocco?.className).toContain('flex-col');
    expect(blocco?.className).toContain('sm:flex-row');
    unmount();
  });
});
