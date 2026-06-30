import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CreditCard, Layers, Plus, RefreshCw, Save, BookOpen, Tag } from 'lucide-react';
import {
  staffGetCarteCatalogo,
  staffGetCarteCatalogoByEspansione,
  staffCreateCartaCatalogo,
  staffUpdateCartaCatalogo,
  staffDeleteCartaCatalogo,
  staffGetCarteBustine,
  staffGetCarteBustineByEspansione,
  staffCreateCartaBustina,
  staffUpdateCartaBustina,
  staffDeleteCartaBustina,
  staffGetCarteEspansioni,
  staffCreateCartaEspansione,
  staffUpdateCartaEspansione,
  staffDeleteCartaEspansione,
  staffGetCarteConfig,
  staffSaveCarteConfig,
  staffGetCarteKeywords,
  staffCreateCartaKeyword,
  staffUpdateCartaKeyword,
  staffDeleteCartaKeyword,
  staffGetCarteEffectSchema,
  getStaffWikiCarteRegolamentoInfo,
  syncStaffWikiCarteRegolamento,
} from '../../api';
import { CARTA_ENERGIA_LABEL, CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../../carte/carteConstants';

const emptyCarta = (espansioneId = '') => ({
  codice: '',
  nome: '',
  tipo: 'PG',
  energia: 'MAR',
  rarita: 'COM',
  costo_gioco: 0,
  attacco: 2,
  salute: 3,
  iniziativa: 3,
  testo_gioco: '',
  testo_lore: '',
  set_collezione: '',
  espansione: espansioneId || null,
  campagna_origine: '',
  legame_id: '',
  tag_tematici: [],
  bonus_equip: {},
  duplicabile: false,
  attiva: true,
  ordine_set: 0,
});

const emptyBustina = (espansioneId = '') => ({
  nome: '',
  descrizione: '',
  costo_crediti: 500,
  carte_per_bustina: 5,
  set_collezione: '',
  espansione: espansioneId || null,
  garantisce_min_rarita: '',
  attiva: true,
  ordine: 0,
});

const emptyEspansione = () => ({
  nome: '',
  slug: '',
  descrizione: '',
  ordine: 0,
  attiva: true,
});

const emptyKeyword = () => ({
  codice: '',
  nome: '',
  testo_regola: '',
  reminder_breve: '',
  priorita: 0,
  attiva: true,
  effect_script: {},
});

const formatEffectScriptText = (script) => {
  if (!script || (typeof script === 'object' && Object.keys(script).length === 0)) return '';
  try {
    return JSON.stringify(script, null, 2);
  } catch {
    return '';
  }
};

const CarteCollezionabiliManager = ({ onLogout }) => {
  const [tab, setTab] = useState('espansioni');
  const [espansioni, setEspansioni] = useState([]);
  const [carte, setCarte] = useState([]);
  const [bustine, setBustine] = useState([]);
  const [keywords, setKeywords] = useState([]);
  const [config, setConfig] = useState({
    pity_soglia: 20,
    max_bustine_giorno: 10,
    mercato_commissione_pct: 8,
    accesso_modo: 'OFF',
    abilitata: false,
  });
  const [selectedEspansione, setSelectedEspansione] = useState(null);
  const [espansioneForm, setEspansioneForm] = useState(emptyEspansione());
  const [selected, setSelected] = useState(null);
  const [form, setForm] = useState(emptyCarta());
  const [bustinaForm, setBustinaForm] = useState(emptyBustina());
  const [selectedBustina, setSelectedBustina] = useState(null);
  const [keywordForm, setKeywordForm] = useState(emptyKeyword());
  const [effectScriptText, setEffectScriptText] = useState('');
  const [mutazioneX, setMutazioneX] = useState('0');
  const [selectedKeyword, setSelectedKeyword] = useState(null);
  const [wikiInfo, setWikiInfo] = useState(null);
  const [wikiSyncing, setWikiSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');

  const activeEspansioneId = selectedEspansione?.id || '';

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [esp, cfg, kw, wiki] = await Promise.all([
        staffGetCarteEspansioni(onLogout),
        staffGetCarteConfig(onLogout),
        staffGetCarteKeywords(onLogout),
        getStaffWikiCarteRegolamentoInfo(onLogout).catch(() => null),
      ]);
      const espList = Array.isArray(esp) ? esp : esp?.results || [];
      setEspansioni(espList);
      if (cfg) setConfig(cfg);
      setKeywords(Array.isArray(kw) ? kw : kw?.results || []);
      setWikiInfo(wiki);

      const espId = selectedEspansione?.id;
      if (espId) {
        const [cat, bust] = await Promise.all([
          staffGetCarteCatalogoByEspansione(espId, onLogout),
          staffGetCarteBustineByEspansione(espId, onLogout),
        ]);
        setCarte(Array.isArray(cat) ? cat : cat?.results || []);
        setBustine(Array.isArray(bust) ? bust : bust?.results || []);
      } else {
        const [cat, bust] = await Promise.all([
          staffGetCarteCatalogo(onLogout),
          staffGetCarteBustine(onLogout),
        ]);
        setCarte(Array.isArray(cat) ? cat : cat?.results || []);
        setBustine(Array.isArray(bust) ? bust : bust?.results || []);
      }
    } catch (e) {
      setMsg(e?.message || 'Errore caricamento.');
    } finally {
      setLoading(false);
    }
  }, [onLogout, selectedEspansione?.id]);

  useEffect(() => {
    load();
  }, [load]);

  const bustinePerEspansione = useMemo(() => {
    const map = new Map();
    espansioni.forEach((e) => map.set(e.id, []));
    bustine.forEach((b) => {
      const key = b.espansione || null;
      if (!map.has(key)) map.set(key, []);
      map.get(key).push(b);
    });
    return map;
  }, [espansioni, bustine]);

  const saveEspansione = async () => {
    try {
      if (selectedEspansione?.id) {
        await staffUpdateCartaEspansione(selectedEspansione.id, espansioneForm, onLogout);
      } else {
        await staffCreateCartaEspansione(espansioneForm, onLogout);
      }
      setMsg('Espansione salvata.');
      setSelectedEspansione(null);
      setEspansioneForm(emptyEspansione());
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio espansione fallito.');
    }
  };

  const saveCarta = async () => {
    try {
      if (selected?.id) {
        await staffUpdateCartaCatalogo(selected.id, form, onLogout);
      } else {
        await staffCreateCartaCatalogo(form, onLogout);
      }
      setMsg('Carta salvata.');
      setSelected(null);
      setForm(emptyCarta(activeEspansioneId));
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio fallito.');
    }
  };

  const saveBustina = async () => {
    try {
      if (selectedBustina?.id) {
        await staffUpdateCartaBustina(selectedBustina.id, bustinaForm, onLogout);
      } else {
        await staffCreateCartaBustina(bustinaForm, onLogout);
      }
      setMsg('Bustina salvata.');
      setSelectedBustina(null);
      setBustinaForm(emptyBustina(activeEspansioneId));
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio fallito.');
    }
  };

  const saveConfig = async () => {
    try {
      await staffSaveCarteConfig(config, onLogout);
      setMsg('Configurazione salvata.');
    } catch (e) {
      setMsg(e?.message || 'Salvataggio config fallito.');
    }
  };

  const saveKeyword = async () => {
    try {
      let effect_script = {};
      if (effectScriptText.trim()) {
        effect_script = JSON.parse(effectScriptText);
      }
      const payload = { ...keywordForm, effect_script };
      if (selectedKeyword?.id) {
        await staffUpdateCartaKeyword(selectedKeyword.id, payload, onLogout);
      } else {
        await staffCreateCartaKeyword(payload, onLogout);
      }
      setMsg('Keyword salvata.');
      setSelectedKeyword(null);
      setKeywordForm(emptyKeyword());
      setEffectScriptText('');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio keyword fallito.');
    }
  };

  const loadMutazioneTemplate = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.mutazione;
      if (tpl) {
        setEffectScriptText(JSON.stringify(tpl, null, 2));
        setMsg('Template Mutazione [X] caricato nello script.');
      }
    } catch (e) {
      setMsg(e?.message || 'Caricamento template fallito.');
    }
  };

  const applyMutazioneComposer = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.mutazione;
      if (!tpl) {
        setMsg('Template Mutazione non disponibile.');
        return;
      }
      const xVal = parseInt(mutazioneX, 10);
      const script = JSON.parse(JSON.stringify(tpl));
      if (script.params?.X) {
        script.params.X.default = Number.isFinite(xVal) ? xVal : 0;
      }
      setEffectScriptText(JSON.stringify(script, null, 2));
      setKeywordForm((p) => ({
        ...p,
        codice: p.codice || 'MUTAZIONE',
        nome: p.nome || 'Mutazione [X]',
        testo_regola: p.testo_regola || (
          'Quando questo Personaggio si esaurisce, puoi sostituirlo con un Personaggio '
          + 'dalla tua mano con costo gioco ≤ [X].'
        ),
        reminder_breve: p.reminder_breve || 'Mutazione ≤[X]',
      }));
      setMsg('Compositore Mutazione applicato (nome, regola, script).');
    } catch (e) {
      setMsg(e?.message || 'Compositore fallito.');
    }
  };

  const applyColpoComposer = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.colpo_influenza;
      if (!tpl) {
        setMsg('Template Colpo non disponibile.');
        return;
      }
      const xVal = parseInt(mutazioneX, 10);
      const script = JSON.parse(JSON.stringify(tpl));
      if (script.params?.X) {
        script.params.X.default = Number.isFinite(xVal) ? xVal : 1;
      }
      setEffectScriptText(JSON.stringify(script, null, 2));
      setKeywordForm((p) => ({
        ...p,
        codice: p.codice || 'COLPO',
        nome: p.nome || 'Colpo [X]',
        testo_regola: p.testo_regola || 'Quando giochi questa carta, infliggi [X] danni all\'influenza avversaria.',
        reminder_breve: p.reminder_breve || 'Colpo [X]',
      }));
      setMsg('Compositore Colpo [X] applicato.');
    } catch (e) {
      setMsg(e?.message || 'Compositore fallito.');
    }
  };

  const applyPescaComposer = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.pesca;
      if (!tpl) {
        setMsg('Template Pesca non disponibile.');
        return;
      }
      const xVal = parseInt(mutazioneX, 10);
      const script = JSON.parse(JSON.stringify(tpl));
      if (script.params?.X) {
        script.params.X.default = Number.isFinite(xVal) ? xVal : 1;
      }
      setEffectScriptText(JSON.stringify(script, null, 2));
      setKeywordForm((p) => ({
        ...p,
        codice: p.codice || 'PESCA',
        nome: p.nome || 'Pesca [X]',
        testo_regola: p.testo_regola || (
          'All\'inizio del tuo turno, mentre questa carta è in gioco: Pesca [X].'
        ),
        reminder_breve: p.reminder_breve || 'Pesca [X]',
      }));
      setMsg('Compositore Pesca [X] (on_turn_start) applicato.');
    } catch (e) {
      setMsg(e?.message || 'Compositore fallito.');
    }
  };

  const applyRigenerazioneComposer = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.rigenerazione_energia;
      if (!tpl) {
        setMsg('Template Rigenerazione non disponibile.');
        return;
      }
      const xVal = parseInt(mutazioneX, 10);
      const script = JSON.parse(JSON.stringify(tpl));
      if (script.params?.X) {
        script.params.X.default = Number.isFinite(xVal) ? xVal : 1;
      }
      setEffectScriptText(JSON.stringify(script, null, 2));
      setKeywordForm((p) => ({
        ...p,
        codice: p.codice || 'RIGENERAZIONE',
        nome: p.nome || 'Rigenerazione [X]',
        testo_regola: p.testo_regola || 'Quando giochi questa carta, guadagni [X] energia.',
        reminder_breve: p.reminder_breve || 'Rigenerazione [X]',
      }));
      setMsg('Compositore Rigenerazione [X] (on_play) applicato.');
    } catch (e) {
      setMsg(e?.message || 'Compositore fallito.');
    }
  };

  const applyDannoEroeComposer = async () => {
    try {
      const data = await staffGetCarteEffectSchema(onLogout);
      const tpl = data?.templates?.danno_eroe;
      if (!tpl) {
        setMsg('Template Danno eroe non disponibile.');
        return;
      }
      const xVal = parseInt(mutazioneX, 10);
      const script = JSON.parse(JSON.stringify(tpl));
      if (script.params?.X) {
        script.params.X.default = Number.isFinite(xVal) ? xVal : 1;
      }
      setEffectScriptText(JSON.stringify(script, null, 2));
      setKeywordForm((p) => ({
        ...p,
        codice: p.codice || 'FERITA',
        nome: p.nome || 'Ferita [X]',
        testo_regola: p.testo_regola || (
          'Quando giochi questa carta, scegli un eroe avversario e infliggi [X] danni.'
        ),
        reminder_breve: p.reminder_breve || 'Ferita [X]',
      }));
      setMsg('Compositore Ferita [X] (scelta eroe) applicato.');
    } catch (e) {
      setMsg(e?.message || 'Compositore fallito.');
    }
  };

  const deleteKeyword = async (id) => {
    if (!window.confirm('Eliminare questa keyword?')) return;
    try {
      await staffDeleteCartaKeyword(id, onLogout);
      setMsg('Keyword eliminata.');
      setSelectedKeyword(null);
      setKeywordForm(emptyKeyword());
      setEffectScriptText('');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
    }
  };

  const handleWikiSync = async (force = true) => {
    setWikiSyncing(true);
    try {
      const res = await syncStaffWikiCarteRegolamento(onLogout, { force });
      const s = res?.summary || {};
      setMsg(`Wiki regolamento: ${s.created || 0} create, ${s.updated || 0} aggiornate.`);
      const info = await getStaffWikiCarteRegolamentoInfo(onLogout);
      setWikiInfo(info);
    } catch (e) {
      setMsg(e?.message || 'Sync wiki fallita.');
    } finally {
      setWikiSyncing(false);
    }
  };

  const selectEspansione = (esp) => {
    setSelectedEspansione(esp);
    setEspansioneForm({ ...esp });
    setSelected(null);
    setForm(emptyCarta(esp?.id));
    setSelectedBustina(null);
    setBustinaForm(emptyBustina(esp?.id));
  };

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4 text-gray-100">
      <header className="flex items-center justify-between border-b border-gray-700 pb-3">
        <h2 className="flex items-center gap-2 text-xl font-bold">
          <CreditCard className="text-violet-400" /> Carte collezionabili
        </h2>
        <button type="button" onClick={load} className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600">
          <RefreshCw size={14} className="inline" /> Aggiorna
        </button>
      </header>

      {msg && <p className="text-sm text-amber-300">{msg}</p>}

      <div className="flex flex-wrap gap-2">
        {['espansioni', 'catalogo', 'bustine', 'keywords', 'config'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1 text-sm capitalize ${tab === t ? 'bg-violet-700' : 'bg-gray-800'}`}
          >
            {t}
          </button>
        ))}
      </div>

      {selectedEspansione && tab !== 'config' && (
        <p className="text-xs text-violet-300">
          Filtro espansione: <strong>{selectedEspansione.nome}</strong>
          {' '}
          <button type="button" className="underline" onClick={() => selectEspansione(null)}>mostra tutte</button>
        </p>
      )}

      {loading && <p className="text-gray-400">Caricamento…</p>}

      {!loading && tab === 'espansioni' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="flex items-center gap-1 font-bold">
                <Layers size={16} className="text-violet-400" /> Espansioni ({espansioni.length})
              </h3>
              <button
                type="button"
                className="flex items-center gap-1 rounded bg-violet-800 px-2 py-1 text-xs"
                onClick={() => { setSelectedEspansione(null); setEspansioneForm(emptyEspansione()); }}
              >
                <Plus size={12} /> Nuova
              </button>
            </div>
            <ul className="max-h-[50vh] space-y-1 overflow-y-auto text-sm">
              {espansioni.map((e) => (
                <li key={e.id}>
                  <button
                    type="button"
                    className={`w-full rounded px-2 py-2 text-left hover:bg-gray-800 ${selectedEspansione?.id === e.id ? 'bg-gray-700' : ''}`}
                    onClick={() => selectEspansione(e)}
                  >
                    <span className="font-bold">{e.nome}</span>
                    <span className="ml-2 text-xs text-gray-500">
                      {e.slug} · {e.carte_count ?? 0} carte · {e.bustine_count ?? 0} bustine
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2 rounded border border-gray-700 p-3">
            <h3 className="font-bold">{selectedEspansione ? 'Modifica espansione' : 'Nuova espansione'}</h3>
            {['nome', 'slug', 'descrizione'].map((f) => (
              <input
                key={f}
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
                placeholder={f}
                value={espansioneForm[f] || ''}
                onChange={(e) => setEspansioneForm((p) => ({ ...p, [f]: e.target.value }))}
              />
            ))}
            <input
              type="number"
              className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              placeholder="Ordine"
              value={espansioneForm.ordine}
              onChange={(e) => setEspansioneForm((p) => ({ ...p, ordine: Number(e.target.value) }))}
            />
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={!!espansioneForm.attiva}
                onChange={(e) => setEspansioneForm((p) => ({ ...p, attiva: e.target.checked }))}
              />
              Attiva
            </label>
            <div className="flex gap-2">
              <button type="button" className="flex items-center gap-1 rounded bg-emerald-800 px-3 py-1 text-sm" onClick={saveEspansione}>
                <Save size={14} /> Salva
              </button>
              {selectedEspansione?.id && (
                <>
                  <button
                    type="button"
                    className="rounded bg-sky-800 px-3 py-1 text-sm"
                    onClick={() => { setTab('catalogo'); selectEspansione(selectedEspansione); }}
                  >
                    Carte
                  </button>
                  <button
                    type="button"
                    className="rounded bg-amber-800 px-3 py-1 text-sm"
                    onClick={() => { setTab('bustine'); selectEspansione(selectedEspansione); }}
                  >
                    Bustine
                  </button>
                  <button
                    type="button"
                    className="rounded bg-red-900 px-3 py-1 text-sm"
                    onClick={async () => {
                      await staffDeleteCartaEspansione(selectedEspansione.id, onLogout);
                      setSelectedEspansione(null);
                      setEspansioneForm(emptyEspansione());
                      load();
                    }}
                  >
                    Elimina
                  </button>
                </>
              )}
            </div>
          </div>
        </div>
      )}

      {!loading && tab === 'catalogo' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-bold">Catalogo ({carte.length})</h3>
              <button
                type="button"
                className="flex items-center gap-1 rounded bg-violet-800 px-2 py-1 text-xs"
                onClick={() => { setSelected(null); setForm(emptyCarta(activeEspansioneId)); }}
              >
                <Plus size={12} /> Nuova
              </button>
            </div>
            <ul className="max-h-[50vh] space-y-1 overflow-y-auto text-sm">
              {carte.map((c) => (
                <li key={c.id}>
                  <button
                    type="button"
                    className={`w-full rounded px-2 py-1 text-left hover:bg-gray-800 ${selected?.id === c.id ? 'bg-gray-700' : ''}`}
                    onClick={() => { setSelected(c); setForm({ ...c }); }}
                  >
                    <span className="font-bold">{c.nome}</span>
                    <span className="ml-2 text-xs text-gray-500">
                      {c.codice} · {CARTA_RARITA_LABEL[c.rarita]}
                      {c.espansione_nome ? ` · ${c.espansione_nome}` : ''}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          </div>
          <div className="space-y-2 rounded border border-gray-700 p-3">
            <h3 className="font-bold">{selected ? 'Modifica carta' : 'Nuova carta'}</h3>
            <select
              className="w-full rounded bg-gray-900 px-2 py-1 text-sm"
              value={form.espansione || ''}
              onChange={(e) => setForm((p) => ({ ...p, espansione: e.target.value || null }))}
            >
              <option value="">— Nessuna espansione —</option>
              {espansioni.map((e) => (
                <option key={e.id} value={e.id}>{e.nome}</option>
              ))}
            </select>
            {['codice', 'nome', 'set_collezione', 'campagna_origine', 'legame_id'].map((f) => (
              <input
                key={f}
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
                placeholder={f}
                value={form[f] || ''}
                onChange={(e) => setForm((p) => ({ ...p, [f]: e.target.value }))}
              />
            ))}
            <div className="grid grid-cols-3 gap-2">
              <select className="rounded bg-gray-900 px-2 py-1 text-sm" value={form.tipo} onChange={(e) => setForm((p) => ({ ...p, tipo: e.target.value }))}>
                {Object.entries(CARTA_TIPO_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <select className="rounded bg-gray-900 px-2 py-1 text-sm" value={form.energia} onChange={(e) => setForm((p) => ({ ...p, energia: e.target.value }))}>
                {Object.entries(CARTA_ENERGIA_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
              <select className="rounded bg-gray-900 px-2 py-1 text-sm" value={form.rarita} onChange={(e) => setForm((p) => ({ ...p, rarita: e.target.value }))}>
                {Object.entries(CARTA_RARITA_LABEL).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </select>
            </div>
            <textarea
              className="h-20 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm"
              placeholder="Testo gioco"
              value={form.testo_gioco || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo_gioco: e.target.value }))}
            />
            <textarea
              className="h-20 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm"
              placeholder="Testo lore"
              value={form.testo_lore || ''}
              onChange={(e) => setForm((p) => ({ ...p, testo_lore: e.target.value }))}
            />
            <div className="flex gap-2">
              <button type="button" className="flex items-center gap-1 rounded bg-emerald-800 px-3 py-1 text-sm" onClick={saveCarta}>
                <Save size={14} /> Salva
              </button>
              {selected?.id && (
                <button
                  type="button"
                  className="rounded bg-red-900 px-3 py-1 text-sm"
                  onClick={async () => {
                    await staffDeleteCartaCatalogo(selected.id, onLogout);
                    setSelected(null);
                    setForm(emptyCarta(activeEspansioneId));
                    load();
                  }}
                >
                  Elimina
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {!loading && tab === 'bustine' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <div>
            <div className="mb-2 flex items-center justify-between">
              <h3 className="font-bold">Bustine ({bustine.length})</h3>
              <button
                type="button"
                className="rounded bg-violet-800 px-2 py-1 text-xs"
                onClick={() => { setSelectedBustina(null); setBustinaForm(emptyBustina(activeEspansioneId)); }}
              >
                <Plus size={12} className="inline" /> Nuova
              </button>
            </div>
            {espansioni.map((e) => {
              const list = bustinePerEspansione.get(e.id) || [];
              if (!list.length && selectedEspansione?.id && selectedEspansione.id !== e.id) return null;
              return (
                <div key={e.id} className="mb-3">
                  <h4 className="mb-1 text-xs font-bold uppercase text-violet-300">{e.nome}</h4>
                  <ul className="space-y-1 text-sm">
                    {list.map((b) => (
                      <li key={b.id}>
                        <button
                          type="button"
                          className="w-full rounded px-2 py-1 text-left hover:bg-gray-800"
                          onClick={() => { setSelectedBustina(b); setBustinaForm({ ...b }); }}
                        >
                          {b.nome} — {b.costo_crediti} CR
                        </button>
                      </li>
                    ))}
                  </ul>
                </div>
              );
            })}
            {(bustinePerEspansione.get(null) || []).length > 0 && (
              <div className="mb-3">
                <h4 className="mb-1 text-xs font-bold uppercase text-gray-500">Senza espansione</h4>
                <ul className="space-y-1 text-sm">
                  {(bustinePerEspansione.get(null) || []).map((b) => (
                    <li key={b.id}>
                      <button
                        type="button"
                        className="w-full rounded px-2 py-1 text-left hover:bg-gray-800"
                        onClick={() => { setSelectedBustina(b); setBustinaForm({ ...b }); }}
                      >
                        {b.nome} — {b.costo_crediti} CR
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <div className="space-y-2 rounded border border-gray-700 p-3">
            <h3 className="font-bold">{selectedBustina ? 'Modifica bustina' : 'Nuova bustina'}</h3>
            <select
              className="w-full rounded bg-gray-900 px-2 py-1 text-sm"
              value={bustinaForm.espansione || ''}
              onChange={(e) => setBustinaForm((p) => ({ ...p, espansione: e.target.value || null }))}
            >
              <option value="">— Nessuna espansione —</option>
              {espansioni.map((e) => (
                <option key={e.id} value={e.id}>{e.nome}</option>
              ))}
            </select>
            {['nome', 'descrizione', 'set_collezione'].map((f) => (
              <input
                key={f}
                className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
                placeholder={f}
                value={bustinaForm[f] || ''}
                onChange={(e) => setBustinaForm((p) => ({ ...p, [f]: e.target.value }))}
              />
            ))}
            <input
              type="number"
              className="w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
              placeholder="Costo CR"
              value={bustinaForm.costo_crediti}
              onChange={(e) => setBustinaForm((p) => ({ ...p, costo_crediti: e.target.value }))}
            />
            <button type="button" className="rounded bg-emerald-800 px-3 py-1 text-sm" onClick={saveBustina}>Salva bustina</button>
            {selectedBustina?.id && (
              <button
                type="button"
                className="ml-2 rounded bg-red-900 px-3 py-1 text-sm"
                onClick={async () => {
                  await staffDeleteCartaBustina(selectedBustina.id, onLogout);
                  setSelectedBustina(null);
                  load();
                }}
              >
                Elimina
              </button>
            )}
          </div>
        </div>
      )}

      {!loading && tab === 'keywords' && (
        <div className="grid gap-4 lg:grid-cols-2">
          <p className="col-span-full text-xs text-gray-500">
            Placeholder <code className="text-violet-300">[X]</code>, <code className="text-violet-300">[Y]</code>…
            nel nome e nel testo regola: es. nome <code>Mutazione [X]</code> + regola
            {' '}
            <code>…costo [X].</code>
            {' '}
            → su carta con <em>Mutazione 0</em> mostra <em>costo 0</em>.
            {' '}
            Guida completa in Wiki → <strong>Gioco carte → Keyword carte — guida master</strong>.
          </p>
          <div className="rounded border border-gray-700 p-3">
            <h3 className="mb-2 flex items-center gap-2 text-sm font-bold text-violet-300">
              <Tag size={16} /> Keyword ({keywords.length})
            </h3>
            <ul className="max-h-80 space-y-1 overflow-y-auto text-sm">
              {keywords.map((k) => (
                <li key={k.id}>
                  <button
                    type="button"
                    className={`w-full rounded px-2 py-1 text-left ${selectedKeyword?.id === k.id ? 'bg-violet-900' : 'hover:bg-gray-800'}`}
                    onClick={() => {
                      setSelectedKeyword(k);
                      setKeywordForm({ ...k });
                      setEffectScriptText(formatEffectScriptText(k.effect_script));
                    }}
                  >
                    <span className="font-mono text-xs text-gray-500">{k.codice}</span>
                    {' — '}
                    {k.nome}
                    {!k.attiva && <span className="ml-1 text-amber-500">(off)</span>}
                  </button>
                </li>
              ))}
              {keywords.length === 0 && <p className="text-gray-500">Nessuna keyword.</p>}
            </ul>
            <button
              type="button"
              className="mt-2 flex items-center gap-1 rounded bg-gray-800 px-2 py-1 text-xs"
              onClick={() => {
                setSelectedKeyword(null);
                setKeywordForm(emptyKeyword());
                setEffectScriptText('');
              }}
            >
              <Plus size={12} /> Nuova keyword
            </button>
          </div>
          <div className="space-y-2 rounded border border-gray-700 p-3">
            <label className="block text-sm">
              Codice
              <input
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1 font-mono uppercase"
                value={keywordForm.codice}
                onChange={(e) => setKeywordForm((p) => ({ ...p, codice: e.target.value.toUpperCase() }))}
              />
            </label>
            <label className="block text-sm">
              Nome (nel testo carta)
              <input
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
                placeholder="Es. Mutazione [X] o Evocazione"
                value={keywordForm.nome}
                onChange={(e) => setKeywordForm((p) => ({ ...p, nome: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              Testo regola completo
              <textarea
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
                rows={4}
                placeholder="Usa gli stessi [X] del nome, es. …costo [X]."
                value={keywordForm.testo_regola}
                onChange={(e) => setKeywordForm((p) => ({ ...p, testo_regola: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              Reminder breve (inline se c&apos;è spazio)
              <input
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
                value={keywordForm.reminder_breve}
                onChange={(e) => setKeywordForm((p) => ({ ...p, reminder_breve: e.target.value }))}
              />
            </label>
            <label className="block text-sm">
              Priorità match
              <input
                type="number"
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
                value={keywordForm.priorita}
                onChange={(e) => setKeywordForm((p) => ({ ...p, priorita: Number(e.target.value) }))}
              />
            </label>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={keywordForm.attiva !== false}
                onChange={(e) => setKeywordForm((p) => ({ ...p, attiva: e.target.checked }))}
              />
              Attiva
            </label>
            <div className="rounded border border-violet-900/50 bg-violet-950/20 p-2">
              <p className="mb-2 text-xs font-bold text-violet-300">Compositore keyword parametrizzate</p>
              <div className="flex flex-wrap items-end gap-2">
                <label className="text-xs">
                  Valore X
                  <input
                    type="number"
                    min={0}
                    className="mt-1 block w-24 rounded bg-gray-900 px-2 py-1"
                    value={mutazioneX}
                    onChange={(e) => setMutazioneX(e.target.value)}
                  />
                </label>
                <button
                  type="button"
                  className="rounded bg-violet-800 px-2 py-1 text-xs"
                  onClick={applyMutazioneComposer}
                >
                  Mutazione [X]
                </button>
                <button
                  type="button"
                  className="rounded bg-rose-900 px-2 py-1 text-xs"
                  onClick={applyColpoComposer}
                >
                  Colpo [X] (on_play)
                </button>
                <button
                  type="button"
                  className="rounded bg-sky-900 px-2 py-1 text-xs"
                  onClick={applyPescaComposer}
                >
                  Pesca [X] (turno)
                </button>
                <button
                  type="button"
                  className="rounded bg-amber-900 px-2 py-1 text-xs"
                  onClick={applyRigenerazioneComposer}
                >
                  Rigenerazione [X]
                </button>
                <button
                  type="button"
                  className="rounded bg-orange-900 px-2 py-1 text-xs"
                  onClick={applyDannoEroeComposer}
                >
                  Ferita [X] (eroe)
                </button>
              </div>
            </div>
            <label className="block text-sm">
              Effect script (JSON v1, opzionale)
              <textarea
                className="mt-1 w-full rounded bg-gray-900 px-2 py-1 font-mono text-xs"
                rows={8}
                placeholder='{"version":1,...}'
                value={effectScriptText}
                onChange={(e) => setEffectScriptText(e.target.value)}
              />
            </label>
            <button
              type="button"
              className="rounded bg-violet-900 px-2 py-1 text-xs"
              onClick={loadMutazioneTemplate}
            >
              Carica template Mutazione [X]
            </button>
            <div className="flex gap-2">
              <button type="button" className="rounded bg-emerald-800 px-3 py-1 text-sm" onClick={saveKeyword}>
                <Save size={14} className="mr-1 inline" />
                Salva
              </button>
              {selectedKeyword?.id && (
                <button
                  type="button"
                  className="rounded bg-red-900 px-3 py-1 text-sm"
                  onClick={() => deleteKeyword(selectedKeyword.id)}
                >
                  Elimina
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {!loading && tab === 'config' && (
        <div className="max-w-md space-y-3 rounded border border-gray-700 p-4">
          <fieldset className="space-y-2">
            <legend className="text-sm font-bold text-violet-300">Accesso gioco carte</legend>
            {[
              { value: 'OFF', label: 'Disattivo — nessun accesso' },
              { value: 'TEST', label: 'Testing — solo PnG staff (tipologia non giocante)' },
              { value: 'OPEN', label: 'Aperto — tutti i personaggi giocanti' },
            ].map((opt) => (
              <label key={opt.value} className="flex items-center gap-2 text-sm">
                <input
                  type="radio"
                  name="accesso_modo"
                  value={opt.value}
                  checked={(config.accesso_modo || (config.abilitata ? 'OPEN' : 'OFF')) === opt.value}
                  onChange={() => setConfig((p) => ({
                    ...p,
                    accesso_modo: opt.value,
                    abilitata: opt.value === 'OPEN',
                  }))}
                />
                {opt.label}
              </label>
            ))}
          </fieldset>
          <p className="text-xs text-gray-500">
            In modalità Testing i PNG staff possono provare bustine, reliquiario e duelli prima del lancio pubblico.
          </p>
          <label className="block text-sm">
            Pity (bustine senza Rara+)
            <input
              type="number"
              className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
              value={config.pity_soglia}
              onChange={(e) => setConfig((p) => ({ ...p, pity_soglia: Number(e.target.value) }))}
            />
          </label>
          <label className="block text-sm">
            Max bustine/giorno
            <input
              type="number"
              className="mt-1 w-full rounded bg-gray-900 px-2 py-1"
              value={config.max_bustine_giorno}
              onChange={(e) => setConfig((p) => ({ ...p, max_bustine_giorno: Number(e.target.value) }))}
            />
          </label>
          <button type="button" className="rounded bg-emerald-800 px-3 py-1 text-sm" onClick={saveConfig}>Salva config</button>

          <div className="mt-6 rounded border border-violet-900/50 bg-violet-950/20 p-3">
            <h4 className="mb-2 flex items-center gap-2 text-sm font-bold text-violet-300">
              <BookOpen size={16} /> Wiki regolamento carte
            </h4>
            <p className="mb-2 text-xs text-gray-500">
              Bozza da <code>docs/wiki/carte/</code>. CLI: <code className="text-gray-400">make wiki-carte-sync ENV=…</code>
              {' '}
              (con <code>WIKI_CARTE_FORCE=1</code> per sovrascrivere). Visibile ai giocatori solo con accesso OPEN;
              staff campagna la vede sempre.
            </p>
            {wikiInfo?.manifest_ok && (
              <p className="mb-2 text-xs text-gray-400">
                Pagina: <code>{wikiInfo.pages?.[0]?.slug || 'carte-collezionabili-regolamento'}</code>
              </p>
            )}
            <div className="flex flex-wrap gap-2">
              <a
                href="/regolamento/carte-collezionabili-regolamento"
                target="_blank"
                rel="noopener noreferrer"
                className="rounded border border-gray-600 px-2 py-1 text-xs hover:bg-gray-800"
              >
                Apri in Wiki
              </a>
              <button
                type="button"
                disabled={wikiSyncing}
                className="flex items-center gap-1 rounded bg-violet-800 px-2 py-1 text-xs disabled:opacity-50"
                onClick={() => handleWikiSync(true)}
              >
                <RefreshCw size={12} className={wikiSyncing ? 'animate-spin' : ''} />
                Sincronizza da repo
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default CarteCollezionabiliManager;
