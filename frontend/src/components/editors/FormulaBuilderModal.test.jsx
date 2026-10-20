/**
 * @vitest-environment jsdom
 *
 * Infusioni e oggetti non passano elementoOptions: la tendina di override
 * deve riempirsi dal catalogo semantico (mattoni AMA).
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, createElement } from 'react';
import { createRoot } from 'react-dom/client';
import FormulaBuilderModal, { FORMULA_BUILDER_OVERLAY_Z_CLASS } from './FormulaBuilderModal';
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
    const modal = document.body.querySelector('[data-testid="formula-builder-modal"]');
    expect(modal).toBeTruthy();
    expect(host.contains(modal)).toBe(false);
    const elementoBtn = [...modal.querySelectorAll('button')].find((btn) =>
      btn.textContent.includes('Elemento principale'),
    );
    expect(elementoBtn).toBeTruthy();
    await act(async () => {
      elementoBtn.click();
    });

    const select = [...modal.querySelectorAll('select')].find((node) =>
      [...node.options].some((opt) => opt.textContent === 'Fuoco'),
    );
    expect(select).toBeTruthy();
    const labels = [...select.options].map((opt) => opt.textContent);
    expect(labels).toContain('Fuoco');
    expect(labels).toContain('Gelo');
    unmount();
  });

  it('con Capacità mostra il danno e Applica resta sopra la barra Salva', async () => {
    staffGetFormulaBuilderSchema.mockResolvedValue({
      default_template: '{formula_source}',
      types: [
        { id: 'attack', label: 'Attacco' },
        { id: 'capacity', label: 'Capacità' },
      ],
      type_templates: {
        attack: ['formula_source'],
        capacity: ['capacity_header', 'formula_prefix', 'formula_source', 'formula_damage_mode', 'formula_status'],
      },
      sections: [
        {
          id: 'formula_source',
          label: 'Sorgente (combinabile)',
          kind: 'multi',
          options: [{ id: 'mental', label: 'Mental', stats: {} }],
        },
        {
          id: 'formula_damage_mode',
          label: 'Sezione danno',
          kind: 'single',
          options: [
            { id: 'none', label: 'Nessun danno', stats: {} },
            { id: 'mischia', label: 'Danni mischia (dannimis+dannigen)', stats: {} },
            { id: 'distanza', label: 'Danni distanza (dannidis+dannigen)', stats: {} },
          ],
        },
      ],
    });
    staffGetFormulaSemanticOptions.mockResolvedValue({ elementi_mattoni: [] });
    staffPreviewFormulaBuilder.mockResolvedValue({
      formula_rendered: 'Capacità ScanLink:',
      formula_template: 'Capacità ScanLink:',
      stats_by_param: {},
    });

    const footer = document.createElement('div');
    footer.dataset.testid = 'staff-editor-mobile-footer';
    footer.className = 'fixed inset-x-0 bottom-0 z-[130]';
    footer.textContent = 'Salva tecnica';
    document.body.appendChild(footer);

    const { host, unmount } = mount(
      createElement(FormulaBuilderModal, {
        open: true,
        onClose: () => {},
        onApply: () => {},
        onLogout: () => {},
        entityName: 'ScanLink',
        statsOptions: [],
        statisticheBase: [],
        elementoOptions: [],
      }),
    );

    await flush();
    await flush();

    const modal = document.body.querySelector('[data-testid="formula-builder-modal"]');
    expect(host.contains(modal)).toBe(false);
    expect(modal.className).toContain(FORMULA_BUILDER_OVERLAY_Z_CLASS);
    const overlayZ = Number(FORMULA_BUILDER_OVERLAY_Z_CLASS.match(/z-\[(\d+)\]/)[1]);
    expect(overlayZ).toBeGreaterThan(130);

    const applica = [...modal.querySelectorAll('button')].find((btn) => btn.textContent.trim() === 'Applica');
    expect(applica).toBeTruthy();
    expect(modal.querySelector('.overflow-y-auto').contains(applica)).toBe(false);

    const tipo = modal.querySelector('select');
    await act(async () => {
      tipo.value = 'capacity';
      tipo.dispatchEvent(new Event('change', { bubbles: true }));
    });

    expect(modal.textContent).toContain('Danni mischia (dannimis+dannigen)');
    expect(modal.textContent).toContain('Danni distanza (dannidis+dannigen)');
    expect(modal.textContent).toContain('dannimis');
    expect(modal.textContent).toContain('dannidis');
    unmount();
  });
});
