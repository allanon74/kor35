import React, { useCallback, useEffect, useMemo, useState } from 'react';
import StaffQrTab from '../StaffQrTab';
import {
  staffAssociaPilotSottosistemaQr,
  staffCreatePilotComando,
  staffCreatePilotComandoCritico,
  staffCreatePilotEvento,
  staffCreatePilotIntensita,
  staffCreatePilotSottosistema,
  staffDeletePilotComando,
  staffDeletePilotComandoCritico,
  staffDeletePilotEvento,
  staffDeletePilotIntensita,
  staffDeletePilotSottosistema,
  staffGetPilotComandi,
  staffGetPilotComandiCritici,
  staffGetPilotEventi,
  staffGetPilotIntensita,
  staffGetPilotSottosistemi,
  staffGetPilotStatiAllerta,
  staffGetPilotRuntimeConfig,
  staffUpdatePilotComando,
  staffUpdatePilotComandoCritico,
  staffUpdatePilotEvento,
  staffUpdatePilotIntensita,
  staffUpdatePilotSottosistema,
  staffUpdatePilotStatoAllerta,
  staffUpdatePilotRuntimeConfig,
} from '../../api';

const PILOT_TABS = [
  { id: 'sottosistemi', label: 'Sottosistemi' },
  { id: 'comandi', label: 'Comandi' },
  { id: 'intensita', label: 'Intensità' },
  { id: 'eventi', label: 'Eventi' },
  { id: 'comandi_critici', label: 'Comandi critici (globali)' },
  { id: 'stati_allerta', label: 'Stati allerta (DEFCON)' },
  { id: 'runtime', label: 'Runtime Console' },
  { id: 'combinazioni', label: 'Combinazioni' },
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

export default function PilotaggioManager({ onLogout }) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [sottosistemi, setSottosistemi] = useState([]);
  const [comandi, setComandi] = useState([]);
  const [intensita, setIntensita] = useState([]);
  const [eventi, setEventi] = useState([]);
  const [comandiCritici, setComandiCritici] = useState([]);
  const [nuovoSotto, setNuovoSotto] = useState({
    codice: '', nome: '', gruppo: '', tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
    capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
  });
  const [nuovoComando, setNuovoComando] = useState({ codice: '', nome: '' });
  const [nuovaIntensita, setNuovaIntensita] = useState({ valore: 0, nome: '' });
  const [nuovoEvento, setNuovoEvento] = useState(defaultEvento);
  const [nuovoCritico, setNuovoCritico] = useState({ pattern: '', nome: '', attivo: true });
  const [editSottoId, setEditSottoId] = useState(null);
  const [editSotto, setEditSotto] = useState({
    codice: '', nome: '', gruppo: '', tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
    capacita_storage: 0, coeff_ricarica_storage: 0.5, capacita_carburante: 0,
    effetti_guasto_json: JSON.stringify(defaultEffettiGuasto(), null, 2),
    effetti_inversione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    effetti_espulsione_json: JSON.stringify(defaultEffettiComandoCritico(), null, 2),
    guasto_percent_per_livello_json: JSON.stringify(defaultGuastoCurve(), null, 2),
    ripristino_percent_per_livello_json: JSON.stringify(defaultCurveZero(), null, 2),
    colori_per_livello_json: JSON.stringify(defaultColorCurve(), null, 2),
  });
  const [editComandoId, setEditComandoId] = useState(null);
  const [editComando, setEditComando] = useState({ codice: '', nome: '' });
  const [editIntensitaId, setEditIntensitaId] = useState(null);
  const [editIntensita, setEditIntensita] = useState({ valore: 0, nome: '' });
  const [editEventoId, setEditEventoId] = useState(null);
  const [editEvento, setEditEvento] = useState(defaultEvento);
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
      const [s, c, i, e, crit, stati, runtime] = await Promise.all([
        staffGetPilotSottosistemi(onLogout),
        staffGetPilotComandi(onLogout),
        staffGetPilotIntensita(onLogout),
        staffGetPilotEventi(onLogout),
        staffGetPilotComandiCritici(onLogout).catch(() => []),
        staffGetPilotStatiAllerta(onLogout).catch(() => []),
        staffGetPilotRuntimeConfig(onLogout).catch(() => null),
      ]);
      setSottosistemi(Array.isArray(s) ? s : []);
      setComandi(Array.isArray(c) ? c : []);
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

  const listaCombinata = useMemo(() => {
    const righe = [];
    for (const s of sottosistemi) {
      for (const i of intensita) {
        for (const c of comandi) {
          righe.push({
            codice: `${s.codice}${c.codice}${i.valore}`,
            sottosistema_codice: s.codice,
            sottosistema_nome: s.nome,
            comando_codice: c.codice,
            comando_nome: c.nome,
            intensita: i.valore,
          });
        }
      }
    }
    return righe;
  }, [sottosistemi, comandi, intensita]);

  const listaSottosistemaNumeroComando = useMemo(() => {
    const righe = [];
    for (const s of sottosistemi) {
      for (const i of intensita) {
        righe.push({
          chiave: `${s.codice}${i.valore}`,
          comandi_disponibili: comandi.map((c) => `${c.codice}:${c.nome}`),
        });
      }
    }
    return righe;
  }, [sottosistemi, comandi, intensita]);

  const addSottosistema = async () => {
    await staffCreatePilotSottosistema(
      {
        ...nuovoSotto,
        codice: nuovoSotto.codice.toUpperCase(),
        coeff_produzione: Number(nuovoSotto.coeff_produzione || 0),
        coeff_consumo_energia: Number(nuovoSotto.coeff_consumo_energia || 0),
        coeff_consumo_carburante: Number(nuovoSotto.coeff_consumo_carburante || 0),
        coeff_effetto_speciale: Number(nuovoSotto.coeff_effetto_speciale || 1),
        rampa_livelli_per_tick: Number(nuovoSotto.rampa_livelli_per_tick || 1),
        capacita_storage: Number(nuovoSotto.capacita_storage || 0),
        coeff_ricarica_storage: Number(nuovoSotto.coeff_ricarica_storage || 0),
        capacita_carburante: Number(nuovoSotto.capacita_carburante || 0),
        effetti_guasto_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_guasto_json || '{}'); } catch (_) { return defaultEffettiGuasto(); }
        })(),
        effetti_inversione_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_inversione_json || '{}'); } catch (_) { return defaultEffettiComandoCritico(); }
        })(),
        effetti_espulsione_json: (() => {
          try { return JSON.parse(nuovoSotto.effetti_espulsione_json || '{}'); } catch (_) { return defaultEffettiComandoCritico(); }
        })(),
        guasto_percent_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.guasto_percent_per_livello_json || '{}'); } catch (_) { return defaultGuastoCurve(); }
        })(),
        ripristino_percent_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.ripristino_percent_per_livello_json || '{}'); } catch (_) { return defaultCurveZero(); }
        })(),
        colori_per_livello: (() => {
          try { return JSON.parse(nuovoSotto.colori_per_livello_json || '{}'); } catch (_) { return defaultColorCurve(); }
        })(),
      },
      onLogout
    );
    setNuovoSotto({
      codice: '', nome: '', gruppo: '', tipo: 'standard', coeff_produzione: 0, coeff_consumo_energia: 1, coeff_consumo_carburante: 0, coeff_effetto_speciale: 1, rampa_livelli_per_tick: 1,
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
  const addComando = async () => {
    await staffCreatePilotComando({ ...nuovoComando, codice: nuovoComando.codice.toUpperCase() }, onLogout);
    setNuovoComando({ codice: '', nome: '' });
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
    await staffCreatePilotEvento(
      {
        ...nuovoEvento,
        codice_soluzione_esatta: '___',
        codici_soluzione_parziale: [],
        codici_precipizio: [],
        regole_json: (() => {
          try { return JSON.parse(nuovoEvento.regole_json || '{}'); } catch (_) { return {}; }
        })(),
        sottosistema: nuovoEvento.sottosistema || null,
        durata_tick: durataSpec,
      },
      onLogout
    );
    setNuovoEvento(defaultEvento);
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
        rampa_livelli_per_tick: Number(editSotto.rampa_livelli_per_tick || 1),
        capacita_storage: Number(editSotto.capacita_storage || 0),
        coeff_ricarica_storage: Number(editSotto.coeff_ricarica_storage || 0),
        capacita_carburante: Number(editSotto.capacita_carburante || 0),
        effetti_guasto_json: (() => {
          try { return JSON.parse(editSotto.effetti_guasto_json || '{}'); } catch (_) { return defaultEffettiGuasto(); }
        })(),
        effetti_inversione_json: (() => {
          try { return JSON.parse(editSotto.effetti_inversione_json || '{}'); } catch (_) { return defaultEffettiComandoCritico(); }
        })(),
        effetti_espulsione_json: (() => {
          try { return JSON.parse(editSotto.effetti_espulsione_json || '{}'); } catch (_) { return defaultEffettiComandoCritico(); }
        })(),
        guasto_percent_per_livello: (() => {
          try { return JSON.parse(editSotto.guasto_percent_per_livello_json || '{}'); } catch (_) { return defaultGuastoCurve(); }
        })(),
        ripristino_percent_per_livello: (() => {
          try { return JSON.parse(editSotto.ripristino_percent_per_livello_json || '{}'); } catch (_) { return defaultCurveZero(); }
        })(),
        colori_per_livello: (() => {
          try { return JSON.parse(editSotto.colori_per_livello_json || '{}'); } catch (_) { return defaultColorCurve(); }
        })(),
      },
      onLogout
    );
    setEditSottoId(null);
    loadData();
  };
  const salvaComando = async () => {
    await staffUpdatePilotComando(editComandoId, { codice: editComando.codice.toUpperCase(), nome: editComando.nome }, onLogout);
    setEditComandoId(null);
    loadData();
  };
  const salvaIntensita = async () => {
    await staffUpdatePilotIntensita(editIntensitaId, { valore: Number(editIntensita.valore), nome: editIntensita.nome }, onLogout);
    setEditIntensitaId(null);
    loadData();
  };
  const salvaEvento = async () => {
    const durataSpec = String(editEvento.durata_tick || '').trim();
    if (!isValidDurataTickSpec(durataSpec)) {
      setError('Durata evento non valida. Usa: N, A-B, -N oppure -');
      return;
    }
    await staffUpdatePilotEvento(
      editEventoId,
      {
        ...editEvento,
        codice_soluzione_esatta: editEvento.codice_soluzione_esatta || '___',
        codici_soluzione_parziale: [],
        codici_precipizio: [],
        regole_json: (() => {
          try { return JSON.parse(editEvento.regole_json || '{}'); } catch (_) { return {}; }
        })(),
        sottosistema: editEvento.sottosistema || null,
        durata_tick: durataSpec,
      },
      onLogout
    );
    setEditEventoId(null);
    loadData();
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

  const addRuleCondition = () => {
    if (!draftCondition.subsystem) return;
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
    } else if (['piene', 'vuote', 'non_piene', 'non_vuote', 'distrutte', 'invertito', 'non_invertito', 'espulso', 'non_espulso'].includes(draftCondition.op)) {
      // Nessun parametro aggiuntivo per condizioni booleane su batteria/serbatoio.
    } else {
      cond.value = Number(draftCondition.value);
    }
    setRuleBuilder((prev) => ({
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

  const generaJsonGuidaEvento = () => {
    const usesDirectional = ['st', 'sp', 'ca'].some((k) => (ruleBuilder[k]?.conditions || []).some((c) => c.op === 'direction'));
    const stExpr = buildExpressionAst(ruleBuilder.st.expression, ruleBuilder.st.conditions);
    const spExpr = buildExpressionAst(ruleBuilder.sp.expression, ruleBuilder.sp.conditions);
    const caExpr = buildExpressionAst(ruleBuilder.ca.expression, ruleBuilder.ca.conditions);
    if (!stExpr || !spExpr || !caExpr) {
      setError('Espressione non valida: usa indici condizione con AND/OR e parentesi, es. (1 AND 2) OR 3');
      return;
    }
    const rule = {
      version: 3,
      usa_direzione_evento: usesDirectional,
      st: { expression: stExpr },
      sp: { expression: spExpr },
      ca: { expression: caExpr },
    };
    setNuovoEvento((p) => ({ ...p, regole_json: JSON.stringify(rule, null, 2) }));
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
                    <strong>{s.codice}</strong> — {s.nome} ({s.gruppo || 'Senza gruppo'} / {s.tipo || 'standard'})
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
                      onClick={() => {
                        setEditSottoId(s.id);
                        setEditSotto({
                          codice: s.codice || '',
                          nome: s.nome || '',
                          gruppo: s.gruppo || '',
                          tipo: s.tipo || 'standard',
                          coeff_produzione: s.coeff_produzione ?? 0,
                          coeff_consumo_energia: s.coeff_consumo_energia ?? 1,
                          coeff_consumo_carburante: s.coeff_consumo_carburante ?? 0,
                          coeff_effetto_speciale: s.coeff_effetto_speciale ?? 1,
                          rampa_livelli_per_tick: s.rampa_livelli_per_tick ?? 1,
                          capacita_storage: s.capacita_storage ?? 0,
                          coeff_ricarica_storage: s.coeff_ricarica_storage ?? 0.5,
                          capacita_carburante: s.capacita_carburante ?? 0,
                          effetti_guasto_json: JSON.stringify(s.effetti_guasto_json || defaultEffettiGuasto(), null, 2),
                          effetti_inversione_json: JSON.stringify(s.effetti_inversione_json || defaultEffettiComandoCritico(), null, 2),
                          effetti_espulsione_json: JSON.stringify(s.effetti_espulsione_json || defaultEffettiComandoCritico(), null, 2),
                          guasto_percent_per_livello_json: JSON.stringify(s.guasto_percent_per_livello || defaultGuastoCurve(), null, 2),
                          ripristino_percent_per_livello_json: JSON.stringify(s.ripristino_percent_per_livello || defaultCurveZero(), null, 2),
                          colori_per_livello_json: JSON.stringify(s.colori_per_livello || defaultColorCurve(), null, 2),
                        });
                      setEditEffettoGuastoBuilder({
                        tipo: String((s.effetti_guasto_json || {}).tipo || 'none'),
                        valore: Number((s.effetti_guasto_json || {}).valore || 0),
                        target_codice: String((s.effetti_guasto_json || {}).target_codice || ''),
                      });
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

      {activeTab === 'comandi' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Comandi (2° carattere)</h3>
        <div className="flex gap-2 mb-3">
          <input className="bg-gray-800 rounded px-2 py-1 w-16" maxLength={1} value={nuovoComando.codice} onChange={(e) => setNuovoComando((p) => ({ ...p, codice: e.target.value }))} placeholder="B" />
          <input className="bg-gray-800 rounded px-2 py-1 flex-1" value={nuovoComando.nome} onChange={(e) => setNuovoComando((p) => ({ ...p, nome: e.target.value }))} placeholder="Nome comando" />
          <button className="px-3 py-1 rounded bg-indigo-600" onClick={addComando}>Aggiungi</button>
        </div>
        {comandi.map((c) => (
          <div key={c.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editComandoId === c.id ? (
              <div className="flex gap-2 w-full">
                <input className="bg-gray-700 rounded px-2 py-1 w-16" maxLength={1} value={editComando.codice} onChange={(e) => setEditComando((p) => ({ ...p, codice: e.target.value }))} />
                <input className="bg-gray-700 rounded px-2 py-1 flex-1" value={editComando.nome} onChange={(e) => setEditComando((p) => ({ ...p, nome: e.target.value }))} />
                <button className="text-emerald-400" onClick={salvaComando}>Salva</button>
                <button className="text-gray-300" onClick={() => setEditComandoId(null)}>Annulla</button>
              </div>
            ) : (
              <>
                <span>{c.codice} - {c.nome}</span>
                <div className="flex gap-3">
                  <button className="text-indigo-300" onClick={() => { setEditComandoId(c.id); setEditComando({ codice: c.codice || '', nome: c.nome || '' }); }}>Modifica</button>
                  <button className="text-red-400" onClick={() => staffDeletePilotComando(c.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
      </section>
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
                  <button className="text-indigo-300" onClick={() => { setEditIntensitaId(i.id); setEditIntensita({ valore: i.valore ?? 0, nome: i.nome || '' }); }}>Modifica</button>
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
                    <span>{idx + 1}) {c.sottosistema} {c.op} {c.value ?? `${c.min}-${c.max}` ?? c.direction_rule}</span>
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
          <textarea className="bg-gray-800 rounded px-2 py-1 md:col-span-2 min-h-32 font-mono text-xs" placeholder="JSON regole avanzate (modificabile)" value={nuovoEvento.regole_json} onChange={(e) => setNuovoEvento((p) => ({ ...p, regole_json: e.target.value }))} />
          <button className="px-3 py-1 rounded bg-indigo-600 md:col-span-2" onClick={addEvento}>Aggiungi evento</button>
        </div>
        {eventi.map((e) => (
          <div key={e.id} className="flex items-center justify-between bg-gray-800/60 rounded px-2 py-1 text-sm mb-1">
            {editEventoId === e.id ? (
              <div className="grid md:grid-cols-2 gap-2 w-full">
                <input className="bg-gray-700 rounded px-2 py-1" value={editEvento.nome} onChange={(ev) => setEditEvento((p) => ({ ...p, nome: ev.target.value }))} />
                <input
                  className={`bg-gray-700 rounded px-2 py-1 font-mono ${isValidDurataTickSpec(editEvento.durata_tick) ? '' : 'border border-red-600'}`}
                  value={editEvento.durata_tick ?? '4'}
                  onChange={(ev) => {
                    const next = ev.target.value.replace(/[^0-9-]/g, '');
                    setEditEvento((p) => ({ ...p, durata_tick: next }));
                  }}
                  placeholder='Durata tick: N | A-B | -N | -'
                />
                <input className="bg-gray-700 rounded px-2 py-1 md:col-span-2" value={editEvento.descrizione} onChange={(ev) => setEditEvento((p) => ({ ...p, descrizione: ev.target.value }))} />
                <p className="text-xs text-gray-400 md:col-span-2">
                  Formati validi: <code>N</code>, <code>A-B</code>, <code>-N</code>, <code>-</code>.
                </p>
                <textarea className="bg-gray-700 rounded px-2 py-1 md:col-span-2 min-h-32 font-mono text-xs" value={editEvento.regole_json} onChange={(ev) => setEditEvento((p) => ({ ...p, regole_json: ev.target.value }))} />
                <div className="flex gap-3 md:col-span-2">
                  <button className="text-emerald-400" onClick={salvaEvento}>Salva</button>
                  <button className="text-gray-300" onClick={() => setEditEventoId(null)}>Annulla</button>
                </div>
              </div>
            ) : (
              <>
                <span>{e.nome} <span className="text-xs text-gray-400">[{e.durata_tick || '4'}]</span></span>
                <div className="flex gap-3">
                  <button
                    className="text-indigo-300"
                    onClick={() => {
                      setEditEventoId(e.id);
                      setEditEvento({
                        nome: e.nome || '',
                        descrizione: e.descrizione || '',
                        codice_soluzione_esatta: e.codice_soluzione_esatta || '',
                        regole_json: JSON.stringify(e.regole_json || { alternative: [] }, null, 2),
                        durata_base_secondi: e.durata_base_secondi ?? 20,
                        durata_tick: e.durata_tick || '4',
                        peso_random: e.peso_random ?? 10,
                        sottosistema: e.sottosistema || '',
                        attivo: e.attivo ?? true,
                      });
                    }}
                  >
                    Modifica
                  </button>
                  <button className="text-red-400" onClick={() => staffDeletePilotEvento(e.id, onLogout).then(loadData)}>Elimina</button>
                </div>
              </>
            )}
          </div>
        ))}
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
                      onClick={() => {
                        setEditCriticoId(row.id);
                        setEditCritico({
                          pattern: row.pattern || '',
                          nome: row.nome || '',
                          attivo: row.attivo ?? true,
                        });
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
                    onClick={() => {
                      setEditStatoId(st.id);
                      setEditStato({
                        nome: st.nome || '',
                        colore: st.colore || '#888888',
                        frequenza_evento_min_sec: st.frequenza_evento_min_sec ?? 60,
                        frequenza_evento_max_sec: st.frequenza_evento_max_sec ?? 90,
                        tempo_risoluzione_secondi: st.tempo_risoluzione_secondi ?? 20,
                        probabilita_evento_per_tick: st.probabilita_evento_per_tick ?? 0,
                        equivale_nave_abbattuta: Boolean(st.equivale_nave_abbattuta),
                      });
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

      {activeTab === 'combinazioni' ? (
      <section className="rounded-xl border border-gray-700 p-4 bg-gray-900/60">
        <h3 className="font-semibold mb-3">Lista richiesta: sottosistema = carattere + numero = comando</h3>
        <div className="max-h-48 overflow-y-auto space-y-1 text-xs mb-4">
          {listaSottosistemaNumeroComando.map((r) => (
            <div key={r.chiave} className="bg-gray-800/60 rounded px-2 py-1">
              {r.chiave} = {r.comandi_disponibili.join(' | ')}
            </div>
          ))}
        </div>
        <h4 className="font-semibold mb-2 text-sm text-gray-300">Dettaglio combinazioni complete (3 caratteri)</h4>
        <div className="max-h-96 overflow-y-auto space-y-1 text-xs">
          {listaCombinata.map((r, idx) => (
            <div key={`${r.codice}-${idx}`} className="bg-gray-800/60 rounded px-2 py-1">
              {r.codice}: {r.sottosistema_codice}={r.sottosistema_nome} + {r.comando_codice}={r.comando_nome} + {r.intensita}
            </div>
          ))}
          {!listaCombinata.length ? <div className="text-gray-400">Nessuna combinazione disponibile.</div> : null}
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
    </div>
  );
}
