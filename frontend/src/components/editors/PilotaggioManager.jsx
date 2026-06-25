import React, { useCallback, useEffect, useMemo, useState } from 'react';
import StaffQrTab from '../StaffQrTab';
import useStaffMinigiocoQr from '../../hooks/useStaffMinigiocoQr';
import StaffMinigiocoPageToolbar from './StaffMinigiocoPageToolbar';
import PilotSottosistemaModal from './PilotSottosistemaModal';
import {
  applyDefaultMinigiocoToQr,
  MINIGIOCO_PAGE_KEYS,
  patchStaffListMinigiocoDefault,
} from '../../utils/staffMinigiocoDefaults';
import StaffMinigiocoUsaDefaultToggle from './StaffMinigiocoUsaDefaultToggle';
import {
  staffAssociaPilotSottosistemaQr,
  staffCreatePilotComandoCritico,
  staffCreatePilotEvento,
  staffCreatePilotIntensita,
  staffCreatePilotSottosistema,
  staffDeletePilotComandoCritico,
  staffDeletePilotEvento,
  staffDeletePilotIntensita,
  staffDeletePilotSottosistema,
  staffGetPilotComandiCritici,
  staffGetPilotEventi,
  staffGetPilotComandoCritico,
  staffGetPilotEvento,
  staffGetPilotIntensita,
  staffGetPilotIntensitaById,
  staffGetPilotSottosistema,
  staffGetPilotSottosistemi,
  staffGetPilotSerbatoioCarburante,
  staffSetPilotSerbatoioCarburante,
  staffGetPilotStatiAllerta,
  staffGetPilotStatoAllerta,
  staffGetPilotRuntimeConfig,
  staffGetPilotSessioneLive,
  staffAzionePilotSessioneSottosistema,
  staffUpdatePilotComandoCritico,
  staffUpdatePilotEvento,
  staffUpdatePilotIntensita,
  staffUpdatePilotSottosistema,
  staffUpdatePilotStatoAllerta,
  staffUpdatePilotRuntimeConfig,
  staffGetPilotStiva,
  staffModificaPilotStiva,
  staffAggiornaCodiciEventiPilot,
} from '../../api';

const PILOT_TABS = [
  { id: 'sottosistemi', label: 'Sottosistemi' },
  { id: 'intensita', label: 'Intensità' },
  { id: 'eventi', label: 'Eventi' },
  { id: 'comandi_critici', label: 'Comandi critici (globali)' },
  { id: 'stati_allerta', label: 'Stati allerta (DEFCON)' },
  { id: 'sessione_live', label: 'Sessione live' },
  { id: 'stiva', label: 'Stiva componenti' },
  { id: 'runtime', label: 'Runtime Console' },
];

const defaultEvento = {
  nome: '',
  descrizione: '',
  regole_json: '{\n  "version": 3\n}',
  tick_min: '4',
  tick_max: '8',
  scadenza_critica: false,
  peso_random: 10,
  sottosistema: '',
  attivo: true,
};

/** Stato form modale modifica evento (include campi testo per array JSON). */
const emptyEditEventoModal = () => ({
  ...defaultEvento,
  codice_soluzione_esatta: '___',
  codici_soluzione_parziale_json: '[]',
  codici_precipizio_json: '[]',
});

const defaultCurveZero = () => {
  const out = {};
  for (let i = 0; i <= 9; i += 1) out[String(i)] = 0;
  return out;
};

const defaultGuastoCurve = () => {
  const out = defaultCurveZero();
  out['7'] = 1;
  out['8'] = 10;
  out['9'] = 25;
  return out;
};

const defaultColorCurve = () => ({
  '0': '#ffffff',
  '1': '#8a2be2',
  '2': '#4b5fd1',
  '3': '#2f8cff',
  '4': '#00b894',
  '5': '#9ccc65',
  '6': '#ffd54f',
  '7': '#ffb74d',
  '8': '#ff7043',
  '9': '#ff3b30',
});

const emptyCondition = {
  outcome: 'sp',
  subsystem: '',
  op: '>',
  value: 0,
  min: 0,
  max: 0,
  direction_rule: 'direzione_opposta',
};

const defaultEffettiGuasto = () => ({
  tipo: 'none',
  valore: 0,
  target_codice: '',
});

const defaultEffettoGuastoBuilder = () => ({
  tipo: 'none',
  valore: 0,
  target_codice: '',
});

function validateEffettoGuastoBuilder(builder) {
  const tipo = String(builder?.tipo || 'none');
  const valore = Number(builder?.valore || 0);
  const target = String(builder?.target_codice || '').trim().toUpperCase();
  if (tipo === 'guasto_altro_percent' && !target) {
    return { valid: false, message: 'Per guasto_altro_percent serve target_codice (1 lettera).' };
  }
  if (tipo === 'guasto_altro_percent' && target.length !== 1) {
    return { valid: false, message: 'target_codice deve essere un solo carattere.' };
  }
  if (['guasto_altro_percent', 'guasto_random_percent', 'riduci_carburante_percent', 'riduci_batterie_percent', 'allunga_distanza_percent'].includes(tipo)) {
    if (!Number.isFinite(valore) || valore < 0 || valore > 100) {
      return { valid: false, message: 'valore deve essere tra 0 e 100.' };
    }
  }
  return { valid: true, message: 'Configurazione valida.' };
}

const defaultEffettiComandoCritico = () => ({
  tipo: 'none',
  probabilita_percent: 0,
  valore: 0,
  target_codice: '',
});

const DEFAULT_RULE_EXPR = '(1)';

function tokenizeRuleExpression(input) {
  const src = String(input || '').trim().toUpperCase();
  if (!src) return [];
  const raw = src.match(/\d+|AND|OR|\(|\)/g) || [];
  return raw.map((t) => t.trim()).filter(Boolean);
}

function buildExpressionAst(expression, conditions) {
  const tokens = tokenizeRuleExpression(expression);
  if (!tokens.length) return null;
  const prec = { OR: 1, AND: 2 };
  const out = [];
  const ops = [];
  for (const tk of tokens) {
    if (/^\d+$/.test(tk)) {
      out.push(tk);
      continue;
    }
    if (tk === 'AND' || tk === 'OR') {
      while (ops.length && (ops[ops.length - 1] === 'AND' || ops[ops.length - 1] === 'OR') && prec[ops[ops.length - 1]] >= prec[tk]) {
        out.push(ops.pop());
      }
      ops.push(tk);
      continue;
    }
    if (tk === '(') {
      ops.push(tk);
      continue;
    }
    if (tk === ')') {
      while (ops.length && ops[ops.length - 1] !== '(') out.push(ops.pop());
      if (!ops.length || ops.pop() !== '(') return null;
    }
  }
  while (ops.length) {
    const op = ops.pop();
    if (op === '(' || op === ')') return null;
    out.push(op);
  }
  const stack = [];
  for (const tk of out) {
    if (/^\d+$/.test(tk)) {
      const idx = Number(tk) - 1;
      if (idx < 0 || idx >= conditions.length) return null;
      stack.push(conditions[idx]);
      continue;
    }
    if (tk !== 'AND' && tk !== 'OR') return null;
    const b = stack.pop();
    const a = stack.pop();
    if (!a || !b) return null;
    stack.push({ op: tk === 'AND' ? 'and' : 'or', items: [a, b] });
  }
  return stack.length === 1 ? stack[0] : null;
}

function validateRuleExpression(expression, conditions) {
  const src = String(expression || '').trim();
  if (!src) {
    return { valid: false, message: 'Formula vuota. Esempio: (1 AND 2) OR 3' };
  }
  const ast = buildExpressionAst(src, conditions || []);
  if (!ast) {
    return { valid: false, message: 'Sintassi non valida o indice condizione inesistente.' };
  }
  return { valid: true, message: 'Formula valida.' };
}

function parseDurataTickToForm(value, scadenzaCritica = false) {
  const raw = String(value ?? '4-8').trim();
  if (/^\d+-\d+$/.test(raw)) {
    const [a, b] = raw.split('-');
    return { scadenza_critica: Boolean(scadenzaCritica), tick_min: a, tick_max: b };
  }
  if (/^\d+$/.test(raw)) {
    return { scadenza_critica: Boolean(scadenzaCritica), tick_min: raw, tick_max: raw };
  }
  return { scadenza_critica: Boolean(scadenzaCritica), tick_min: '4', tick_max: '8' };
}

function composeDurataTickFromForm(form) {
  const lo = Math.max(1, Number(form.tick_min) || 1);
  const hi = Math.max(lo, Number(form.tick_max) || lo);
  return lo === hi ? String(lo) : `${lo}-${hi}`;
}

function isValidDurataTickForm(form) {
  const lo = Number(form.tick_min);
  const hi = Number(form.tick_max);
  return Number.isFinite(lo) && lo >= 1 && Number.isFinite(hi) && hi >= 1;
}

function formatDurataTickLabel(value, scadenzaCritica = false) {
  const raw = String(value ?? '').trim();
  if (/^\d+-\d+$/.test(raw)) {
    const [a, b] = raw.split('-');
    return a === b ? `${a} tick` : `${a}–${b} tick`;
  }
  if (/^\d+$/.test(raw)) return `${raw} tick`;
  return raw || '—';
}

/** Ricostruisce il builder UI da `regole_json` (persistenza round-trip via _conditions / _expr). */
function ruleBuilderFromRegoleJson(rj) {
  const r = rj && typeof rj === 'object' ? rj : {};
  const branch = (k) => ({
    conditions: Array.isArray(r[k]?._conditions) ? r[k]._conditions : [],
    expression:
      typeof r[k]?._expr === 'string' && String(r[k]._expr).trim()
        ? String(r[k]._expr).trim()
        : DEFAULT_RULE_EXPR,
  });
  const sp = branch('sp');
  const st = branch('st');
  return { st, sp, ca: branch('ca') };
}

const defaultCaEffetto = () => ({
  tipo: 'precipizio',
  modalita: 'tutti',
  sottosistema_ids: [],
  quantita: 1,
  pool: 'scelti',
});

/** Ricostruisce lo stato UI da `regole_json.ca_effetto`. */
function caEffettoFromRegoleJson(rj) {
  const cae = rj?.ca_effetto;
  if (!cae || typeof cae !== 'object') return defaultCaEffetto();
  const tipoRaw = String(cae.tipo || 'precipizio');
  if (tipoRaw !== 'guasto_sottosistema' && tipoRaw !== 'guasto_sottosistemi') {
    return defaultCaEffetto();
  }
  let ids = [];
  if (Array.isArray(cae.sottosistema_ids)) ids = cae.sottosistema_ids.map(String);
  else if (Array.isArray(cae.sottosistemi_ids)) ids = cae.sottosistemi_ids.map(String);
  else if (cae.sottosistema_id) ids = [String(cae.sottosistema_id)];
  ids = [...new Set(ids.map((x) => x.trim()).filter(Boolean))];
  const modalita = String(cae.modalita || 'tutti') === 'random' ? 'random' : 'tutti';
  const pool = modalita === 'random' && !ids.length ? 'tutti_sessione' : 'scelti';
  return {
    tipo: 'guasto_sottosistemi',
    modalita,
    sottosistema_ids: ids,
    quantita: Math.max(1, Number(cae.quantita) || 1),
    pool,
  };
}

function toggleCaSottosistemaId(ids, id) {
  const sid = String(id || '').trim();
  if (!sid) return ids;
  const set = new Set((ids || []).map(String));
  if (set.has(sid)) set.delete(sid);
  else set.add(sid);
  return [...set];
}

/** Unisce ST/SP/CA (AST + metadati UI) e `ca_effetto` nel documento regole. */
function mergeCaAndRulesIntoRegole(baseJson, rb, caEffetto) {
  const out =
    baseJson && typeof baseJson === 'object' && !Array.isArray(baseJson) ? { ...baseJson } : {};
  if (!out.version) out.version = 3;
  const usesDirectional = ['st', 'sp', 'ca'].some((k) =>
    (rb[k]?.conditions || []).some((c) => c.op === 'direction')
  );
  out.usa_direzione_evento = usesDirectional;
  for (const k of ['st', 'sp', 'ca']) {
    const ast = buildExpressionAst(rb[k].expression, rb[k].conditions);
    if (!ast) {
      return {
        ok: false,
        error: `Espressione ${k.toUpperCase()} non valida: controlla condizioni e formula (es. (1 AND 2) OR 3).`,
        regole: null,
      };
    }
    out[k] = {
      ...(out[k] && typeof out[k] === 'object' && !Array.isArray(out[k]) ? out[k] : {}),
      expression: ast,
      _conditions: rb[k].conditions,
      _expr: rb[k].expression,
    };
  }
  const ce = caEffetto && typeof caEffetto === 'object' ? caEffetto : defaultCaEffetto();
  if (ce.tipo === 'guasto_sottosistemi') {
    const ids = [...new Set((ce.sottosistema_ids || []).map((x) => String(x).trim()).filter(Boolean))];
    if (ce.modalita === 'random') {
      if (ce.pool === 'scelti' && !ids.length) {
        return {
          ok: false,
          error: 'Per guasto CA random da elenco seleziona almeno un sottosistema.',
          regole: null,
        };
      }
      const payload = {
        tipo: 'guasto_sottosistemi',
        modalita: 'random',
        quantita: Math.max(1, Number(ce.quantita) || 1),
      };
      if (ids.length) payload.sottosistema_ids = ids;
      out.ca_effetto = payload;
    } else {
      if (!ids.length) {
        return {
          ok: false,
          error: 'Per guasto CA su sottosistemi scelti seleziona almeno un sottosistema.',
          regole: null,
        };
      }
      out.ca_effetto = { tipo: 'guasto_sottosistemi', modalita: 'tutti', sottosistema_ids: ids };
    }
  } else {
    out.ca_effetto = { tipo: 'precipizio' };
  }
  return { ok: true, error: '', regole: out };
}

function CaEffettoFields({ caEffetto, setCaEffetto, sottosistemi }) {
  const ce = caEffetto && typeof caEffetto === 'object' ? caEffetto : defaultCaEffetto();
  const isGuasto = ce.tipo === 'guasto_sottosistemi';
  const showScelti = isGuasto && (ce.modalita === 'tutti' || ce.pool === 'scelti');
  return (
    <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 space-y-3">
      <div className="text-xs font-semibold text-amber-200/90">Effetto esito CA</div>
      <p className="text-[11px] text-gray-400 leading-relaxed">
        Di default il CA precipita la nave. In alternativa puoi forzare il guasto di uno o più sottosistemi
        (anche scelti a caso tra un elenco o tra tutti quelli online in sessione).
      </p>
      <div className="flex flex-wrap gap-3 items-end">
        <label className="block min-w-[10rem]">
          <span className="text-xs text-gray-400">Tipo effetto CA</span>
          <select
            className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
            value={ce.tipo}
            onChange={(ev) => {
              const v = ev.target.value;
              setCaEffetto(v === 'guasto_sottosistemi' ? { ...defaultCaEffetto(), tipo: 'guasto_sottosistemi' } : defaultCaEffetto());
            }}
          >
            <option value="precipizio">Precipizio nave</option>
            <option value="guasto_sottosistemi">Guasto sottosistema/i</option>
          </select>
        </label>
        {isGuasto ? (
          <label className="block min-w-[12rem]">
            <span className="text-xs text-gray-400">Modalità guasto</span>
            <select
              className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
              value={ce.modalita}
              onChange={(ev) =>
                setCaEffetto((p) => ({
                  ...p,
                  modalita: ev.target.value,
                  pool: ev.target.value === 'random' ? p.pool || 'scelti' : 'scelti',
                }))
              }
            >
              <option value="tutti">Tutti i selezionati</option>
              <option value="random">N random</option>
            </select>
          </label>
        ) : null}
        {isGuasto && ce.modalita === 'random' ? (
          <>
            <label className="block min-w-[12rem]">
              <span className="text-xs text-gray-400">Pool random</span>
              <select
                className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
                value={ce.pool}
                onChange={(ev) =>
                  setCaEffetto((p) => ({
                    ...p,
                    pool: ev.target.value,
                    sottosistema_ids: ev.target.value === 'tutti_sessione' ? [] : p.sottosistema_ids,
                  }))
                }
              >
                <option value="scelti">Da elenco sotto</option>
                <option value="tutti_sessione">Qualsiasi online in sessione</option>
              </select>
            </label>
            <label className="block w-24">
              <span className="text-xs text-gray-400">Quantità N</span>
              <input
                type="number"
                min={1}
                className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
                value={ce.quantita}
                onChange={(ev) => setCaEffetto((p) => ({ ...p, quantita: ev.target.value }))}
              />
            </label>
          </>
        ) : null}
      </div>
      {showScelti ? (
        <div className="space-y-1">
          <span className="text-xs text-gray-400">Sottosistemi</span>
          <div className="flex flex-wrap gap-x-4 gap-y-1 max-h-36 overflow-y-auto rounded border border-gray-700/80 bg-gray-950/40 p-2">
            {sottosistemi.map((ss) => {
              const checked = (ce.sottosistema_ids || []).map(String).includes(String(ss.id));
              return (
                <label key={ss.id} className="flex items-center gap-1.5 text-xs text-gray-300 cursor-pointer">
                  <input
                    type="checkbox"
                    className="rounded border-gray-600"
                    checked={checked}
                    onChange={() =>
                      setCaEffetto((p) => ({
                        ...p,
                        sottosistema_ids: toggleCaSottosistemaId(p.sottosistema_ids, ss.id),
                      }))
                    }
                  />
                  <span>
                    {ss.nome} <span className="font-mono text-indigo-300/90">({ss.codice})</span>
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      ) : null}
    </div>
  );
}

export default function PilotaggioManager({ onLogout }) {
  const { openMinigioco, minigiocoModal } = useStaffMinigiocoQr(onLogout);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sottosistemi, setSottosistemi] = useState([]);
  const [intensita, setIntensita] = useState([]);
  const [eventi, setEventi] = useState([]);
  const [comandiCritici, setComandiCritici] = useState([]);
  const [nuovoSotto, setNuovoSotto] = useState({
    codice: '', nome: '', gruppo: '', ordine_gruppo: 0, ordine: 0, tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
    capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
    richiede_componenti_riparazione: false,
    requisiti_riparazione_json: '[]',
    richiede_componenti_ricarica: false,
    requisiti_ricarica_json: '[]',
  });
  const [nuovoEvento, setNuovoEvento] = useState(defaultEvento);
  const [nuovoCritico, setNuovoCritico] = useState({ pattern: '', nome: '', attivo: true });
  const [editSottoId, setEditSottoId] = useState(null);
  const [sottoModalMode, setSottoModalMode] = useState(null);
  const [createEventoModalOpen, setCreateEventoModalOpen] = useState(false);
  const [editSotto, setEditSotto] = useState({
    codice: '', nome: '', gruppo: '', ordine_gruppo: 0, ordine: 0, tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
    capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
    richiede_componenti_riparazione: false,
    requisiti_riparazione_json: '[]',
    richiede_componenti_ricarica: false,
    requisiti_ricarica_json: '[]',
  });
  const [editIntensita, setEditIntensita] = useState({ valore: 0, nome: '' });
  const [editIntensitaId, setEditIntensitaId] = useState(null);
  const [nuovaIntensita, setNuovaIntensita] = useState({ valore: 0, nome: '' });
  const [editEventoId, setEditEventoId] = useState(null);
  const [editEvento, setEditEvento] = useState(() => emptyEditEventoModal());
  const [editCriticoId, setEditCriticoId] = useState(null);
  const [editCritico, setEditCritico] = useState({ pattern: '', nome: '', attivo: true });
  const [nuovoEffettoGuastoBuilder, setNuovoEffettoGuastoBuilder] = useState(defaultEffettoGuastoBuilder());
  const [editEffettoGuastoBuilder, setEditEffettoGuastoBuilder] = useState(defaultEffettoGuastoBuilder());
  const [serbatoioFuel, setSerbatoioFuel] = useState(null);
  const [serbatoioFuelDraft, setSerbatoioFuelDraft] = useState('');
  const [serbatoioFuelBusy, setSerbatoioFuelBusy] = useState(false);
  const nuovoEffettoValidation = useMemo(
    () => validateEffettoGuastoBuilder(nuovoEffettoGuastoBuilder),
    [nuovoEffettoGuastoBuilder]
  );
  const editEffettoValidation = useMemo(
    () => validateEffettoGuastoBuilder(editEffettoGuastoBuilder),
    [editEffettoGuastoBuilder]
  );

  const [scanningForSottosistemaId, setScanningForSottosistemaId] = useState(null);
  const [qrStatus, setQrStatus] = useState({ type: '', message: '' });
  const [activeTab, setActiveTab] = useState('sottosistemi');
  const [statiAllerta, setStatiAllerta] = useState([]);
  const [editStatoId, setEditStatoId] = useState(null);
  const [editStato, setEditStato] = useState({});
  const [runtimeConfig, setRuntimeConfig] = useState(null);
  const [runtimeSaving, setRuntimeSaving] = useState(false);
  const [runtimeSaveFeedback, setRuntimeSaveFeedback] = useState(null);
  const [stivaData, setStivaData] = useState(null);
  const [stivaBusy, setStivaBusy] = useState(false);
  const [eventiCodiciBusy, setEventiCodiciBusy] = useState(false);
  const [sessioneLive, setSessioneLive] = useState(null);
  const [sessioneLiveBusy, setSessioneLiveBusy] = useState(false);
  const [editCaEffetto, setEditCaEffetto] = useState(defaultCaEffetto);
  const [createCaEffetto, setCreateCaEffetto] = useState(defaultCaEffetto);
  const [editRuleBuilder, setEditRuleBuilder] = useState({
    st: { conditions: [], expression: DEFAULT_RULE_EXPR },
    sp: { conditions: [], expression: DEFAULT_RULE_EXPR },
    ca: { conditions: [], expression: DEFAULT_RULE_EXPR },
  });
  const [ruleBuilder, setRuleBuilder] = useState({
    st: { conditions: [], expression: DEFAULT_RULE_EXPR },
    sp: { conditions: [], expression: DEFAULT_RULE_EXPR },
    ca: { conditions: [], expression: DEFAULT_RULE_EXPR },
  });
  const [draftCondition, setDraftCondition] = useState(emptyCondition);
  const ruleValidation = useMemo(
    () => ({
      st: validateRuleExpression(ruleBuilder.st.expression, ruleBuilder.st.conditions),
      sp: validateRuleExpression(ruleBuilder.sp.expression, ruleBuilder.sp.conditions),
      ca: validateRuleExpression(ruleBuilder.ca.expression, ruleBuilder.ca.conditions),
    }),
    [ruleBuilder]
  );
  const editRuleValidation = useMemo(
    () => ({
      st: validateRuleExpression(editRuleBuilder.st.expression, editRuleBuilder.st.conditions),
      sp: validateRuleExpression(editRuleBuilder.sp.expression, editRuleBuilder.sp.conditions),
      ca: validateRuleExpression(editRuleBuilder.ca.expression, editRuleBuilder.ca.conditions),
    }),
    [editRuleBuilder]
  );
  const selectedConditionSubsystem = useMemo(
    () => sottosistemi.find((s) => s.codice === draftCondition.subsystem) || null,
    [sottosistemi, draftCondition.subsystem]
  );
  const conditionOps = useMemo(() => {
    const t = String(selectedConditionSubsystem?.tipo || '').toLowerCase();
    if (t === 'batteria' || t === 'serbatoio') {
      return [
        { value: 'piene', label: 'piene' },
        { value: 'vuote', label: 'vuote' },
        { value: 'non_piene', label: 'non piene' },
        { value: 'non_vuote', label: 'non vuote' },
        { value: 'distrutte', label: 'distrutte' },
      ];
    }
    return [
      { value: '>', label: '>' },
      { value: '<', label: '<' },
      { value: '=', label: '=' },
      { value: 'between', label: 'between' },
      { value: 'direction', label: 'direction' },
      { value: 'invertito', label: 'invertito' },
      { value: 'non_invertito', label: 'non invertito' },
      { value: 'espulso', label: 'espulso' },
      { value: 'non_espulso', label: 'non espulso' },
    ];
  }, [selectedConditionSubsystem]);

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const [s, i, e, crit, stati, runtime] = await Promise.all([
        staffGetPilotSottosistemi(onLogout),
        staffGetPilotIntensita(onLogout),
        staffGetPilotEventi(onLogout),
        staffGetPilotComandiCritici(onLogout).catch(() => []),
        staffGetPilotStatiAllerta(onLogout).catch(() => []),
        staffGetPilotRuntimeConfig(onLogout).catch(() => null),
      ]);
      setSottosistemi(Array.isArray(s) ? s : []);
      setIntensita(Array.isArray(i) ? i : []);
      setEventi(Array.isArray(e) ? e : []);
      setComandiCritici(Array.isArray(crit) ? crit : []);
      setStatiAllerta(Array.isArray(stati) ? stati : []);
      setRuntimeConfig(runtime || null);
    } catch (err) {
      setError(err?.message || 'Errore caricamento pilotaggio.');
    } finally {
      setLoading(false);
    }
  }, [onLogout]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const resetNuovoSotto = () => ({
    codice: '',
    nome: '',
    gruppo: '',
    ordine_gruppo: 0,
    ordine: 0,
    tipo: 'standard',
    coeff_produzione: 0,
    coeff_consumo_energia: 1,
    coeff_consumo_carburante: 0,
    coeff_effetto_speciale: 1,
    rampa_livelli_per_tick: 1,
    capacita_storage: 0,
    coeff_ricarica_storage: 0.5,
    capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
    richiede_componenti_riparazione: false,
    requisiti_riparazione_json: '[]',
    richiede_componenti_ricarica: false,
    requisiti_ricarica_json: '[]',
  });

  const openCreateSottoModal = () => {
    setNuovoSotto(resetNuovoSotto());
    setNuovoEffettoGuastoBuilder(defaultEffettoGuastoBuilder());
    setSottoModalMode('create');
    if (!stivaData?.mattoni_catalogo?.length) {
      staffGetPilotStiva(onLogout).then((data) => setStivaData(data)).catch(() => {});
    }
  };

  const closeSottoModal = () => {
    setSottoModalMode(null);
    setEditSottoId(null);
    setSerbatoioFuel(null);
    setSerbatoioFuelDraft('');
    setSerbatoioFuelBusy(false);
  };

  const loadSerbatoioFuel = useCallback(async (sottosistemaId) => {
    if (!sottosistemaId) return;
    setSerbatoioFuel({ loading: true });
    try {
      const data = await staffGetPilotSerbatoioCarburante(sottosistemaId, onLogout);
      setSerbatoioFuel(data);
      if (data?.sessione_attiva && data.carburante_attuale != null) {
        setSerbatoioFuelDraft(String(Math.round(Number(data.carburante_attuale))));
      } else {
        setSerbatoioFuelDraft(String(Math.round(Number(data?.carburante_massimo || 0))));
      }
    } catch (err) {
      setSerbatoioFuel({ loading: false, error: err?.message || 'Errore lettura carburante.' });
    }
  }, [onLogout]);

  const applicaSerbatoioFuel = async (payload) => {
    if (!editSottoId) return;
    setSerbatoioFuelBusy(true);
    setError('');
    try {
      const data = await staffSetPilotSerbatoioCarburante(editSottoId, payload, onLogout);
      setSerbatoioFuel(data);
      if (data?.carburante_attuale != null) {
        setSerbatoioFuelDraft(String(Math.round(Number(data.carburante_attuale))));
      }
    } catch (err) {
      setError(err?.message || 'Impossibile aggiornare il carburante.');
    } finally {
      setSerbatoioFuelBusy(false);
    }
  };

  const closeCreateEventoModal = useCallback(() => {
    setCreateEventoModalOpen(false);
    setNuovoEvento(defaultEvento);
    setCreateCaEffetto(defaultCaEffetto());
    setRuleBuilder({
      st: { conditions: [], expression: DEFAULT_RULE_EXPR },
      sp: { conditions: [], expression: DEFAULT_RULE_EXPR },
      ca: { conditions: [], expression: DEFAULT_RULE_EXPR },
    });
    setError('');
  }, []);

  const addSottosistema = async () => {
    await staffCreatePilotSottosistema(
      {
        ...nuovoSotto,
        codice: nuovoSotto.codice.toUpperCase(),
        coeff_produzione: Number(nuovoSotto.coeff_produzione || 0),
        coeff_consumo_energia: Number(nuovoSotto.coeff_consumo_energia || 0),
        coeff_consumo_carburante: Number(nuovoSotto.coeff_consumo_carburante || 0),
        coeff_effetto_speciale: Number(nuovoSotto.coeff_effetto_speciale || 1),
        ordine_gruppo: Number(nuovoSotto.ordine_gruppo ?? 0),
        ordine: Number(nuovoSotto.ordine ?? 0),
        rampa_livelli_per_tick: Number(nuovoSotto.rampa_livelli_per_tick || 1),
        capacita_storage: Number(nuovoSotto.capacita_storage || 0),
        coeff_ricarica_storage: Number(nuovoSotto.coeff_ricarica_storage || 0),
        capacita_carburante: Number(nuovoSotto.capacita_carburante || 0),
        effetti_guasto_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_guasto_json || '{}'); } catch { return defaultEffettiGuasto(); }
        })(),
        effetti_inversione_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_inversione_json || '{}'); } catch { return defaultEffettiComandoCritico(); }
        })(),
        effetti_espulsione_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_espulsione_json || '{}'); } catch { return defaultEffettiComandoCritico(); }
        })(),
        guasto_percent_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.guasto_percent_per_livello_json || '{}'); } catch { return defaultGuastoCurve(); }
        })(),
        ripristino_percent_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.ripristino_percent_per_livello_json || '{}'); } catch { return defaultCurveZero(); }
        })(),
        colori_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.colori_per_livello_json || '{}'); } catch { return defaultColorCurve(); }
        })(),
        richiede_componenti_riparazione: Boolean(nuovoSotto.richiede_componenti_riparazione),
        requisiti_riparazione_json: (() => {
          try { return JSON.parse(nuovoSotto.requisiti_riparazione_json || '[]'); } catch { return []; }
        })(),
        richiede_componenti_ricarica: Boolean(nuovoSotto.richiede_componenti_ricarica),
        requisiti_ricarica_json: (() => {
          try { return JSON.parse(nuovoSotto.requisiti_ricarica_json || '[]'); } catch { return []; }
        })(),
      },
      onLogout
    );
    setNuovoSotto(resetNuovoSotto());
    closeSottoModal();
    loadData();
  };

  const addIntensita = async () => {
    await staffCreatePilotIntensita({ ...nuovaIntensita, valore: Number(nuovaIntensita.valore) }, onLogout);
    setNuovaIntensita({ valore: 0, nome: '' });
    loadData();
  };
  const addEvento = async () => {
    if (!isValidDurataTickForm(nuovoEvento)) {
      setError('Durata tick non valida: min e max devono essere ≥ 1.');
      return;
    }
    const durataSpec = composeDurataTickFromForm(nuovoEvento);
    let regoleObj;
    try {
      regoleObj = JSON.parse(nuovoEvento.regole_json || '{}');
    } catch {
      setError('JSON regole non valido.');
      return;
    }
    const merged = mergeCaAndRulesIntoRegole(regoleObj, ruleBuilder, createCaEffetto);
    if (!merged.ok) {
      setError(merged.error);
      return;
    }
    setError('');
    await staffCreatePilotEvento(
      {
        ...nuovoEvento,
        codice_soluzione_esatta: '___',
        codici_soluzione_parziale: [],
        codici_precipizio: [],
        regole_json: merged.regole,
        sottosistema: nuovoEvento.sottosistema || null,
        durata_tick: durataSpec,
        scadenza_critica: Boolean(nuovoEvento.scadenza_critica),
      },
      onLogout
    );
    setNuovoEvento(defaultEvento);
    setCreateCaEffetto(defaultCaEffetto());
    closeCreateEventoModal();
    loadData();
  };
  const addComandoCritico = async () => {
    await staffCreatePilotComandoCritico(
      {
        pattern: nuovoCritico.pattern.trim().toUpperCase(),
        nome: nuovoCritico.nome.trim(),
        attivo: Boolean(nuovoCritico.attivo),
      },
      onLogout
    );
    setNuovoCritico({ pattern: '', nome: '', attivo: true });
    loadData();
  };
  const salvaComandoCritico = async () => {
    await staffUpdatePilotComandoCritico(
      editCriticoId,
      {
        pattern: editCritico.pattern.trim().toUpperCase(),
        nome: editCritico.nome.trim(),
        attivo: Boolean(editCritico.attivo),
      },
      onLogout
    );
    setEditCriticoId(null);
    loadData();
  };
  const salvaSottosistema = async () => {
    await staffUpdatePilotSottosistema(
      editSottoId,
      {
        ...editSotto,
        codice: editSotto.codice.toUpperCase(),
        coeff_produzione: Number(editSotto.coeff_produzione || 0),
        coeff_consumo_energia: Number(editSotto.coeff_consumo_energia || 0),
        coeff_consumo_carburante: Number(editSotto.coeff_consumo_carburante || 0),
        coeff_effetto_speciale: Number(editSotto.coeff_effetto_speciale || 1),
        ordine_gruppo: Number(editSotto.ordine_gruppo ?? 0),
        ordine: Number(editSotto.ordine ?? 0),
        rampa_livelli_per_tick: Number(editSotto.rampa_livelli_per_tick || 1),
        capacita_storage: Number(editSotto.capacita_storage || 0),
        coeff_ricarica_storage: Number(editSotto.coeff_ricarica_storage || 0),
        capacita_carburante: Number(editSotto.capacita_carburante || 0),
        effetti_guasto_json: (() => {
          try { return JSON.parse(editSotto.effetti_guasto_json || '{}'); } catch { return defaultEffettiGuasto(); }
        })(),
        effetti_inversione_json: (() => {
          try { return JSON.parse(editSotto.effetti_inversione_json || '{}'); } catch { return defaultEffettiComandoCritico(); }
        })(),
        effetti_espulsione_json: (() => {
          try { return JSON.parse(editSotto.effetti_espulsione_json || '{}'); } catch { return defaultEffettiComandoCritico(); }
        })(),
        guasto_percent_per_livello: (() => {
          try { return JSON.parse(editSotto.guasto_percent_per_livello_json || '{}'); } catch { return defaultGuastoCurve(); }
        })(),
        ripristino_percent_per_livello: (() => {
          try { return JSON.parse(editSotto.ripristino_percent_per_livello_json || '{}'); } catch { return defaultCurveZero(); }
        })(),
        colori_per_livello: (() => {
          try { return JSON.parse(editSotto.colori_per_livello_json || '{}'); } catch { return defaultColorCurve(); }
        })(),
        richiede_componenti_riparazione: Boolean(editSotto.richiede_componenti_riparazione),
        requisiti_riparazione_json: (() => {
          try { return JSON.parse(editSotto.requisiti_riparazione_json || '[]'); } catch { return []; }
        })(),
        richiede_componenti_ricarica: Boolean(editSotto.richiede_componenti_ricarica),
        requisiti_ricarica_json: (() => {
          try { return JSON.parse(editSotto.requisiti_ricarica_json || '[]'); } catch { return []; }
        })(),
      },
      onLogout
    );
    closeSottoModal();
    loadData();
  };

  const salvaIntensita = async () => {
    await staffUpdatePilotIntensita(editIntensitaId, { valore: Number(editIntensita.valore), nome: editIntensita.nome }, onLogout);
    setEditIntensitaId(null);
    loadData();
  };
  const closeEditEventoModal = useCallback(() => {
    setEditEventoId(null);
    setEditEvento(emptyEditEventoModal());
    setEditRuleBuilder({
      sp: { conditions: [], expression: DEFAULT_RULE_EXPR },
      ca: { conditions: [], expression: DEFAULT_RULE_EXPR },
    });
    setEditCaEffetto(defaultCaEffetto());
    setError('');
  }, []);

  const openEditEventoModal = useCallback(
    async (row) => {
      setError('');
      try {
        const e = await staffGetPilotEvento(row.id, onLogout);
        let rj = e.regole_json;
        if (typeof rj === 'string') {
          try {
            rj = JSON.parse(rj || '{}');
          } catch {
            rj = {};
          }
        }
        if (!rj || typeof rj !== 'object') rj = {};
        setEditRuleBuilder(ruleBuilderFromRegoleJson(rj));
        setEditCaEffetto(caEffettoFromRegoleJson(rj));
        setEditEvento({
          nome: e.nome || '',
          descrizione: e.descrizione ?? '',
          codice_soluzione_esatta: e.codice_soluzione_esatta || '___',
          codici_soluzione_parziale_json: JSON.stringify(e.codici_soluzione_parziale || [], null, 2),
          codici_precipizio_json: JSON.stringify(e.codici_precipizio || [], null, 2),
          regole_json: JSON.stringify(rj && Object.keys(rj).length ? rj : { version: 3 }, null, 2),
          ...parseDurataTickToForm(e.durata_tick, e.scadenza_critica),
          peso_random: e.peso_random ?? 10,
          sottosistema: e.sottosistema || '',
          attivo: e.attivo !== false,
        });
        setEditEventoId(e.id);
      } catch (err) {
        setError(err?.message || 'Impossibile caricare il dettaglio evento.');
      }
    },
    [onLogout]
  );

  useEffect(() => {
    if (!editEventoId) return undefined;
    const onKey = (ev) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        closeEditEventoModal();
      }
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [editEventoId, closeEditEventoModal]);

  const salvaEvento = async () => {
    setError('');
    if (!isValidDurataTickForm(editEvento)) {
      setError('Durata tick non valida: min e max devono essere ≥ 1.');
      return;
    }
    const durataSpec = composeDurataTickFromForm(editEvento);
    let regole_json;
    try {
      regole_json = JSON.parse(editEvento.regole_json || '{}');
    } catch {
      setError('JSON «Regole avanzate» non valido.');
      return;
    }
    const mergedRules = mergeCaAndRulesIntoRegole(
      regole_json,
      editRuleBuilder,
      editCaEffetto
    );
    if (!mergedRules.ok) {
      setError(mergedRules.error);
      return;
    }
    regole_json = mergedRules.regole;
    let codici_soluzione_parziale;
    let codici_precipizio;
    try {
      const rawP = JSON.parse(editEvento.codici_soluzione_parziale_json || '[]');
      const rawC = JSON.parse(editEvento.codici_precipizio_json || '[]');
      codici_soluzione_parziale = Array.isArray(rawP) ? rawP : [];
      codici_precipizio = Array.isArray(rawC) ? rawC : [];
    } catch {
      setError('JSON codici parziale o precipizio non valido (devono essere array JSON).');
      return;
    }
    const codice = String(editEvento.codice_soluzione_esatta || '___')
      .trim()
      .toUpperCase()
      .slice(0, 3) || '___';
    const payload = {
      nome: String(editEvento.nome || '').trim(),
      descrizione: String(editEvento.descrizione ?? ''),
      codice_soluzione_esatta: codice,
      codici_soluzione_parziale,
      codici_precipizio,
      regole_json,
      durata_tick: durataSpec,
      scadenza_critica: Boolean(editEvento.scadenza_critica),
      peso_random: Math.max(0, Number(editEvento.peso_random) || 0),
      sottosistema: editEvento.sottosistema || null,
      attivo: Boolean(editEvento.attivo),
    };
    if (!payload.nome) {
      setError('Il nome evento è obbligatorio.');
      return;
    }
    try {
      await staffUpdatePilotEvento(editEventoId, payload, onLogout);
      closeEditEventoModal();
      loadData();
    } catch (err) {
      setError(err?.message || 'Errore salvataggio evento.');
    }
  };

  const salvaStatoAllerta = async () => {
    await staffUpdatePilotStatoAllerta(
      editStatoId,
      {
        nome: editStato.nome,
        colore: editStato.colore,
        frequenza_evento_min_sec: Number(editStato.frequenza_evento_min_sec),
        frequenza_evento_max_sec: Number(editStato.frequenza_evento_max_sec),
        tempo_risoluzione_secondi: Number(editStato.tempo_risoluzione_secondi),
        probabilita_evento_per_tick: Number(editStato.probabilita_evento_per_tick),
        equivale_nave_abbattuta: Boolean(editStato.equivale_nave_abbattuta),
      },
      onLogout
    );
    setEditStatoId(null);
    loadData();
  };

  const generaEffettoGuastoJson = (builder) => JSON.stringify({
    tipo: String(builder.tipo || 'none'),
    valore: Number(builder.valore || 0),
    target_codice: String(builder.target_codice || '').trim().toUpperCase(),
  }, null, 2);

  const buildCondFromDraft = () => {
    if (!draftCondition.subsystem) return null;
    const out = draftCondition.outcome;
    const cond = {
      sottosistema: draftCondition.subsystem,
      op: draftCondition.op,
    };
    if (draftCondition.op === 'between') {
      cond.min = Number(draftCondition.min);
      cond.max = Number(draftCondition.max);
    } else if (draftCondition.op === 'direction') {
      cond.direction_rule = draftCondition.direction_rule;
    } else if (
      ['piene', 'vuote', 'non_piene', 'non_vuote', 'distrutte', 'invertito', 'non_invertito', 'espulso', 'non_espulso'].includes(
        draftCondition.op
      )
    ) {
      // Nessun parametro aggiuntivo per condizioni booleane su batteria/serbatoio.
    } else {
      cond.value = Number(draftCondition.value);
    }
    return { out, cond };
  };

  const addRuleCondition = () => {
    const pair = buildCondFromDraft();
    if (!pair) return;
    const { out, cond } = pair;
    setRuleBuilder((prev) => ({
      ...prev,
      [out]: {
        ...prev[out],
        conditions: [...prev[out].conditions, cond],
      },
    }));
  };

  const addEditRuleCondition = () => {
    const pair = buildCondFromDraft();
    if (!pair) return;
    const { out, cond } = pair;
    setEditRuleBuilder((prev) => ({
      ...prev,
      [out]: {
        ...prev[out],
        conditions: [...prev[out].conditions, cond],
      },
    }));
  };

  const removeRuleCondition = (outcome, idx) => {
    setRuleBuilder((prev) => ({
      ...prev,
      [outcome]: {
        ...prev[outcome],
        conditions: prev[outcome].conditions.filter((_, i) => i !== idx),
      },
    }));
  };

  const removeEditRuleCondition = (outcome, idx) => {
    setEditRuleBuilder((prev) => ({
      ...prev,
      [outcome]: {
        ...prev[outcome],
        conditions: prev[outcome].conditions.filter((_, i) => i !== idx),
      },
    }));
  };

  const generaJsonGuidaEvento = () => {
    let base = {};
    try {
      base = JSON.parse(nuovoEvento.regole_json || '{}');
    } catch {
      setError('JSON regole esistente non valido: riparto da oggetto vuoto.');
      base = { version: 3 };
    }
    const merged = mergeCaAndRulesIntoRegole(base, ruleBuilder, createCaEffetto);
    if (!merged.ok) {
      setError(merged.error);
      return;
    }
    setError('');
    setNuovoEvento((p) => ({ ...p, regole_json: JSON.stringify(merged.regole, null, 2) }));
  };

  const generaJsonGuidaEventoEdit = () => {
    let base = {};
    try {
      base = JSON.parse(editEvento.regole_json || '{}');
    } catch {
      setError('JSON regole non valido in modifica.');
      return;
    }
    const merged = mergeCaAndRulesIntoRegole(base, editRuleBuilder, editCaEffetto);
    if (!merged.ok) {
      setError(merged.error);
      return;
    }
    setError('');
    setEditEvento((p) => ({ ...p, regole_json: JSON.stringify(merged.regole, null, 2) }));
  };

  const salvaRuntimeConfig = async () => {
    if (!runtimeConfig || runtimeSaving) return;
    setRuntimeSaving(true);
    setRuntimeSaveFeedback(null);
    try {
      const updated = await staffUpdatePilotRuntimeConfig(
        {
          login_required_console: Boolean(runtimeConfig.login_required_console),
          tick_interval_secondi: Number(runtimeConfig.tick_interval_secondi || 5),
          alarm_audio_enabled: Boolean(runtimeConfig.alarm_audio_enabled),
          riparazione_componenti_abilitata: Boolean(runtimeConfig.riparazione_componenti_abilitata),
          annichilamento_opposti_abilitato: Boolean(runtimeConfig.annichilamento_opposti_abilitato),
          compattatore_console_abilitata: Boolean(runtimeConfig.compattatore_console_abilitata),
          compattatore_login_richiesto: Boolean(runtimeConfig.compattatore_login_richiesto),
          compattatore_stat_accesso_sigla: String(runtimeConfig.compattatore_stat_accesso_sigla || '0IN').trim(),
          compattatore_quantico_abilitato: Boolean(runtimeConfig.compattatore_quantico_abilitato),
        },
        onLogout,
      );
      setRuntimeConfig(updated);
      setRuntimeSaveFeedback({
        type: 'success',
        text: 'Runtime salvato — le modifiche sono attive sul server.',
      });
    } catch (err) {
      setRuntimeSaveFeedback({
        type: 'error',
        text: err?.message || 'Salvataggio runtime non riuscito.',
      });
    } finally {
      setRuntimeSaving(false);
    }
  };

  useEffect(() => {
    if (runtimeSaveFeedback?.type !== 'success') return undefined;
    const t = setTimeout(() => setRuntimeSaveFeedback(null), 5000);
    return () => clearTimeout(t);
  }, [runtimeSaveFeedback]);

  const loadSessioneLive = useCallback(async () => {
    try {
      const data = await staffGetPilotSessioneLive(onLogout);
      setSessioneLive(data);
    } catch (_) {
      setSessioneLive(null);
    }
  }, [onLogout]);

  useEffect(() => {
    if (activeTab !== 'sessione_live') return undefined;
    loadSessioneLive();
    const timer = setInterval(loadSessioneLive, 4000);
    return () => clearInterval(timer);
  }, [activeTab, loadSessioneLive]);

  const loadStiva = useCallback(async () => {
    try {
      const data = await staffGetPilotStiva(onLogout);
      setStivaData(data);
    } catch (_) {
      setStivaData(null);
    }
  }, [onLogout]);

  useEffect(() => {
    if (activeTab !== 'stiva') return undefined;
    loadStiva();
    return undefined;
  }, [activeTab, loadStiva]);

  const modificaStiva = async (mattoneId, delta) => {
    setStivaBusy(true);
    setError('');
    try {
      const data = await staffModificaPilotStiva({ mattone_id: mattoneId, delta }, onLogout);
      setStivaData(data);
    } catch (err) {
      setError(err?.message || 'Modifica stiva non riuscita.');
    } finally {
      setStivaBusy(false);
    }
  };

  const aggiornaCodiciEventi = async (dryRun = false) => {
    setEventiCodiciBusy(true);
    setError('');
    try {
      const res = await staffAggiornaCodiciEventiPilot({ dry_run: dryRun, solo_attivi: true }, onLogout);
      if (!dryRun) await loadData();
      setError('');
      const n = res?.conteggio ?? 0;
      const fonte = res?.fonte_stato || 'nave';
      window.alert(
        dryRun
          ? `Anteprima: ${n} eventi (${fonte}). Nessuna modifica salvata.`
          : `Codici aggiornati per ${n} eventi (fonte: ${fonte}).`
      );
    } catch (err) {
      setError(err?.message || 'Aggiornamento codici eventi non riuscito.');
    } finally {
      setEventiCodiciBusy(false);
    }
  };

  const azioneSottosistemaLive = async (sottosistemaId, azione) => {
    setSessioneLiveBusy(true);
    setError('');
    try {
      const data = await staffAzionePilotSessioneSottosistema(
        { sottosistema_id: sottosistemaId, azione },
        onLogout
      );
      setSessioneLive(data);
    } catch (err) {
      setError(err?.message || 'Azione sottosistema non riuscita.');
    } finally {
      setSessioneLiveBusy(false);
    }
  };

  if (loading) {
    return <div className="p-6 text-gray-300">Caricamento modulo pilotaggio...</div>;
  }

  return (
    <div className="p-6 space-y-6 text-gray-100">
      <h2 className="text-xl font-bold">Gestione Pilotaggio</h2>
      {error ? <div className="rounded bg-red-900/40 border border-red-600 p-3 text-sm">{error}</div> : null}

      <div className="flex flex-wrap gap-2 border-b border-gray-600 pb-3">
        {PILOT_TABS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => setActiveTab(t.id)}
            className={`px-3 py-2 rounded-t text-sm font-medium transition-colors ${
              activeTab === t.id
                ? 'bg-indigo-700 text-white'
                : 'bg-gray-800 text-gray-400 hover:text-gray-200'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {activeTab === 'sottosistemi' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Sottosistemi (1° carattere)</h3>
        <p className="text-xs text-gray-400 mb-3 leading-relaxed">
          Inserisci codice e nome, poi aggiungi la riga. Usa <strong className="text-gray-300">Scansiona QR</strong> sul
          sottosistema: il sistema collega il QR al sottosistema (se il cartellino è nuovo crea anche il manifesto pilota
          dietro le quinte). Non serve cercare id di vista a mano.
          {' '}
          <strong className="text-gray-300">Ordine colonna sistema</strong> e <strong className="text-gray-300">ordine nel gruppo</strong>{' '}
          regolano la disposizione sulla console pilota (stesso ordine colonna per tutti i sottosistemi dello stesso gruppo).
        </p>
        {qrStatus.message ? (
          <div
            className={`mb-3 rounded px-3 py-2 text-sm ${
              qrStatus.type === 'success' ? 'bg-emerald-900/40 border border-emerald-700 text-emerald-100' : 'bg-red-900/40 border border-red-700 text-red-100'
            }`}
          >
            {qrStatus.message}
          </div>
        ) : null}
        <StaffMinigiocoPageToolbar
          pageKey={MINIGIOCO_PAGE_KEYS.pilotSottosistemi}
          pageLabel="Pilotaggio — Sottosistemi"
          onLogout={onLogout}
        />
        <div className="flex justify-end my-3">
          <button
            type="button"
            className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium"
            onClick={openCreateSottoModal}
          >
            Nuovo sottosistema
          </button>
        </div>
        <div className="space-y-2 text-sm">
          {sottosistemi.map((s) => (
            <div
              key={s.id}
              className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-gray-800/60 rounded-lg px-3 py-2 border border-gray-700/80"
            >
              <span className="wrap-break-word min-w-0">
                <strong className="font-mono text-indigo-200">{s.codice}</strong> — {s.nome}
                <span className="text-gray-400 text-xs block sm:inline sm:ml-2">
                  ({s.gruppo || 'Senza gruppo'} / {s.tipo || 'standard'} · col.{s.ordine_gruppo ?? 0} · #{s.ordine ?? 0})
                  {s.stato_qr === 'pronto'
                    ? ' · QR collegato'
                    : s.stato_qr === 'incompleto'
                      ? ' · vista OK, manca scan cartellino'
                      : ' · nessun QR'}
                </span>
              </span>
              <div className="flex flex-wrap gap-2 shrink-0 items-center">
                <StaffMinigiocoUsaDefaultToggle
                  qrcodeId={s.qrcode_id}
                  usaDefault={s.minigioco_usa_default}
                  pageKey={MINIGIOCO_PAGE_KEYS.pilotSottosistemi}
                  onLogout={onLogout}
                  compact
                  onChange={(val) =>
                    setSottosistemi((prev) =>
                      prev.map((row) =>
                        row.id === s.id ? { ...row, minigioco_usa_default: Boolean(val) } : row,
                      ),
                    )
                  }
                />
                <button
                  type="button"
                  className="px-2 py-1 rounded bg-gray-700 text-sm text-white"
                  onClick={() => setScanningForSottosistemaId(s.id)}
                >
                  Scansiona QR
                </button>
                <button
                  type="button"
                  className="px-2 py-1 rounded bg-indigo-800 text-sm text-white disabled:opacity-40"
                  disabled={!s.qrcode_id}
                  onClick={() => openMinigioco(s.qrcode_id, `${s.codice} — ${s.nome}`)}
                  title={s.qrcode_id ? 'Configura minigioco QR' : 'Associa prima un QR'}
                >
                  Minigioco
                </button>
                <button
                  type="button"
                  className="px-2 py-1 rounded bg-indigo-900/80 text-sm text-indigo-200"
                  onClick={async () => {
                    setError('');
                    try {
                      const full = await staffGetPilotSottosistema(s.id, onLogout);
                      setEditSottoId(full.id);
                      setEditSotto({
                        codice: full.codice || '',
                        nome: full.nome || '',
                        gruppo: full.gruppo || '',
                        ordine_gruppo: full.ordine_gruppo ?? 0,
                        ordine: full.ordine ?? 0,
                        tipo: full.tipo || 'standard',
                        coeff_produzione: full.coeff_produzione ?? 0,
                        coeff_consumo_energia: full.coeff_consumo_energia ?? 1,
                        coeff_consumo_carburante: full.coeff_consumo_carburante ?? 0,
                        coeff_effetto_speciale: full.coeff_effetto_speciale ?? 1,
                        rampa_livelli_per_tick: full.rampa_livelli_per_tick ?? 1,
                        capacita_storage: full.capacita_storage ?? 0,
                        coeff_ricarica_storage: full.coeff_ricarica_storage ?? 0.5,
                        capacita_carburante: full.capacita_carburante ?? 0,
                        effetti_guasto_json: JSON.stringify(full.effetti_guasto_json || defaultEffettiGuasto(), null, 2),
                        effetti_inversione_json: JSON.stringify(full.effetti_inversione_json || defaultEffettiComandoCritico(), null, 2),
                        effetti_espulsione_json: JSON.stringify(full.effetti_espulsione_json || defaultEffettiComandoCritico(), null, 2),
                        guasto_percent_per_livello_json: JSON.stringify(full.guasto_percent_per_livello || defaultGuastoCurve(), null, 2),
                        ripristino_percent_per_livello_json: JSON.stringify(full.ripristino_percent_per_livello || defaultCurveZero(), null, 2),
                        colori_per_livello_json: JSON.stringify(full.colori_per_livello || defaultColorCurve(), null, 2),
                        richiede_componenti_riparazione: Boolean(full.richiede_componenti_riparazione),
                        requisiti_riparazione_json: JSON.stringify(full.requisiti_riparazione_json || [], null, 2),
                        richiede_componenti_ricarica: Boolean(full.richiede_componenti_ricarica),
                        requisiti_ricarica_json: JSON.stringify(full.requisiti_ricarica_json || [], null, 2),
                      });
                      setEditEffettoGuastoBuilder({
                        tipo: String((full.effetti_guasto_json || {}).tipo || 'none'),
                        valore: Number((full.effetti_guasto_json || {}).valore || 0),
                        target_codice: String((full.effetti_guasto_json || {}).target_codice || ''),
                      });
                      setSottoModalMode('edit');
                      if (!stivaData?.mattoni_catalogo?.length) {
                        staffGetPilotStiva(onLogout).then((data) => setStivaData(data)).catch(() => {});
                      }
                      if (String(full.tipo || '').toLowerCase() === 'serbatoio') {
                        loadSerbatoioFuel(full.id);
                      } else {
                        setSerbatoioFuel(null);
                      }
                    } catch (err) {
                      setError(err?.message || 'Impossibile caricare il sottosistema.');
                    }
                  }}
                >
                  Modifica
                </button>
                <button
                  type="button"
                  className="px-2 py-1 rounded text-sm text-red-400 hover:bg-red-950/40"
                  onClick={() => staffDeletePilotSottosistema(s.id, onLogout).then(loadData)}
                >
                  Elimina
                </button>
              </div>
            </div>
          ))}
          {!sottosistemi.length ? (
            <p className="text-gray-500 text-sm py-4 text-center">Nessun sottosistema. Clicca «Nuovo sottosistema».</p>
          ) : null}
        </div>
      </section>
      ) : null}

      {scanningForSottosistemaId ? (
        <div className="fixed inset-0 z-50 bg-black flex flex-col">
          <div className="p-4 flex justify-between items-center bg-gray-900 border-b border-gray-800 gap-2">
            <span className="font-bold text-white text-sm sm:text-base">
              Associa QR al sottosistema selezionato
            </span>
            <button
              type="button"
              onClick={() => setScanningForSottosistemaId(null)}
              className="px-4 py-2 bg-red-600 hover:bg-red-700 rounded transition-colors shrink-0"
            >
              Chiudi
            </button>
          </div>
          <div className="flex-1 min-h-0">
            <StaffQrTab
              onScanSuccess={async (qr_id) => {
                try {
                  await staffAssociaPilotSottosistemaQr(scanningForSottosistemaId, qr_id, onLogout);
                  await applyDefaultMinigiocoToQr(
                    MINIGIOCO_PAGE_KEYS.pilotSottosistemi,
                    qr_id,
                    onLogout,
                  );
                  setScanningForSottosistemaId(null);
                  setQrStatus({ type: 'success', message: 'QR associato al sottosistema.' });
                  loadData();
                } catch (error) {
                  const detail =
                    error?.data?.error ||
                    error?.message ||
                    (typeof error?.data === 'string' ? error.data : null) ||
                    'Errore sconosciuto';
                  setQrStatus({ type: 'error', message: `Errore: ${detail}` });
                }
              }}
              onLogout={onLogout}
            />
          </div>
        </div>
      ) : null}

      {activeTab === 'intensita' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Intensità (3° carattere numerico)</h3>
        <div className="flex gap-2 mb-3">
          <input type="number" min={0} max={9} className="bg-gray-800 rounded px-2 py-1 w-20" value={nuovaIntensita.valore} onChange={(e) => setNuovaIntensita((p) => ({ ...p, valore: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1" value={nuovaIntensita.nome} onChange={(e) => setNuovaIntensita((p) => ({ ...p, nome: e.target.value }))} placeholder="Nome intensità (opzionale)" />
          <button className="px-3 py-1 rounded bg-indigo-600" onClick={addIntensita}>Aggiungi</button>
        </div>
        {intensita.map((i) => (
          <div key={i.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editIntensitaId === i.id ? (
              <div className="flex gap-2 w-full">
                <input type="number" min={0} max={9} className="bg-gray-700 rounded px-2 py-1 w-20" value={editIntensita.valore} onChange={(e) => setEditIntensita((p) => ({ ...p, valore: e.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 flex-1" value={editIntensita.nome} onChange={(e) => setEditIntensita((p) => ({ ...p, nome: e.target.value }))} />
                <button className="text-emerald-400" onClick={salvaIntensita}>Salva</button>
                <button className="text-gray-300" onClick={() => setEditIntensitaId(null)}>Annulla</button>
              </div>
            ) : (
              <>
                <span>{i.valore} - {i.nome || `Intensità ${i.valore}`}</span>
                <div className="flex gap-3">
                  <button
                    className="text-indigo-300"
                    type="button"
                    onClick={async () => {
                      setError('');
                      try {
                        const row = await staffGetPilotIntensitaById(i.id, onLogout);
                        setEditIntensitaId(row.id);
                        setEditIntensita({ valore: row.valore ?? 0, nome: row.nome || '' });
                      } catch (err) {
                        setError(err?.message || 'Impossibile caricare intensità.');
                      }
                    }}
                  >
                    Modifica
                  </button>
                  <button className="text-red-400" onClick={() => staffDeletePilotIntensita(i.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>
      ) : null}

      {activeTab === 'eventi' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
          <h3 className="font-semibold">Eventi viaggio (randomici)</h3>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              disabled={eventiCodiciBusy}
              className="px-3 py-2 rounded-lg border border-amber-600/60 text-amber-200 hover:bg-amber-950/40 text-sm disabled:opacity-50"
              onClick={() => aggiornaCodiciEventi(true)}
            >
              Anteprima codici da stato
            </button>
            <button
              type="button"
              disabled={eventiCodiciBusy}
              className="px-3 py-2 rounded-lg bg-amber-700 hover:bg-amber-600 text-sm font-medium disabled:opacity-50"
              onClick={() => aggiornaCodiciEventi(false)}
            >
              Aggiorna codici da stato nave
            </button>
            <button
              type="button"
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-sm font-medium"
              onClick={() => {
                setError('');
                setCreateEventoModalOpen(true);
              }}
            >
              Nuovo evento
            </button>
          </div>
        </div>
        <p className="text-xs text-gray-400 mb-3">
          I pulsanti «codici da stato» rigenerano soluzione totale, parziali e catastrofi in base ai livelli
          attuali dei sottosistemi (sessione console attiva o registro nave).
        </p>
        <StaffMinigiocoPageToolbar
          pageKey={MINIGIOCO_PAGE_KEYS.pilotEventi}
          pageLabel="Pilotaggio — Eventi"
          onLogout={onLogout}
        />
        <div className="space-y-2 mt-3">
          {eventi.map((e) => (
            <div
              key={e.id}
              className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between bg-gray-800/60 rounded-lg px-3 py-2 text-sm border border-gray-700/80"
            >
              <div className="min-w-0 flex-1">
                <div className="font-medium text-white truncate" title={e.nome}>
                  {e.nome}
                </div>
                <div className="text-xs text-gray-400 mt-0.5 flex flex-wrap gap-x-2 gap-y-0.5">
                  <span>
                    durata{' '}
                    <span className="font-mono text-gray-300">{formatDurataTickLabel(e.durata_tick)}</span>
                  </span>
                  {e.scadenza_critica ? (
                    <span className="text-amber-300/90">scadenza CA</span>
                  ) : null}
                  <span>peso {e.peso_random ?? 10}</span>
                  <span>{e.attivo !== false ? 'attivo' : 'disattivato'}</span>
                  {e.sottosistema_codice ? (
                    <span className="font-mono text-indigo-300/90">{e.sottosistema_codice}</span>
                  ) : null}
                  <span className="font-mono text-amber-200/90" title="Codice legacy">
                    {e.codice_soluzione_esatta || '—'}
                  </span>
                </div>
              </div>
              <div className="flex gap-3 shrink-0">
                <button type="button" className="text-indigo-300 hover:text-indigo-200" onClick={() => openEditEventoModal(e)}>
                  Modifica
                </button>
                <button type="button" className="text-red-400 hover:text-red-300" onClick={() => staffDeletePilotEvento(e.id, onLogout).then(loadData)}>
                  Elimina
                </button>
              </div>
            </div>
          ))}
        </div>
      </section>
      ) : null}

      {activeTab === 'comandi_critici' ? (
      <section className="rounded-xl border border-red-900/40 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2 text-red-200">Comandi critici globali</h3>
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          Definisci pattern sul codice a 3 caratteri (stessa sintassi degli eventi: jolly <strong className="text-gray-300">_</strong>, intervalli{' '}
          <strong className="text-gray-300 font-mono">XY(N-M)</strong>). Se il pilota inserisce un codice valido che matcha una riga{' '}
          <em>attiva</em>, la nave precipita subito — anche senza evento attivo o durante decollo/atterraggio.
        </p>
        <div className="flex flex-wrap gap-2 mb-3 items-end">
          <input className="bg-gray-800 rounded px-2 py-1 font-mono w-28" maxLength={48} placeholder="XX9" value={nuovoCritico.pattern} onChange={(e) => setNuovoCritico((p) => ({ ...p, pattern: e.target.value }))} />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1 min-w-[8rem]" placeholder="Etichetta (opzionale)" value={nuovoCritico.nome} onChange={(e) => setNuovoCritico((p) => ({ ...p, nome: e.target.value }))} />
          <label className="flex items-center gap-2 text-sm text-gray-300">
            <input type="checkbox" checked={nuovoCritico.attivo} onChange={(e) => setNuovoCritico((p) => ({ ...p, attivo: e.target.checked }))} />
            Attivo
          </label>
          <button type="button" className="px-3 py-1 rounded bg-red-800 hover:bg-red-700 text-white shrink-0" onClick={addComandoCritico}>Aggiungi</button>
        </div>
        <div className="space-y-1 text-sm">
          {comandiCritici.map((row) => (
            <div key={row.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-gray-800/60 rounded px-2 py-2 border border-gray-700">
              {editCriticoId === row.id ? (
                <div className="flex flex-wrap gap-2 w-full items-center">
                  <input className="bg-gray-700 rounded px-2 py-1 font-mono w-28" maxLength={48} value={editCritico.pattern} onChange={(e) => setEditCritico((p) => ({ ...p, pattern: e.target.value }))} />
                  <input className="bg-gray-700 rounded px-2 py-1 flex-1 min-w-[10rem]" value={editCritico.nome} onChange={(e) => setEditCritico((p) => ({ ...p, nome: e.target.value }))} />
                  <label className="flex items-center gap-2 text-xs text-gray-300 shrink-0">
                    <input type="checkbox" checked={Boolean(editCritico.attivo)} onChange={(e) => setEditCritico((p) => ({ ...p, attivo: e.target.checked }))} />
                    Attivo
                  </label>
                  <button type="button" className="text-emerald-400 shrink-0" onClick={salvaComandoCritico}>Salva</button>
                  <button type="button" className="text-gray-300 shrink-0" onClick={() => setEditCriticoId(null)}>Annulla</button>
                </div>
              ) : (
                <>
                  <span>
                    <span className="font-mono text-amber-200">{row.pattern}</span>
                    {row.nome ? <span className="text-gray-400 ml-2">— {row.nome}</span> : null}
                    {!row.attivo ? <span className="text-gray-500 ml-2 text-xs">(disattivato)</span> : null}
                  </span>
                  <div className="flex gap-3 shrink-0">
                    <button
                      type="button"
                      className="text-indigo-300"
                      onClick={async () => {
                        setError('');
                        try {
                          const full = await staffGetPilotComandoCritico(row.id, onLogout);
                          setEditCriticoId(full.id);
                          setEditCritico({
                            pattern: full.pattern || '',
                            nome: full.nome || '',
                            attivo: full.attivo ?? true,
                          });
                        } catch (err) {
                          setError(err?.message || 'Impossibile caricare il comando critico.');
                        }
                      }}
                    >
                      Modifica
                    </button>
                    <button type="button" className="text-red-400" onClick={() => staffDeletePilotComandoCritico(row.id, onLogout).then(loadData)}>Elimina</button>
                  </div>
                </>
              )}
            </div>
          ))}
          {!comandiCritici.length ? <p className="text-gray-500 text-sm">Nessun pattern critico configurato.</p> : null}
        </div>
      </section>
      ) : null}

      {activeTab === 'stati_allerta' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Stati di allerta (DEFCON 0–6)</h3>
        <p className="text-xs text-gray-400 mb-4 leading-relaxed">
          Livelli allineati al DEFCON della sessione. Imposta la <strong className="text-gray-300">durata del tick durante gli eventi</strong>{' '}
          (in secondi: sostituisce l&apos;intervallo Runtime Console finché l&apos;evento è attivo) e la probabilità di spawn per tick.
          Segna un solo livello come <strong className="text-gray-300">nave abbattuta</strong>.
        </p>
        <div className="space-y-3 text-sm">
          {statiAllerta.map((st) => (
            <div key={st.id} className="bg-gray-800/70 rounded-lg p-3 border border-gray-600">
              {editStatoId === st.id ? (
                <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-2 items-end">
                  <div className="text-xs text-gray-500 sm:col-span-2 lg:col-span-3">Livello {st.livello}</div>
                  <label className="block">
                    <span className="text-xs text-gray-400">Nome</span>
                    <input className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.nome || ''} onChange={(e) => setEditStato((p) => ({ ...p, nome: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Colore (#RRGGBB)</span>
                    <div className="flex gap-2 mt-0.5">
                      <input type="color" className="h-9 w-14 rounded cursor-pointer border-0 p-0 bg-transparent" value={(editStato.colore || '#888888').slice(0, 7)} onChange={(e) => setEditStato((p) => ({ ...p, colore: e.target.value }))} />
                      <input className="bg-gray-700 rounded px-2 py-1 flex-1 font-mono text-xs" value={editStato.colore || ''} onChange={(e) => setEditStato((p) => ({ ...p, colore: e.target.value }))} />
                    </div>
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Durata del tick durante eventi (s)</span>
                    <input type="number" min={1} className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.tempo_risoluzione_secondi} onChange={(e) => setEditStato((p) => ({ ...p, tempo_risoluzione_secondi: e.target.value }))} />
                    <span className="text-[10px] text-gray-500 mt-0.5 block">
                      Ogni tick evento dura così (es. 20s). Durata totale evento ≈ tick catalogo × questo valore.
                    </span>
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Prob. evento per tick (0..1)</span>
                    <input type="number" min={0} max={1} step={0.01} className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.probabilita_evento_per_tick ?? 0} onChange={(e) => setEditStato((p) => ({ ...p, probabilita_evento_per_tick: e.target.value }))} />
                    <span className="text-[10px] text-gray-500 mt-0.5 block">
                      Ogni tick motore sorteggia se generare un evento (se non ce n&apos;è uno attivo).
                    </span>
                  </label>
                  {Number(editStato.probabilita_evento_per_tick ?? 0) <= 0 ? (
                    <label className="block sm:col-span-2 lg:col-span-1">
                      <span className="text-xs text-gray-400">Freq. eventi min–max (s) — solo se prob/tick = 0</span>
                      <div className="flex gap-2 mt-0.5">
                        <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_min_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_min_sec: e.target.value }))} />
                        <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_max_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_max_sec: e.target.value }))} />
                      </div>
                      <span className="text-[10px] text-gray-500 mt-0.5 block">
                        Fallback temporizzato: prossimo evento tra min e max secondi (random). Ignorato se prob/tick &gt; 0.
                      </span>
                    </label>
                  ) : null}
                  <label className="flex items-center gap-2 sm:col-span-2 lg:col-span-3 cursor-pointer">
                    <input type="checkbox" checked={Boolean(editStato.equivale_nave_abbattuta)} onChange={(e) => setEditStato((p) => ({ ...p, equivale_nave_abbattuta: e.target.checked }))} />
                    <span className="text-sm text-red-300">Equivale a nave abbattuta / precipitata</span>
                  </label>
                  <div className="flex gap-2 sm:col-span-2 lg:col-span-3">
                    <button type="button" className="text-emerald-400" onClick={salvaStatoAllerta}>Salva</button>
                    <button type="button" className="text-gray-400" onClick={() => setEditStatoId(null)}>Annulla</button>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3">
                  <div className="flex items-center gap-3">
                    <span className="inline-flex items-center justify-center w-10 h-10 rounded-lg font-bold text-white shrink-0" style={{ backgroundColor: st.colore || '#555' }}>
                      {st.livello}
                    </span>
                    <div>
                      <div className="font-semibold">{st.nome}</div>
                      <div className="text-xs text-gray-400">
                        Tick evento {st.tempo_risoluzione_secondi}s · Prob/tick {st.probabilita_evento_per_tick}
                        {Number(st.probabilita_evento_per_tick ?? 0) <= 0 ? (
                          <span> · Eventi ogni {st.frequenza_evento_min_sec}–{st.frequenza_evento_max_sec}s</span>
                        ) : null}
                        {st.equivale_nave_abbattuta ? <span className="text-red-400 ml-2">· Nave abbattuta</span> : null}
                      </div>
                    </div>
                  </div>
                  <button
                    type="button"
                    className="text-indigo-300 shrink-0 self-start md:self-center"
                    onClick={async () => {
                      setError('');
                      try {
                        const full = await staffGetPilotStatoAllerta(st.id, onLogout);
                        setEditStatoId(full.id);
                        setEditStato({
                          nome: full.nome || '',
                          colore: full.colore || '#888888',
                          frequenza_evento_min_sec: full.frequenza_evento_min_sec ?? 60,
                          frequenza_evento_max_sec: full.frequenza_evento_max_sec ?? 90,
                          tempo_risoluzione_secondi: full.tempo_risoluzione_secondi ?? 20,
                          probabilita_evento_per_tick: full.probabilita_evento_per_tick ?? 0,
                          equivale_nave_abbattuta: Boolean(full.equivale_nave_abbattuta),
                        });
                      } catch (err) {
                        setError(err?.message || 'Impossibile caricare lo stato allerta.');
                      }
                    }}
                  >
                    Modifica
                  </button>
                </div>
              )}
            </div>
          ))}
          {!statiAllerta.length ? (
            <p className="text-gray-400 text-sm">Nessuno stato caricato. Esegui le migrazioni (<code className="text-xs">0005_statoallertapilot</code>).</p>
          ) : null}
        </div>
      </section>
      ) : null}

      {activeTab === 'sessione_live' ? (
      <section className="rounded-xl border border-amber-900/50 p-4 bg-gray-900/60 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-2">
          <div>
            <h3 className="font-semibold text-amber-200">Sessione live — guasto / riparazione</h3>
            <p className="text-xs text-gray-400 mt-1">
              Azioni sul volo attivo corrente (stato <code className="text-amber-100">volo</code>).
              Aggiornamento automatico ogni 4s.
            </p>
          </div>
          <button
            type="button"
            className="px-3 py-1 rounded bg-gray-700 hover:bg-gray-600 text-sm"
            onClick={loadSessioneLive}
            disabled={sessioneLiveBusy}
          >
            Aggiorna
          </button>
        </div>

        {!sessioneLive?.sessione ? (
          <p className="text-gray-400 text-sm">Nessun volo attivo in questo momento.</p>
        ) : (
          <>
            <div className="grid md:grid-cols-4 gap-3 text-sm">
              <div className="rounded-lg border border-gray-700 bg-gray-950/50 p-3">
                <div className="text-xs text-gray-500 uppercase">Pilota</div>
                <div className="font-medium">{sessioneLive.sessione.pilota_nome || '—'}</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-gray-950/50 p-3">
                <div className="text-xs text-gray-500 uppercase">Rotta</div>
                <div>{sessioneLive.sessione.partenza_nome || '—'} → {sessioneLive.sessione.arrivo_nome || '—'}</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-gray-950/50 p-3">
                <div className="text-xs text-gray-500 uppercase">DEFCON</div>
                <div className="text-xl font-bold">{sessioneLive.sessione.defcon}</div>
              </div>
              <div className="rounded-lg border border-gray-700 bg-gray-950/50 p-3">
                <div className="text-xs text-gray-500 uppercase">Decollo</div>
                <div className={sessioneLive.decollo_effettuato ? 'text-emerald-400' : 'text-amber-300'}>
                  {sessioneLive.decollo_effettuato ? 'In crociera' : 'A terra (motori off)'}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Distanza {Math.round(sessioneLive.sessione.distanza_percorsa || 0)} / {Math.round(sessioneLive.sessione.distanza_target || 0)}
                </div>
              </div>
            </div>

            {(sessioneLive.eventi_attivi || []).length > 0 ? (
              <div className="rounded-lg border border-red-900/40 bg-red-950/20 p-3 text-sm">
                <div className="font-semibold text-red-200 mb-1">Eventi attivi</div>
                {(sessioneLive.eventi_attivi || []).map((ev) => (
                  <div key={ev.id} className="text-red-100/90">
                    {ev.nome}
                    {ev.ticks_rimanenti != null ? ` — ${ev.ticks_rimanenti} tick` : ''}
                    {ev.precipita_a_scadenza ? ' (critico)' : ''}
                  </div>
                ))}
              </div>
            ) : null}

            <div className="overflow-x-auto rounded-lg border border-gray-700">
              <table className="w-full text-sm">
                <thead className="bg-gray-800/80 text-left text-xs uppercase text-gray-400">
                  <tr>
                    <th className="p-2">Cod</th>
                    <th className="p-2">Nome</th>
                    <th className="p-2">Liv</th>
                    <th className="p-2">Stato</th>
                    <th className="p-2 text-right">Azioni staff</th>
                  </tr>
                </thead>
                <tbody>
                  {(sessioneLive.sottosistemi || []).map((st) => {
                    const inRepair = st.recovery_at && new Date(st.recovery_at) > new Date();
                    let statoLabel = 'Online';
                    let statoClass = 'text-emerald-400';
                    if (inRepair) {
                      statoLabel = 'Ripristino auto';
                      statoClass = 'text-amber-400';
                    } else if (!st.online) {
                      statoLabel = 'Guasto';
                      statoClass = 'text-red-400';
                    }
                    return (
                      <tr key={st.id} className="border-t border-gray-800">
                        <td className="p-2 font-mono font-bold">{st.codice}</td>
                        <td className="p-2">{st.nome}</td>
                        <td className="p-2">{st.livello_attuale ?? 0}</td>
                        <td className={`p-2 font-medium ${statoClass}`}>{statoLabel}</td>
                        <td className="p-2 text-right space-x-1">
                          <button
                            type="button"
                            disabled={sessioneLiveBusy || !st.online}
                            className="px-2 py-1 rounded bg-red-800 hover:bg-red-700 disabled:opacity-40 text-xs"
                            onClick={() => azioneSottosistemaLive(st.sottosistema_id, 'guasto')}
                          >
                            Guasta
                          </button>
                          <button
                            type="button"
                            disabled={sessioneLiveBusy || st.online}
                            className="px-2 py-1 rounded bg-emerald-700 hover:bg-emerald-600 disabled:opacity-40 text-xs"
                            onClick={() => azioneSottosistemaLive(st.sottosistema_id, 'ripara')}
                          >
                            Ripara
                          </button>
                          <button
                            type="button"
                            disabled={sessioneLiveBusy || st.online}
                            className="px-2 py-1 rounded bg-amber-800 hover:bg-amber-700 disabled:opacity-40 text-xs"
                            onClick={() => azioneSottosistemaLive(st.sottosistema_id, 'ripristino')}
                          >
                            Timer
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
      ) : null}

      {activeTab === 'stiva' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60 space-y-4">
        <h3 className="font-semibold">Stiva componenti nave</h3>
        <p className="text-xs text-gray-400">
          Inventario globale condiviso. Coppie opposte: massimo 5 tick di coesistenza, poi annichilamento 1:1 in un colpo.
        </p>
        {!stivaData ? (
          <p className="text-gray-500 text-sm">Caricamento stiva… (esegui <code className="text-gray-400">seed_componenti_nave</code> se il catalogo è vuoto)</p>
        ) : (
          <>
            {stivaData.coppie_opposite?.length ? (
              <div className="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
                {stivaData.coppie_opposite.map((c) => (
                  <div key={c.id} className="rounded border border-gray-700 bg-gray-800/50 p-2 text-xs">
                    <div className="font-medium">{c.colore_a.nome} ↔ {c.colore_b.nome}</div>
                    <div className="text-gray-400 mt-1">
                      Qty: {c.colore_a.quantita} / {c.colore_b.quantita}
                      {c.entrambi_presenti ? (
                        <span className="text-amber-300 ml-2">Coesistenza {c.tick_coesistenza}/{c.tick_coesistenza_max}</span>
                      ) : null}
                    </div>
                  </div>
                ))}
              </div>
            ) : null}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-left text-gray-400 border-b border-gray-700">
                    <th className="py-2 pr-2">Indice</th>
                    <th className="py-2 pr-2">Mattone</th>
                    <th className="py-2 pr-2">Colore</th>
                    <th className="py-2 pr-2">Qty</th>
                    <th className="py-2">Azioni</th>
                  </tr>
                </thead>
                <tbody>
                  {(stivaData.mattoni_catalogo || []).map((m) => {
                    const row = (stivaData.righe || []).find((r) => r.mattone_id === m.id);
                    const qty = row?.quantita ?? 0;
                    return (
                      <tr key={m.id} className="border-b border-gray-800/80">
                        <td className="py-2 pr-2 font-mono">{m.indice_componente}</td>
                        <td className="py-2 pr-2">{m.nome}</td>
                        <td className="py-2 pr-2">{m.colore_nome}</td>
                        <td className="py-2 pr-2 font-mono">{qty}</td>
                        <td className="py-2 flex gap-1">
                          <button type="button" disabled={stivaBusy} className="px-2 py-0.5 rounded bg-emerald-800 text-xs" onClick={() => modificaStiva(m.id, 1)}>+1</button>
                          <button type="button" disabled={stivaBusy || qty <= 0} className="px-2 py-0.5 rounded bg-red-900 text-xs" onClick={() => modificaStiva(m.id, -1)}>-1</button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </>
        )}
      </section>
      ) : null}

      {activeTab === 'runtime' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Runtime Console Pilotaggio</h3>
        <p className="text-xs text-gray-400 mb-4">
          Intervallo del tick motore in <strong className="text-gray-300">viaggio regolare</strong> (senza evento attivo).
          Con evento attivo il motore usa la durata tick del DEFCON corrente.
          {' '}Le checkbox hanno effetto sul server solo dopo <strong className="text-gray-300">Salva runtime</strong>.
        </p>
        {runtimeConfig ? (
          <div className="space-y-3 text-sm">
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.login_required_console)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, login_required_console: e.target.checked }))}
              />
              Richiedi login console (ticket/QR)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.alarm_audio_enabled)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, alarm_audio_enabled: e.target.checked }))}
              />
              Abilita audio allarmi console (beep su criticita)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.riparazione_componenti_abilitata)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, riparazione_componenti_abilitata: e.target.checked }))}
              />
              Riparazione sottosistemi con componenti (stiva)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.annichilamento_opposti_abilitato)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, annichilamento_opposti_abilitato: e.target.checked }))}
              />
              Annichilamento colori opposti in stiva
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.compattatore_console_abilitata)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, compattatore_console_abilitata: e.target.checked }))}
              />
              Console compattatore (/pilot/?screen=compattatore)
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.compattatore_login_richiesto)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, compattatore_login_richiesto: e.target.checked }))}
              />
              Login richiesto per console compattatore
            </label>
            <label className="flex items-center gap-2">
              <input
                type="checkbox"
                checked={Boolean(runtimeConfig.compattatore_quantico_abilitato)}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, compattatore_quantico_abilitato: e.target.checked }))}
              />
              Compattatore Quantico (sacrificio oggetto → componenti; disattivo fino a evento)
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Statistica accesso compattatore</span>
              <input
                className="bg-gray-800 rounded px-2 py-1 mt-1 font-mono uppercase"
                maxLength={3}
                value={runtimeConfig.compattatore_stat_accesso_sigla ?? '0IN'}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, compattatore_stat_accesso_sigla: e.target.value }))}
              />
            </label>
            <label className="block">
              <span className="text-xs text-gray-400">Intervallo tick (secondi)</span>
              <input
                type="number"
                min={0.5}
                step={0.5}
                className="bg-gray-800 rounded px-2 py-1 mt-1"
                value={runtimeConfig.tick_interval_secondi ?? 5}
                onChange={(e) => setRuntimeConfig((p) => ({ ...p, tick_interval_secondi: e.target.value }))}
              />
            </label>
            <button
              type="button"
              className="px-3 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              onClick={salvaRuntimeConfig}
              disabled={runtimeSaving}
            >
              {runtimeSaving ? 'Salvataggio…' : 'Salva runtime'}
            </button>
            {runtimeSaveFeedback ? (
              <p
                className={`text-xs rounded-md px-3 py-2 border ${
                  runtimeSaveFeedback.type === 'success'
                    ? 'text-emerald-200 bg-emerald-950/40 border-emerald-700/50'
                    : 'text-red-200 bg-red-950/40 border-red-700/50'
                }`}
                role="status"
                aria-live="polite"
              >
                {runtimeSaveFeedback.text}
              </p>
            ) : null}
          </div>
        ) : (
          <div className="text-gray-400 text-sm">Runtime config non disponibile.</div>
        )}
      </section>
      ) : null}

      {editEventoId ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          role="presentation"
          onClick={closeEditEventoModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="pilot-edit-evento-title"
            className="bg-gray-800 rounded-2xl w-full max-w-5xl max-h-[min(92vh,900px)] flex flex-col border border-indigo-500/40 shadow-2xl shadow-indigo-950/50"
            onClick={(ev) => ev.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-start gap-3 px-5 pt-4 pb-3 border-b border-gray-700/90 bg-gray-800/95">
              <div>
                <h3 id="pilot-edit-evento-title" className="text-lg font-bold text-indigo-300">
                  Modifica evento viaggio
                </h3>
                <p className="text-xs text-gray-400 mt-1 leading-relaxed">
                  Testo per il pilota, regole ST/SP/CA, codici e collegamento a sottosistema. Salva per applicare al catalogo.
                </p>
              </div>
              <button
                type="button"
                className="shrink-0 px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:bg-gray-700 border border-gray-600"
                onClick={closeEditEventoModal}
              >
                Chiudi
              </button>
            </div>
            <div className="flex-1 overflow-y-auto min-h-0 px-5 py-4 space-y-4 text-sm">
              {error ? (
                <div className="rounded-lg border border-red-700/50 bg-red-950/50 px-3 py-2 text-sm text-red-100">
                  {error}
                </div>
              ) : null}
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Nome</span>
                <input
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                  value={editEvento.nome}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, nome: ev.target.value }))}
                />
              </label>
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Descrizione (pilota)</span>
                <textarea
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none min-h-[88px] resize-y"
                  value={editEvento.descrizione}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, descrizione: ev.target.value }))}
                />
              </label>
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Durata evento (tick min–max)</span>
                  <div className="flex gap-2 mt-1">
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                      value={editEvento.tick_min}
                      onChange={(ev) => setEditEvento((p) => ({ ...p, tick_min: ev.target.value }))}
                      placeholder="min"
                    />
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                      value={editEvento.tick_max}
                      onChange={(ev) => setEditEvento((p) => ({ ...p, tick_max: ev.target.value }))}
                      placeholder="max"
                    />
                  </div>
                  <p className="text-[11px] text-gray-500 mt-1">
                    Numero di tick dell&apos;evento (fisso se min=max, altrimenti random inclusivo).
                    Secondi totali ≈ tick × durata tick DEFCON attuale.
                  </p>
                </label>
                <label className="flex items-start gap-2 cursor-pointer pt-1">
                  <input
                    type="checkbox"
                    className="mt-1 rounded border-gray-600"
                    checked={Boolean(editEvento.scadenza_critica)}
                    onChange={(ev) =>
                      setEditEvento((p) => ({
                        ...p,
                        scadenza_critica: ev.target.checked,
                      }))
                    }
                  />
                  <span className="text-sm text-gray-300">
                    Scadenza critica: allo scadere dei tick applica{' '}
                    <code className="text-gray-400">ca_effetto</code>; altrimenti l&apos;evento scompare
                  </span>
                </label>
                <label className="block">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Peso random</span>
                  <input
                    type="number"
                    min={0}
                    className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                    value={editEvento.peso_random}
                    onChange={(ev) => setEditEvento((p) => ({ ...p, peso_random: ev.target.value }))}
                  />
                </label>
                <label className="block">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Codice legacy (3 car.)</span>
                  <input
                    maxLength={3}
                    className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none font-mono uppercase"
                    value={editEvento.codice_soluzione_esatta ?? ''}
                    onChange={(ev) =>
                      setEditEvento((p) => ({
                        ...p,
                        codice_soluzione_esatta: ev.target.value.toUpperCase().replace(/[^A-Z0-9_()-]/g, '').slice(0, 3),
                      }))
                    }
                  />
                </label>
              </div>
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Sottosistema collegato</span>
                <select
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                  value={editEvento.sottosistema || ''}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, sottosistema: ev.target.value }))}
                >
                  <option value="">Nessuno</option>
                  {sottosistemi.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.nome} ({s.codice})
                    </option>
                  ))}
                </select>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input
                  type="checkbox"
                  className="rounded border-gray-600"
                  checked={Boolean(editEvento.attivo)}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, attivo: ev.target.checked }))}
                />
                <span className="text-gray-300">Evento attivo nel pool random</span>
              </label>

              <div className="rounded-xl border border-indigo-900/40 p-4 space-y-3 bg-gray-900/50">
                <div className="text-xs font-semibold text-indigo-200/90 uppercase tracking-wide">Composer condizioni ST / SP / CA</div>
                <p className="text-[11px] text-gray-500 leading-relaxed">
                  ST = soluzione totale (DEFCON −1, evento chiuso). SP = parziale (evento prosegue, DEFCON invariato).
                  CA = effetto critico. Durata in tick; ogni tick evento dura quanto il DEFCON (Stati allerta).
                </p>
                <div className="grid md:grid-cols-7 gap-2 border border-gray-700 rounded-lg p-2">
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.outcome} onChange={(ev) => setDraftCondition((p) => ({ ...p, outcome: ev.target.value }))}>
                    <option value="st">ST (soluzione totale)</option>
                    <option value="sp">SP (parziale)</option>
                    <option value="ca">CA (critico)</option>
                  </select>
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.subsystem} onChange={(ev) => setDraftCondition((p) => ({ ...p, subsystem: ev.target.value }))}>
                    <option value="">Sottosistema…</option>
                    {sottosistemi.map((ss) => (
                      <option key={ss.id} value={ss.codice}>
                        {ss.nome} ({ss.codice})
                      </option>
                    ))}
                  </select>
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.op} onChange={(ev) => setDraftCondition((p) => ({ ...p, op: ev.target.value }))}>
                    {conditionOps.map((o) => (
                      <option key={o.value} value={o.value}>
                        {o.label}
                      </option>
                    ))}
                  </select>
                  {draftCondition.op === 'between' ? (
                    <>
                      <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.min} onChange={(ev) => setDraftCondition((p) => ({ ...p, min: ev.target.value }))} placeholder="min" />
                      <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.max} onChange={(ev) => setDraftCondition((p) => ({ ...p, max: ev.target.value }))} placeholder="max" />
                    </>
                  ) : draftCondition.op === 'direction' ? (
                    <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.direction_rule} onChange={(ev) => setDraftCondition((p) => ({ ...p, direction_rule: ev.target.value }))}>
                      <option value="stessa_direzione">stessa_direzione</option>
                      <option value="direzione_opposta">direzione_opposta</option>
                      <option value="non_stessa_direzione">non_stessa_direzione</option>
                      <option value="non_direzione_opposta">non_direzione_opposta</option>
                    </select>
                  ) : ['piene', 'vuote', 'non_piene', 'non_vuote', 'distrutte', 'invertito', 'non_invertito', 'espulso', 'non_espulso'].includes(draftCondition.op) ? (
                    <div className="bg-gray-900 rounded px-2 py-1 text-xs text-gray-300">Condizione booleana</div>
                  ) : (
                    <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.value} onChange={(ev) => setDraftCondition((p) => ({ ...p, value: ev.target.value }))} placeholder="val" />
                  )}
                  <button type="button" className="px-3 py-1 rounded bg-indigo-700 text-sm" onClick={addEditRuleCondition}>
                    Aggiungi
                  </button>
                  <button type="button" className="px-3 py-1 rounded bg-sky-700 text-sm" onClick={generaJsonGuidaEventoEdit}>
                    Aggiorna JSON
                  </button>
                </div>
                <div className="grid md:grid-cols-3 gap-2">
                  {['st', 'sp', 'ca'].map((k) => (
                    <div key={`edit-${k}`} className="border border-gray-700 rounded-lg p-2 bg-gray-950/40">
                      <div className="flex justify-between items-center mb-2">
                        <strong>{k.toUpperCase()}</strong>
                        <span className="text-[11px] text-gray-500">Formula con parentesi</span>
                      </div>
                      <input
                        className="bg-gray-900 rounded px-2 py-1 text-xs w-full mb-2 font-mono border border-gray-700"
                        placeholder="(1 AND 2) OR 3"
                        value={editRuleBuilder[k].expression || ''}
                        onChange={(ev) => setEditRuleBuilder((p) => ({ ...p, [k]: { ...p[k], expression: ev.target.value } }))}
                      />
                      <div className={`text-[11px] mb-2 ${editRuleValidation[k].valid ? 'text-emerald-300' : 'text-amber-300'}`}>
                        {editRuleValidation[k].valid ? 'OK' : 'Errore'}: {editRuleValidation[k].message}
                      </div>
                      <div className="space-y-1 text-xs">
                        {(editRuleBuilder[k].conditions || []).map((c, idx) => (
                          <div key={`${k}-edit-${idx}`} className="bg-gray-900 rounded px-2 py-1 flex justify-between gap-2">
                            <span>
                              {idx + 1}) {c.sottosistema} {c.op}{' '}
                              {c.op === 'between' ? `${c.min}-${c.max}` : ''}
                              {c.op === 'direction' ? c.direction_rule : ''}
                              {![
                                'between',
                                'direction',
                                'piene',
                                'vuote',
                                'non_piene',
                                'non_vuote',
                                'distrutte',
                                'invertito',
                                'non_invertito',
                                'espulso',
                                'non_espulso',
                              ].includes(c.op)
                                ? c.value
                                : ''}
                            </span>
                            <button type="button" className="text-red-400 shrink-0" onClick={() => removeEditRuleCondition(k, idx)}>
                              x
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <CaEffettoFields caEffetto={editCaEffetto} setCaEffetto={setEditCaEffetto} sottosistemi={sottosistemi} />

              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Regole avanzate (JSON)</span>
                <textarea
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none min-h-[140px] font-mono text-xs leading-relaxed resize-y"
                  value={editEvento.regole_json}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, regole_json: ev.target.value }))}
                />
              </label>
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Codici soluzione parziale (array JSON)</span>
                <textarea
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none min-h-[72px] font-mono text-xs resize-y"
                  value={editEvento.codici_soluzione_parziale_json}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, codici_soluzione_parziale_json: ev.target.value }))}
                />
              </label>
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Codici precipizio (array JSON)</span>
                <textarea
                  className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none min-h-[72px] font-mono text-xs resize-y"
                  value={editEvento.codici_precipizio_json}
                  onChange={(ev) => setEditEvento((p) => ({ ...p, codici_precipizio_json: ev.target.value }))}
                />
              </label>
            </div>
            <div className="shrink-0 flex flex-wrap justify-end gap-2 px-5 py-3 border-t border-gray-700 bg-gray-900/80">
              <button
                type="button"
                className="px-4 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700"
                onClick={closeEditEventoModal}
              >
                Annulla
              </button>
              <button type="button" className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium" onClick={salvaEvento}>
                Salva modifiche
              </button>
            </div>
          </div>
        </div>
      ) : null}

      <PilotSottosistemaModal
        open={sottoModalMode !== null}
        mode={sottoModalMode === 'edit' ? 'edit' : 'create'}
        draft={sottoModalMode === 'edit' ? editSotto : nuovoSotto}
        setDraft={sottoModalMode === 'edit' ? setEditSotto : setNuovoSotto}
        effettoBuilder={sottoModalMode === 'edit' ? editEffettoGuastoBuilder : nuovoEffettoGuastoBuilder}
        setEffettoBuilder={sottoModalMode === 'edit' ? setEditEffettoGuastoBuilder : setNuovoEffettoGuastoBuilder}
        effettoValidation={sottoModalMode === 'edit' ? editEffettoValidation : nuovoEffettoValidation}
        generaEffettoGuastoJson={generaEffettoGuastoJson}
        onSave={sottoModalMode === 'edit' ? salvaSottosistema : addSottosistema}
        onClose={closeSottoModal}
        serbatoioFuel={sottoModalMode === 'edit' && String(editSotto.tipo || '').toLowerCase() === 'serbatoio' ? serbatoioFuel : null}
        serbatoioFuelDraft={serbatoioFuelDraft}
        setSerbatoioFuelDraft={setSerbatoioFuelDraft}
        serbatoioFuelBusy={serbatoioFuelBusy}
        onApplySerbatoioFuel={() => applicaSerbatoioFuel({ carburante_attuale: Number(serbatoioFuelDraft) })}
        onFillSerbatoioFuel={() => applicaSerbatoioFuel({ riempi: true })}
        onRefreshSerbatoioFuel={() => loadSerbatoioFuel(editSottoId)}
        mattoniCatalogo={stivaData?.mattoni_catalogo || []}
      />

      {createEventoModalOpen ? (
        <div
          className="fixed inset-0 z-[100] flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
          role="presentation"
          onClick={closeCreateEventoModal}
        >
          <div
            role="dialog"
            aria-modal="true"
            className="bg-gray-800 rounded-2xl w-full max-w-5xl max-h-[min(92vh,900px)] flex flex-col border border-indigo-500/40 shadow-2xl"
            onClick={(ev) => ev.stopPropagation()}
          >
            <div className="shrink-0 flex justify-between items-start gap-3 px-5 pt-4 pb-3 border-b border-gray-700/90">
              <div>
                <h3 className="text-lg font-bold text-indigo-300">Nuovo evento viaggio</h3>
                <p className="text-xs text-gray-400 mt-1">Nome, regole SP/CA e collegamento sottosistema.</p>
              </div>
              <button type="button" className="shrink-0 px-3 py-1.5 rounded-lg text-sm text-gray-300 hover:bg-gray-700 border border-gray-600" onClick={closeCreateEventoModal}>
                Chiudi
              </button>
            </div>
            <div className="flex-1 overflow-y-auto min-h-0 px-5 py-4 space-y-4 text-sm">
              {error ? (
                <div className="rounded-lg border border-red-700/50 bg-red-950/50 px-3 py-2 text-sm text-red-100">{error}</div>
              ) : null}
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Nome</span>
                <input className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600" value={nuovoEvento.nome} onChange={(e) => setNuovoEvento((p) => ({ ...p, nome: e.target.value }))} />
              </label>
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Descrizione</span>
                <textarea className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 min-h-[72px]" value={nuovoEvento.descrizione} onChange={(e) => setNuovoEvento((p) => ({ ...p, descrizione: e.target.value }))} />
              </label>
              <div className="grid sm:grid-cols-2 gap-4">
                <label className="block">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Durata evento (tick min–max)</span>
                  <div className="flex gap-2 mt-1">
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600"
                      value={nuovoEvento.tick_min}
                      onChange={(e) => setNuovoEvento((p) => ({ ...p, tick_min: e.target.value }))}
                    />
                    <input
                      type="number"
                      min={1}
                      className="w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600"
                      value={nuovoEvento.tick_max}
                      onChange={(e) => setNuovoEvento((p) => ({ ...p, tick_max: e.target.value }))}
                    />
                  </div>
                </label>
                <label className="flex items-start gap-2 cursor-pointer pt-6">
                  <input
                    type="checkbox"
                    className="mt-1 rounded border-gray-600"
                    checked={Boolean(nuovoEvento.scadenza_critica)}
                    onChange={(e) =>
                      setNuovoEvento((p) => ({
                        ...p,
                        scadenza_critica: e.target.checked,
                      }))
                    }
                  />
                  <span className="text-sm text-gray-300">Scadenza critica (CA a tick finiti, altrimenti scompare)</span>
                </label>
              </div>
              <div className="rounded-xl border border-indigo-900/40 p-4 space-y-3 bg-gray-900/50">
                <div className="text-xs font-semibold text-indigo-200/90 uppercase tracking-wide">Composer ST / SP / CA</div>
                <div className="grid md:grid-cols-7 gap-2 border border-gray-700 rounded-lg p-2">
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.outcome} onChange={(e) => setDraftCondition((p) => ({ ...p, outcome: e.target.value }))}>
                    <option value="st">ST (soluzione totale)</option>
                    <option value="sp">SP (parziale)</option><option value="ca">CA</option>
                  </select>
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.subsystem} onChange={(e) => setDraftCondition((p) => ({ ...p, subsystem: e.target.value }))}>
                    <option value="">Sottosistema…</option>
                    {sottosistemi.map((s) => <option key={s.id} value={s.codice}>{s.nome} ({s.codice})</option>)}
                  </select>
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.op} onChange={(e) => setDraftCondition((p) => ({ ...p, op: e.target.value }))}>
                    {conditionOps.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
                  </select>
                  {draftCondition.op === 'between' ? (
                    <>
                      <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.min} onChange={(e) => setDraftCondition((p) => ({ ...p, min: e.target.value }))} />
                      <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.max} onChange={(e) => setDraftCondition((p) => ({ ...p, max: e.target.value }))} />
                    </>
                  ) : draftCondition.op === 'direction' ? (
                    <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.direction_rule} onChange={(e) => setDraftCondition((p) => ({ ...p, direction_rule: e.target.value }))}>
                      <option value="direzione_opposta">direzione_opposta</option>
                    </select>
                  ) : ['piene', 'vuote', 'non_piene', 'non_vuote', 'distrutte', 'invertito', 'non_invertito', 'espulso', 'non_espulso'].includes(draftCondition.op) ? (
                    <div className="bg-gray-900 rounded px-2 py-1 text-xs text-gray-300">Booleana</div>
                  ) : (
                    <input type="number" min={0} max={9} className="bg-gray-900 rounded px-2 py-1" value={draftCondition.value} onChange={(e) => setDraftCondition((p) => ({ ...p, value: e.target.value }))} />
                  )}
                  <button type="button" className="px-3 py-1 rounded bg-indigo-700 text-sm" onClick={addRuleCondition}>Aggiungi</button>
                  <button type="button" className="px-3 py-1 rounded bg-sky-700 text-sm" onClick={generaJsonGuidaEvento}>Aggiorna JSON</button>
                </div>
                <div className="grid md:grid-cols-3 gap-2">
                  {['st', 'sp', 'ca'].map((k) => (
                    <div key={`create-${k}`} className="border border-gray-700 rounded-lg p-2 bg-gray-950/40">
                      <strong className="text-xs">{k.toUpperCase()}</strong>
                      <input className="bg-gray-900 rounded px-2 py-1 text-xs w-full mt-1 mb-1 font-mono border border-gray-700" placeholder="(1 AND 2)" value={ruleBuilder[k].expression || ''} onChange={(e) => setRuleBuilder((p) => ({ ...p, [k]: { ...p[k], expression: e.target.value } }))} />
                      <div className={`text-[11px] mb-1 ${ruleValidation[k].valid ? 'text-emerald-300' : 'text-amber-300'}`}>{ruleValidation[k].message}</div>
                      {(ruleBuilder[k].conditions || []).map((c, idx) => (
                        <div key={`${k}-c-${idx}`} className="text-[11px] flex justify-between bg-gray-900 rounded px-1 py-0.5 mb-0.5">
                          <span>{idx + 1}) {c.sottosistema} {c.op}</span>
                          <button type="button" className="text-red-400" onClick={() => removeRuleCondition(k, idx)}>x</button>
                        </div>
                      ))}
                    </div>
                  ))}
                </div>
              </div>
              <CaEffettoFields caEffetto={createCaEffetto} setCaEffetto={setCreateCaEffetto} sottosistemi={sottosistemi} />
              <label className="block">
                <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Regole avanzate (JSON)</span>
                <textarea className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 min-h-[120px] font-mono text-xs" value={nuovoEvento.regole_json} onChange={(e) => setNuovoEvento((p) => ({ ...p, regole_json: e.target.value }))} />
              </label>
            </div>
            <div className="shrink-0 flex justify-end gap-2 px-5 py-3 border-t border-gray-700 bg-gray-900/80">
              <button type="button" className="px-4 py-2 rounded-lg border border-gray-600 text-gray-300 hover:bg-gray-700" onClick={closeCreateEventoModal}>Annulla</button>
              <button type="button" className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-medium" onClick={addEvento}>Crea evento</button>
            </div>
          </div>
        </div>
      ) : null}

      {minigiocoModal}
    </div>
  );
}
