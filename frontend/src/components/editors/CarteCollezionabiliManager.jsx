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
  getStaffWikiCarteRegolamentoInfo,
  syncStaffWikiCarteRegolamento,
  resolveMediaUrl,
  getPunteggiList,
} from '../../api';
import { CARTA_RARITA_LABEL, CARTA_TIPO_LABEL } from '../../carte/carteConstants';
import {
  LabeledField,
  StaffFieldGrid,
  StaffListRow,
  StaffListToolbar,
  StaffModal,
  staffInputClass,
} from '../../staff/StaffCrudUi';
import CartaCatalogoEditModal from './carte/CartaCatalogoEditModal';
import ComboReliquiarioStaffPanel from './ComboReliquiarioStaffPanel';
import EffectScriptWizard from './EffectScriptWizard';
import { effectScriptsFromApi, effectScriptsToApi } from './CartaEffectScriptsEditor';
import MercatoScambiStaffPanel from './MercatoScambiStaffPanel';

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
});

const emptyErrata = (cartaId = '') => ({
  carta: cartaId || '',
  effective_from: '',
  attiva: true,
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
      const [esp, cfg, kw, tagRes, errRes, wiki, punt] = await Promise.all([
        staffGetCarteEspansioni(onLogout),
        staffGetCarteConfig(onLogout),
        staffGetCarteKeywords(onLogout),
        staffGetCarteTags(onLogout),
        staffGetCarteErrata(onLogout),
        getStaffWikiCarteRegolamentoInfo(onLogout).catch(() => null),
        getPunteggiList(onLogout).catch(() => []),
      ]);
      const espList = Array.isArray(esp) ? esp : esp?.results || [];
      setEspansioni(espList);
      if (cfg) setConfig(cfg);
      setKeywords(Array.isArray(kw) ? kw : kw?.results || []);
      setTags(Array.isArray(tagRes) ? tagRes : tagRes?.results || []);
      setErrata(Array.isArray(errRes) ? errRes : errRes?.results || []);
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

  const filteredErrata = useMemo(
    () => (errataCardFilter ? errata.filter((e) => e.carta === errataCardFilter) : errata),
    [errata, errataCardFilter],
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
    setEspansioneForm(e ? { ...e } : emptyEspansione());
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
    setKeywordForm(k ? { ...k } : emptyKeyword());
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
        {['espansioni', 'catalogo', 'bustine', 'tags', 'keywords', 'errata', 'combo-reliquiario', 'scambi', 'config'].map((t) => (
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
        <div>
          <StaffListToolbar
            title="Espansioni"
            count={espansioni.length}
            onAdd={() => openEspansioneModal(null)}
            addLabel="Nuova espansione"
          />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {espansioni.map((e) => (
              <StaffListRow
                key={e.id}
                onEdit={() => openEspansioneModal(e)}
                onDelete={() => deleteEspansione(e.id)}
                deleteConfirm={`Eliminare l'espansione «${e.nome}»?`}
              >
                <p className="font-bold text-white">{e.nome}</p>
                <p className="text-xs text-gray-500">
                  <span className="text-gray-400">Slug:</span> {e.slug}
                  {' · '}
                  <span className="text-gray-400">Carte:</span> {e.carte_count ?? 0}
                  {' · '}
                  <span className="text-gray-400">Bustine:</span> {e.bustine_count ?? 0}
                  {!e.attiva && <span className="ml-2 text-amber-500">(disattiva)</span>}
                  {e.in_vendita === false && <span className="ml-2 text-red-400">(fuori vendita)</span>}
                  {e.legale_duello === false && <span className="ml-2 text-orange-400">(non legale duello)</span>}
                </p>
                <button
                  type="button"
                  className="mt-1 text-[10px] text-violet-400 underline"
                  onClick={() => { selectEspansione(e); setTab('catalogo'); }}
                >
                  Filtra catalogo e bustine
                </button>
              </StaffListRow>
            ))}
          </ul>
        </div>
      )}

      <StaffModal
        open={espansioneModalOpen}
        title={espansioneEditTarget?.id ? `Modifica espansione — ${espansioneForm.nome}` : 'Nuova espansione'}
        onClose={() => setEspansioneModalOpen(false)}
        onSave={saveEspansione}
      >
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
      </StaffModal>

      {!loading && tab === 'catalogo' && (
        <div>
          <StaffListToolbar
            title="Catalogo carte"
            count={carte.length}
            onAdd={() => openCartaModal(null)}
            addLabel="Nuova carta"
          />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {carte.map((c) => (
              <StaffListRow
                key={c.id}
                onEdit={() => openCartaModal(c)}
                onDelete={() => deleteCarta(c.id)}
                deleteConfirm={`Eliminare la carta «${c.nome}» (${c.codice})?`}
              >
                <p className="font-bold text-white">{c.nome}</p>
                <p className="text-xs text-gray-500">
                  <span className="text-gray-400">Codice:</span> {c.codice}
                  {' · '}
                  <span className="text-gray-400">Tipo:</span> {CARTA_TIPO_LABEL[c.tipo] || c.tipo}
                  {' · '}
                  <span className="text-gray-400">Rarità:</span> {CARTA_RARITA_LABEL[c.rarita] || c.rarita}
                </p>
                <p className="text-xs text-gray-600">
                  {c.espansione_nome && <><span className="text-gray-400">Espansione:</span> {c.espansione_nome} · </>}
                  {c.set_collezione && <><span className="text-gray-400">Set:</span> {c.set_collezione} · </>}
                  {c.legame_id && <><span className="text-gray-400">Legame:</span> {c.legame_id} · </>}
                  {(c.tag_codici || []).length > 0 && (
                    <><span className="text-gray-400">Tag:</span> [{c.tag_codici.join(', ')}]</>
                  )}
                  {c.bandita && <span className="ml-2 text-red-400">(bandita)</span>}
                  {c.legale_duello === false && <span className="ml-2 text-orange-400">(non legale duello)</span>}
                  {errata.some((e) => e.carta === c.id && e.attiva) && <span className="ml-2 text-amber-300">(errata)</span>}
                  {!c.attiva && <span className="ml-1 text-amber-500">(disattiva)</span>}
                </p>
              </StaffListRow>
            ))}
          </ul>
        </div>
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
      />

      {!loading && tab === 'bustine' && (
        <div>
          <StaffListToolbar
            title="Bustine"
            count={bustine.length}
            onAdd={() => openBustinaModal(null)}
            addLabel="Nuova bustina"
          />
          {espansioni.map((e) => {
            const list = bustinePerEspansione.get(e.id) || [];
            if (!list.length && selectedEspansione?.id && selectedEspansione.id !== e.id) return null;
            if (!list.length) return null;
            return (
              <div key={e.id} className="mb-4">
                <h4 className="mb-2 text-xs font-bold uppercase text-violet-300">{e.nome}</h4>
                <ul className="space-y-1">
                  {list.map((b) => (
                    <StaffListRow
                      key={b.id}
                      onEdit={() => openBustinaModal(b)}
                      onDelete={() => deleteBustina(b.id)}
                      deleteConfirm={`Eliminare la bustina «${b.nome}»?`}
                    >
                      <p className="font-bold">{b.nome}</p>
                      <p className="text-xs text-gray-500">
                        <span className="text-gray-400">Costo:</span> {b.costo_crediti} CR
                        {' · '}
                        <span className="text-gray-400">Carte:</span> {b.carte_per_bustina}
                        {b.set_collezione && (
                          <> · <span className="text-gray-400">Set:</span> {b.set_collezione}</>
                        )}
                      </p>
                    </StaffListRow>
                  ))}
                </ul>
              </div>
            );
          })}
          {(bustinePerEspansione.get(null) || []).length > 0 && (
            <div className="mb-4">
              <h4 className="mb-2 text-xs font-bold uppercase text-gray-500">Senza espansione</h4>
              <ul className="space-y-1">
                {(bustinePerEspansione.get(null) || []).map((b) => (
                  <StaffListRow
                    key={b.id}
                    onEdit={() => openBustinaModal(b)}
                    onDelete={() => deleteBustina(b.id)}
                    deleteConfirm={`Eliminare la bustina «${b.nome}»?`}
                  >
                    <p className="font-bold">{b.nome}</p>
                    <p className="text-xs text-gray-500">{b.costo_crediti} CR · {b.carte_per_bustina} carte</p>
                  </StaffListRow>
                ))}
              </ul>
            </div>
          )}
        </div>
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
          <StaffListToolbar title="Tag meccanici" count={tags.length} onAdd={() => openTagModal(null)} addLabel="Nuovo tag" />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {tags.map((t) => (
              <StaffListRow
                key={t.id}
                onEdit={() => openTagModal(t)}
                onDelete={() => deleteTag(t.id)}
                deleteConfirm={`Eliminare il tag «${t.nome}»?`}
              >
                <p className="font-bold">{t.nome}</p>
                <p className="text-xs text-gray-500">
                  <span className="font-mono text-gray-400">{t.codice}</span>
                  {t.colore && <> · <span className="text-gray-400">Colore:</span> {t.colore}</>}
                  {!t.attiva && <span className="ml-2 text-amber-500">(disattivo)</span>}
                </p>
              </StaffListRow>
            ))}
          </ul>
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
          <StaffListToolbar
            title="Keyword condivise"
            count={keywords.length}
            onAdd={() => openKeywordModal(null)}
            addLabel="Nuova keyword"
          />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {keywords.map((k) => (
              <StaffListRow
                key={k.id}
                onEdit={() => openKeywordModal(k)}
                onDelete={() => deleteKeyword(k.id)}
                deleteConfirm={`Eliminare la keyword «${k.nome}»?`}
              >
                <p className="font-bold">{k.nome}</p>
                <p className="text-xs text-gray-500">
                  <span className="font-mono text-gray-400">{k.codice}</span>
                  {' · '}
                  <span className="text-gray-400">Priorità:</span> {k.priorita ?? 0}
                  {k.effect_script && Object.keys(k.effect_script).length > 0 && (
                    <span className="ml-2 text-violet-400">EffectScript</span>
                  )}
                  {!k.attiva && <span className="ml-2 text-amber-500">(disattiva)</span>}
                </p>
              </StaffListRow>
            ))}
          </ul>
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
          <StaffListToolbar
            title="Errata carte"
            count={filteredErrata.length}
            onAdd={() => openErrataModal(null)}
            addLabel="Nuova errata"
          />
          <ul className="max-h-[70vh] space-y-1 overflow-y-auto">
            {filteredErrata.map((e) => (
              <StaffListRow
                key={e.id}
                onEdit={() => openErrataModal(e)}
                onDelete={() => deleteErrata(e.id)}
                deleteConfirm={`Eliminare errata «${e.titolo || e.id}»?`}
              >
                <p className="font-bold text-white">{e.titolo || 'Errata senza titolo'}</p>
                <p className="text-xs text-gray-500">
                  <span className="text-gray-400">Carta:</span> {carte.find((c) => c.id === e.carta)?.nome || e.carta}
                  {' · '}
                  <span className="text-gray-400">Effettiva da:</span> {e.effective_from || '—'}
                  {' · '}
                  <span className="text-gray-400">Stato:</span> {e.attiva ? 'attiva' : 'disattiva'}
                </p>
              </StaffListRow>
            ))}
          </ul>
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
