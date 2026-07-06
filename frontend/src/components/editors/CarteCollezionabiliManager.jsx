import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CreditCard, ImagePlus, Layers, Plus, RefreshCw, Save, BookOpen, Tag, X } from 'lucide-react';
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
  getStaffWikiCarteRegolamentoInfo,
  syncStaffWikiCarteRegolamento,
  resolveMediaUrl,
  getPunteggiList,
} from '../../api';
import { CARTA_ENERGIA_LABEL, CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../../carte/carteConstants';
import { CardRulesPreview } from '../../carte/cardTextBlocks';
import BonusEquipEditor from './BonusEquipEditor';
import ComboReliquiarioStaffPanel from './ComboReliquiarioStaffPanel';
import EffectScriptWizard from './EffectScriptWizard';
import MercatoScambiStaffPanel from './MercatoScambiStaffPanel';
import StatModInline from './inlines/StatModInline';

function normalizeCartaStats(rows) {
  return (rows || []).map((row) => ({
    ...row,
    statistica: row.statistica?.id || row.statistica,
    limit_a_aure: row.limit_a_aure || [],
    limit_a_elementi: row.limit_a_elementi || [],
    tipo_modificatore: row.tipo_modificatore || 'ADD',
    valore: row.valore ?? 0,
  }));
}

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
  testo_reliquiario: '',
  statistiche_reliquiario: [],
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

const CARTA_READ_ONLY_KEYS = new Set([
  'id', 'sync_id', 'created_at', 'updated_at', 'immagine_url', 'espansione_nome', 'campagna', 'immagine',
]);

const ESPANSIONE_READ_ONLY_KEYS = new Set([
  'id', 'sync_id', 'created_at', 'updated_at', 'immagine_url', 'campagna', 'carte_count', 'bustine_count', 'immagine',
]);

function stripForApi(form, readOnlyKeys) {
  const out = {};
  Object.entries(form || {}).forEach(([key, val]) => {
    if (!readOnlyKeys.has(key)) out[key] = val;
  });
  return out;
}

function appendFormField(fd, key, val) {
  if (val === null || val === undefined) return;
  if (typeof val === 'boolean') {
    fd.append(key, val ? 'true' : 'false');
    return;
  }
  if (typeof val === 'object') {
    fd.append(key, JSON.stringify(val));
    return;
  }
  fd.append(key, String(val));
}

function buildCartaFormData(form, file) {
  const fd = new FormData();
  Object.entries(stripForApi(form, CARTA_READ_ONLY_KEYS)).forEach(([key, val]) => {
    appendFormField(fd, key, val);
  });
  if (file) fd.append('immagine', file);
  return fd;
}

function buildEspansioneFormData(form, file) {
  const fd = new FormData();
  Object.entries(stripForApi(form, ESPANSIONE_READ_ONLY_KEYS)).forEach(([key, val]) => {
    appendFormField(fd, key, val);
  });
  if (file) fd.append('immagine', file);
  return fd;
}

function CartaImmagineUpload({ label, previewUrl, file, onFileChange, onRemoveExisting, removeExisting }) {
  return (
    <div className="rounded border border-gray-700 bg-gray-900/50 p-2">
      <p className="mb-2 text-xs font-bold text-gray-300">{label}</p>
      {previewUrl ? (
        <div className="relative mb-2 flex justify-center">
          <img
            src={previewUrl}
            alt="Anteprima"
            className="max-h-40 rounded border border-gray-600 object-contain"
          />
          {file && (
            <button
              type="button"
              className="absolute right-0 top-0 rounded-full bg-gray-900/90 p-1 text-gray-300 hover:text-white"
              title="Annulla nuovo file"
              onClick={() => onFileChange(null)}
            >
              <X size={14} />
            </button>
          )}
        </div>
      ) : (
        <p className="mb-2 text-center text-[10px] text-gray-500">Nessuna immagine</p>
      )}
      <label className="flex cursor-pointer items-center justify-center gap-2 rounded border border-dashed border-violet-700 bg-violet-950/20 px-2 py-2 text-xs text-violet-200 hover:bg-violet-950/40">
        <ImagePlus size={14} />
        {file ? file.name : 'Scegli immagine (JPG, PNG, WebP)'}
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          className="hidden"
          onChange={(e) => onFileChange(e.target.files?.[0] || null)}
        />
      </label>
      {previewUrl && !file && onRemoveExisting && (
        <label className="mt-2 flex items-center gap-2 text-xs text-gray-400">
          <input
            type="checkbox"
            checked={!!removeExisting}
            onChange={(e) => onRemoveExisting(e.target.checked)}
          />
          Rimuovi immagine salvata
        </label>
      )}
      <p className="mt-1 text-[10px] text-gray-500">
        Compare nell&apos;arte della carta in app. Dopo il deploy, sincronizza i file con make sync-media se usi il mirror.
      </p>
    </div>
  );
}

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
  const [selectedKeyword, setSelectedKeyword] = useState(null);
  const [wikiInfo, setWikiInfo] = useState(null);
  const [wikiSyncing, setWikiSyncing] = useState(false);
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState('');
  const [cartaImmagineFile, setCartaImmagineFile] = useState(null);
  const [cartaFilePreview, setCartaFilePreview] = useState(null);
  const [removeCartaImmagine, setRemoveCartaImmagine] = useState(false);
  const [espansioneImmagineFile, setEspansioneImmagineFile] = useState(null);
  const [espansioneFilePreview, setEspansioneFilePreview] = useState(null);
  const [removeEspansioneImmagine, setRemoveEspansioneImmagine] = useState(false);
  const [punteggi, setPunteggi] = useState([]);

  const statsOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'ST'), [punteggi]);
  const auraOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'AU'), [punteggi]);
  const elementOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'EL'), [punteggi]);

  const activeEspansioneId = selectedEspansione?.id || '';

  useEffect(() => {
    if (!cartaImmagineFile) {
      setCartaFilePreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(cartaImmagineFile);
    setCartaFilePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [cartaImmagineFile]);

  useEffect(() => {
    if (!espansioneImmagineFile) {
      setEspansioneFilePreview(null);
      return undefined;
    }
    const url = URL.createObjectURL(espansioneImmagineFile);
    setEspansioneFilePreview(url);
    return () => URL.revokeObjectURL(url);
  }, [espansioneImmagineFile]);

  const cartaPreviewUrl = cartaFilePreview
    || (!removeCartaImmagine && form.immagine_url ? resolveMediaUrl(form.immagine_url) : null);

  const espansionePreviewUrl = espansioneFilePreview
    || (!removeEspansioneImmagine && espansioneForm.immagine_url ? resolveMediaUrl(espansioneForm.immagine_url) : null);

  const resetCartaImmagineState = () => {
    setCartaImmagineFile(null);
    setRemoveCartaImmagine(false);
  };

  const resetEspansioneImmagineState = () => {
    setEspansioneImmagineFile(null);
    setRemoveEspansioneImmagine(false);
  };

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [esp, cfg, kw, wiki, punt] = await Promise.all([
        staffGetCarteEspansioni(onLogout),
        staffGetCarteConfig(onLogout),
        staffGetCarteKeywords(onLogout),
        getStaffWikiCarteRegolamentoInfo(onLogout).catch(() => null),
        getPunteggiList(onLogout).catch(() => []),
      ]);
      const espList = Array.isArray(esp) ? esp : esp?.results || [];
      setEspansioni(espList);
      if (cfg) setConfig(cfg);
      setKeywords(Array.isArray(kw) ? kw : kw?.results || []);
      setWikiInfo(wiki);
      setPunteggi(punt || []);

      const espId = selectedEspansione?.id;
      const loadCatalogo = espId
        ? staffGetCarteCatalogoByEspansione(espId, onLogout)
        : staffGetCarteCatalogo(onLogout);
      const loadBustine = espId
        ? staffGetCarteBustineByEspansione(espId, onLogout)
        : staffGetCarteBustine(onLogout);

      const [catRes, bustRes] = await Promise.allSettled([loadCatalogo, loadBustine]);
      const partialErrors = [];

      if (catRes.status === 'fulfilled') {
        const cat = catRes.value;
        setCarte(Array.isArray(cat) ? cat : cat?.results || []);
      } else {
        setCarte([]);
        partialErrors.push(catRes.reason?.message || 'catalogo');
      }

      if (bustRes.status === 'fulfilled') {
        const bust = bustRes.value;
        setBustine(Array.isArray(bust) ? bust : bust?.results || []);
      } else {
        setBustine([]);
        partialErrors.push(bustRes.reason?.message || 'bustine');
      }

      if (partialErrors.length) {
        setMsg(`Caricamento parziale: errore su ${partialErrors.join(', ')}.`);
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
      let payload;
      if (espansioneImmagineFile) {
        payload = buildEspansioneFormData(espansioneForm, espansioneImmagineFile);
      } else if (removeEspansioneImmagine && selectedEspansione?.id) {
        payload = { ...stripForApi(espansioneForm, ESPANSIONE_READ_ONLY_KEYS), immagine: null };
      } else {
        payload = stripForApi(espansioneForm, ESPANSIONE_READ_ONLY_KEYS);
      }
      if (selectedEspansione?.id) {
        await staffUpdateCartaEspansione(selectedEspansione.id, payload, onLogout);
      } else {
        await staffCreateCartaEspansione(payload, onLogout);
      }
      setMsg('Espansione salvata.');
      setSelectedEspansione(null);
      setEspansioneForm(emptyEspansione());
      resetEspansioneImmagineState();
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio espansione fallito.');
    }
  };

  const saveCarta = async () => {
    try {
      let payload;
      const formPayload = {
        ...form,
        statistiche_reliquiario: normalizeCartaStats(form.statistiche_reliquiario),
      };
      if (cartaImmagineFile) {
        payload = buildCartaFormData(formPayload, cartaImmagineFile);
      } else if (removeCartaImmagine && selected?.id) {
        payload = { ...stripForApi(formPayload, CARTA_READ_ONLY_KEYS), immagine: null };
      } else {
        payload = stripForApi(formPayload, CARTA_READ_ONLY_KEYS);
      }
      if (selected?.id) {
        await staffUpdateCartaCatalogo(selected.id, payload, onLogout);
      } else {
        await staffCreateCartaCatalogo(payload, onLogout);
      }
      setMsg('Carta salvata.');
      setSelected(null);
      setForm(emptyCarta(activeEspansioneId));
      resetCartaImmagineState();
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
    setEspansioneForm(esp ? { ...esp } : emptyEspansione());
    resetEspansioneImmagineState();
    setSelected(null);
    setForm(emptyCarta(esp?.id));
    resetCartaImmagineState();
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
        {['espansioni', 'catalogo', 'bustine', 'keywords', 'combo-reliquiario', 'scambi', 'config'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1 text-sm capitalize ${tab === t ? 'bg-violet-700' : 'bg-gray-800'}`}
          >
            {t === 'combo-reliquiario' ? 'combo reliquiario' : t === 'scambi' ? 'mercato scambi' : t}
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
                onClick={() => { setSelectedEspansione(null); setEspansioneForm(emptyEspansione()); resetEspansioneImmagineState(); }}
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
            <CartaImmagineUpload
              label="Immagine copertina espansione"
              previewUrl={espansionePreviewUrl}
              file={espansioneImmagineFile}
              onFileChange={setEspansioneImmagineFile}
              removeExisting={removeEspansioneImmagine}
              onRemoveExisting={selectedEspansione?.immagine_url ? setRemoveEspansioneImmagine : null}
            />
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
                onClick={() => { setSelected(null); setForm(emptyCarta(activeEspansioneId)); resetCartaImmagineState(); }}
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
                    onClick={() => {
                      setSelected(c);
                      setForm({
                        ...c,
                        bonus_equip: c.bonus_equip && typeof c.bonus_equip === 'object' ? c.bonus_equip : {},
                        statistiche_reliquiario: normalizeCartaStats(c.statistiche_reliquiario),
                        testo_reliquiario: c.testo_reliquiario || '',
                      });
                      resetCartaImmagineState();
                    }}
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
            <CartaImmagineUpload
              label="Immagine arte carta"
              previewUrl={cartaPreviewUrl}
              file={cartaImmagineFile}
              onFileChange={setCartaImmagineFile}
              removeExisting={removeCartaImmagine}
              onRemoveExisting={form.immagine_url ? setRemoveCartaImmagine : null}
            />
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
            <div className="rounded border border-violet-900/50 bg-violet-950/20 p-2">
              <h4 className="mb-2 text-xs font-bold text-violet-300">Statistiche in gioco</h4>
              <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
                {[
                  { key: 'costo_gioco', label: 'Costo gioco', min: 0, max: 3 },
                  { key: 'attacco', label: 'Attacco', min: 0, max: 99 },
                  { key: 'salute', label: 'Salute', min: 0, max: 99 },
                  { key: 'iniziativa', label: 'Iniziativa', min: 0, max: 5 },
                ].map(({ key, label, min, max }) => (
                  <label key={key} className="block text-xs text-gray-400">
                    {label}
                    <input
                      type="number"
                      min={min}
                      max={max}
                      className="mt-0.5 w-full rounded border border-gray-600 bg-gray-900 px-2 py-1 text-sm"
                      value={form[key] ?? ''}
                      onChange={(e) => {
                        const raw = e.target.value;
                        setForm((p) => ({
                          ...p,
                          [key]: raw === '' ? null : Number(raw),
                        }));
                      }}
                    />
                  </label>
                ))}
              </div>
              <p className="mt-1 text-[10px] text-gray-500">
                Costo, Attacco, Salute e Iniziativa compaiono sulle carte PG in duello (icone spada, cuore, cronometro).
              </p>
              <label className="mt-2 flex items-center gap-2 text-xs text-gray-400">
                <input
                  type="checkbox"
                  checked={!!form.duplicabile}
                  onChange={(e) => setForm((p) => ({ ...p, duplicabile: e.target.checked }))}
                />
                Duplicabile nel mazzo (max 2 copie)
              </label>
            </div>
            <BonusEquipEditor
              tipo={form.tipo}
              value={form.bonus_equip}
              onChange={(bonus_equip) => setForm((p) => ({ ...p, bonus_equip }))}
            />
            <div className="rounded border border-violet-900/50 bg-violet-950/20 p-2 space-y-2">
              <h4 className="text-xs font-bold text-violet-300">Testo gioco (Keywords)</h4>
              <textarea
                className="h-36 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm leading-relaxed"
                placeholder="Testo regole in gioco — le Keywords del tab dedicato vengono evidenziate in anteprima"
                value={form.testo_gioco || ''}
                onChange={(e) => setForm((p) => ({ ...p, testo_gioco: e.target.value }))}
              />
              <CardRulesPreview text={form.testo_gioco} keywords={keywords} />
            </div>
            <div className="rounded border border-indigo-900/50 bg-indigo-950/20 p-2 space-y-2">
              <h4 className="text-xs font-bold text-indigo-300">Testo reliquiario (solo se equipaggiata)</h4>
              <p className="text-[10px] text-gray-500">
                Sostituisce il testo gioco nello slot reliquiario del personaggio. Non compare sulla carta in collezione/duello.
              </p>
              <textarea
                className="h-28 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm leading-relaxed"
                placeholder="Effetto passivo nel reliquiario…"
                value={form.testo_reliquiario || ''}
                onChange={(e) => setForm((p) => ({ ...p, testo_reliquiario: e.target.value }))}
              />
              <CardRulesPreview
                text={form.testo_reliquiario}
                keywords={keywords}
                label="Anteprima testo reliquiario"
              />
            </div>
            <StatModInline
              items={form.statistiche_reliquiario || []}
              options={statsOptions}
              auraOptions={auraOptions}
              elementOptions={elementOptions}
              onAdd={() => setForm((p) => ({
                ...p,
                statistiche_reliquiario: [...(p.statistiche_reliquiario || []), {
                  statistica: null,
                  valore: 0,
                  tipo_modificatore: 'ADD',
                  usa_limitazione_aura: false,
                  usa_limitazione_elemento: false,
                  usa_condizione_text: false,
                  condizione_text: '',
                  limit_a_aure: [],
                  limit_a_elementi: [],
                }],
              }))}
              onChange={(i, field, val) => setForm((p) => {
                const next = [...(p.statistiche_reliquiario || [])];
                next[i] = { ...next[i], [field]: val };
                return { ...p, statistiche_reliquiario: next };
              })}
              onRemove={(i) => setForm((p) => ({
                ...p,
                statistiche_reliquiario: (p.statistiche_reliquiario || []).filter((_, idx) => idx !== i),
              }))}
            />
            <div className="rounded border border-gray-700/80 bg-gray-900/40 p-2 space-y-2">
              <h4 className="text-xs font-bold text-gray-300">Testo di lore</h4>
              <textarea
                className="h-44 w-full rounded border border-gray-600 bg-gray-900 p-2 text-sm leading-relaxed"
                placeholder="Flavor, storia, citazioni…"
                value={form.testo_lore || ''}
                onChange={(e) => setForm((p) => ({ ...p, testo_lore: e.target.value }))}
              />
            </div>
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
                    resetCartaImmagineState();
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
            Guida completa in Wiki → <strong>EffectScript v1 — vocabolario</strong> e <strong>Keyword carte — guida master</strong>.
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
            <EffectScriptWizard
              keywordForm={keywordForm}
              setKeywordForm={setKeywordForm}
              effectScriptText={effectScriptText}
              setEffectScriptText={setEffectScriptText}
              onLogout={onLogout}
              onMessage={setMsg}
            />
            {!effectScriptText && (
              <p className="text-[10px] text-gray-500">
                Nessuno script: la keyword resta solo testuale. Usa il wizard per aggiungere effetti automatici in duello.
              </p>
            )}
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

      {!loading && tab === 'combo-reliquiario' && (
        <ComboReliquiarioStaffPanel onLogout={onLogout} carteCatalogo={carte} />
      )}

      {!loading && tab === 'scambi' && (
        <MercatoScambiStaffPanel onLogout={onLogout} />
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
