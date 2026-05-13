import React, { useCallback, useEffect, useMemo, useState } from 'react';
import StaffQrTab from '../StaffQrTab';
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
  staffGetPilotStatiAllerta,
  staffGetPilotStatoAllerta,
  staffGetPilotRuntimeConfig,
  staffUpdatePilotComandoCritico,
  staffUpdatePilotEvento,
  staffUpdatePilotIntensita,
  staffUpdatePilotSottosistema,
  staffUpdatePilotStatoAllerta,
  staffUpdatePilotRuntimeConfig,
} from '../../api';

const PILOT_TABS = [
  { id: 'sottosistemi', label: 'Sottosistemi' },
  { id: 'intensita', label: 'Intensità' },
  { id: 'eventi', label: 'Eventi' },
  { id: 'comandi_critici', label: 'Comandi critici (globali)' },
  { id: 'stati_allerta', label: 'Stati allerta (DEFCON)' },
  { id: 'runtime', label: 'Runtime Console' },
];

const defaultEvento = {
  nome: '',
  descrizione: '',
  regole_json: '{\n  "version": 3\n}',
  durata_base_secondi: 20,
  durata_tick: '4',
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
  outcome: 'st',
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

function isValidDurataTickSpec(value) {
  return /^(\d+|\d+-\d+|-\d+|-)$/.test(String(value || '').trim());
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
  return { st: branch('st'), sp: branch('sp'), ca: branch('ca') };
}

/** Unisce ST/SP/CA (AST + metadati UI) e `ca_effetto` nel documento regole. */
function mergeCaAndRulesIntoRegole(baseJson, rb, caTipo, caSottoId) {
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
  if (caTipo === 'guasto_sottosistema') {
    const sid = String(caSottoId || '').trim();
    if (!sid) {
      return {
        ok: false,
        error: 'Per effetto CA «guasto sottosistema» seleziona un sottosistema.',
        regole: null,
      };
    }
    out.ca_effetto = { tipo: 'guasto_sottosistema', sottosistema_id: sid };
  } else {
    out.ca_effetto = { tipo: 'precipizio' };
  }
  return { ok: true, error: '', regole: out };
}

export default function PilotaggioManager({ onLogout }) {
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
  });
  const [nuovoEvento, setNuovoEvento] = useState(defaultEvento);
  const [nuovoCritico, setNuovoCritico] = useState({ pattern: '', nome: '', attivo: true });
  const [editSottoId, setEditSottoId] = useState(null);
  const [editSotto, setEditSotto] = useState({
    codice: '', nome: '', gruppo: '', ordine_gruppo: 0, ordine: 0, tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
    capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
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
  const [editCaEffettoTipo, setEditCaEffettoTipo] = useState('precipizio');
  const [editCaEffettoSottosistemaId, setEditCaEffettoSottosistemaId] = useState('');
  const [createCaEffettoTipo, setCreateCaEffettoTipo] = useState('precipizio');
  const [createCaEffettoSottosistemaId, setCreateCaEffettoSottosistemaId] = useState('');
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
      },
      onLogout
    );
    setNuovoSotto({
      codice: '', nome: '', gruppo: '', ordine_gruppo: 0, ordine: 0, tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
      capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
      effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
      effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
      effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
      guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
      ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
      colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
    });
    loadData();
  };

  const addIntensita = async () => {
    await staffCreatePilotIntensita({ ...nuovaIntensita, valore: Number(nuovaIntensita.valore) }, onLogout);
    setNuovaIntensita({ valore: 0, nome: '' });
    loadData();
  };
  const addEvento = async () => {
    const durataSpec = String(nuovoEvento.durata_tick || '').trim();
    if (!isValidDurataTickSpec(durataSpec)) {
      setError('Durata evento non valida. Usa: N, A-B, -N oppure -');
      return;
    }
    let regoleObj;
    try {
      regoleObj = JSON.parse(nuovoEvento.regole_json || '{}');
    } catch {
      setError('JSON regole non valido.');
      return;
    }
    const merged = mergeCaAndRulesIntoRegole(regoleObj, ruleBuilder, createCaEffettoTipo, createCaEffettoSottosistemaId);
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
      },
      onLogout
    );
    setNuovoEvento(defaultEvento);
    setCreateCaEffettoTipo('precipizio');
    setCreateCaEffettoSottosistemaId('');
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
      },
      onLogout
    );
    setEditSottoId(null);
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
      st: { conditions: [], expression: DEFAULT_RULE_EXPR },
      sp: { conditions: [], expression: DEFAULT_RULE_EXPR },
      ca: { conditions: [], expression: DEFAULT_RULE_EXPR },
    });
    setEditCaEffettoTipo('precipizio');
    setEditCaEffettoSottosistemaId('');
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
        const cae = rj.ca_effetto && typeof rj.ca_effetto === 'object' ? rj.ca_effetto : {};
        if (cae.tipo === 'guasto_sottosistema') {
          setEditCaEffettoTipo('guasto_sottosistema');
          setEditCaEffettoSottosistemaId(String(cae.sottosistema_id || '').trim());
        } else {
          setEditCaEffettoTipo('precipizio');
          setEditCaEffettoSottosistemaId('');
        }
        setEditEvento({
          nome: e.nome || '',
          descrizione: e.descrizione ?? '',
          codice_soluzione_esatta: e.codice_soluzione_esatta || '___',
          codici_soluzione_parziale_json: JSON.stringify(e.codici_soluzione_parziale || [], null, 2),
          codici_precipizio_json: JSON.stringify(e.codici_precipizio || [], null, 2),
          regole_json: JSON.stringify(rj && Object.keys(rj).length ? rj : { version: 3 }, null, 2),
          durata_base_secondi: e.durata_base_secondi ?? 20,
          durata_tick: e.durata_tick || '4',
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
    const durataSpec = String(editEvento.durata_tick || '').trim();
    if (!isValidDurataTickSpec(durataSpec)) {
      setError('Durata evento non valida. Usa: N, A-B, -N oppure -');
      return;
    }
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
      editCaEffettoTipo,
      editCaEffettoSottosistemaId
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
      durata_base_secondi: Math.max(1, Number(editEvento.durata_base_secondi) || 20),
      durata_tick: durataSpec,
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
    const merged = mergeCaAndRulesIntoRegole(base, ruleBuilder, createCaEffettoTipo, createCaEffettoSottosistemaId);
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
    const merged = mergeCaAndRulesIntoRegole(base, editRuleBuilder, editCaEffettoTipo, editCaEffettoSottosistemaId);
    if (!merged.ok) {
      setError(merged.error);
      return;
    }
    setError('');
    setEditEvento((p) => ({ ...p, regole_json: JSON.stringify(merged.regole, null, 2) }));
  };

  const salvaRuntimeConfig = async () => {
    if (!runtimeConfig) return;
    const updated = await staffUpdatePilotRuntimeConfig(
      {
        login_required_console: Boolean(runtimeConfig.login_required_console),
        tick_interval_secondi: Number(runtimeConfig.tick_interval_secondi || 5),
        alarm_audio_enabled: Boolean(runtimeConfig.alarm_audio_enabled),
      },
      onLogout
    );
    setRuntimeConfig(updated);
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
        <div className="grid md:grid-cols-3 gap-3 mb-3">
          <label className="block">
            <span className="text-xs text-gray-400">Codice (1 carattere)</span>
            <input className="bg-gray-800 rounded px-2 py-1 w-16 shrink-0 mt-1" maxLength={1} value={nuovoSotto.codice} onChange={(e) => setNuovoSotto((p) => ({ ...p, codice: e.target.value }))} placeholder="A" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Nome sottosistema</span>
            <input className="bg-gray-800 rounded px-2 py-1 flex-1 min-w-0 mt-1 w-full" value={nuovoSotto.nome} onChange={(e) => setNuovoSotto((p) => ({ ...p, nome: e.target.value }))} placeholder="Reattore principale" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Gruppo sistema</span>
            <input className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.gruppo} onChange={(e) => setNuovoSotto((p) => ({ ...p, gruppo: e.target.value }))} placeholder="Alimentazione / Difesa / ..." />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Ordine colonna (gruppo)</span>
            <input type="number" min={0} step={1} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.ordine_gruppo ?? 0} onChange={(e) => setNuovoSotto((p) => ({ ...p, ordine_gruppo: e.target.value }))} />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Ordine nel gruppo</span>
            <input type="number" min={0} step={1} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.ordine ?? 0} onChange={(e) => setNuovoSotto((p) => ({ ...p, ordine: e.target.value }))} />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Tipo sottosistema</span>
            <select className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.tipo} onChange={(e) => setNuovoSotto((p) => ({ ...p, tipo: e.target.value }))}>
              <option value="standard">standard</option><option value="generatore">generatore</option><option value="batteria">batteria</option><option value="serbatoio">serbatoio</option><option value="motore">motore</option><option value="portale">portale</option><option value="manovra">manovra</option>
            </select>
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Produzione energia per livello</span>
            <input type="number" step="0.1" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.coeff_produzione} onChange={(e) => setNuovoSotto((p) => ({ ...p, coeff_produzione: e.target.value }))} placeholder="Es. 2.5" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Consumo energia per livello</span>
            <input type="number" step="0.1" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.coeff_consumo_energia} onChange={(e) => setNuovoSotto((p) => ({ ...p, coeff_consumo_energia: e.target.value }))} placeholder="Es. 1.0" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Consumo carburante per livello</span>
            <input type="number" step="0.1" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.coeff_consumo_carburante} onChange={(e) => setNuovoSotto((p) => ({ ...p, coeff_consumo_carburante: e.target.value }))} placeholder="Es. 0.8" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Coefficiente effetto speciale</span>
            <input type="number" step="0.01" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.coeff_effetto_speciale || 1} onChange={(e) => setNuovoSotto((p) => ({ ...p, coeff_effetto_speciale: e.target.value }))} placeholder="Portale: 0.15" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Rampa livelli per tick</span>
            <input type="number" min={1} max={9} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.rampa_livelli_per_tick || 1} onChange={(e) => setNuovoSotto((p) => ({ ...p, rampa_livelli_per_tick: e.target.value }))} placeholder="Es. 1" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Capacita batterie (storage)</span>
            <input type="number" step="0.1" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.capacita_storage ?? 0} onChange={(e) => setNuovoSotto((p) => ({ ...p, capacita_storage: e.target.value }))} placeholder="Solo tipo batteria" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Coeff. ricarica batterie</span>
            <input type="number" step="0.01" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.coeff_ricarica_storage ?? 0.5} onChange={(e) => setNuovoSotto((p) => ({ ...p, coeff_ricarica_storage: e.target.value }))} placeholder="Solo tipo batteria" />
          </label>
          <label className="block">
            <span className="text-xs text-gray-400">Capacita serbatoio carburante</span>
            <input type="number" step="0.1" className="bg-gray-800 rounded px-2 py-1 mt-1 w-full" value={nuovoSotto.capacita_carburante ?? 0} onChange={(e) => setNuovoSotto((p) => ({ ...p, capacita_carburante: e.target.value }))} placeholder="Solo tipo serbatoio" />
          </label>
          <label className="block md:col-span-3">
            <span className="text-xs text-gray-400">Effetto su guasto sottosistema (JSON)</span>
            <textarea rows={5} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.effetti_guasto_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, effetti_guasto_json: e.target.value }))} />
          </label>
          <div className="md:col-span-3 border border-gray-700 rounded p-2 bg-gray-900/60">
            <div className="text-xs text-gray-300 mb-2">Generatore rapido JSON effetto guasto</div>
            <div className="grid md:grid-cols-4 gap-2">
              <select className="bg-gray-800 rounded px-2 py-1" value={nuovoEffettoGuastoBuilder.tipo} onChange={(e) => setNuovoEffettoGuastoBuilder((p) => ({ ...p, tipo: e.target.value }))}>
                <option value="none">none</option>
                <option value="guasto_altro_percent">guasto_altro_percent</option>
                <option value="guasto_random_percent">guasto_random_percent</option>
                <option value="riduci_carburante_percent">riduci_carburante_percent</option>
                <option value="riduci_batterie_percent">riduci_batterie_percent</option>
                <option value="allunga_distanza_percent">allunga_distanza_percent</option>
                <option value="naufragio">naufragio</option>
              </select>
              <input type="number" step="0.1" min={0} max={100} disabled={['none', 'naufragio'].includes(nuovoEffettoGuastoBuilder.tipo)} className="bg-gray-800 rounded px-2 py-1 disabled:opacity-40" placeholder="valore %" value={nuovoEffettoGuastoBuilder.valore} onChange={(e) => setNuovoEffettoGuastoBuilder((p) => ({ ...p, valore: e.target.value }))} />
              <input className="bg-gray-800 rounded px-2 py-1 disabled:opacity-40" maxLength={1} disabled={nuovoEffettoGuastoBuilder.tipo !== 'guasto_altro_percent'} placeholder="target codice" value={nuovoEffettoGuastoBuilder.target_codice} onChange={(e) => setNuovoEffettoGuastoBuilder((p) => ({ ...p, target_codice: e.target.value.toUpperCase() }))} />
              <button type="button" disabled={!nuovoEffettoValidation.valid} className="px-3 py-1 rounded bg-indigo-700 disabled:opacity-40" onClick={() => setNuovoSotto((p) => ({ ...p, effetti_guasto_json: generaEffettoGuastoJson(nuovoEffettoGuastoBuilder) }))}>Genera JSON</button>
            </div>
            <div className={`text-xs mt-2 ${nuovoEffettoValidation.valid ? 'text-emerald-300' : 'text-amber-300'}`}>{nuovoEffettoValidation.message}</div>
          </div>
          <label className="block md:col-span-3">
            <span className="text-xs text-gray-400">Effetto su attivazione INVERTI (JSON con probabilita_percent)</span>
            <textarea rows={4} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.effetti_inversione_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, effetti_inversione_json: e.target.value }))} />
          </label>
          <label className="block md:col-span-3">
            <span className="text-xs text-gray-400">Effetto su attivazione ESPULSIONE (JSON con probabilita_percent)</span>
            <textarea rows={4} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.effetti_espulsione_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, effetti_espulsione_json: e.target.value }))} />
          </label>
          <label className="block md:col-span-1">
            <span className="text-xs text-gray-400">Guasto % per livello (JSON 0..9)</span>
            <textarea rows={6} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.guasto_percent_per_livello_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, guasto_percent_per_livello_json: e.target.value }))} />
          </label>
          <label className="block md:col-span-1">
            <span className="text-xs text-gray-400">Ripristino % per livello (JSON 0..9)</span>
            <textarea rows={6} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.ripristino_percent_per_livello_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, ripristino_percent_per_livello_json: e.target.value }))} />
          </label>
          <label className="block md:col-span-1">
            <span className="text-xs text-gray-400">Colori per livello (HEX JSON 0..9)</span>
            <textarea rows={6} className="bg-gray-800 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={nuovoSotto.colori_per_livello_json} onChange={(e) => setNuovoSotto((p) => ({ ...p, colori_per_livello_json: e.target.value }))} />
          </label>
          <div className="md:col-span-3">
            <button className="px-3 py-1 rounded bg-indigo-600 shrink-0" onClick={addSottosistema}>Aggiungi sottosistema</button>
          </div>
        </div>
        <div className="space-y-1 text-sm">
          {sottosistemi.map((s) => (
            <div key={s.id} className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 bg-gray-800/60 rounded px-2 py-2">
              {editSottoId === s.id ? (
                <div className="grid md:grid-cols-3 gap-2 w-full items-end">
                  <label className="block">
                    <span className="text-xs text-gray-400">Codice</span>
                    <input className="bg-gray-700 rounded px-2 py-1 w-16 shrink-0 mt-1" maxLength={1} value={editSotto.codice} onChange={(e) => setEditSotto((p) => ({ ...p, codice: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Nome</span>
                    <input className="bg-gray-700 rounded px-2 py-1 flex-1 min-w-40 mt-1 w-full" value={editSotto.nome} onChange={(e) => setEditSotto((p) => ({ ...p, nome: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Gruppo</span>
                    <input className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.gruppo || ''} onChange={(e) => setEditSotto((p) => ({ ...p, gruppo: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Ordine colonna (gruppo)</span>
                    <input type="number" min={0} step={1} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.ordine_gruppo ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, ordine_gruppo: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Ordine nel gruppo</span>
                    <input type="number" min={0} step={1} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.ordine ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, ordine: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Tipo</span>
                    <select className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.tipo || 'standard'} onChange={(e) => setEditSotto((p) => ({ ...p, tipo: e.target.value }))}>
                      <option value="standard">standard</option><option value="generatore">generatore</option><option value="batteria">batteria</option><option value="serbatoio">serbatoio</option><option value="motore">motore</option><option value="portale">portale</option><option value="manovra">manovra</option>
                    </select>
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Prod. energia/livello</span>
                    <input type="number" step="0.1" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.coeff_produzione ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, coeff_produzione: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Cons. energia/livello</span>
                    <input type="number" step="0.1" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.coeff_consumo_energia ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, coeff_consumo_energia: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Cons. carburante/livello</span>
                    <input type="number" step="0.1" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.coeff_consumo_carburante ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, coeff_consumo_carburante: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Coeff. speciale</span>
                    <input type="number" step="0.01" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.coeff_effetto_speciale ?? 1} onChange={(e) => setEditSotto((p) => ({ ...p, coeff_effetto_speciale: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Rampa livelli/tick</span>
                    <input type="number" min={1} max={9} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.rampa_livelli_per_tick ?? 1} onChange={(e) => setEditSotto((p) => ({ ...p, rampa_livelli_per_tick: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Capacita batterie (storage)</span>
                    <input type="number" step="0.1" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.capacita_storage ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, capacita_storage: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Coeff. ricarica batterie</span>
                    <input type="number" step="0.01" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.coeff_ricarica_storage ?? 0.5} onChange={(e) => setEditSotto((p) => ({ ...p, coeff_ricarica_storage: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Capacita serbatoio carburante</span>
                    <input type="number" step="0.1" className="bg-gray-700 rounded px-2 py-1 mt-1 w-full" value={editSotto.capacita_carburante ?? 0} onChange={(e) => setEditSotto((p) => ({ ...p, capacita_carburante: e.target.value }))} />
                  </label>
                  <label className="block md:col-span-3">
                    <span className="text-xs text-gray-400">Effetto su guasto sottosistema (JSON)</span>
                    <textarea rows={5} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.effetti_guasto_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, effetti_guasto_json: e.target.value }))} />
                  </label>
                  <div className="md:col-span-3 border border-gray-600 rounded p-2 bg-gray-800/50">
                    <div className="text-xs text-gray-300 mb-2">Generatore rapido JSON effetto guasto</div>
                    <div className="grid md:grid-cols-4 gap-2">
                      <select className="bg-gray-700 rounded px-2 py-1" value={editEffettoGuastoBuilder.tipo} onChange={(e) => setEditEffettoGuastoBuilder((p) => ({ ...p, tipo: e.target.value }))}>
                        <option value="none">none</option>
                        <option value="guasto_altro_percent">guasto_altro_percent</option>
                        <option value="guasto_random_percent">guasto_random_percent</option>
                        <option value="riduci_carburante_percent">riduci_carburante_percent</option>
                        <option value="riduci_batterie_percent">riduci_batterie_percent</option>
                        <option value="allunga_distanza_percent">allunga_distanza_percent</option>
                        <option value="naufragio">naufragio</option>
                      </select>
                      <input type="number" step="0.1" min={0} max={100} disabled={['none', 'naufragio'].includes(editEffettoGuastoBuilder.tipo)} className="bg-gray-700 rounded px-2 py-1 disabled:opacity-40" placeholder="valore %" value={editEffettoGuastoBuilder.valore} onChange={(e) => setEditEffettoGuastoBuilder((p) => ({ ...p, valore: e.target.value }))} />
                      <input className="bg-gray-700 rounded px-2 py-1 disabled:opacity-40" maxLength={1} disabled={editEffettoGuastoBuilder.tipo !== 'guasto_altro_percent'} placeholder="target codice" value={editEffettoGuastoBuilder.target_codice} onChange={(e) => setEditEffettoGuastoBuilder((p) => ({ ...p, target_codice: e.target.value.toUpperCase() }))} />
                      <button type="button" disabled={!editEffettoValidation.valid} className="px-3 py-1 rounded bg-indigo-700 disabled:opacity-40" onClick={() => setEditSotto((p) => ({ ...p, effetti_guasto_json: generaEffettoGuastoJson(editEffettoGuastoBuilder) }))}>Genera JSON</button>
                    </div>
                    <div className={`text-xs mt-2 ${editEffettoValidation.valid ? 'text-emerald-300' : 'text-amber-300'}`}>{editEffettoValidation.message}</div>
                  </div>
                  <label className="block md:col-span-3">
                    <span className="text-xs text-gray-400">Effetto su attivazione INVERTI (JSON con probabilita_percent)</span>
                    <textarea rows={4} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.effetti_inversione_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, effetti_inversione_json: e.target.value }))} />
                  </label>
                  <label className="block md:col-span-3">
                    <span className="text-xs text-gray-400">Effetto su attivazione ESPULSIONE (JSON con probabilita_percent)</span>
                    <textarea rows={4} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.effetti_espulsione_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, effetti_espulsione_json: e.target.value }))} />
                  </label>
                  <label className="block md:col-span-1">
                    <span className="text-xs text-gray-400">Guasto % per livello (JSON 0..9)</span>
                    <textarea rows={6} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.guasto_percent_per_livello_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, guasto_percent_per_livello_json: e.target.value }))} />
                  </label>
                  <label className="block md:col-span-1">
                    <span className="text-xs text-gray-400">Ripristino % per livello (JSON 0..9)</span>
                    <textarea rows={6} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.ripristino_percent_per_livello_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, ripristino_percent_per_livello_json: e.target.value }))} />
                  </label>
                  <label className="block md:col-span-1">
                    <span className="text-xs text-gray-400">Colori per livello (HEX JSON 0..9)</span>
                    <textarea rows={6} className="bg-gray-700 rounded px-2 py-1 mt-1 w-full font-mono text-xs" value={editSotto.colori_per_livello_json || ''} onChange={(e) => setEditSotto((p) => ({ ...p, colori_per_livello_json: e.target.value }))} />
                  </label>
                  <button className="text-emerald-400 shrink-0" type="button" onClick={salvaSottosistema}>Salva</button>
                  <button className="text-gray-300 shrink-0" type="button" onClick={() => setEditSottoId(null)}>Annulla</button>
                </div>
              ) : (
                <>
                  <span className="wrap-break-word">
                    <strong>{s.codice}</strong> — {s.nome} ({s.gruppo || 'Senza gruppo'} / {s.tipo || 'standard'} · col.{s.ordine_gruppo ?? 0} · #{s.ordine ?? 0})
                    {s.stato_qr === 'pronto'
                      ? ' · QR collegato'
                      : s.stato_qr === 'incompleto'
                        ? ' · vista OK, manca ancora lo scan del cartellino'
                        : ' · nessun QR'}
                  </span>
                  <div className="flex flex-wrap gap-2 shrink-0">
                    <button
                      type="button"
                      className="px-2 py-1 rounded bg-gray-700 text-sm text-white"
                      onClick={() => setScanningForSottosistemaId(s.id)}
                    >
                      Scansiona QR
                    </button>
                    <button
                      type="button"
                      className="text-indigo-300 text-sm"
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
                          });
                          setEditEffettoGuastoBuilder({
                            tipo: String((full.effetti_guasto_json || {}).tipo || 'none'),
                            valore: Number((full.effetti_guasto_json || {}).valore || 0),
                            target_codice: String((full.effetti_guasto_json || {}).target_codice || ''),
                          });
                        } catch (err) {
                          setError(err?.message || 'Impossibile caricare il sottosistema.');
                        }
                      }}
                    >
                      Modifica parametri
                    </button>
                    <button type="button" className="text-red-400 text-sm" onClick={() => staffDeletePilotSottosistema(s.id, onLogout).then(loadData)}>Elimina</button>
                  </div>
                </>
              )}
            </div>
          ))}
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
        <h3 className="font-semibold mb-3">Eventi viaggio (randomici)</h3>
        <div className="grid md:grid-cols-7 gap-2 mb-3 border border-gray-700 rounded p-2">
          <select className="bg-gray-800 rounded px-2 py-1" value={draftCondition.outcome} onChange={(e) => setDraftCondition((p) => ({ ...p, outcome: e.target.value }))}>
            <option value="st">ST (migliora)</option>
            <option value="sp">SP (stabile)</option>
            <option value="ca">CA (precipita)</option>
          </select>
          <select className="bg-gray-800 rounded px-2 py-1" value={draftCondition.subsystem} onChange={(e) => setDraftCondition((p) => ({ ...p, subsystem: e.target.value }))}>
            <option value="">Sottosistema...</option>
            {sottosistemi.map((s) => <option key={s.id} value={s.codice}>{s.nome} ({s.codice})</option>)}
          </select>
          <select className="bg-gray-800 rounded px-2 py-1" value={draftCondition.op} onChange={(e) => setDraftCondition((p) => ({ ...p, op: e.target.value }))}>
            {conditionOps.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
          </select>
          {draftCondition.op === 'between' ? (
            <>
              <input type="number" min={0} max={9} className="bg-gray-800 rounded px-2 py-1" value={draftCondition.min} onChange={(e) => setDraftCondition((p) => ({ ...p, min: e.target.value }))} placeholder="min" />
              <input type="number" min={0} max={9} className="bg-gray-800 rounded px-2 py-1" value={draftCondition.max} onChange={(e) => setDraftCondition((p) => ({ ...p, max: e.target.value }))} placeholder="max" />
            </>
          ) : draftCondition.op === 'direction' ? (
            <select className="bg-gray-800 rounded px-2 py-1" value={draftCondition.direction_rule} onChange={(e) => setDraftCondition((p) => ({ ...p, direction_rule: e.target.value }))}>
              <option value="stessa_direzione">stessa_direzione</option>
              <option value="direzione_opposta">direzione_opposta</option>
              <option value="non_stessa_direzione">non_stessa_direzione</option>
              <option value="non_direzione_opposta">non_direzione_opposta</option>
            </select>
          ) : (
            (['piene', 'vuote', 'non_piene', 'non_vuote', 'distrutte', 'invertito', 'non_invertito', 'espulso', 'non_espulso'].includes(draftCondition.op)
              ? <div className="bg-gray-800 rounded px-2 py-1 text-xs text-gray-300">Condizione booleana</div>
              : <input type="number" min={0} max={9} className="bg-gray-800 rounded px-2 py-1" value={draftCondition.value} onChange={(e) => setDraftCondition((p) => ({ ...p, value: e.target.value }))} placeholder="val" />)
          )}
          <button className="px-3 py-1 rounded bg-indigo-700" onClick={addRuleCondition}>Aggiungi</button>
          <button className="px-3 py-1 rounded bg-sky-700" onClick={generaJsonGuidaEvento}>Genera JSON ST/SP/CA</button>
        </div>
        <div className="grid md:grid-cols-3 gap-2 mb-3">
          {['st', 'sp', 'ca'].map((k) => (
            <div key={k} className="border border-gray-700 rounded p-2">
              <div className="flex justify-between items-center mb-2">
                <strong>{k.toUpperCase()}</strong>
                <span className="text-[11px] text-gray-400">Usa formula con parentesi</span>
              </div>
              <input
                className="bg-gray-800 rounded px-2 py-1 text-xs w-full mb-2 font-mono"
                placeholder="(1 AND 2) OR 3"
                value={ruleBuilder[k].expression || ''}
                onChange={(e) => setRuleBuilder((p) => ({ ...p, [k]: { ...p[k], expression: e.target.value } }))}
              />
              <div className={`text-[11px] mb-2 ${ruleValidation[k].valid ? 'text-emerald-300' : 'text-amber-300'}`}>
                {ruleValidation[k].valid ? 'OK' : 'Errore'}: {ruleValidation[k].message}
              </div>
              <div className="space-y-1 text-xs">
                {(ruleBuilder[k].conditions || []).map((c, idx) => (
                  <div key={`${k}-${idx}`} className="bg-gray-800 rounded px-2 py-1 flex justify-between gap-2">
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
                    <button className="text-red-400" onClick={() => removeRuleCondition(k, idx)}>x</button>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
        <div className="grid md:grid-cols-2 gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1" placeholder="Nome evento" value={nuovoEvento.nome} onChange={(e) => setNuovoEvento((p) => ({ ...p, nome: e.target.value }))} />
          <input
            className={`bg-gray-800 rounded px-2 py-1 font-mono ${isValidDurataTickSpec(nuovoEvento.durata_tick) ? '' : 'border border-red-600'}`}
            placeholder='Durata tick: N | A-B | -N | -'
            value={nuovoEvento.durata_tick}
            onChange={(e) => {
              const next = e.target.value.replace(/[^0-9-]/g, '');
              setNuovoEvento((p) => ({ ...p, durata_tick: next }));
            }}
          />
          <input className="bg-gray-800 rounded px-2 py-1 md:col-span-2" placeholder="Descrizione" value={nuovoEvento.descrizione} onChange={(e) => setNuovoEvento((p) => ({ ...p, descrizione: e.target.value }))} />
          <p className="text-xs text-gray-400 md:col-span-2">
            Durata evento: <code>N</code>=esatto, <code>A-B</code>=random tra estremi, <code>-N</code>=persiste ma se non arriva ST entro N tick la nave precipita, <code>-</code>=persiste finche non arriva ST.
          </p>
          <div className="md:col-span-2 rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 space-y-2">
            <div className="text-xs font-semibold text-amber-200/90">Effetto esito CA (quando scatta la ramo CA)</div>
            <p className="text-[11px] text-gray-400 leading-relaxed">
              Di default il CA precipita la nave. Puoi invece applicare un guasto mirato a un sottosistema (il motore di gioco usa <code className="text-gray-300">ca_effetto</code> nel JSON regole).
            </p>
            <div className="flex flex-wrap gap-3 items-end">
              <label className="block min-w-[10rem]">
                <span className="text-xs text-gray-400">Tipo effetto CA</span>
                <select
                  className="bg-gray-800 rounded px-2 py-1 mt-1 w-full"
                  value={createCaEffettoTipo}
                  onChange={(e) => setCreateCaEffettoTipo(e.target.value)}
                >
                  <option value="precipizio">Precipizio nave</option>
                  <option value="guasto_sottosistema">Guasto sottosistema</option>
                </select>
              </label>
              {createCaEffettoTipo === 'guasto_sottosistema' ? (
                <label className="block flex-1 min-w-[12rem]">
                  <span className="text-xs text-gray-400">Sottosistema in guasto</span>
                  <select
                    className="bg-gray-800 rounded px-2 py-1 mt-1 w-full"
                    value={createCaEffettoSottosistemaId}
                    onChange={(e) => setCreateCaEffettoSottosistemaId(e.target.value)}
                  >
                    <option value="">Seleziona…</option>
                    {sottosistemi.map((s) => (
                      <option key={s.id} value={s.id}>
                        {s.nome} ({s.codice})
                      </option>
                    ))}
                  </select>
                </label>
              ) : null}
            </div>
          </div>
          <textarea className="bg-gray-800 rounded px-2 py-1 md:col-span-2 min-h-32 font-mono text-xs" placeholder="JSON regole avanzate (modificabile)" value={nuovoEvento.regole_json} onChange={(e) => setNuovoEvento((p) => ({ ...p, regole_json: e.target.value }))} />
          <button className="px-3 py-1 rounded bg-indigo-600 md:col-span-2" onClick={addEvento}>Aggiungi evento</button>
        </div>
        <div className="space-y-2 mt-2">
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
                    tick <span className="font-mono text-gray-300">{e.durata_tick || '4'}</span>
                  </span>
                  <span>peso {e.peso_random ?? 10}</span>
                  <span>{e.attivo !== false ? 'attivo' : 'disattivato'}</span>
                  {e.sottosistema_codice ? (
                    <span className="font-mono text-indigo-300/90">{e.sottosistema_codice}</span>
                  ) : null}
                  <span className="font-mono text-amber-200/90" title="Codice risoluzione ST">
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
          Livelli allineati al DEFCON della sessione. Imposta intervallo tra un evento e l&apos;altro (secondi) e il countdown per risolvere un evento mentre sei in quel livello.
          Segna un solo livello come <strong className="text-gray-300">nave abbattuta</strong> (crash / DEFCON oltre il massimo).
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
                  <label className="block sm:col-span-2 lg:col-span-1">
                    <span className="text-xs text-gray-400">Freq. eventi min–max (s)</span>
                    <div className="flex gap-2 mt-0.5">
                      <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_min_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_min_sec: e.target.value }))} />
                      <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full" value={editStato.frequenza_evento_max_sec} onChange={(e) => setEditStato((p) => ({ ...p, frequenza_evento_max_sec: e.target.value }))} />
                    </div>
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Tempo risoluzione evento (s)</span>
                    <input type="number" min={3} className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.tempo_risoluzione_secondi} onChange={(e) => setEditStato((p) => ({ ...p, tempo_risoluzione_secondi: e.target.value }))} />
                  </label>
                  <label className="block">
                    <span className="text-xs text-gray-400">Prob. evento per tick (0..1)</span>
                    <input type="number" min={0} max={1} step={0.01} className="bg-gray-700 rounded px-2 py-1 w-full mt-0.5" value={editStato.probabilita_evento_per_tick ?? 0} onChange={(e) => setEditStato((p) => ({ ...p, probabilita_evento_per_tick: e.target.value }))} />
                  </label>
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
                        Eventi ogni {st.frequenza_evento_min_sec}–{st.frequenza_evento_max_sec}s · Risoluzione {st.tempo_risoluzione_secondi}s · Prob/tick {st.probabilita_evento_per_tick}
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

      {activeTab === 'runtime' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-2">Runtime Console Pilotaggio</h3>
        <p className="text-xs text-gray-400 mb-4">
          Login console opzionale: tienilo disattivo in dev/test; abilitalo in produzione mirror Pi.
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
            <button className="px-3 py-1 rounded bg-indigo-600" onClick={salvaRuntimeConfig}>Salva runtime</button>
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
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Durata tick</span>
                  <input
                    className={`mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border font-mono text-sm ${
                      isValidDurataTickSpec(editEvento.durata_tick) ? 'border-gray-600' : 'border-red-500'
                    } focus:border-indigo-500 outline-none`}
                    value={editEvento.durata_tick ?? '4'}
                    onChange={(ev) => {
                      const next = ev.target.value.replace(/[^0-9-]/g, '');
                      setEditEvento((p) => ({ ...p, durata_tick: next }));
                    }}
                    placeholder="N | A-B | -N | -"
                  />
                  <p className="text-[11px] text-gray-500 mt-1">
                    <code>N</code>, <code>A-B</code>, <code>-N</code>, <code>-</code>
                  </p>
                </label>
                <label className="block">
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Countdown base (secondi)</span>
                  <input
                    type="number"
                    min={1}
                    className="mt-1 w-full bg-gray-900 rounded-lg px-3 py-2 border border-gray-600 focus:border-indigo-500 outline-none"
                    value={editEvento.durata_base_secondi}
                    onChange={(ev) => setEditEvento((p) => ({ ...p, durata_base_secondi: ev.target.value }))}
                  />
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
                  <span className="text-xs font-semibold text-gray-400 uppercase tracking-wide">Codice ST (3 car.)</span>
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
                  Le condizioni e le formule qui sotto aggiornano il campo JSON «Regole avanzate» (anche <code className="text-gray-400">ca_effetto</code>) al salvataggio; usa «Aggiorna JSON da builder» per vedere l&apos;anteprima nel textarea.
                </p>
                <div className="grid md:grid-cols-7 gap-2 border border-gray-700 rounded-lg p-2">
                  <select className="bg-gray-900 rounded px-2 py-1" value={draftCondition.outcome} onChange={(ev) => setDraftCondition((p) => ({ ...p, outcome: ev.target.value }))}>
                    <option value="st">ST (migliora)</option>
                    <option value="sp">SP (stabile)</option>
                    <option value="ca">CA</option>
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

              <div className="rounded-lg border border-amber-900/50 bg-amber-950/20 p-3 space-y-2">
                <div className="text-xs font-semibold text-amber-200/90">Effetto esito CA</div>
                <p className="text-[11px] text-gray-400 leading-relaxed">
                  Di default il CA precipita la nave. In alternativa puoi forzare il guasto di un sottosistema specifico (campo <code className="text-gray-300">ca_effetto</code> nel JSON).
                </p>
                <div className="flex flex-wrap gap-3 items-end">
                  <label className="block min-w-[10rem]">
                    <span className="text-xs text-gray-400">Tipo effetto CA</span>
                    <select
                      className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
                      value={editCaEffettoTipo}
                      onChange={(ev) => setEditCaEffettoTipo(ev.target.value)}
                    >
                      <option value="precipizio">Precipizio nave</option>
                      <option value="guasto_sottosistema">Guasto sottosistema</option>
                    </select>
                  </label>
                  {editCaEffettoTipo === 'guasto_sottosistema' ? (
                    <label className="block flex-1 min-w-[12rem]">
                      <span className="text-xs text-gray-400">Sottosistema in guasto</span>
                      <select
                        className="bg-gray-900 rounded px-2 py-1 mt-1 w-full border border-gray-700"
                        value={editCaEffettoSottosistemaId}
                        onChange={(ev) => setEditCaEffettoSottosistemaId(ev.target.value)}
                      >
                        <option value="">Seleziona…</option>
                        {sottosistemi.map((ss) => (
                          <option key={ss.id} value={ss.id}>
                            {ss.nome} ({ss.codice})
                          </option>
                        ))}
                      </select>
                    </label>
                  ) : null}
                </div>
              </div>

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
    </div>
  );
}
