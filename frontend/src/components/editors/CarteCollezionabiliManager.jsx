import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { CreditCard, ImagePlus, RefreshCw, BookOpen, X } from 'lucide-react';
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
  staffGetCarteTags,
  staffCreateCartaTag,
  staffUpdateCartaTag,
  staffDeleteCartaTag,
  staffGetCarteErrata,
  staffCreateCartaErrata,
  staffUpdateCartaErrata,
  staffDeleteCartaErrata,
  staffGetCartePlatformGioco,
  staffCreateCartePlatformGioco,
  staffUpdateCartePlatformGioco,
  staffBootstrapCartePlatformGioco,
  staffGetCartePlatformTemplates,
  getStaffWikiCarteRegolamentoInfo,
  syncStaffWikiCarteRegolamento,
  resolveMediaUrl,
  getPunteggiList,
} from '../../api';
import { CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../../carte/carteConstants';
import {
  LabeledField,
  StaffFieldGrid,
  StaffModal,
  staffInputClass,
} from '../../staff/StaffCrudUi';
import CartaCatalogoEditModal from './carte/CartaCatalogoEditModal';
import JsonSpecField, { parseJsonObject } from './carte/JsonSpecField';
import ComboReliquiarioStaffPanel from './ComboReliquiarioStaffPanel';
import EffectScriptWizard from './EffectScriptWizard';
import { effectScriptsFromApi, effectScriptsToApi } from './CartaEffectScriptsEditor';
import MercatoScambiStaffPanel from './MercatoScambiStaffPanel';
import MasterGenericList from './MasterGenericList';

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
  tag_ids: [],
  bonus_equip: {},
  effect_scripts_entries: [],
  layout_versione: 'STD',
  legale_duello: true,
  bandita: false,
  ban_reason: '',
  duplicabile: false,
  attiva: true,
  ordine_set: 0,
  studio_template: null,
  studio_carta_spec: {},
  arena_playable_spec: {},
  mse_campi: {},
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
  in_vendita: true,
  vendita_dal: '',
  vendita_al: '',
  legale_duello: true,
  disclaimer_disattiva: '',
  gioco_definizione: null,
  studio_set_spec: {},
  mse_set_riferimento: '',
});

const emptyTag = () => ({
  codice: '',
  nome: '',
  descrizione: '',
  colore: '',
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
  mse_match_pattern: '',
  mse_reminder_template: '',
  mse_export_mode: 'kor35',
});

const emptyErrata = (cartaId = '') => ({
  carta: cartaId || '',
  effective_from: '',
  attiva: true,
  versione: '',
  pubblicata: false,
  pubblicata_at: '',
  pubblicata_nota: '',
  titolo: '',
  descrizione: '',
  testo_gioco_override: '',
  costo_gioco_override: null,
  attacco_override: null,
  salute_override: null,
  iniziativa_override: null,
  effect_scripts_override: [],
  effect_scripts_override_text: '',
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
  const [tags, setTags] = useState([]);
  const [errata, setErrata] = useState([]);
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
  const [tagForm, setTagForm] = useState(emptyTag());
  const [selectedTag, setSelectedTag] = useState(null);
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
  const [cartaModalOpen, setCartaModalOpen] = useState(false);
  const [espansioneModalOpen, setEspansioneModalOpen] = useState(false);
  const [espansioneEditTarget, setEspansioneEditTarget] = useState(null);
  const [bustinaModalOpen, setBustinaModalOpen] = useState(false);
  const [tagModalOpen, setTagModalOpen] = useState(false);
  const [keywordModalOpen, setKeywordModalOpen] = useState(false);
  const [errataModalOpen, setErrataModalOpen] = useState(false);
  const [selectedErrata, setSelectedErrata] = useState(null);
  const [errataForm, setErrataForm] = useState(emptyErrata());
  const [errataCardFilter, setErrataCardFilter] = useState('');
  const [studioTemplates, setStudioTemplates] = useState([]);
  const [platformGiochi, setPlatformGiochi] = useState([]);
  const [espansioneEditTab, setEspansioneEditTab] = useState('catalogo');
  const [platformGiocoForm, setPlatformGiocoForm] = useState({
    slug: '',
    nome: '',
    descrizione: '',
    studio_abilitato: false,
    arena_abilitata: false,
    mse_game_name: '',
  });

  const statsOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'ST'), [punteggi]);
  const auraOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'AU'), [punteggi]);
  const elementOptions = useMemo(() => punteggi.filter((p) => p.tipo === 'EL'), [punteggi]);

  const activeEspansioneId = selectedEspansione?.id || '';
  const gameplayLocked = (config?.accesso_modo || 'OFF') === 'OPEN';

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
      const [esp, cfg, kw, tagRes, errRes, wiki, punt, tmplRes, giocoRes] = await Promise.all([
        staffGetCarteEspansioni(onLogout),
        staffGetCarteConfig(onLogout),
        staffGetCarteKeywords(onLogout),
        staffGetCarteTags(onLogout),
        staffGetCarteErrata(onLogout),
        getStaffWikiCarteRegolamentoInfo(onLogout).catch(() => null),
        getPunteggiList(onLogout).catch(() => []),
        staffGetCartePlatformTemplates(onLogout).catch(() => []),
        staffGetCartePlatformGioco(onLogout).catch(() => []),
      ]);
      const espList = Array.isArray(esp) ? esp : esp?.results || [];
      setEspansioni(espList);
      if (cfg) setConfig(cfg);
      setKeywords(Array.isArray(kw) ? kw : kw?.results || []);
      setTags(Array.isArray(tagRes) ? tagRes : tagRes?.results || []);
      setErrata(Array.isArray(errRes) ? errRes : errRes?.results || []);
      setWikiInfo(wiki);
      setPunteggi(punt || []);
      setStudioTemplates(Array.isArray(tmplRes) ? tmplRes : tmplRes?.results || []);
      const giocoList = Array.isArray(giocoRes) ? giocoRes : giocoRes?.results || [];
      setPlatformGiochi(giocoList);
      if (giocoList[0]) {
        setPlatformGiocoForm({ ...giocoList[0] });
      } else {
        setPlatformGiocoForm({
          slug: '',
          nome: '',
          descrizione: '',
          studio_abilitato: false,
          arena_abilitata: false,
          mse_game_name: '',
        });
      }

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

  const filteredErrata = useMemo(
    () => (errataCardFilter ? errata.filter((e) => e.carta === errataCardFilter) : errata),
    [errata, errataCardFilter],
  );

  const espansioneById = useMemo(
    () => new Map(espansioni.map((e) => [e.id, e])),
    [espansioni],
  );

  const cartaById = useMemo(
    () => new Map(carte.map((c) => [c.id, c])),
    [carte],
  );
  const errataJsonError = useMemo(() => {
    const raw = errataForm.effect_scripts_override_text || '';
    if (!raw.trim()) return '';
    try {
      const parsed = JSON.parse(raw);
      if (!Array.isArray(parsed)) return 'Il JSON deve essere un array.';
      return '';
    } catch {
      return 'JSON non valido in Effect scripts override.';
    }
  }, [errataForm.effect_scripts_override_text]);

  const deleteCarta = async (id) => {
    try {
      await staffDeleteCartaCatalogo(id, onLogout);
      setMsg('Carta eliminata.');
      if (selected?.id === id) {
        setCartaModalOpen(false);
        setSelected(null);
        setForm(emptyCarta(activeEspansioneId));
        resetCartaImmagineState();
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
    }
  };

  const openCartaModal = (c = null) => {
    if (c) {
      setSelected(c);
      setForm({
        ...c,
        bonus_equip: c.bonus_equip && typeof c.bonus_equip === 'object' ? c.bonus_equip : {},
        statistiche_reliquiario: normalizeCartaStats(c.statistiche_reliquiario),
        testo_reliquiario: c.testo_reliquiario || '',
        tag_ids: c.tag_ids || [],
        effect_scripts_entries: effectScriptsFromApi(c.effect_scripts),
        legale_duello: c.legale_duello !== false,
        bandita: !!c.bandita,
        ban_reason: c.ban_reason || '',
        studio_template: c.studio_template || null,
        studio_carta_spec: c.studio_carta_spec && typeof c.studio_carta_spec === 'object' ? c.studio_carta_spec : {},
        arena_playable_spec: c.arena_playable_spec && typeof c.arena_playable_spec === 'object' ? c.arena_playable_spec : {},
        mse_campi: c.mse_campi && typeof c.mse_campi === 'object' ? c.mse_campi : {},
      });
    } else {
      setSelected(null);
      setForm(emptyCarta(activeEspansioneId));
    }
    resetCartaImmagineState();
    setCartaModalOpen(true);
  };

  const saveEspansione = async () => {
    try {
      try {
        parseJsonObject(espansioneForm.studio_set_spec, 'studio_set_spec');
      } catch (e) {
        setMsg(e?.message || 'JSON studio_set_spec non valido.');
        return;
      }
      let payload;
      if (espansioneImmagineFile) {
        payload = buildEspansioneFormData(espansioneForm, espansioneImmagineFile);
      } else if (removeEspansioneImmagine && espansioneEditTarget?.id) {
        payload = { ...stripForApi(espansioneForm, ESPANSIONE_READ_ONLY_KEYS), immagine: null };
      } else {
        payload = stripForApi(espansioneForm, ESPANSIONE_READ_ONLY_KEYS);
      }
      if (espansioneEditTarget?.id) {
        await staffUpdateCartaEspansione(espansioneEditTarget.id, payload, onLogout);
      } else {
        await staffCreateCartaEspansione(payload, onLogout);
      }
      setMsg('Espansione salvata.');
      setEspansioneModalOpen(false);
      setEspansioneEditTarget(null);
      setEspansioneForm(emptyEspansione());
      resetEspansioneImmagineState();
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio espansione fallito.');
    }
  };

  const openEspansioneModal = (e = null) => {
    setEspansioneEditTarget(e);
    setEspansioneForm(e ? {
      ...e,
      studio_set_spec: e.studio_set_spec && typeof e.studio_set_spec === 'object' ? e.studio_set_spec : {},
      gioco_definizione: e.gioco_definizione || null,
      mse_set_riferimento: e.mse_set_riferimento || '',
    } : emptyEspansione());
    setEspansioneEditTab('catalogo');
    resetEspansioneImmagineState();
    setEspansioneModalOpen(true);
  };

  const deleteEspansione = async (id) => {
    try {
      await staffDeleteCartaEspansione(id, onLogout);
      setMsg('Espansione eliminata.');
      if (selectedEspansione?.id === id) {
        setEspansioneModalOpen(false);
        selectEspansione(null);
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
    }
  };

  const saveCarta = async () => {
    try {
      let effect_scripts;
      try {
        effect_scripts = effectScriptsToApi(form.effect_scripts_entries || []);
      } catch (e) {
        setMsg(e?.message || 'EffectScript carta: JSON non valido.');
        return;
      }
      try {
        parseJsonObject(form.studio_carta_spec, 'studio_carta_spec');
        parseJsonObject(form.arena_playable_spec, 'arena_playable_spec');
        parseJsonObject(form.mse_campi, 'mse_campi');
      } catch (e) {
        setMsg(e?.message || 'JSON tab Avanzato non valido.');
        return;
      }
      let payload;
      const formPayload = {
        ...form,
        statistiche_reliquiario: normalizeCartaStats(form.statistiche_reliquiario),
        effect_scripts,
      };
      delete formPayload.effect_scripts_entries;
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
      setCartaModalOpen(false);
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
      setBustinaModalOpen(false);
      setSelectedBustina(null);
      setBustinaForm(emptyBustina(activeEspansioneId));
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio fallito.');
    }
  };

  const openBustinaModal = (b = null) => {
    setSelectedBustina(b);
    setBustinaForm(b ? { ...b } : emptyBustina(activeEspansioneId));
    setBustinaModalOpen(true);
  };

  const deleteBustina = async (id) => {
    try {
      await staffDeleteCartaBustina(id, onLogout);
      setMsg('Bustina eliminata.');
      if (selectedBustina?.id === id) {
        setBustinaModalOpen(false);
        setSelectedBustina(null);
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
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
      setKeywordModalOpen(false);
      setSelectedKeyword(null);
      setKeywordForm(emptyKeyword());
      setEffectScriptText('');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio keyword fallito.');
    }
  };

  const openKeywordModal = (k = null) => {
    setSelectedKeyword(k);
    setKeywordForm(k ? {
      ...k,
      mse_match_pattern: k.mse_match_pattern || '',
      mse_reminder_template: k.mse_reminder_template || '',
      mse_export_mode: k.mse_export_mode || 'kor35',
    } : emptyKeyword());
    setEffectScriptText(k ? formatEffectScriptText(k.effect_script) : '');
    setKeywordModalOpen(true);
  };

  const deleteKeyword = async (id) => {
    try {
      await staffDeleteCartaKeyword(id, onLogout);
      setMsg('Keyword eliminata.');
      if (selectedKeyword?.id === id) {
        setKeywordModalOpen(false);
        setSelectedKeyword(null);
        setKeywordForm(emptyKeyword());
        setEffectScriptText('');
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione fallita.');
    }
  };

  const saveTag = async () => {
    try {
      const payload = { ...tagForm };
      if (selectedTag?.id) {
        await staffUpdateCartaTag(selectedTag.id, payload, onLogout);
      } else {
        await staffCreateCartaTag(payload, onLogout);
      }
      setMsg('Tag salvato.');
      setTagModalOpen(false);
      setSelectedTag(null);
      setTagForm(emptyTag());
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio tag fallito.');
    }
  };

  const openTagModal = (t = null) => {
    setSelectedTag(t);
    setTagForm(t ? { ...t } : emptyTag());
    setTagModalOpen(true);
  };

  const deleteTag = async (id) => {
    try {
      await staffDeleteCartaTag(id, onLogout);
      setMsg('Tag eliminato.');
      if (selectedTag?.id === id) {
        setTagModalOpen(false);
        setSelectedTag(null);
        setTagForm(emptyTag());
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione tag fallita.');
    }
  };

  const openErrataModal = (row = null) => {
    setSelectedErrata(row);
    setErrataForm(
      row
        ? {
          ...row,
          effect_scripts_override_text: row.effect_scripts_override?.length
            ? JSON.stringify(row.effect_scripts_override, null, 2)
            : '',
        }
        : emptyErrata(selected?.id || ''),
    );
    setErrataModalOpen(true);
  };

  const saveErrata = async () => {
    if (errataJsonError) {
      setMsg(errataJsonError);
      return;
    }
    try {
      const payload = { ...errataForm };
      if (payload.effect_scripts_override_text?.trim()) {
        payload.effect_scripts_override = JSON.parse(payload.effect_scripts_override_text);
      } else {
        payload.effect_scripts_override = [];
      }
      delete payload.effect_scripts_override_text;
      if (selectedErrata?.id) {
        await staffUpdateCartaErrata(selectedErrata.id, payload, onLogout);
      } else {
        await staffCreateCartaErrata(payload, onLogout);
      }
      setMsg('Errata salvata.');
      setErrataModalOpen(false);
      setSelectedErrata(null);
      setErrataForm(emptyErrata());
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio errata fallito.');
    }
  };

  const deleteErrata = async (id) => {
    try {
      await staffDeleteCartaErrata(id, onLogout);
      setMsg('Errata eliminata.');
      if (selectedErrata?.id === id) {
        setErrataModalOpen(false);
        setSelectedErrata(null);
        setErrataForm(emptyErrata());
      }
      await load();
    } catch (e) {
      setMsg(e?.message || 'Eliminazione errata fallita.');
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
    setEspansioneForm(esp ? {
      ...esp,
      studio_set_spec: esp.studio_set_spec && typeof esp.studio_set_spec === 'object' ? esp.studio_set_spec : {},
      gioco_definizione: esp.gioco_definizione || null,
      mse_set_riferimento: esp.mse_set_riferimento || '',
    } : emptyEspansione());
    resetEspansioneImmagineState();
    setSelected(null);
    setForm(emptyCarta(esp?.id));
    resetCartaImmagineState();
    setSelectedBustina(null);
    setBustinaForm(emptyBustina(esp?.id));
  };

  const savePlatformGioco = async () => {
    try {
      const payload = {
        slug: platformGiocoForm.slug,
        nome: platformGiocoForm.nome,
        descrizione: platformGiocoForm.descrizione || '',
        studio_abilitato: !!platformGiocoForm.studio_abilitato,
        arena_abilitata: !!platformGiocoForm.arena_abilitata,
        mse_game_name: platformGiocoForm.mse_game_name || '',
        meta: platformGiocoForm.meta && typeof platformGiocoForm.meta === 'object' ? platformGiocoForm.meta : {},
      };
      if (platformGiocoForm.id) {
        await staffUpdateCartePlatformGioco(platformGiocoForm.id, payload, onLogout);
      } else {
        await staffCreateCartePlatformGioco(payload, onLogout);
      }
      setMsg('Definizione gioco platform salvata.');
      await load();
    } catch (e) {
      setMsg(e?.message || 'Salvataggio platform fallito.');
    }
  };

  const bootstrapPlatformGioco = async () => {
    if (!platformGiocoForm.id) {
      setMsg('Salva prima la definizione gioco.');
      return;
    }
    try {
      const res = await staffBootstrapCartePlatformGioco(platformGiocoForm.id, onLogout);
      setMsg(`Bootstrap: creati ${(res?.created || []).join(', ') || 'nessun elemento nuovo'}.`);
      await load();
    } catch (e) {
      setMsg(e?.message || 'Bootstrap platform fallito.');
    }
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
        {['espansioni', 'catalogo', 'bustine', 'tags', 'keywords', 'errata', 'combo-reliquiario', 'scambi', 'platform', 'config'].map((t) => (
          <button
            key={t}
            type="button"
            onClick={() => setTab(t)}
            className={`rounded px-3 py-1 text-sm capitalize ${tab === t ? 'bg-violet-700' : 'bg-gray-800'}`}
          >
            {t === 'combo-reliquiario' ? 'combo reliquiario' : t === 'scambi' ? 'mercato scambi' : t === 'platform' ? 'platform' : t}
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
        <MasterGenericList
          title="Espansioni"
          items={espansioni}
          fill={false}
          persistKey="staff-carte-espansioni"
          addLabel="Nuova espansione"
          emptyMessage="Nessuna espansione."
          getItemLabel={(e) => e.nome}
          onAdd={() => openEspansioneModal(null)}
          onEdit={openEspansioneModal}
          onDelete={deleteEspansione}
          extraRowActions={(e) => (
            <button
              type="button"
              className="px-2 py-1 text-[10px] font-bold uppercase text-violet-300 hover:text-white"
              onClick={() => { selectEspansione(e); setTab('catalogo'); }}
            >
              Filtra catalogo
            </button>
          )}
          filterConfig={[
            {
              key: 'attiva',
              label: 'Attiva',
              options: [{ id: true, label: 'Attive' }, { id: false, label: 'Disattive' }],
              match: (item, values) => values.some((v) => !!item.attiva === v),
            },
          ]}
          columns={[
            { key: 'nome', header: 'Nome', getSortValue: (e) => e.nome || '', render: (e) => <span className="font-bold text-white">{e.nome}</span> },
            { key: 'slug', header: 'Slug', getSortValue: (e) => e.slug || '', render: (e) => <span className="font-mono text-xs text-gray-400">{e.slug}</span> },
            { key: 'carte', header: 'Carte', getSortValue: (e) => e.carte_count ?? 0, render: (e) => e.carte_count ?? 0, align: 'center', width: 80 },
            { key: 'bustine', header: 'Bustine', getSortValue: (e) => e.bustine_count ?? 0, render: (e) => e.bustine_count ?? 0, align: 'center', width: 90 },
            {
              key: 'attiva',
              header: 'Attiva',
              getSortValue: (e) => (e.attiva ? 1 : 0),
              getFilterValue: (e) => (e.attiva ? 'Sì' : 'No'),
              render: (e) => (e.attiva ? 'Sì' : 'No'),
              align: 'center',
              width: 80,
            },
            {
              key: 'vendita',
              header: 'Vendita',
              getSortValue: (e) => (e.in_vendita === false ? 0 : 1),
              getFilterValue: (e) => (e.in_vendita === false ? 'Fuori vendita' : 'In vendita'),
              render: (e) => (e.in_vendita === false ? 'Fuori vendita' : 'In vendita'),
              width: 120,
            },
          ]}
        />
      )}

      <StaffModal
        open={espansioneModalOpen}
        title={espansioneEditTarget?.id ? `Modifica espansione — ${espansioneForm.nome}` : 'Nuova espansione'}
        onClose={() => setEspansioneModalOpen(false)}
        onSave={saveEspansione}
      >
        <div className="mb-3 flex flex-wrap gap-2 border-b border-gray-700 pb-2">
          {[
            { id: 'catalogo', label: 'Catalogo' },
            { id: 'avanzato', label: 'Avanzato (Studio)' },
          ].map(({ id, label }) => (
            <button
              key={id}
              type="button"
              onClick={() => setEspansioneEditTab(id)}
              className={`rounded px-3 py-1 text-xs ${
                espansioneEditTab === id ? 'bg-violet-700 text-white' : 'bg-gray-800 text-gray-300'
              }`}
            >
              {label}
            </button>
          ))}
        </div>
        {espansioneEditTab === 'avanzato' ? (
          <div className="space-y-3">
            <LabeledField
              label="Definizione gioco platform"
              hint="Collega l'espansione al container Card Studio / Arena (tab Platform)."
            >
              <select
                className={staffInputClass()}
                value={espansioneForm.gioco_definizione || ''}
                onChange={(ev) => setEspansioneForm((p) => ({
                  ...p,
                  gioco_definizione: ev.target.value || null,
                }))}
              >
                <option value="">— Nessuna —</option>
                {platformGiochi.map((g) => (
                  <option key={g.id} value={g.id}>{g.nome} ({g.slug})</option>
                ))}
              </select>
            </LabeledField>
            <LabeledField label="Riferimento MSE set" hint="Path o id package .mse-set.">
              <input
                className={staffInputClass('font-mono')}
                value={espansioneForm.mse_set_riferimento || ''}
                onChange={(ev) => setEspansioneForm((p) => ({ ...p, mse_set_riferimento: ev.target.value }))}
              />
            </LabeledField>
            <JsonSpecField
              label="studio_set_spec (JSON)"
              hint="Metadati set Card Studio (studio_set_spec_v1)."
              value={espansioneForm.studio_set_spec}
              onChange={(studio_set_spec) => setEspansioneForm((p) => ({ ...p, studio_set_spec }))}
            />
          </div>
        ) : (
        <div className="space-y-3">
          <LabeledField label="Nome" required>
            <input
              className={staffInputClass()}
              value={espansioneForm.nome || ''}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, nome: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Slug" required hint="Identificatore URL univoco (es. caduta-del-consiglio).">
            <input
              className={staffInputClass('font-mono')}
              value={espansioneForm.slug || ''}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, slug: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Descrizione">
            <textarea
              className={staffInputClass('min-h-[80px]')}
              value={espansioneForm.descrizione || ''}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, descrizione: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Ordine menu">
            <input
              type="number"
              className={staffInputClass()}
              value={espansioneForm.ordine}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, ordine: Number(ev.target.value) }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!espansioneForm.attiva}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, attiva: ev.target.checked }))}
            />
            Espansione attiva
          </label>
          {!espansioneForm.attiva && (
            <p className="rounded border border-amber-700/60 bg-amber-950/30 px-2 py-1 text-xs text-amber-200">
              Attenzione: disattivando l'espansione, le carte non saranno più disponibili ai giocatori.
            </p>
          )}
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={espansioneForm.in_vendita !== false}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, in_vendita: ev.target.checked }))}
            />
            Espansione in vendita (acquisto bustine)
          </label>
          <StaffFieldGrid>
            <LabeledField label="Vendita dal">
              <input
                type="datetime-local"
                className={staffInputClass()}
                value={espansioneForm.vendita_dal ? String(espansioneForm.vendita_dal).slice(0, 16) : ''}
                onChange={(ev) => setEspansioneForm((p) => ({ ...p, vendita_dal: ev.target.value || null }))}
              />
            </LabeledField>
            <LabeledField label="Vendita al">
              <input
                type="datetime-local"
                className={staffInputClass()}
                value={espansioneForm.vendita_al ? String(espansioneForm.vendita_al).slice(0, 16) : ''}
                onChange={(ev) => setEspansioneForm((p) => ({ ...p, vendita_al: ev.target.value || null }))}
              />
            </LabeledField>
          </StaffFieldGrid>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={espansioneForm.legale_duello !== false}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, legale_duello: ev.target.checked }))}
            />
            Espansione legale nei duelli
          </label>
          <LabeledField
            label="Disclaimer disattivazione (staff)"
            hint="Mostrato in staff per ricordare l'impatto della disattivazione."
          >
            <textarea
              className={staffInputClass('min-h-[72px]')}
              value={espansioneForm.disclaimer_disattiva || ''}
              onChange={(ev) => setEspansioneForm((p) => ({ ...p, disclaimer_disattiva: ev.target.value }))}
            />
          </LabeledField>
          <CartaImmagineUpload
            label="Copertina espansione"
            previewUrl={espansionePreviewUrl}
            file={espansioneImmagineFile}
            onFileChange={setEspansioneImmagineFile}
            removeExisting={removeEspansioneImmagine}
            onRemoveExisting={espansioneEditTarget?.immagine_url ? setRemoveEspansioneImmagine : null}
          />
        </div>
        )}
      </StaffModal>

      {!loading && tab === 'catalogo' && (
        <MasterGenericList
          title="Catalogo carte"
          items={carte}
          fill={false}
          persistKey="staff-carte-catalogo"
          addLabel="Nuova carta"
          emptyMessage="Nessuna carta in catalogo."
          searchPlaceholder="Cerca nome, codice, set…"
          getSearchText={(c) => [c.nome, c.codice, c.espansione_nome, c.set_collezione, c.legame_id, ...(c.tag_codici || [])].filter(Boolean).join(' ')}
          getItemLabel={(c) => `${c.nome} (${c.codice})`}
          onAdd={() => openCartaModal(null)}
          onEdit={openCartaModal}
          onDelete={deleteCarta}
          filterConfig={[
            {
              key: 'tipo',
              label: 'Tipo',
              options: Object.entries(CARTA_TIPO_LABEL).map(([id, label]) => ({ id, label })),
            },
            {
              key: 'rarita',
              label: 'Rarità',
              options: Object.entries(CARTA_RARITA_LABEL).map(([id, label]) => ({ id, label })),
            },
            {
              key: 'attiva',
              label: 'Attiva',
              options: [{ id: true, label: 'Attive' }, { id: false, label: 'Disattive' }],
              match: (item, values) => values.some((v) => !!item.attiva === v),
            },
          ]}
          columns={[
            { key: 'nome', header: 'Nome', getSortValue: (c) => c.nome || '', render: (c) => <span className="font-bold text-white">{c.nome}</span> },
            { key: 'codice', header: 'Codice', getSortValue: (c) => c.codice || '', render: (c) => <span className="font-mono text-xs">{c.codice}</span> },
            { key: 'tipo', header: 'Tipo', getSortValue: (c) => CARTA_TIPO_LABEL[c.tipo] || c.tipo, render: (c) => CARTA_TIPO_LABEL[c.tipo] || c.tipo, width: 110 },
            { key: 'rarita', header: 'Rarità', getSortValue: (c) => CARTA_RARITA_LABEL[c.rarita] || c.rarita, render: (c) => CARTA_RARITA_LABEL[c.rarita] || c.rarita, width: 110 },
            { key: 'espansione', header: 'Espansione', getSortValue: (c) => c.espansione_nome || '', render: (c) => c.espansione_nome || '—' },
            { key: 'set', header: 'Set', getSortValue: (c) => c.set_collezione || '', render: (c) => c.set_collezione || '—' },
            {
              key: 'stato',
              header: 'Stato',
              getSortValue: (c) => [c.attiva ? 'a' : 'z', c.bandita ? 'b' : '', c.legale_duello === false ? 'n' : ''].join(),
              getFilterValue: (c) => [!c.attiva && 'disattiva', c.bandita && 'bandita', c.legale_duello === false && 'non legale'].filter(Boolean).join(' ') || 'ok',
              render: (c) => (
                <span className="text-xs text-gray-400">
                  {!c.attiva && <span className="text-amber-500">disattiva </span>}
                  {c.bandita && <span className="text-red-400">bandita </span>}
                  {c.legale_duello === false && <span className="text-orange-400">non legale</span>}
                  {c.attiva && !c.bandita && c.legale_duello !== false && '—'}
                </span>
              ),
            },
          ]}
        />
      )}

      <CartaCatalogoEditModal
        open={cartaModalOpen}
        isEdit={!!selected?.id}
        form={form}
        setForm={setForm}
        onClose={() => setCartaModalOpen(false)}
        onSave={saveCarta}
        espansioni={espansioni}
        tags={tags}
        keywords={keywords}
        statsOptions={statsOptions}
        auraOptions={auraOptions}
        elementOptions={elementOptions}
        punteggi={punteggi}
        cartaPreviewUrl={cartaPreviewUrl}
        cartaImmagineFile={cartaImmagineFile}
        onCartaImmagineChange={setCartaImmagineFile}
        removeCartaImmagine={removeCartaImmagine}
        onRemoveCartaImmagine={setRemoveCartaImmagine}
        onMessage={setMsg}
        gameplayLocked={gameplayLocked}
        studioTemplates={studioTemplates}
      />

      {!loading && tab === 'platform' && (
        <div className="max-w-xl space-y-4">
          <p className="text-xs text-gray-400">
            Configurazione Card Studio / Card Arena per la campagna attiva. Documentazione: docs/card-platform/.
          </p>
          <StaffFieldGrid>
            <LabeledField label="Slug gioco" required>
              <input
                className={staffInputClass('font-mono')}
                value={platformGiocoForm.slug || ''}
                onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, slug: e.target.value }))}
              />
            </LabeledField>
            <LabeledField label="Nome gioco" required>
              <input
                className={staffInputClass()}
                value={platformGiocoForm.nome || ''}
                onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, nome: e.target.value }))}
              />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Descrizione">
            <textarea
              className={staffInputClass('min-h-[72px]')}
              value={platformGiocoForm.descrizione || ''}
              onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, descrizione: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Nome MSE game (export)">
            <input
              className={staffInputClass()}
              value={platformGiocoForm.mse_game_name || ''}
              onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, mse_game_name: e.target.value }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!platformGiocoForm.studio_abilitato}
              onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, studio_abilitato: e.target.checked }))}
            />
            Card Studio abilitato
          </label>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!platformGiocoForm.arena_abilitata}
              onChange={(e) => setPlatformGiocoForm((p) => ({ ...p, arena_abilitata: e.target.checked }))}
            />
            Card Arena abilitata
          </label>
          <div className="flex flex-wrap gap-2">
            <button
              type="button"
              className="rounded bg-violet-700 px-3 py-1 text-sm hover:bg-violet-600"
              onClick={savePlatformGioco}
            >
              Salva definizione gioco
            </button>
            {platformGiocoForm.id && (
              <button
                type="button"
                className="rounded bg-gray-700 px-3 py-1 text-sm hover:bg-gray-600"
                onClick={bootstrapPlatformGioco}
              >
                Bootstrap template + ruleset
              </button>
            )}
          </div>
          {studioTemplates.length > 0 && (
            <div>
              <h4 className="mb-2 text-xs font-bold uppercase text-violet-300">Template Studio</h4>
              <ul className="space-y-1 text-sm text-gray-300">
                {studioTemplates.map((t) => (
                  <li key={t.id}>
                    {t.nome} <span className="font-mono text-xs text-gray-500">({t.slug})</span>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}

      {!loading && tab === 'bustine' && (
        <MasterGenericList
          title="Bustine"
          items={bustine}
          fill={false}
          persistKey="staff-carte-bustine"
          addLabel="Nuova bustina"
          emptyMessage="Nessuna bustina."
          getItemLabel={(b) => b.nome}
          onAdd={() => openBustinaModal(null)}
          onEdit={openBustinaModal}
          onDelete={deleteBustina}
          filterConfig={[
            {
              key: 'espansione',
              label: 'Espansione',
              options: [
                { id: '__none__', label: 'Senza espansione' },
                ...espansioni.map((e) => ({ id: e.id, label: e.nome })),
              ],
              match: (item, values) =>
                values.some((v) => (v === '__none__' ? !item.espansione : String(item.espansione) === String(v))),
            },
          ]}
          columns={[
            { key: 'nome', header: 'Nome', getSortValue: (b) => b.nome || '', render: (b) => <span className="font-bold">{b.nome}</span> },
            {
              key: 'espansione',
              header: 'Espansione',
              getSortValue: (b) => espansioneById.get(b.espansione)?.nome || '',
              render: (b) => espansioneById.get(b.espansione)?.nome || 'Senza espansione',
            },
            { key: 'costo', header: 'Costo CR', getSortValue: (b) => Number(b.costo_crediti || 0), render: (b) => b.costo_crediti, align: 'right', width: 100 },
            { key: 'carte', header: 'Carte', getSortValue: (b) => b.carte_per_bustina ?? 0, render: (b) => b.carte_per_bustina, align: 'center', width: 80 },
            { key: 'set', header: 'Set', getSortValue: (b) => b.set_collezione || '', render: (b) => b.set_collezione || '—' },
          ]}
        />
      )}

      <StaffModal
        open={bustinaModalOpen}
        title={selectedBustina?.id ? `Modifica bustina — ${bustinaForm.nome}` : 'Nuova bustina'}
        onClose={() => setBustinaModalOpen(false)}
        onSave={saveBustina}
      >
        <div className="space-y-3">
          <LabeledField label="Espansione">
            <select
              className={staffInputClass()}
              value={bustinaForm.espansione || ''}
              onChange={(e) => setBustinaForm((p) => ({ ...p, espansione: e.target.value || null }))}
            >
              <option value="">— Nessuna —</option>
              {espansioni.map((e) => (
                <option key={e.id} value={e.id}>{e.nome}</option>
              ))}
            </select>
          </LabeledField>
          <LabeledField label="Nome" required>
            <input
              className={staffInputClass()}
              value={bustinaForm.nome || ''}
              onChange={(e) => setBustinaForm((p) => ({ ...p, nome: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Descrizione">
            <textarea
              className={staffInputClass('min-h-[72px]')}
              value={bustinaForm.descrizione || ''}
              onChange={(e) => setBustinaForm((p) => ({ ...p, descrizione: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Set cronaca (legacy)" hint="Filtra carte eleggibili per set narrativo.">
            <input
              className={staffInputClass()}
              value={bustinaForm.set_collezione || ''}
              onChange={(e) => setBustinaForm((p) => ({ ...p, set_collezione: e.target.value }))}
            />
          </LabeledField>
          <StaffFieldGrid>
            <LabeledField label="Costo (CR)">
              <input
                type="number"
                className={staffInputClass()}
                value={bustinaForm.costo_crediti}
                onChange={(e) => setBustinaForm((p) => ({ ...p, costo_crediti: e.target.value }))}
              />
            </LabeledField>
            <LabeledField label="Carte per bustina">
              <input
                type="number"
                className={staffInputClass()}
                value={bustinaForm.carte_per_bustina}
                onChange={(e) => setBustinaForm((p) => ({ ...p, carte_per_bustina: Number(e.target.value) }))}
              />
            </LabeledField>
          </StaffFieldGrid>
        </div>
      </StaffModal>

      {!loading && tab === 'tags' && (
        <div>
          <p className="mb-3 text-xs text-gray-500">
            I <strong>tag</strong> sono etichette meccaniche assegnate dal catalogo (non si cercano nel testo).
            Le keyword e gli EffectScript carta possono usarli per buff, distruzione o filtri.
          </p>
          <MasterGenericList
            title="Tag meccanici"
            items={tags}
            fill={false}
            persistKey="staff-carte-tags"
            addLabel="Nuovo tag"
            emptyMessage="Nessun tag."
            getItemLabel={(t) => t.nome}
            onAdd={() => openTagModal(null)}
            onEdit={openTagModal}
            onDelete={deleteTag}
            columns={[
              { key: 'nome', header: 'Nome', getSortValue: (t) => t.nome || '', render: (t) => <span className="font-bold">{t.nome}</span> },
              { key: 'codice', header: 'Codice', getSortValue: (t) => t.codice || '', render: (t) => <span className="font-mono text-xs">{t.codice}</span> },
              { key: 'colore', header: 'Colore', getSortValue: (t) => t.colore || '', render: (t) => t.colore || '—' },
              {
                key: 'attiva',
                header: 'Attivo',
                getSortValue: (t) => (t.attiva ? 1 : 0),
                getFilterValue: (t) => (t.attiva ? 'Sì' : 'No'),
                render: (t) => (t.attiva ? 'Sì' : 'No'),
                align: 'center',
                width: 80,
              },
            ]}
          />
        </div>
      )}

      <StaffModal
        open={tagModalOpen}
        title={selectedTag?.id ? `Modifica tag — ${tagForm.nome}` : 'Nuovo tag'}
        onClose={() => setTagModalOpen(false)}
        onSave={saveTag}
      >
        <div className="space-y-3">
          <LabeledField label="Codice" required hint="Es. CAVALIERE — univoco per campagna.">
            <input
              className={staffInputClass('font-mono uppercase')}
              value={tagForm.codice}
              onChange={(e) => setTagForm((p) => ({ ...p, codice: e.target.value.toUpperCase() }))}
            />
          </LabeledField>
          <LabeledField label="Nome" required>
            <input
              className={staffInputClass()}
              value={tagForm.nome}
              onChange={(e) => setTagForm((p) => ({ ...p, nome: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Descrizione">
            <textarea
              className={staffInputClass('min-h-[72px]')}
              rows={3}
              value={tagForm.descrizione || ''}
              onChange={(e) => setTagForm((p) => ({ ...p, descrizione: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Colore UI" hint="Es. #c9a227 per glossario.">
            <input
              className={staffInputClass('font-mono')}
              value={tagForm.colore || ''}
              onChange={(e) => setTagForm((p) => ({ ...p, colore: e.target.value }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={tagForm.attiva !== false}
              onChange={(e) => setTagForm((p) => ({ ...p, attiva: e.target.checked }))}
            />
            Tag attivo
          </label>
        </div>
      </StaffModal>

      {!loading && tab === 'keywords' && (
        <div>
          <p className="mb-3 text-xs text-gray-500">
            Placeholder <code className="text-violet-300">[X]</code> nel nome e nel testo regola.
            Wiki: <strong>EffectScript v1</strong> e <strong>Keyword carte — guida master</strong>.
          </p>
          <MasterGenericList
            title="Keyword condivise"
            items={keywords}
            fill={false}
            persistKey="staff-carte-keywords"
            addLabel="Nuova keyword"
            emptyMessage="Nessuna keyword."
            getItemLabel={(k) => k.nome}
            onAdd={() => openKeywordModal(null)}
            onEdit={openKeywordModal}
            onDelete={deleteKeyword}
            columns={[
              { key: 'nome', header: 'Nome', getSortValue: (k) => k.nome || '', render: (k) => <span className="font-bold">{k.nome}</span> },
              { key: 'codice', header: 'Codice', getSortValue: (k) => k.codice || '', render: (k) => <span className="font-mono text-xs">{k.codice}</span> },
              { key: 'priorita', header: 'Priorità', getSortValue: (k) => k.priorita ?? 0, render: (k) => k.priorita ?? 0, align: 'center', width: 90 },
              {
                key: 'script',
                header: 'EffectScript',
                getSortValue: (k) => (k.effect_script && Object.keys(k.effect_script).length ? 1 : 0),
                getFilterValue: (k) => (k.effect_script && Object.keys(k.effect_script).length ? 'Sì' : 'No'),
                render: (k) => (k.effect_script && Object.keys(k.effect_script).length ? 'Sì' : '—'),
                align: 'center',
                width: 110,
              },
              {
                key: 'attiva',
                header: 'Attiva',
                getSortValue: (k) => (k.attiva ? 1 : 0),
                getFilterValue: (k) => (k.attiva ? 'Sì' : 'No'),
                render: (k) => (k.attiva ? 'Sì' : 'No'),
                align: 'center',
                width: 80,
              },
            ]}
          />
        </div>
      )}

      <StaffModal
        open={keywordModalOpen}
        wide
        title={selectedKeyword?.id ? `Modifica keyword — ${keywordForm.nome}` : 'Nuova keyword'}
        onClose={() => setKeywordModalOpen(false)}
        onSave={saveKeyword}
      >
        <div className="space-y-3">
          <StaffFieldGrid>
            <LabeledField label="Codice" required>
              <input
                className={staffInputClass('font-mono uppercase')}
                value={keywordForm.codice}
                onChange={(e) => setKeywordForm((p) => ({ ...p, codice: e.target.value.toUpperCase() }))}
              />
            </LabeledField>
            <LabeledField label="Priorità match" hint="Più alto = preferito su overlap.">
              <input
                type="number"
                className={staffInputClass()}
                value={keywordForm.priorita}
                onChange={(e) => setKeywordForm((p) => ({ ...p, priorita: Number(e.target.value) }))}
              />
            </LabeledField>
          </StaffFieldGrid>
          <LabeledField label="Nome (nel testo carta)" required hint='Es. Mutazione [X] o Evocazione'>
            <input
              className={staffInputClass()}
              value={keywordForm.nome}
              onChange={(e) => setKeywordForm((p) => ({ ...p, nome: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Testo regola completo" hint="Mostrato al tap; stessi [X] del nome.">
            <textarea
              className={staffInputClass('min-h-[96px]')}
              value={keywordForm.testo_regola}
              onChange={(e) => setKeywordForm((p) => ({ ...p, testo_regola: e.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Reminder breve">
            <input
              className={staffInputClass()}
              value={keywordForm.reminder_breve}
              onChange={(e) => setKeywordForm((p) => ({ ...p, reminder_breve: e.target.value }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={keywordForm.attiva !== false}
              onChange={(e) => setKeywordForm((p) => ({ ...p, attiva: e.target.checked }))}
            />
            Keyword attiva
          </label>
          <EffectScriptWizard
            keywordForm={keywordForm}
            setKeywordForm={setKeywordForm}
            effectScriptText={effectScriptText}
            setEffectScriptText={setEffectScriptText}
            onLogout={onLogout}
            onMessage={setMsg}
          />
          <div className="rounded border border-gray-700 bg-gray-900/40 p-3">
            <p className="mb-2 text-xs font-bold uppercase tracking-wide text-violet-300">Export MSE (avanzato)</p>
            <LabeledField label="Modalità export">
              <select
                className={staffInputClass()}
                value={keywordForm.mse_export_mode || 'kor35'}
                onChange={(e) => setKeywordForm((p) => ({ ...p, mse_export_mode: e.target.value }))}
              >
                <option value="kor35">Solo KOR35</option>
                <option value="mse_compat">Compatibile MSE</option>
                <option value="both">KOR35 + MSE</option>
              </select>
            </LabeledField>
            <LabeledField label="Pattern match MSE">
              <input
                className={staffInputClass('font-mono')}
                value={keywordForm.mse_match_pattern || ''}
                onChange={(e) => setKeywordForm((p) => ({ ...p, mse_match_pattern: e.target.value }))}
              />
            </LabeledField>
            <LabeledField label="Template reminder MSE">
              <textarea
                className={staffInputClass('min-h-[72px]')}
                value={keywordForm.mse_reminder_template || ''}
                onChange={(e) => setKeywordForm((p) => ({ ...p, mse_reminder_template: e.target.value }))}
              />
            </LabeledField>
          </div>
        </div>
      </StaffModal>

      {!loading && tab === 'errata' && (
        <div>
          <div className="mb-2 max-w-sm">
            <LabeledField label="Filtro carta">
              <select
                className={staffInputClass()}
                value={errataCardFilter}
                onChange={(e) => setErrataCardFilter(e.target.value)}
              >
                <option value="">— Tutte le carte —</option>
                {carte.map((c) => (
                  <option key={c.id} value={c.id}>{c.nome} ({c.codice})</option>
                ))}
              </select>
            </LabeledField>
          </div>
          <MasterGenericList
            title="Errata carte"
            items={filteredErrata}
            fill={false}
            persistKey="staff-carte-errata"
            addLabel="Nuova errata"
            emptyMessage="Nessuna errata."
            getItemLabel={(e) => e.titolo || `Errata ${e.id}`}
            onAdd={() => openErrataModal(null)}
            onEdit={openErrataModal}
            onDelete={deleteErrata}
            columns={[
              { key: 'titolo', header: 'Titolo', getSortValue: (e) => e.titolo || '', render: (e) => <span className="font-bold text-white">{e.titolo || 'Senza titolo'}</span> },
              {
                key: 'carta',
                header: 'Carta',
                getSortValue: (e) => cartaById.get(e.carta)?.nome || '',
                render: (e) => cartaById.get(e.carta)?.nome || e.carta,
              },
              { key: 'da', header: 'Effettiva da', getSortValue: (e) => e.effective_from || '', render: (e) => e.effective_from || '—' },
              { key: 'versione', header: 'Versione', getSortValue: (e) => e.versione || '', render: (e) => e.versione || '—' },
              {
                key: 'attiva',
                header: 'Attiva',
                getSortValue: (e) => (e.attiva ? 1 : 0),
                getFilterValue: (e) => (e.attiva ? 'Sì' : 'No'),
                render: (e) => (e.attiva ? 'Sì' : 'No'),
                align: 'center',
                width: 80,
              },
              {
                key: 'pubblicata',
                header: 'Pubblicata',
                getSortValue: (e) => (e.pubblicata ? 1 : 0),
                getFilterValue: (e) => (e.pubblicata ? 'Sì' : 'No'),
                render: (e) => (e.pubblicata ? 'Sì' : '—'),
                align: 'center',
                width: 100,
              },
            ]}
          />
        </div>
      )}

      <StaffModal
        open={errataModalOpen}
        title={selectedErrata?.id ? `Modifica errata — ${errataForm.titolo || ''}` : 'Nuova errata carta'}
        onClose={() => setErrataModalOpen(false)}
        onSave={saveErrata}
      >
        <div className="space-y-3">
          <LabeledField label="Carta" required>
            <select
              className={staffInputClass()}
              value={errataForm.carta || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, carta: ev.target.value }))}
            >
              <option value="">— Seleziona carta —</option>
              {carte.map((c) => (
                <option key={c.id} value={c.id}>{c.nome} ({c.codice})</option>
              ))}
            </select>
          </LabeledField>
          <LabeledField label="Data efficacia" required>
            <input
              type="datetime-local"
              className={staffInputClass()}
              value={errataForm.effective_from ? String(errataForm.effective_from).slice(0, 16) : ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, effective_from: ev.target.value }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!errataForm.attiva}
              onChange={(ev) => setErrataForm((p) => ({ ...p, attiva: ev.target.checked }))}
            />
            Errata attiva
          </label>
          <LabeledField label="Versione errata">
            <input
              className={staffInputClass()}
              placeholder="es. 2026.07-A"
              value={errataForm.versione || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, versione: ev.target.value }))}
            />
          </LabeledField>
          <label className="flex items-center gap-2 text-sm">
            <input
              type="checkbox"
              checked={!!errataForm.pubblicata}
              onChange={(ev) => setErrataForm((p) => ({ ...p, pubblicata: ev.target.checked }))}
            />
            Pubblicata ai giocatori
          </label>
          <LabeledField label="Pubblicata il">
            <input
              type="datetime-local"
              className={staffInputClass()}
              value={errataForm.pubblicata_at ? String(errataForm.pubblicata_at).slice(0, 16) : ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, pubblicata_at: ev.target.value || null }))}
            />
          </LabeledField>
          <LabeledField label="Nota pubblicazione">
            <textarea
              className={staffInputClass('min-h-[72px]')}
              value={errataForm.pubblicata_nota || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, pubblicata_nota: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Titolo">
            <input
              className={staffInputClass()}
              value={errataForm.titolo || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, titolo: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Descrizione">
            <textarea
              className={staffInputClass('min-h-[80px]')}
              value={errataForm.descrizione || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, descrizione: ev.target.value }))}
            />
          </LabeledField>
          <LabeledField label="Override testo gioco">
            <textarea
              className={staffInputClass('min-h-[100px]')}
              value={errataForm.testo_gioco_override || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, testo_gioco_override: ev.target.value }))}
            />
          </LabeledField>
          <StaffFieldGrid cols={2}>
            {[
              ['costo_gioco_override', 'Costo gioco'],
              ['attacco_override', 'Attacco'],
              ['salute_override', 'Salute'],
              ['iniziativa_override', 'Iniziativa'],
            ].map(([key, label]) => (
              <LabeledField key={key} label={label}>
                <input
                  type="number"
                  className={staffInputClass()}
                  value={errataForm[key] ?? ''}
                  onChange={(ev) => setErrataForm((p) => ({ ...p, [key]: ev.target.value === '' ? null : Number(ev.target.value) }))}
                />
              </LabeledField>
            ))}
          </StaffFieldGrid>
          <LabeledField label="Effect scripts override (JSON)">
            <textarea
              className={staffInputClass('min-h-[110px] font-mono')}
              placeholder='[{"codice":"RITO","nome":"Rito","script":{"version":1,"trigger":{"event":"on_play"},"steps":[]}}]'
              value={errataForm.effect_scripts_override_text || ''}
              onChange={(ev) => setErrataForm((p) => ({ ...p, effect_scripts_override_text: ev.target.value }))}
            />
            {!!errataJsonError && (
              <p className="mt-1 text-xs text-red-400">{errataJsonError}</p>
            )}
          </LabeledField>
        </div>
      </StaffModal>

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
