import React, { useEffect, useMemo, useRef, useState } from 'react';
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
  entityName = '',
  elementoPrincipaleId = null,
  elementoOptions = [],
  savedSelections = null,
  savedFormulaType = null,
}) => {
  const [schema, setSchema] = useState(null);
  const [formulaType, setFormulaType] = useState(defaultFormulaType);
  const [selections, setSelections] = useState({});
  const [sourceElementId, setSourceElementId] = useState('');
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
  const [excludeAlwaysRango, setExcludeAlwaysRango] = useState(false);
  const [excludeAlwaysMolt, setExcludeAlwaysMolt] = useState(false);
  const [excludeAlwaysPrefix, setExcludeAlwaysPrefix] = useState(false);
  const [excludeAlwaysStatus, setExcludeAlwaysStatus] = useState(false);
  const [includeSpecificEffect, setIncludeSpecificEffect] = useState(false);
  const [effectDescription, setEffectDescription] = useState('');
  const [omitFormulaSource, setOmitFormulaSource] = useState(false);
  const wasOpenRef = useRef(false);

  const restoreFromSavedSelections = (sel) => {
    const data = sel && typeof sel === 'object' ? sel : {};
    if (data.formula_type) {
      setFormulaType(data.formula_type);
    } else if (savedFormulaType) {
      setFormulaType(savedFormulaType);
    } else {
      setFormulaType(defaultFormulaType || 'attack');
    }
    const nextSelections = {};
    ['formula_type', 'formula_prefix', 'formula_target', 'formula_source', 'formula_status', 'formula_damage_mode'].forEach((key) => {
      if (data[key] !== undefined && data[key] !== null) {
        nextSelections[key] = data[key];
      }
    });
    setSelections(nextSelections);
    setSourceElementId(data.source_element_id ? String(data.source_element_id) : '');
    setIncludeCura(!!data.include_cura);
    setExcludeAlwaysRango(!!data.exclude_always_rango);
    setExcludeAlwaysMolt(!!data.exclude_always_molt);
    setExcludeAlwaysPrefix(!!data.exclude_always_prefix);
    setExcludeAlwaysStatus(!!data.exclude_always_status);
    setIncludeSpecificEffect(!!data.include_specific_effect);
    setEffectDescription(data.effect_description || '');
    setOmitFormulaSource(!!data.omit_formula_source);
  };

  const normalizedElementoOptions = useMemo(
    () => (elementoOptions || []).map((el) => ({
      id: String(el.id),
      label: el.label || el.dichiarazione || el.nome || `Elemento ${el.id}`,
    })),
    [elementoOptions]
  );

  const templateBlocks = useMemo(() => {
    const blocks = schema?.type_templates?.[formulaType] || schema?.type_templates?.attack || [];
    return new Set(blocks);
  }, [schema, formulaType]);

  const visibleSections = useMemo(() => {
    const blockToSection = {
      formula_type: 'formula_type',
      formula_prefix: 'formula_prefix',
      formula_target: 'formula_target',
      formula_source: 'formula_source',
      formula_status: 'formula_status',
      formula_damage_mode: 'formula_damage_mode',
    };
    const allowed = new Set(
      Object.entries(blockToSection)
        .filter(([block]) => templateBlocks.has(block))
        .map(([, sectionId]) => sectionId)
    );
    return (schema?.sections || []).filter((section) => allowed.has(section.id));
  }, [schema, templateBlocks]);

  const visibleNumericParams = useMemo(() => {
    const blocks = templateBlocks;
    return NUMERIC_CONTROLLED_PARAMS.filter((param) => {
      if (param === 'rango' || param === 'molt') return blocks.has(param);
      if (param === 'dannimis' || param === 'dannidis' || param === 'dannigen') {
        return blocks.has('formula_damage_mode');
      }
      if (param === 'cura' || param === 'curapf') return blocks.has('formula_cura');
      if (param === 'gittata') return blocks.has('formula_target');
      if (param === 'durata') return blocks.has('formula_status');
      if (param === 'livello') return blocks.has('formula_type');
      if (param === 'dcono' || param === 'area') return blocks.has('formula_target');
      return false;
    });
  }, [templateBlocks]);

  const sourceSelections = useMemo(() => {
    const raw = selections.formula_source;
    if (Array.isArray(raw)) return raw;
    if (raw) return [raw];
    return [];
  }, [selections.formula_source]);

  const wantsElementSource = sourceSelections.some(
    (sid) => String(sid).toLowerCase() === 'elemento_principale'
  );

  const tessituraElementoId = elementoPrincipaleId ? String(elementoPrincipaleId) : '';

  const tessituraElementoLabel = useMemo(() => {
    if (!tessituraElementoId) return '';
    const match = normalizedElementoOptions.find((el) => el.id === tessituraElementoId);
    return match?.label || `Elemento #${tessituraElementoId}`;
  }, [normalizedElementoOptions, tessituraElementoId]);

  const effectiveSourceElementId = useMemo(() => {
    if (!wantsElementSource) return '';
    if (sourceElementId) return sourceElementId;
    return tessituraElementoId;
  }, [wantsElementSource, sourceElementId, tessituraElementoId]);

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

  const buildSelectionsPayload = () => ({
    ...selections,
    entity_name: (entityName || '').trim() || null,
    include_cura: includeCura,
    exclude_always_rango: excludeAlwaysRango,
    exclude_always_molt: excludeAlwaysMolt,
    exclude_always_prefix: excludeAlwaysPrefix,
    exclude_always_status: excludeAlwaysStatus,
    include_specific_effect: includeSpecificEffect,
    effect_description: effectDescription,
    omit_formula_source: omitFormulaSource,
    source_element_id: wantsElementSource && effectiveSourceElementId ? effectiveSourceElementId : null,
  });

  useEffect(() => {
    if (!open) {
      wasOpenRef.current = false;
      return;
    }
    if (wasOpenRef.current) {
      return;
    }
    wasOpenRef.current = true;

    if (savedSelections && Object.keys(savedSelections).length > 0) {
      restoreFromSavedSelections(savedSelections);
    } else {
      setFormulaType(defaultFormulaType || 'attack');
      setSelections({});
      setSourceElementId('');
      setIncludeCura(false);
      setExcludeAlwaysRango(false);
      setExcludeAlwaysMolt(false);
      setExcludeAlwaysPrefix(false);
      setExcludeAlwaysStatus(false);
      setIncludeSpecificEffect(false);
      setEffectDescription('');
      setOmitFormulaSource(
        Boolean(
          formulaValue
          && !String(formulaValue).includes('{formula_source}')
          && (String(formulaValue).includes('{danni_mischia}') || String(formulaValue).includes('{danni_distanza}'))
        )
      );
    }
    staffGetFormulaBuilderSchema(onLogout)
      .then((data) => setSchema(data || null))
      .catch((err) => console.error('Errore schema formula builder:', err));
  }, [open, onLogout, defaultFormulaType, elementoPrincipaleId, formulaValue, savedSelections, savedFormulaType]);

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
        selections: buildSelectionsPayload(),
        custom_text: '',
        context: {
          entity_name: (entityName || '').trim() || undefined,
        },
      },
      onLogout
    )
      .then((res) => setPreview(res?.formula_rendered || ''))
      .catch((err) => {
        console.error('Errore preview formula:', err);
        setPreview('Errore preview formula.');
      })
      .finally(() => setLoadingPreview(false));
  }, [
    open,
    schema,
    formulaType,
    selections,
    effectiveSourceElementId,
    wantsElementSource,
    includeCura,
    excludeAlwaysRango,
    excludeAlwaysMolt,
    excludeAlwaysPrefix,
    excludeAlwaysStatus,
    includeSpecificEffect,
    effectDescription,
    omitFormulaSource,
    entityName,
    statsByParamFromForm,
    numericValues,
    onLogout,
  ]);

  if (!open) {
    return null;
  }

  const TARGET_GITTATA_BY_OPTION = {
    flusso: 3,
    dardo: 10,
  };

  const setSelectionValue = (sectionId, value, isMulti) => {
    if (sectionId === 'formula_source') {
      setOmitFormulaSource(false);
    }

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

    if (sectionId === 'formula_target' && TARGET_GITTATA_BY_OPTION[value] !== undefined) {
      setNumericValues((prev) => ({ ...prev, gittata: TARGET_GITTATA_BY_OPTION[value] }));
    }
  };

  const toggleOmitFormulaSource = () => {
    setOmitFormulaSource((prev) => {
      const next = !prev;
      if (next) {
        setSelections((s) => ({ ...s, formula_source: [] }));
      }
      return next;
    });
  };

  const handleApply = async () => {
    try {
      const res = await staffPreviewFormulaBuilder(
        {
          formula: '',
          formula_type: formulaType,
          stats_by_param: { ...statsByParamFromForm, ...numericValues },
          selections: buildSelectionsPayload(),
          custom_text: '',
          context: {
            entity_name: (entityName || '').trim() || undefined,
          },
        },
        onLogout
      );
      onApply?.({
        statsByParam: res?.stats_by_param || {},
        formulaText: (res?.formula_template || schema?.default_template || '').trim(),
        customText: '',
        controlledParams: [...getControlledParams(schema), ...NUMERIC_CONTROLLED_PARAMS],
        formulaBuilderSelezioni: {
          formula_type: formulaType,
          ...buildSelectionsPayload(),
        },
        elementoPrincipaleId:
          wantsElementSource && effectiveSourceElementId
            ? parseInt(effectiveSourceElementId, 10)
            : null,
      });
      onClose?.();
    } catch (err) {
      console.error('Errore apply formula builder:', err);
    }
  };

  const formulaTypeLabel = (schema?.types || []).find((t) => t.id === formulaType)?.label || formulaType;

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
              onChange={(e) => {
                const nextType = e.target.value;
                setFormulaType(nextType);
                setSelections({});
                if (nextType !== 'attack') {
                  setOmitFormulaSource(false);
                }
              }}
              className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
            >
              {(schema?.types || []).map((t) => (
                <option key={t.id} value={t.id}>
                  {t.label}
                </option>
              ))}
            </select>
            {formulaType === 'capacity' && (
              <p className="mt-2 text-xs text-emerald-300">
                Prefisso formula:{' '}
                <strong>
                  Capacità {(entityName || '').trim() || '{nome entità}'}:
                </strong>
              </p>
            )}
          </div>
          {visibleSections.map((section) => {
            const isMulti = section.kind === 'multi';
            const selected = selections[section.id];
            const isSourceSection = section.id === 'formula_source';
            return (
              <div key={section.id} className="border border-gray-700 rounded-lg p-3">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs uppercase tracking-widest text-gray-400">{section.label}</div>
                  {isSourceSection && formulaType === 'attack' && (
                    <button
                      type="button"
                      onClick={toggleOmitFormulaSource}
                      className={`text-[11px] px-2 py-0.5 rounded border ${
                        omitFormulaSource
                          ? 'border-amber-400 bg-amber-900/40 text-amber-100'
                          : 'border-gray-600 text-gray-300 hover:bg-gray-800'
                      }`}
                    >
                      Ometti sorgente in formula
                    </button>
                  )}
                </div>
                <div className="flex flex-wrap gap-2">
                  {(section.options || []).map((opt) => {
                    const active = isMulti
                      ? Array.isArray(selected) && selected.includes(opt.id)
                      : selected === opt.id;
                    return (
                      <button
                        key={opt.id}
                        type="button"
                        onClick={() => !omitFormulaSource && setSelectionValue(section.id, opt.id, isMulti)}
                        disabled={isSourceSection && omitFormulaSource}
                        className={`px-3 py-1 text-sm rounded border ${
                          isSourceSection && omitFormulaSource
                            ? 'opacity-40 cursor-not-allowed bg-gray-900 border-gray-700 text-gray-500'
                            : active
                              ? 'bg-indigo-600 border-indigo-400 text-white'
                              : 'bg-gray-800 border-gray-600 text-gray-200'
                        }`}
                      >
                        {opt.label}
                      </button>
                    );
                  })}
                </div>
                {isSourceSection && (
                  <p className="mt-2 text-xs text-gray-500">
                    Puoi combinare più voci (es. Chop + Blam + Elemento →{' '}
                    <code className="text-emerald-300">Chop! / Blam! / Fuoco!</code>).
                    {formulaType === 'attack' ? (
                      <>
                        {' '}Solo negli <strong>attacchi</strong>, con danno totale 1, Chop/Blam in mischia
                        o Pierce a distanza possono comparire in forma compatta{' '}
                        <code className="text-emerald-300">(Chop!)</code> /{' '}
                        <code className="text-emerald-300">(Pierce!)</code> se non selezioni la sorgente.
                      </>
                    ) : (
                      <>
                        {' '}Per <strong>tessiture e capacità</strong> le sorgenti vanno sempre dichiarate
                        esplicitamente (niente forma compatta).
                      </>
                    )}
                  </p>
                )}
                {isSourceSection && formulaType === 'attack' && omitFormulaSource && (
                  <p className="mt-2 text-xs text-amber-300">
                    La sorgente non comparirà in formula (né Chop né (Chop!)).
                  </p>
                )}
                {isSourceSection && wantsElementSource && !omitFormulaSource && (
                  <div className="mt-3 space-y-2">
                    {tessituraElementoId ? (
                      <p className="text-sm text-emerald-300">
                        Elemento dalla tessitura: <strong>{tessituraElementoLabel}</strong>
                      </p>
                    ) : (
                      <p className="text-sm text-amber-300">
                        Nessun elemento principale impostato nel form tessitura: scegline uno sotto o impostalo nel
                        campo «Elemento Principale» prima di applicare.
                      </p>
                    )}
                    <label className="text-xs text-gray-400 uppercase tracking-widest block mb-1">
                      Imposta o sovrascrivi elemento (opzionale)
                    </label>
                    <select
                      value={sourceElementId}
                      onChange={(e) => setSourceElementId(e.target.value)}
                      className="w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
                    >
                      <option value="">
                        {tessituraElementoId
                          ? `— Usa elemento tessitura (${tessituraElementoLabel}) —`
                          : '— Seleziona elemento —'}
                      </option>
                      {normalizedElementoOptions.map((el) => (
                        <option key={el.id} value={el.id}>
                          {el.label}
                        </option>
                      ))}
                    </select>
                    <p className="text-[11px] text-gray-500">
                      Se scegli un elemento qui, alla pressione di «Applica» aggiorna anche il campo Elemento
                      Principale nel form tessitura.
                    </p>
                  </div>
                )}
              </div>
            );
          })}

          {visibleNumericParams.length > 0 && (
            <div className="border border-gray-700 rounded-lg p-3">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Valori numerici</div>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                {visibleNumericParams.map((param) => (
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
          )}

          {(templateBlocks.has('formula_cura') || templateBlocks.has('formula_prefix') || templateBlocks.has('formula_status')) && (
            <div className="border border-gray-700 rounded-lg p-3">
              <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Sezione opzionale</div>
              {templateBlocks.has('formula_cura') && (
                <label className="flex items-center gap-2 text-sm text-gray-200">
                  <input type="checkbox" checked={includeCura} onChange={(e) => setIncludeCura(e.target.checked)} />
                  Inserisci cura nella formula
                </label>
              )}
              <div className="mt-3 grid grid-cols-1 md:grid-cols-2 gap-2">
                {templateBlocks.has('rango') && (
                  <label className="flex items-center gap-2 text-sm text-gray-200">
                    <input type="checkbox" checked={excludeAlwaysRango} onChange={(e) => setExcludeAlwaysRango(e.target.checked)} />
                    Escludi SEMPRE rango
                  </label>
                )}
                {templateBlocks.has('molt') && (
                  <label className="flex items-center gap-2 text-sm text-gray-200">
                    <input type="checkbox" checked={excludeAlwaysMolt} onChange={(e) => setExcludeAlwaysMolt(e.target.checked)} />
                    Escludi SEMPRE moltiplicatore
                  </label>
                )}
                {templateBlocks.has('formula_prefix') && (
                  <label className="flex items-center gap-2 text-sm text-gray-200">
                    <input type="checkbox" checked={excludeAlwaysPrefix} onChange={(e) => setExcludeAlwaysPrefix(e.target.checked)} />
                    Escludi SEMPRE prefisso
                  </label>
                )}
                {templateBlocks.has('formula_status') && (
                  <label className="flex items-center gap-2 text-sm text-gray-200">
                    <input type="checkbox" checked={excludeAlwaysStatus} onChange={(e) => setExcludeAlwaysStatus(e.target.checked)} />
                    Escludi SEMPRE stato
                  </label>
                )}
              </div>
              {templateBlocks.has('formula_source') && (
                <p className="mt-2 text-xs text-gray-500">
                  La sorgente in formula usa sempre il placeholder <code className="text-emerald-300">{'{formula_source}'}</code>.
                </p>
              )}
              {templateBlocks.has('formula_damage_mode') && (
                <p className="mt-2 text-xs text-gray-500">
                  In «Sezione danno» scegli nessun danno, danni mischia o danni distanza.
                </p>
              )}
            </div>
          )}

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Effetto specifico</div>
            <label className="flex items-center gap-2 text-sm text-gray-200">
              <input
                type="checkbox"
                checked={includeSpecificEffect}
                onChange={(e) => setIncludeSpecificEffect(e.target.checked)}
              />
              Attiva effetto specifico
            </label>
            {includeSpecificEffect && (
              <input
                type="text"
                value={effectDescription}
                onChange={(e) => setEffectDescription(e.target.value)}
                className="mt-2 w-full bg-gray-950 p-2 rounded border border-gray-700 text-sm text-white"
                placeholder="Descrizione effetto"
              />
            )}
          </div>

          <div className="border border-gray-700 rounded-lg p-3">
            <div className="text-xs uppercase tracking-widest text-gray-400 mb-2">Preview ({formulaTypeLabel})</div>
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
