import React, { useEffect, useMemo, useState } from 'react';
import { staffGetFormulaBuilderSchema, staffPreviewFormulaBuilder } from '../../api';

const FormulaBuilderModal = ({
  open,
  onClose,
  onApply,
  onLogout,
  statsOptions = [],
  statisticheBase = [],
  formulaValue = '',
  defaultFormulaType = 'attack',
}) => {
  const [schema, setSchema] = useState(null);
  const [formulaType, setFormulaType] = useState(defaultFormulaType);
  const [selections, setSelections] = useState({});
  const [customText, setCustomText] = useState('');
  const [preview, setPreview] = useState('');
  const [loadingPreview, setLoadingPreview] = useState(false);
  const [numericValues, setNumericValues] = useState({
    rango: 1,
    molt: 1,
    durata: 10,
    cura: 0,
    curapf: 0,
    livello: 1,
    gittata: 3,
    dcono: 10,
    area: 5,
    dannigen: 0,
    dannimis: 0,
    dannidis: 0,
  });
  const [includeCura, setIncludeCura] = useState(false);

  const statsByParamFromForm = useMemo(() => {
    const byId = new Map(statsOptions.map((s) => [String(s.id), s]));
    const out = {};
    (statisticheBase || []).forEach((item) => {
      const statId = String(item.statistica?.id || item.statistica || '');
      const stat = byId.get(statId);
      const parametro = stat?.parametro;
      if (parametro) {
        out[parametro] = Number(item.valore_base || 0);
      }
    });
    return out;
  }, [statisticheBase, statsOptions]);

  useEffect(() => {
    if (!open) {
      return;
    }
    setFormulaType(defaultFormulaType || 'attack');
    staffGetFormulaBuilderSchema(onLogout)
      .then((data) => setSchema(data || null))
      .catch((err) => console.error('Errore schema formula builder:', err));
  }, [open, onLogout, defaultFormulaType]);

  useEffect(() => {
    if (!open || !schema) {
      return;
    }
    setLoadingPreview(true);
    staffPreviewFormulaBuilder(
      {
        formula: '',
        formula_type: formulaType,
        stats_by_param: { ...statsByParamFromForm, ...numericValues },
        selections: { ...selections, include_cura: includeCura },
        custom_text: customText,
      },
      onLogout
    )
      .then((res) => setPreview(res?.formula_rendered || ''))
      .catch((err) => {
        console.error('Errore preview formula:', err);
        setPreview('Errore preview formula.');
      })
      .finally(() => setLoadingPreview(false));
  }, [open, schema, formulaType, selections, includeCura, customText, formulaValue, statsByParamFromForm, numericValues, onLogout]);

  if (!open) {
    return null;
  }

  const setSelectionValue = (sectionId, value, isMulti) => {
    setSelections((prev) => {
      if (!isMulti) {
        return { ...prev, [sectionId]: value };
      }
      const current = Array.isArray(prev[sectionId]) ? prev[sectionId] : [];
      const next = current.includes(value)
        ? current.filter((x) => x !== value)
        : [...current, value];
      return { ...prev, [sectionId]: next };
    });
  };

  const handleApply = async () => {
    try {
      const res = await staffPreviewFormulaBuilder(
        {
          formula: '',
          formula_type: formulaType,
          stats_by_param: { ...statsByParamFromForm, ...numericValues },
          selections: { ...selections, include_cura: includeCura },
          custom_text: customText,
        },
        onLogout
      );
      onApply?.({
        statsByParam: res?.stats_by_param || {},
        formulaText: (res?.formula_template || schema?.default_template || '').trim(),
        customText: customText.trim(),
        controlledParams: [...getControlledParams(schema), ...NUMERIC_CONTROLLED_PARAMS],
      });
      onClose?.();
    } catch (err) {
      console.error('Errore apply formula builder:', err);
    }
  };

  return (
    <div className="fixed inset-0 z-[10000] bg-black/70 flex items-center justify-center p-4">
      <div className="w-full max-w-5xl max-h-[90vh] overflow-y-auto bg-gray-900 border border-gray-700 rounded-xl shadow-2xl">
        <div className="p-4 border-b border-gray-700 flex justify-between items-center">
          <h3 className="text-lg font-bold text-white">Costruisci formula</h3>
          <button onClick={onClose} className="px-3 py-1 rounded bg-gray-700 text-white text-sm">Chiudi</button>
        </div>
        <div className="p-4 space-y-4">
          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Tipo formula</div>
            <select
              value={formulaType}
              onChange={(e) => setFormulaType(e.target.value)}
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
            >
              {(schema?.types || []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          {schema?.sections?.map((section) => {
            const isMulti = section.kind === 'multi';
            const selected = selections[section.id];
            return (
              <div key={section.id} className="border border-gray-700 rounded-lg p-3">
                <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">{section.label}</div>
                <div className="flex flex-wrap gap-2">
                  {(section.options || []).map((opt) => {
                    const active = isMulti
                      ? Array.isArray(selected) && selected.includes(opt.id)
                      : selected === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => setSelectionValue(section.id, opt.id, isMulti)}
                        className={`px-3 py-1 text-sm rounded border ${
                          active ? 'bg-indigo-600 border-indigo-400 text-white' : 'bg-gray-800 border-gray-600 text-gray-200'
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
              </div>
            );
          })}

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Valori numerici</div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
              {NUMERIC_CONTROLLED_PARAMS.map((param) => (
                <label key={param} className="text-xs text-gray-300 flex flex-col gap-1">
                  <span>{param}</span>
                  <input
                    type="number"
                    value={numericValues[param] ?? 0}
                    onChange={(e) =>
                      setNumericValues((prev) => ({ ...prev, [param]: Number(e.target.value || 0) }))
                    }
                    className="bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
                  />
                </label>
              ))}
            </div>
          </div>

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Sezione opzionale</div>
            <label className="flex items-center gap-2 text-sm text-gray-200">
              <input type="checkbox" checked={includeCura} onChange={(e) => setIncludeCura(e.target.checked)} />
              Inserisci cura nella formula
            </label>
            <p className="mt-2 text-xs text-gray-500">
              In «Danno (tipo attacco)» scegli in mischia o a distanza: nella formula viene scritta la somma
              corretta (dannigen+dannimis o dannigen+dannidis), indipendentemente dai valori sotto. In gioco il
              totale si mostra così: 1 = niente; 2–9 = lettere con ! (es. tre!); 10+ = numero con ! (es. 12!).
            </p>
          </div>

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Testo custom</div>
            <input
              type="text"
              value={customText}
              onChange={(e) => setCustomText(e.target.value)}
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
              placeholder="Aggiungi testo libero in coda"
            />
          </div>

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Preview</div>
            <div className="text-sm text-emerald-300 min-h-8">
              {loadingPreview ? 'Aggiornamento preview...' : preview || '-'}
            </div>
          </div>
        </div>
        <div className="p-4 border-t border-gray-700 flex justify-end gap-2">
          <button type="button" onClick={onClose} className="px-4 py-2 bg-gray-700 rounded text-white text-sm">
            Annulla
          </button>
          <button type="button" onClick={handleApply} className="px-4 py-2 bg-indigo-600 rounded text-white text-sm font-bold">
            Applica
          </button>
        </div>
      </div>
    </div>
  );
};

function getControlledParams(schema) {
  const out = new Set();
  (schema?.sections || []).forEach((section) => {
    (section.options || []).forEach((opt) => {
      Object.keys(opt.stats || {}).forEach((param) => out.add(param));
    });
  });
  return Array.from(out);
}

const NUMERIC_CONTROLLED_PARAMS = [
  'rango',
  'molt',
  'durata',
  'cura',
  'curapf',
  'livello',
  'gittata',
  'dcono',
  'area',
  'dannigen',
  'dannimis',
  'dannidis',
];

export default FormulaBuilderModal;
