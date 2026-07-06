import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CheckCircle2, AlertCircle, Wand2, BookOpen } from 'lucide-react';
import { staffGetCarteEffectSchema, staffValidateCarteEffectScript } from '../../api';

const TRIGGER_EVENTS = [
  { value: 'on_play', label: 'on_play — carta giocata' },
  { value: 'on_exhaust', label: 'on_exhaust — esaurimento' },
  { value: 'on_attack', label: 'on_attack — dopo attacco' },
  { value: 'on_turn_start', label: 'on_turn_start — inizio turno' },
  { value: 'on_turn_end', label: 'on_turn_end — fine turno' },
  { value: 'manual', label: 'manual — solo azione esplicita' },
];

const TRIGGER_SOURCES = [
  { value: 'this', label: 'this — questa carta' },
  { value: 'self', label: 'self — controller' },
  { value: 'opponent', label: 'opponent — avversario' },
];

export const EFFECT_SCRIPT_RECIPES = [
  {
    templateKey: 'mutazione',
    label: 'Mutazione [X]',
    codice: 'MUTAZIONE',
    nome: 'Mutazione [X]',
    testo_regola:
      'Quando questo Personaggio si esaurisce, puoi sostituirlo con un Personaggio dalla tua mano con costo gioco ≤ [X].',
    reminder_breve: 'Mutazione ≤[X]',
    defaultX: 0,
  },
  {
    templateKey: 'colpo_influenza',
    label: 'Colpo [X]',
    codice: 'COLPO',
    nome: 'Colpo [X]',
    testo_regola: "Quando giochi questa carta, infliggi [X] danni all'influenza avversaria.",
    reminder_breve: 'Colpo [X]',
    defaultX: 1,
  },
  {
    templateKey: 'pesca',
    label: 'Pesca [X]',
    codice: 'PESCA',
    nome: 'Pesca [X]',
    testo_regola: "All'inizio del tuo turno, mentre questa carta è in gioco: Pesca [X].",
    reminder_breve: 'Pesca [X]',
    defaultX: 1,
  },
  {
    templateKey: 'rigenerazione_energia',
    label: 'Rigenerazione [X]',
    codice: 'RIGENERAZIONE',
    nome: 'Rigenerazione [X]',
    testo_regola: 'Quando giochi questa carta, guadagni [X] energia.',
    reminder_breve: 'Rigenerazione [X]',
    defaultX: 1,
  },
  {
    templateKey: 'danno_eroe',
    label: 'Ferita [X]',
    codice: 'FERITA',
    nome: 'Ferita [X]',
    testo_regola: 'Quando giochi questa carta, infliggi [X] danni a un eroe avversario a tua scelta.',
    reminder_breve: 'Ferita [X]',
    defaultX: 1,
  },
  {
    templateKey: 'guscio',
    label: 'Guscio [X]',
    codice: 'GUSCIO',
    nome: 'Guscio [X]',
    testo_regola:
      'Quando giochi questa carta, ottiene [X] segnalini Guscio. '
      + 'Quando sta per morire, perde un Guscio invece di morire.',
    reminder_breve: 'Guscio [X]',
    defaultX: 1,
  },
  {
    templateKey: 'guarigione',
    label: 'Guarigione [X]',
    codice: 'GUARIGIONE',
    nome: 'Guarigione [X]',
    testo_regola: 'A fine turno, questo personaggio recupera [X] PV (fino al massimo).',
    reminder_breve: 'Guarigione [X]',
    defaultX: 1,
  },
  {
    templateKey: 'guarigione_completa',
    label: 'Guarigione',
    codice: 'GUARIGIONE',
    nome: 'Guarigione',
    testo_regola: 'A fine turno, questo personaggio recupera tutti i PV.',
    reminder_breve: 'Guarigione',
    defaultX: 0,
  },
  {
    templateKey: 'sinergia_pesca',
    label: 'Sinergia [X] (pesca)',
    codice: 'SINERGIA',
    nome: 'Sinergia [X]',
    testo_regola:
      'All\'inizio del tuo turno, se controlli 2+ personaggi con Sinergia: Pesca [X].',
    reminder_breve: 'Sinergia [X]',
    defaultX: 1,
  },
  {
    templateKey: 'sinergia_energia',
    label: 'Sinergia [X] (mana)',
    codice: 'SINERGIA',
    nome: 'Sinergia [X]',
    testo_regola:
      'All\'inizio del tuo turno, se controlli 2+ personaggi con Sinergia: +[X] mana.',
    reminder_breve: 'Sinergia +[X]',
    defaultX: 1,
  },
];

function parsePlaceholders(...texts) {
  const found = new Set();
  texts.forEach((text) => {
    if (!text) return;
    const matches = String(text).matchAll(/\[([A-Z]+)\]/g);
    for (const m of matches) found.add(m[1]);
  });
  return [...found];
}

function tryParseJson(text) {
  if (!text?.trim()) return null;
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

function patchScript(script, { placeholders, paramValues, triggerEvent, triggerSource }) {
  const out = JSON.parse(JSON.stringify(script));
  out.version = 1;
  out.trigger = { event: triggerEvent, source: triggerSource };
  if (!out.params) out.params = {};
  placeholders.forEach((ph) => {
    const raw = paramValues[ph];
    const num = Number.isFinite(Number(raw)) ? Number(raw) : 0;
    if (!out.params[ph]) {
      out.params[ph] = { type: 'int', from_placeholder: ph, default: num };
    } else {
      out.params[ph].from_placeholder = ph;
      out.params[ph].default = num;
    }
  });
  return out;
}

export default function EffectScriptWizard({
  keywordForm,
  setKeywordForm,
  effectScriptText,
  setEffectScriptText,
  onLogout,
  onMessage,
}) {
  const [schemaData, setSchemaData] = useState(null);
  const [selectedRecipeKey, setSelectedRecipeKey] = useState(null);
  const [paramValues, setParamValues] = useState({ X: 0 });
  const [triggerEvent, setTriggerEvent] = useState('on_play');
  const [triggerSource, setTriggerSource] = useState('this');
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [validating, setValidating] = useState(false);
  const [validation, setValidation] = useState(null);

  useEffect(() => {
    staffGetCarteEffectSchema(onLogout)
      .then(setSchemaData)
      .catch((e) => onMessage?.(e?.message || 'Caricamento schema EffectScript fallito.'));
  }, [onLogout, onMessage]);

  const placeholders = useMemo(
    () => parsePlaceholders(keywordForm.nome, keywordForm.codice, keywordForm.testo_regola),
    [keywordForm.nome, keywordForm.codice, keywordForm.testo_regola],
  );

  const syncScriptText = useCallback(
    (baseScript) => {
      const patched = patchScript(baseScript, {
        placeholders,
        paramValues,
        triggerEvent,
        triggerSource,
      });
      setEffectScriptText(JSON.stringify(patched, null, 2));
      return patched;
    },
    [placeholders, paramValues, triggerEvent, triggerSource, setEffectScriptText],
  );

  const applyRecipe = (recipe) => {
    const tpl = schemaData?.templates?.[recipe.templateKey];
    if (!tpl) {
      onMessage?.(`Template «${recipe.label}» non disponibile.`);
      return;
    }
    setSelectedRecipeKey(recipe.templateKey);
    const nextParams = { ...paramValues };
    placeholders.forEach((ph) => {
      if (nextParams[ph] == null) nextParams[ph] = recipe.defaultX ?? 0;
    });
    setParamValues(nextParams);
    setTriggerEvent(tpl.trigger?.event || 'on_play');
    setTriggerSource(tpl.trigger?.source || 'this');
    setKeywordForm((prev) => ({
      ...prev,
      codice: prev.codice || recipe.codice,
      nome: prev.nome || recipe.nome,
      testo_regola: prev.testo_regola || recipe.testo_regola,
      reminder_breve: prev.reminder_breve || recipe.reminder_breve,
    }));
    syncScriptText(tpl);
    setValidation(null);
    onMessage?.(`Ricetta «${recipe.label}» applicata.`);
  };

  useEffect(() => {
    const parsed = tryParseJson(effectScriptText);
    if (!parsed?.trigger) return;
    setTriggerEvent(parsed.trigger.event || 'on_play');
    setTriggerSource(parsed.trigger.source || 'this');
    const fromScript = {};
    Object.entries(parsed.params || {}).forEach(([k, v]) => {
      if (v?.default != null) fromScript[k] = v.default;
    });
    if (Object.keys(fromScript).length) {
      setParamValues((prev) => ({ ...prev, ...fromScript }));
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps -- solo al mount

  useEffect(() => {
    if (!selectedRecipeKey || !schemaData?.templates?.[selectedRecipeKey]) return;
    syncScriptText(schemaData.templates[selectedRecipeKey]);
  }, [paramValues, triggerEvent, triggerSource, placeholders, selectedRecipeKey, schemaData, syncScriptText]);

  const stepSummary = useMemo(() => {
    const parsed = tryParseJson(effectScriptText);
    return (parsed?.steps || []).map((s, i) => `${i + 1}. ${s.type}${s.id ? ` (${s.id})` : ''}`);
  }, [effectScriptText]);

  const handleValidate = async () => {
    setValidating(true);
    setValidation(null);
    try {
      const parsed = tryParseJson(effectScriptText);
      if (!parsed) {
        setValidation({ ok: false, detail: 'JSON non valido.' });
        return;
      }
      const res = await staffValidateCarteEffectScript(
        {
          script: parsed,
          nome: keywordForm.nome,
          codice: keywordForm.codice,
        },
        onLogout,
      );
      setValidation({ ok: true, detail: res?.detail || 'Script valido.' });
    } catch (e) {
      const detail = e?.data?.detail || e?.message || 'Validazione fallita.';
      const errors = e?.data?.errors;
      setValidation({
        ok: false,
        detail: Array.isArray(errors) ? errors.join(' ') : detail,
      });
    } finally {
      setValidating(false);
    }
  };

  return (
    <div className="space-y-3 rounded border border-violet-900/50 bg-violet-950/20 p-3">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1 text-xs font-bold text-violet-300">
          <Wand2 size={14} /> Wizard EffectScript v1
        </p>
        <a
          href="/wiki/carte-effect-script-v1"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1 text-[10px] text-violet-400 hover:text-violet-200"
        >
          <BookOpen size={12} /> Wiki sintassi completa
        </a>
      </div>

      <div>
        <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-gray-500">1 — Ricetta</p>
        <div className="flex flex-wrap gap-1">
          {EFFECT_SCRIPT_RECIPES.map((recipe) => (
            <button
              key={recipe.templateKey}
              type="button"
              className={`rounded px-2 py-1 text-[10px] font-bold ${
                selectedRecipeKey === recipe.templateKey
                  ? 'bg-violet-700 text-white'
                  : 'bg-gray-800 text-gray-300 hover:bg-gray-700'
              }`}
              onClick={() => applyRecipe(recipe)}
            >
              {recipe.label}
            </button>
          ))}
          <button
            type="button"
            className={`rounded px-2 py-1 text-[10px] font-bold ${
              !selectedRecipeKey ? 'bg-gray-600 text-white' : 'bg-gray-800 text-gray-400'
            }`}
            onClick={() => {
              setSelectedRecipeKey(null);
              const blank = {
                version: 1,
                params: {},
                trigger: { event: triggerEvent, source: triggerSource },
                steps: [{ type: 'modify_influence', target: 'opponent', delta: -1 }],
              };
              syncScriptText(blank);
            }}
          >
            Vuoto
          </button>
        </div>
      </div>

      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-gray-500">2 — Trigger</p>
          <select
            className="mb-1 w-full rounded bg-gray-900 px-2 py-1 text-xs text-white"
            value={triggerEvent}
            onChange={(e) => setTriggerEvent(e.target.value)}
          >
            {TRIGGER_EVENTS.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
          <select
            className="w-full rounded bg-gray-900 px-2 py-1 text-xs text-white"
            value={triggerSource}
            onChange={(e) => setTriggerSource(e.target.value)}
          >
            {TRIGGER_SOURCES.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </div>
        <div>
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-gray-500">
            3 — Parametri ({placeholders.length ? placeholders.join(', ') : 'nessun [X] nel nome'})
          </p>
          {placeholders.length === 0 ? (
            <p className="text-[10px] text-gray-500">
              Aggiungi <code className="text-violet-300">[X]</code> nel nome keyword per parametrizzare.
            </p>
          ) : (
            <div className="flex flex-wrap gap-2">
              {placeholders.map((ph) => (
                <label key={ph} className="text-[10px]">
                  [{ph}]
                  <input
                    type="number"
                    className="mt-0.5 block w-20 rounded bg-gray-900 px-2 py-1 text-xs text-white"
                    value={paramValues[ph] ?? 0}
                    onChange={(e) => setParamValues((prev) => ({
                      ...prev,
                      [ph]: e.target.value,
                    }))}
                  />
                </label>
              ))}
            </div>
          )}
        </div>
      </div>

      {stepSummary.length > 0 && (
        <div>
          <p className="mb-1 text-[10px] font-bold uppercase tracking-wide text-gray-500">Passi ({stepSummary.length})</p>
          <ul className="space-y-0.5 text-[10px] text-gray-400">
            {stepSummary.map((line) => (
              <li key={line}>{line}</li>
            ))}
          </ul>
        </div>
      )}

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded bg-emerald-900 px-2 py-1 text-xs font-bold text-emerald-100"
          onClick={handleValidate}
          disabled={validating}
        >
          {validating ? 'Validazione…' : 'Valida script'}
        </button>
        <button
          type="button"
          className="rounded bg-gray-800 px-2 py-1 text-xs text-gray-300"
          onClick={() => setAdvancedOpen((v) => !v)}
        >
          {advancedOpen ? 'Nascondi JSON' : 'Modifica JSON avanzato'}
        </button>
        {validation && (
          <span
            className={`flex items-center gap-1 text-[10px] ${
              validation.ok ? 'text-emerald-400' : 'text-rose-400'
            }`}
          >
            {validation.ok ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
            {validation.detail}
          </span>
        )}
      </div>

      {advancedOpen && (
        <textarea
          className="w-full rounded bg-gray-950 px-2 py-1 font-mono text-[10px] text-gray-200"
          rows={10}
          value={effectScriptText}
          onChange={(e) => {
            setSelectedRecipeKey(null);
            setEffectScriptText(e.target.value);
            setValidation(null);
          }}
        />
      )}
    </div>
  );
}
