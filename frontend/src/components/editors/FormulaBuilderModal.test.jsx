/**
 * @vitest-environment jsdom
 *
 * Infusioni e oggetti non passano elementoOptions: la tendina di override
 * deve riempirsi dal catalogo semantico (mattoni AMA).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import FormulaBuilderModal from './FormulaBuilderModal';
import {
  staffGetFormulaBuilderSchema,
  staffGetFormulaSemanticOptions,
  staffPreviewFormulaBuilder,
} from '../../api';

vi.mock('../../api', () => ({
  staffGetFormulaBuilderSchema: vi.fn(),
  staffGetFormulaSemanticOptions: vi.fn(),
  staffPreviewFormulaBuilder: vi.fn(),
}));

const schema = {
  default_template: '{formula_source}',
  types: [{ id: 'attack', label: 'Attacco' }],
  type_templates: { attack: ['formula_source'] },
  sections: [
    {
      id: 'formula_source',
      label: 'Sorgente (combinabile)',
      kind: 'multi',
      options: [
        { id: 'chop', label: 'Chop', stats: {} },
        { id: 'elemento_principale', label: 'Elemento principale (tessitura)', stats: {} },
      ],
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
    await new Promise((resolve) => setTimeout(resolve, 0));
  });
}

describe('FormulaBuilderModal override elementi', () => {
  afterEach(() => {
    vi.clearAllMocks();
    document.body.innerHTML = '';
  });

  it('valorizza la tendina di override anche senza elementoOptions', async () => {
    staffGetFormulaBuilderSchema.mockResolvedValue(schema);
    staffGetFormulaSemanticOptions.mockResolvedValue({
      elementi_mattoni: [
        { id: 11, nome: 'Fuoco', dichiarazione: 'Fuoco', label: 'Fuoco' },
        { id: 12, nome: 'Gelo', dichiarazione: 'Gelo', label: 'Gelo' },
      ],
    });
    staffPreviewFormulaBuilder.mockResolvedValue({
      formula_rendered: 'preview',
      formula_template: '{formula_source}',
      stats_by_param: {},
    });

    const onLogout = () => {};
    const { host, unmount } = mount(
      createElement(FormulaBuilderModal, {
        open: true,
        onClose: () => {},
        onApply: () => {},
        onLogout,
        entityName: "Marchio Aker'Atlan - Delta",
        statsOptions: [],
        statisticheBase: [],
        elementoOptions: [],
      }),
    );

    await flush();
    await flush();

    expect(staffGetFormulaSemanticOptions).toHaveBeenCalled();
    const elementoBtn = [...host.querySelectorAll('button')].find((btn) =>
      btn.textContent.includes('Elemento principale'),
    );
    expect(elementoBtn).toBeTruthy();
    await act(async () => {
      elementoBtn.click();
    });

    const select = [...host.querySelectorAll('select')].find((node) =>
      [...node.options].some((opt) => opt.textContent === 'Fuoco'),
    );
    expect(select).toBeTruthy();
    const labels = [...select.options].map((opt) => opt.textContent);
    expect(labels).toContain('Fuoco');
    expect(labels).toContain('Gelo');
    unmount();
  });
});
