import { useEffect, useMemo, useState } from "react";
import { sanitizeEspansionePayload } from "./api/errors";
import { mergeRecordById } from "./api/listUtils";
import {
  deleteCarta,
  deleteEspansione,
  importMseSet,
  importMseStyleTemplate,
  loadInitialData,
  saveCarta,
  saveEspansione,
  saveGioco,
  saveKeyword,
} from "./api/client";
import { sortCardsForSetOrder, suggestCardIdentity } from "./mse/cardSetOrder";
import { defaultStylingFromSpec } from "./mse/resolveLayers";
import MseWorkspaceBar from "./components/MseWorkspaceBar";
import MseEditorActions from "./components/MseEditorActions";
import MseCardsTab from "./components/MseCardsTab";
import MseKeywordsTab from "./components/MseKeywordsTab";
import MseRandomPackTab from "./components/MseRandomPackTab";
import MseSetTab from "./components/MseSetTab";
import MseStatisticsTab from "./components/MseStatisticsTab";
import MseStyleTab from "./components/MseStyleTab";
import {
  normFieldKey,
} from "./mse/fieldUtils";
import { buildSetStatistics } from "./mse/statistics";
import {
  buildPackRegistry,
  selectablePackTypes,
  simulateRandomPacks,
  summarizePackTypes,
} from "./mse/randomPack";
import { buildMetaWithPackDraft, clonePackDraft } from "./mse/packSpecUtils";

const emptyEspansione = {
  nome: "",
  slug: "",
  descrizione: "",
  attiva: true,
  in_vendita: true,
  legale_duello: true,
  gioco_definizione: null,
  default_studio_template: null,
  studio_set_spec: {},
  mse_set_riferimento: "",
};

const emptyCarta = {
  codice: "",
  nome: "",
  tipo: "PG",
  energia: "MAR",
  rarita: "COM",
  costo_gioco: 0,
  attacco: 0,
  salute: 0,
  iniziativa: 0,
  testo_gioco: "",
  testo_lore: "",
  espansione: null,
  layout_versione: "STD",
  studio_template: null,
  studio_carta_spec: {},
  arena_playable_spec: {},
  mse_campi: {},
  attiva: true,
  ordine_set: 0,
};

function parseJsonOrThrow(raw, label) {
  if (!raw || !String(raw).trim()) return {};
  const parsed = JSON.parse(raw);
  if (typeof parsed !== "object" || Array.isArray(parsed) || parsed === null) {
    throw new Error(`${label}: atteso oggetto JSON.`);
  }
  return parsed;
}

const emptyKeyword = {
  codice: "",
  nome: "",
  testo_regola: "",
  reminder_breve: "",
  priorita: 0,
  attiva: true,
  effect_script: {},
  mse_match_pattern: "",
  mse_reminder_template: "",
  mse_export_mode: "kor35",
};

const emptyGioco = {
  slug: "",
  nome: "",
  modello_base: "kor35",
  studio_abilitato: true,
  arena_abilitata: false,
  mse_game_name: "",
};

const PANELS = [
  { id: "cards", label: "Cards" },
  { id: "style", label: "Style" },
  { id: "set_info", label: "Set" },
  { id: "keywords", label: "Keywords" },
  { id: "statistics", label: "Statistics" },
  { id: "random_pack", label: "Random Pack" },
  { id: "console", label: "Console" },
];

const DEFAULT_CARD_LIST_COLUMNS = [
  { key: "nome", label: "Name" },
  { key: "codice", label: "Code" },
];

function pickDefaultGame(giochi) {
  if (!giochi?.length) return null;
  return (
    giochi.find((g) => g.slug === "kor35" && g.modello_base === "kor35") ||
    giochi.find((g) => g.modello_base === "kor35") ||
    giochi.find((g) => g.slug === "magic" || g.modello_base === "mtg") ||
    giochi[0]
  );
}

function sortGiochiForStudio(giochi) {
  const rank = (g) => {
    if (g.slug === "kor35" || g.modello_base === "kor35") return 0;
    if (g.slug === "magic" || g.modello_base === "mtg") return 1;
    return 2;
  };
  return [...(giochi || [])].sort((a, b) => {
    const d = rank(a) - rank(b);
    return d !== 0 ? d : String(a.nome || "").localeCompare(String(b.nome || ""));
  });
}

const ESPANSIONE_READ_ONLY = new Set([
  "id",
  "sync_id",
  "created_at",
  "updated_at",
  "campagna",
  "bustine_count",
  "carte_count",
  "immagine_url",
]);

const CARTA_READ_ONLY = new Set([
  "id",
  "sync_id",
  "created_at",
  "updated_at",
  "campagna",
  "espansione_nome",
  "immagine_url",
  "tag_codici",
  "statistiche_reliquiario",
]);

function stripPayloadFields(form, readOnlyKeys) {
  const out = {};
  Object.entries(form || {}).forEach(([k, v]) => {
    if (!readOnlyKeys.has(k)) out[k] = v;
  });
  return out;
}

function parseJsonObject(raw, label) {
  try {
    return parseJsonOrThrow(raw, label);
  } catch {
    return {};
  }
}

function buildCardSavePayload(cardForm, { studioSpecText, playableSpecText, mseCampiText }) {
  const fromTextMse = parseJsonObject(mseCampiText, "mse_campi");
  const fromFormMse = cardForm.mse_campi && typeof cardForm.mse_campi === "object" ? cardForm.mse_campi : {};
  const fromTextStudio = parseJsonObject(studioSpecText, "studio_carta_spec");
  const fromFormStudio =
    cardForm.studio_carta_spec && typeof cardForm.studio_carta_spec === "object" ? cardForm.studio_carta_spec : {};
  return {
    ...stripPayloadFields(cardForm, CARTA_READ_ONLY),
    studio_carta_spec: {
      ...fromTextStudio,
      ...fromFormStudio,
      styling: {
        ...(fromTextStudio.styling || {}),
        ...(fromFormStudio.styling || {}),
      },
    },
    arena_playable_spec: parseJsonObject(playableSpecText, "arena_playable_spec"),
    mse_campi: { ...fromTextMse, ...fromFormMse },
  };
}

function buildNewEspForm({ selectedGameId, defaultTemplateByGame }) {
  return {
    ...emptyEspansione,
    gioco_definizione: selectedGameId || null,
    default_studio_template: selectedGameId ? defaultTemplateByGame[selectedGameId] || null : null,
  };
}

function buildNewCardForm({
  selectedExpansionId,
  selectedGameId,
  espansioniById,
  defaultTemplateByGame,
  templatesForSelectedGame,
  carte = [],
}) {
  const esp = selectedExpansionId ? espansioniById[selectedExpansionId] : null;
  const tmpl =
    esp?.default_studio_template ||
    (selectedGameId ? defaultTemplateByGame[selectedGameId] : null) ||
    templatesForSelectedGame[0]?.id ||
    null;
  const expansionCards = selectedExpansionId
    ? carte.filter((c) => c.espansione === selectedExpansionId)
    : [];
  const suggested = esp ? suggestCardIdentity({ expansionCards, espansione: esp }) : { codice: "", ordine_set: 0 };
  return {
    ...emptyCarta,
    espansione: selectedExpansionId || null,
    studio_template: tmpl,
    codice: suggested.codice,
    ordine_set: suggested.ordine_set,
  };
}

export default function App() {
  const [tab, setTab] = useState("cards");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const [espansioni, setEspansioni] = useState([]);
  const [carte, setCarte] = useState([]);
  const [keywords, setKeywords] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [msePackages, setMsePackages] = useState([]);
  const [giochi, setGiochi] = useState([]);
  const [giocoForm, setGiocoForm] = useState(emptyGioco);

  const [espForm, setEspForm] = useState(emptyEspansione);
  const [espId, setEspId] = useState(null);
  const [espSetSpecText, setEspSetSpecText] = useState("{}");
  const [cardForm, setCardForm] = useState(emptyCarta);
  const [cardId, setCardId] = useState(null);
  const [cardFilter, setCardFilter] = useState("");
  const [studioSpecText, setStudioSpecText] = useState("{}");
  const [playableSpecText, setPlayableSpecText] = useState("{}");
  const [mseCampiText, setMseCampiText] = useState("{}");

  const [kwForm, setKwForm] = useState(emptyKeyword);
  const [kwId, setKwId] = useState(null);
  const [effectScriptText, setEffectScriptText] = useState("{}");
  const [mseStyleFile, setMseStyleFile] = useState(null);
  const [mseImportName, setMseImportName] = useState("");
  const [mseImportSlug, setMseImportSlug] = useState("");
  const [mseImportDefault, setMseImportDefault] = useState(false);
  const [mseSetFile, setMseSetFile] = useState(null);
  const [mseSetImportName, setMseSetImportName] = useState("");
  const [mseSetImportSlug, setMseSetImportSlug] = useState("");
  const [importingSet, setImportingSet] = useState(false);
  const [selectedGameId, setSelectedGameId] = useState("");
  const [defaultsAppliedGameId, setDefaultsAppliedGameId] = useState("");
  const [selectedExpansionId, setSelectedExpansionId] = useState("");
  const [stylingValues, setStylingValues] = useState({});
  const [selectedPackName, setSelectedPackName] = useState("");
  const [packCopies, setPackCopies] = useState(1);
  const [generatedPackResult, setGeneratedPackResult] = useState(null);
  const [packDraft, setPackDraft] = useState({ pack_items: [], pack_types: [] });
  const [packDraftBaseline, setPackDraftBaseline] = useState("");
  const [packSaving, setPackSaving] = useState(false);
  const [stylePreviewTemplateId, setStylePreviewTemplateId] = useState("");

  const applyLoadedData = (data) => {
    setEspansioni(data.espansioni);
    setCarte(data.carte);
    setKeywords(data.keywords);
    setTemplates(data.templates);
    setMsePackages(data.packages || []);
    setGiochi(data.giochi);
    const defaultGame = pickDefaultGame(data.giochi);
    if (defaultGame) {
      setGiocoForm(defaultGame);
      setSelectedGameId((prev) => prev || defaultGame.id);
    }
    return data;
  };

  const reloadData = async ({ showLoading = false } = {}) => {
    if (showLoading) setLoading(true);
    try {
      const data = await loadInitialData();
      return applyLoadedData(data);
    } catch (err) {
      setMsg(err.message || "Errore caricamento.");
      throw err;
    } finally {
      if (showLoading) setLoading(false);
    }
  };

  const refresh = () => reloadData({ showLoading: true });

  useEffect(() => {
    refresh();
  }, []);

  const espansioniById = useMemo(
    () => Object.fromEntries(espansioni.map((e) => [e.id, e])),
    [espansioni]
  );
  const sortedGiochi = useMemo(() => sortGiochiForStudio(giochi), [giochi]);
  const filteredCards = useMemo(() => {
    let pool = carte;
    if (selectedExpansionId) {
      pool = pool.filter((c) => c.espansione === selectedExpansionId);
    } else if (selectedGameId) {
      pool = pool.filter((c) => {
        if (!c.espansione) return true;
        const esp = espansioniById[c.espansione];
        return esp?.gioco_definizione === selectedGameId;
      });
    }
    const q = cardFilter.trim().toLowerCase();
    if (q) {
      pool = pool.filter((c) =>
        [c.nome, c.codice, c.tipo, c.energia, c.rarita].some((v) =>
          String(v || "").toLowerCase().includes(q)
        )
      );
    }
    return sortCardsForSetOrder(pool);
  }, [carte, selectedExpansionId, selectedGameId, espansioniById, cardFilter]);
  const defaultTemplateByGame = useMemo(() => {
    const map = {};
    templates.forEach((t) => {
      if (!map[t.gioco_definizione] && t.is_default_for_new_cards && t.attivo !== false) {
        map[t.gioco_definizione] = t.id;
      }
    });
    return map;
  }, [templates]);
  const templatesById = useMemo(
    () => Object.fromEntries(templates.map((t) => [t.id, t])),
    [templates]
  );
  const selectedGame = useMemo(
    () => giochi.find((g) => g.id === selectedGameId) || null,
    [giochi, selectedGameId]
  );
  const gameCardFields = useMemo(
    () => selectedGame?.meta?.mse_game_spec?.card_fields || [],
    [selectedGame]
  );
  const gameSetFields = useMemo(
    () => selectedGame?.meta?.mse_game_spec?.set_fields || [],
    [selectedGame]
  );
  const gameHasKeywords = useMemo(
    () => Boolean(selectedGame?.meta?.mse_game_spec?.has_keywords),
    [selectedGame]
  );
  const gameKeywordModes = useMemo(
    () => selectedGame?.meta?.mse_game_spec?.keyword_modes || [],
    [selectedGame]
  );
  const visiblePanels = useMemo(() => {
    return PANELS.filter((p) => {
      if (p.id === "keywords") return gameHasKeywords;
      if (p.id === "random_pack") return Boolean(selectedGameId);
      return true;
    });
  }, [gameHasKeywords, selectedGameId]);
  const gameCardListColumns = useMemo(() => {
    const cols = gameCardFields
      .filter((f) => f.card_list_allow !== false && (f.card_list_visible || f.identifying))
      .sort((a, b) => (a.card_list_column ?? 0) - (b.card_list_column ?? 0))
      .slice(0, 8)
      .map((f) => ({
        key: normFieldKey(f.name),
        label: f.card_list_name || f.name,
        width: f.card_list_width || 100,
        align: f.card_list_alignment || "left",
      }));
    return cols.length > 0 ? cols : DEFAULT_CARD_LIST_COLUMNS;
  }, [gameCardFields]);

  const gamePackSpec = useMemo(() => {
    const base = selectedGame?.meta?.mse_game_spec || null;
    if (!base && !packDraft.pack_items.length && !packDraft.pack_types.length) return null;
    return {
      ...(base || { version: "1" }),
      pack_items: packDraft.pack_items,
      pack_types: packDraft.pack_types,
    };
  }, [selectedGame, packDraft]);
  const packDraftDirty = useMemo(
    () => JSON.stringify(packDraft) !== packDraftBaseline,
    [packDraft, packDraftBaseline]
  );
  const selectablePacks = useMemo(() => selectablePackTypes(gamePackSpec), [gamePackSpec]);
  const packRegistry = useMemo(() => buildPackRegistry(gamePackSpec), [gamePackSpec]);

  const packCardPool = useMemo(() => {
    return carte.filter((c) => {
      if (c.attiva === false) return false;
      if (selectedExpansionId && c.espansione !== selectedExpansionId) return false;
      if (!selectedExpansionId && selectedGameId) {
        const esp = espansioniById[c.espansione];
        if (esp?.gioco_definizione && esp.gioco_definizione !== selectedGameId) return false;
      }
      return true;
    });
  }, [carte, selectedExpansionId, selectedGameId, espansioniById]);

  const packSummaryRows = useMemo(() => {
    if (!gamePackSpec || !packCardPool.length) return [];
    return summarizePackTypes(gamePackSpec, packRegistry, packCardPool, gameCardFields, packCopies);
  }, [gamePackSpec, packRegistry, packCardPool, gameCardFields, packCopies]);

  useEffect(() => {
    if (!selectablePacks.length) {
      setSelectedPackName("");
      return;
    }
    if (!selectablePacks.some((p) => p.name === selectedPackName)) {
      setSelectedPackName(selectablePacks[0].name);
    }
  }, [selectablePacks, selectedPackName]);

  useEffect(() => {
    const draft = clonePackDraft(selectedGame?.meta?.mse_game_spec);
    setPackDraft(draft);
    setPackDraftBaseline(JSON.stringify(draft));
    setGeneratedPackResult(null);
  }, [selectedGameId, selectedGame?.meta?.mse_game_spec]);

  const savePackSpec = async () => {
    if (!selectedGameId || !selectedGame) {
      setMsg("Seleziona un gioco prima di salvare i pack.");
      return;
    }
    setPackSaving(true);
    try {
      const meta = buildMetaWithPackDraft(selectedGame.meta, packDraft);
      const saved = await saveGioco(selectedGameId, { meta });
      setGiochi((prev) => prev.map((g) => (g.id === saved.id ? saved : g)));
      if (giocoForm.id === saved.id) setGiocoForm(saved);
      const draft = clonePackDraft(saved.meta?.mse_game_spec);
      setPackDraft(draft);
      setPackDraftBaseline(JSON.stringify(draft));
      setMsg("Pack spec salvata sul gioco.");
    } catch (err) {
      setMsg(err.message || "Errore salvataggio pack spec.");
    } finally {
      setPackSaving(false);
    }
  };

  const runRandomPack = () => {
    const packType = selectablePacks.find((p) => p.name === selectedPackName) || selectablePacks[0];
    if (!packType || !packCardPool.length) {
      setMsg("Nessun pack type o pool carte vuoto.");
      return;
    }
    const result = simulateRandomPacks({
      packType,
      registry: packRegistry,
      cards: packCardPool,
      gameCardFields,
      copies: packCopies,
    });
    setGeneratedPackResult(result);
    setMsg(`Generati ${result.packs.length} pack (${result.total} carte).`);
  };

  const statisticsReport = useMemo(() => {
    const pool = carte.filter((c) => {
      if (selectedExpansionId && c.espansione !== selectedExpansionId) return false;
      if (!selectedExpansionId && selectedGameId) {
        const esp = espansioniById[c.espansione];
        if (esp?.gioco_definizione && esp.gioco_definizione !== selectedGameId) return false;
      }
      return true;
    });
    return buildSetStatistics({ cards: pool, cardFields: gameCardFields });
  }, [carte, selectedExpansionId, selectedGameId, espansioniById, gameCardFields]);

  const cardListRowStyle = (row) =>
    resolveCardListRowColor({
      gameSpec: selectedGame?.meta?.mse_game_spec,
      cardFields: gameCardFields,
      row,
    });

  useEffect(() => {
    if (!visiblePanels.some((p) => p.id === tab)) {
      setTab("cards");
    }
  }, [visiblePanels, tab]);
  const templatesForSelectedGame = useMemo(
    () => templates.filter((t) => !selectedGameId || t.gioco_definizione === selectedGameId),
    [templates, selectedGameId]
  );
  const espansioniForWorkspace = useMemo(
    () =>
      espansioni.filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId),
    [espansioni, selectedGameId]
  );
  const workspaceCardPool = useMemo(() => {
    let pool = carte;
    if (selectedExpansionId) {
      pool = pool.filter((c) => c.espansione === selectedExpansionId);
    } else if (selectedGameId) {
      pool = pool.filter((c) => {
        if (!c.espansione) return true;
        const esp = espansioniById[c.espansione];
        return esp?.gioco_definizione === selectedGameId;
      });
    }
    return pool;
  }, [carte, selectedExpansionId, selectedGameId, espansioniById]);

  const activeTemplate = useMemo(
    () => (cardForm.studio_template ? templatesById[cardForm.studio_template] : null),
    [cardForm.studio_template, templatesById]
  );

  const mseV1 = useMemo(() => activeTemplate?.layout_spec?.mse_v1 || null, [activeTemplate]);

  useEffect(() => {
    if (!mseV1) {
      setStylingValues({});
      return;
    }
    const saved = cardForm.studio_carta_spec?.styling || {};
    setStylingValues({ ...defaultStylingFromSpec(mseV1), ...saved });
  }, [mseV1, cardForm.studio_template, cardId, cardForm.studio_carta_spec]);

  useEffect(() => {
    if (cardForm.studio_template) {
      setStylePreviewTemplateId(cardForm.studio_template);
    }
  }, [cardForm.studio_template]);

  const patchStylingValue = (field, rawValue) => {
    const name = field?.name;
    if (!name) return;
    const next = { ...stylingValues, [name]: rawValue, [normFieldKey(name)]: rawValue };
    setStylingValues(next);
    let spec = {};
    try {
      spec = parseJsonOrThrow(studioSpecText, "studio_carta_spec");
    } catch {
      spec = {};
    }
    spec.styling = next;
    const txt = JSON.stringify(spec, null, 2);
    setStudioSpecText(txt);
    setCardForm((p) => ({ ...p, studio_carta_spec: spec }));
  };

  useEffect(() => {
    if (cardId || !cardForm.espansione || cardForm.studio_template) return;
    const esp = espansioniById[cardForm.espansione];
    if (!esp) return;
    const tmpl =
      esp.default_studio_template ||
      (esp.gioco_definizione ? defaultTemplateByGame[esp.gioco_definizione] : null);
    if (tmpl) {
      setCardForm((prev) => ({ ...prev, studio_template: tmpl }));
    }
  }, [cardId, cardForm.espansione, cardForm.studio_template, espansioniById, defaultTemplateByGame]);

  useEffect(() => {
    if (!cardForm.espansione) return;
    const esp = espansioniById[cardForm.espansione];
    if (esp?.gioco_definizione) {
      setSelectedGameId(esp.gioco_definizione);
    }
  }, [cardForm.espansione, espansioniById]);

  useEffect(() => {
    if (cardId || !selectedGameId) return;
    if (!cardForm.studio_template || !templatesById[cardForm.studio_template]) {
      const fallback = defaultTemplateByGame[selectedGameId] || templatesForSelectedGame[0]?.id;
      if (fallback) {
        setCardForm((prev) => ({ ...prev, studio_template: fallback }));
      }
    }
  }, [
    cardId,
    selectedGameId,
    cardForm.studio_template,
    templatesById,
    defaultTemplateByGame,
    templatesForSelectedGame,
  ]);

  const onEditEsp = (row) => {
    setEspId(row.id);
    setEspForm({ ...emptyEspansione, ...row });
    setEspSetSpecText(JSON.stringify(row.studio_set_spec || {}, null, 2));
    if (row.gioco_definizione) setSelectedGameId(row.gioco_definizione);
    setSelectedExpansionId(row.id);
  };

  const onNewEsp = () => {
    setEspId(null);
    setEspForm(buildNewEspForm({ selectedGameId, defaultTemplateByGame }));
    setEspSetSpecText("{}");
    setTab("set_info");
  };

  const onNewCard = () => {
    setCardId(null);
    const draft = buildNewCardForm({
      selectedExpansionId,
      selectedGameId,
      espansioniById,
      defaultTemplateByGame,
      templatesForSelectedGame,
      carte,
    });
    setCardForm(draft);
    setStudioSpecText("{}");
    setPlayableSpecText("{}");
    setMseCampiText("{}");
    setTab("cards");
  };

  const onNewKeyword = () => {
    setKwId(null);
    setKwForm(emptyKeyword);
    setEffectScriptText("{}");
  };

  const onEditCard = (row) => {
    setCardId(row.id);
    setCardForm({ ...emptyCarta, ...row });
    setStudioSpecText(JSON.stringify(row.studio_carta_spec || {}, null, 2));
    setPlayableSpecText(JSON.stringify(row.arena_playable_spec || {}, null, 2));
    setMseCampiText(JSON.stringify(row.mse_campi || {}, null, 2));
    const esp = row.espansione ? espansioniById[row.espansione] : null;
    if (esp?.gioco_definizione) {
      setSelectedGameId(esp.gioco_definizione);
    } else if (row.studio_template && templatesById[row.studio_template]?.gioco_definizione) {
      setSelectedGameId(templatesById[row.studio_template].gioco_definizione);
    }
  };

  const refreshAfterMutation = async ({ kind, saved }) => {
    if (kind === "card" && saved?.id) {
      setCarte((prev) => mergeRecordById(prev, saved));
      onEditCard(saved);
    } else if (kind === "esp" && saved?.id) {
      setEspansioni((prev) => mergeRecordById(prev, saved));
      onEditEsp(saved);
    }
    try {
      const data = await reloadData({ showLoading: false });
      if (kind === "card" && saved?.id) {
        const freshCard = data.carte.find((row) => row.id === saved.id);
        if (freshCard) onEditCard(freshCard);
      } else if (kind === "esp" && saved?.id) {
        const freshEsp = data.espansioni.find((row) => row.id === saved.id);
        if (freshEsp) onEditEsp(freshEsp);
      }
    } catch {
      // merge + onEdit già applicati
    }
  };

  const selectNeighborCard = (delta) => {
    if (!filteredCards.length) return;
    const idx = filteredCards.findIndex((c) => c.id === cardId);
    const target = idx < 0 ? filteredCards[0] : filteredCards[(idx + delta + filteredCards.length) % filteredCards.length];
    onEditCard(target);
  };

  const onEditKw = (row) => {
    setKwId(row.id);
    setKwForm({ ...emptyKeyword, ...row });
    setEffectScriptText(JSON.stringify(row.effect_script || {}, null, 2));
  };

  const handleSaveEsp = async () => {
    try {
      const raw = {
        ...stripPayloadFields(espForm, ESPANSIONE_READ_ONLY),
        studio_set_spec: parseJsonOrThrow(espSetSpecText, "studio_set_spec"),
      };
      const payload = sanitizeEspansionePayload(raw);
      if (!payload.nome) {
        setMsg("Nome set obbligatorio (campo title / nome).");
        return;
      }
      if (!payload.slug) {
        setMsg("Codice set obbligatorio (campo code / slug).");
        return;
      }
      const saved = await saveEspansione(espId, payload);
      setMsg(espId ? "Set aggiornato." : "Set creato.");
      await refreshAfterMutation({ kind: "esp", saved });
    } catch (err) {
      setMsg(err.message || "Salvataggio set fallito.");
    }
  };

  const handleDeleteEsp = async () => {
    if (!espId) return;
    const label = espForm.nome || espForm.slug || espId;
    if (!window.confirm(`Eliminare il set «${label}»? Le carte collegate possono restare orfane.`)) {
      return;
    }
    try {
      await deleteEspansione(espId);
      setMsg("Set eliminato.");
      setEspId(null);
      setEspForm(emptyEspansione);
      setEspSetSpecText("{}");
      if (selectedExpansionId === espId) setSelectedExpansionId("");
      await reloadData({ showLoading: false });
    } catch (err) {
      setMsg(err.message || "Eliminazione set fallita.");
    }
  };

  const handleSaveCard = async () => {
    try {
      let formForSave = cardForm;
      if (!cardId && !String(cardForm.codice || "").trim() && cardForm.espansione) {
        const esp = espansioniById[cardForm.espansione];
        const expansionCards = carte.filter((c) => c.espansione === cardForm.espansione);
        const suggested = suggestCardIdentity({ expansionCards, espansione: esp });
        formForSave = { ...cardForm, ...suggested };
        setCardForm(formForSave);
      }
      const payload = buildCardSavePayload(formForSave, {
        studioSpecText,
        playableSpecText,
        mseCampiText,
      });
      const saved = await saveCarta(cardId, payload);
      setMsg(cardId ? "Carta aggiornata." : "Carta creata.");
      await refreshAfterMutation({ kind: "card", saved });
    } catch (err) {
      setMsg(err.message || "Salvataggio carta fallito.");
    }
  };

  const handleDeleteCard = async () => {
    if (!cardId) return;
    const label = cardForm.nome || cardForm.codice || cardId;
    if (!window.confirm(`Eliminare la carta «${label}» dal catalogo?`)) {
      return;
    }
    try {
      await deleteCarta(cardId);
      setMsg("Carta eliminata.");
      setCardId(null);
      setCardForm(
        buildNewCardForm({
          selectedExpansionId,
          selectedGameId,
          espansioniById,
          defaultTemplateByGame,
          templatesForSelectedGame,
          carte,
        })
      );
      setStudioSpecText("{}");
      setPlayableSpecText("{}");
      setMseCampiText("{}");
      await reloadData({ showLoading: false });
    } catch (err) {
      setMsg(err.message || "Eliminazione carta fallita.");
    }
  };

  const updateCardField = (key, value) => {
    setCardForm((prev) => ({ ...prev, [key]: value }));
  };

  const updateTemplateByGame = (templateId) => {
    const nextTemplate = templateId || null;
    updateCardField("studio_template", nextTemplate);
  };

  const getSetSpecValue = (field) => {
    let spec = {};
    try {
      spec = parseJsonOrThrow(espSetSpecText, "studio_set_spec");
    } catch {
      spec = {};
    }
    const k = normFieldKey(field?.name);
    if (["name", "title"].includes(k)) return espForm.nome || "";
    if (["description", "descrizione"].includes(k)) return espForm.descrizione || "";
    if (["code", "slug", "set_code"].includes(k)) return espForm.slug || "";
    return spec?.mse_set_fields?.[k] ?? field.initial ?? "";
  };

  const setSetSpecValue = (field, rawValue) => {
    const k = normFieldKey(field?.name);
    const fType = String(field?.type || "text").toLowerCase();
    const v = fType === "multiple choice"
      ? (Array.isArray(rawValue) ? rawValue : String(rawValue || "").split(",").map((x) => x.trim()).filter(Boolean))
      : rawValue;
    if (["name", "title"].includes(k)) {
      setEspForm((p) => ({ ...p, nome: String(v) }));
      return;
    }
    if (["description", "descrizione"].includes(k)) {
      setEspForm((p) => ({ ...p, descrizione: String(v) }));
      return;
    }
    if (["code", "slug", "set_code"].includes(k)) {
      setEspForm((p) => ({ ...p, slug: String(v) }));
      return;
    }
    let spec = {};
    try {
      spec = parseJsonOrThrow(espSetSpecText, "studio_set_spec");
    } catch {
      spec = {};
    }
    spec.mse_set_fields = { ...(spec.mse_set_fields || {}), [k]: v };
    setEspSetSpecText(JSON.stringify(spec, null, 2));
  };

  const setDynamicFieldValue = (field, rawValue) => {
    const k = normFieldKey(field?.name);
    const fType = String(field?.type || "").toLowerCase();
    const v = ["number", "int"].includes(fType)
      ? Number(rawValue || 0)
      : fType === "multiple choice"
        ? (Array.isArray(rawValue) ? rawValue : String(rawValue || "").split(",").map((x) => x.trim()).filter(Boolean))
      : rawValue;
    if (["name", "card_name", "title"].includes(k)) return updateCardField("nome", String(v));
    if (["rules", "rules_text", "text", "card_text"].includes(k)) return updateCardField("testo_gioco", String(v));
    if (["lore", "flavor", "flavor_text"].includes(k)) return updateCardField("testo_lore", String(v));
    if (["type", "card_type"].includes(k)) return updateCardField("tipo", String(v));
    if (["energy", "mana", "resource"].includes(k)) return updateCardField("energia", String(v));
    if (["rarity"].includes(k)) return updateCardField("rarita", String(v));
    if (["cost", "mana_cost"].includes(k)) return updateCardField("costo_gioco", Number(v));
    if (["attack", "power", "forza"].includes(k)) return updateCardField("attacco", Number(v));
    if (["health", "toughness", "robustezza"].includes(k)) return updateCardField("salute", Number(v));
    if (["initiative", "iniziativa"].includes(k)) return updateCardField("iniziativa", Number(v));

    setCardForm((prev) => ({
      ...prev,
      mse_campi: {
        ...(prev.mse_campi || {}),
        [k]: v,
      },
    }));
    try {
      const parsed = parseJsonOrThrow(mseCampiText, "mse_campi");
      parsed[k] = v;
      setMseCampiText(JSON.stringify(parsed, null, 2));
    } catch {
      setMseCampiText(JSON.stringify({ [k]: v }, null, 2));
    }
  };

  const onDynamicFilePicked = (field, file) => {
    if (!file) return;
    const pseudoPath = file.name;
    setDynamicFieldValue(field, pseudoPath);
    setMsg(`File selezionato per ${field?.name}: ${pseudoPath}`);
  };

  const applyGameFieldDefaults = (fields) => {
    if (!Array.isArray(fields) || fields.length === 0) return;
    setCardForm((prev) => {
      const next = { ...prev, mse_campi: { ...(prev.mse_campi || {}) } };
      fields.forEach((field) => {
        const k = normFieldKey(field?.name);
        const fType = String(field?.type || "text").toLowerCase();
        const initial = field?.initial ?? field?.default ?? "";
        const current = next.mse_campi?.[k];
        if (current === undefined || current === "") {
          if (fType === "multiple choice") {
            next.mse_campi[k] = String(initial || "")
              .split(",")
              .map((x) => x.trim())
              .filter(Boolean);
          } else if (!["name", "card_name", "title", "rules", "rules_text", "text", "card_text", "lore", "flavor", "flavor_text", "type", "card_type", "energy", "mana", "resource", "rarity", "cost", "mana_cost", "attack", "power", "forza", "health", "toughness", "robustezza", "initiative", "iniziativa"].includes(k)) {
            next.mse_campi[k] = initial;
          }
        }
        if (["name", "card_name", "title"].includes(k) && !next.nome && initial) next.nome = String(initial);
        if (["rules", "rules_text", "text", "card_text"].includes(k) && !next.testo_gioco && initial) next.testo_gioco = String(initial);
        if (["lore", "flavor", "flavor_text"].includes(k) && !next.testo_lore && initial) next.testo_lore = String(initial);
        if (["type", "card_type"].includes(k) && !next.tipo && initial) next.tipo = String(initial);
        if (["energy", "mana", "resource"].includes(k) && !next.energia && initial) next.energia = String(initial);
        if (["rarity"].includes(k) && !next.rarita && initial) next.rarita = String(initial);
        if (["cost", "mana_cost"].includes(k) && !next.costo_gioco && initial !== "") next.costo_gioco = Number(initial) || 0;
        if (["attack", "power", "forza"].includes(k) && !next.attacco && initial !== "") next.attacco = Number(initial) || 0;
        if (["health", "toughness", "robustezza"].includes(k) && !next.salute && initial !== "") next.salute = Number(initial) || 0;
        if (["initiative", "iniziativa"].includes(k) && !next.iniziativa && initial !== "") next.iniziativa = Number(initial) || 0;
      });
      try {
        setMseCampiText(JSON.stringify(next.mse_campi || {}, null, 2));
      } catch {
        // ignore
      }
      return next;
    });
  };

  useEffect(() => {
    if (cardId || !selectedGameId) return;
    if (defaultsAppliedGameId === selectedGameId) return;
    applyGameFieldDefaults(gameCardFields);
    setDefaultsAppliedGameId(selectedGameId);
  }, [cardId, selectedGameId, defaultsAppliedGameId, gameCardFields]);

  const handleSaveKeyword = async () => {
    try {
      const payload = {
        ...kwForm,
        effect_script: parseJsonOrThrow(effectScriptText, "effect_script"),
      };
      await saveKeyword(kwId, payload);
      setMsg("Keyword salvata.");
      setKwId(null);
      setKwForm(emptyKeyword);
      setEffectScriptText("{}");
      await reloadData({ showLoading: false });
    } catch (err) {
      setMsg(err.message || "Salvataggio keyword fallito.");
    }
  };

  const handleGameChange = (gid) => {
    setSelectedGameId(gid);
    setSelectedExpansionId("");
    if (!cardId && !cardForm.espansione) {
      const fallback =
        defaultTemplateByGame[gid] ||
        templates.find((t) => t.gioco_definizione === gid)?.id ||
        null;
      updateCardField("studio_template", fallback);
    }
  };

  const handleExpansionChange = (expId) => {
    const next = expId || "";
    setSelectedExpansionId(next);
    if (next) {
      const esp = espansioniById[next];
      if (esp?.gioco_definizione) {
        setSelectedGameId(esp.gioco_definizione);
      }
    }
    if (!cardId) {
      setCardForm((prev) => ({ ...prev, espansione: next || null }));
    }
  };

  useEffect(() => {
    if (cardId || !selectedExpansionId) return;
    setCardForm((prev) =>
      prev.espansione === selectedExpansionId ? prev : { ...prev, espansione: selectedExpansionId }
    );
  }, [cardId, selectedExpansionId]);

  const primarySaveAction = useMemo(() => {
    if (tab === "cards") {
      return {
        label: cardId ? "Salva carta" : "Crea carta",
        onClick: handleSaveCard,
      };
    }
    if (tab === "set_info") {
      return {
        label: espId ? "Salva set" : "Crea set",
        onClick: handleSaveEsp,
      };
    }
    if (tab === "keywords" && gameHasKeywords) {
      return { label: kwId ? "Salva keyword" : "Crea keyword", onClick: handleSaveKeyword };
    }
    if (tab === "random_pack") return { label: "Salva pack spec", onClick: savePackSpec };
    return null;
  }, [tab, gameHasKeywords, cardId, espId, kwId]);

  const primaryDeleteAction = useMemo(() => {
    if (tab === "cards" && cardId) return { label: "Elimina carta", onClick: handleDeleteCard };
    if (tab === "set_info" && espId) return { label: "Elimina set", onClick: handleDeleteEsp };
    return null;
  }, [tab, cardId, espId]);

  const handleImportMseSet = async () => {
    if (!mseSetFile) {
      setMsg("Seleziona prima un file .mse-set/.zip.");
      return;
    }
    const giocoId = selectedGameId || giocoForm.id;
    if (!giocoId) {
      setMsg("Seleziona un gioco prima di importare il set.");
      return;
    }
    setImportingSet(true);
    try {
      const res = await importMseSet({
        file: mseSetFile,
        gioco_definizione: giocoId,
        nome: mseSetImportName,
        slug: mseSetImportSlug,
      });
      const s = res?.import_summary || {};
      setMsg(
        `Set importato: ${s.card_count || 0} carte (${s.cards_created || 0} nuove, ${s.cards_updated || 0} aggiornate).`
      );
      setMseSetFile(null);
      setMseSetImportName("");
      setMseSetImportSlug("");
      await reloadData({ showLoading: false });
      if (res?.espansione) {
        onEditEsp(res.espansione);
      }
    } catch (err) {
      setMsg(err.message || "Import .mse-set fallito.");
    } finally {
      setImportingSet(false);
    }
  };

  const handleImportMseStyle = async () => {
    if (!mseStyleFile) {
      setMsg("Seleziona prima un file .mse-style/.zip.");
      return;
    }
    try {
      const res = await importMseStyleTemplate({
        file: mseStyleFile,
        gioco_definizione: giocoForm.id,
        nome: mseImportName,
        slug: mseImportSlug,
        is_default_for_new_cards: mseImportDefault,
      });
      const s = res?.import_summary || {};
      setMsg(
        `Template importato. Asset: ${s.assets_total || 0} (img ${s.images_total || 0}, text ${
          s.text_total || 0
        }, bin ${s.binary_total || 0}).`
      );
      setMseStyleFile(null);
      setMseImportName("");
      setMseImportSlug("");
      setMseImportDefault(false);
      await reloadData({ showLoading: false });
    } catch (err) {
      setMsg(err.message || "Import .mse-style fallito.");
    }
  };

  return (
    <main className="app mse">
      <header className="header">
        <h1>Magic Set Editor — KOR35 Card Studio</h1>
      </header>

      {!loading && (
        <MseWorkspaceBar
          giochi={sortedGiochi}
          selectedGameId={selectedGameId}
          onGameChange={handleGameChange}
          espansioni={espansioni}
          selectedExpansionId={selectedExpansionId}
          onExpansionChange={handleExpansionChange}
          templatesCount={templatesForSelectedGame.length}
          cardsCount={workspaceCardPool.length}
        />
      )}

      <div className="toolbar">
        <button type="button" onClick={refresh}>Refresh</button>
        {primarySaveAction && (
          <button type="button" className="mse-btn-primary" onClick={primarySaveAction.onClick}>
            {primarySaveAction.label}
          </button>
        )}
        {primaryDeleteAction && (
          <button type="button" className="mse-btn-danger" onClick={primaryDeleteAction.onClick}>
            {primaryDeleteAction.label}
          </button>
        )}
      </div>

      <nav className="tabs mse-tabs">
        {visiblePanels.map((p) => (
          <button
            key={p.id}
            type="button"
            className={tab === p.id ? "active" : ""}
            onClick={() => setTab(p.id)}
          >
            {p.label}
          </button>
        ))}
      </nav>

      {!loading && primarySaveAction && (
        <MseEditorActions
          saveLabel={primarySaveAction.label}
          onSave={primarySaveAction.onClick}
          deleteLabel={primaryDeleteAction?.label}
          onDelete={primaryDeleteAction?.onClick}
          hint={
            tab === "cards"
              ? cardId
                ? `Modifica carta: ${cardForm.nome || cardForm.codice || cardId}`
                : "Nuova carta — compila code e name, poi salva."
              : tab === "set_info"
                ? espId
                  ? `Modifica set: ${espForm.nome || espForm.slug || espId}`
                  : "Nuovo set — titolo e codice obbligatori."
                : ""
          }
        />
      )}

      {msg && <p className="msg">{msg}</p>}
      {loading && <p>Caricamento…</p>}

      {!loading && tab === "cards" && (
        <MseCardsTab
          cardForm={cardForm}
          setCardForm={setCardForm}
          cardId={cardId}
          cardFilter={cardFilter}
          setCardFilter={setCardFilter}
          filteredCards={filteredCards}
          gameCardFields={gameCardFields}
          gameCardListColumns={gameCardListColumns}
          cardListRowStyle={cardListRowStyle}
          onSelectCard={onEditCard}
          onNewCard={onNewCard}
          onDeleteCard={handleDeleteCard}
          onSaveCard={handleSaveCard}
          saveCardLabel={cardId ? "Salva carta" : "Crea carta"}
          canDeleteCard={Boolean(cardId)}
          isNewCard={!cardId}
          selectNeighborCard={selectNeighborCard}
          selectedGameId={selectedGameId}
          espansioni={espansioni}
          templatesForSelectedGame={templatesForSelectedGame}
          updateCardField={updateCardField}
          updateTemplateByGame={updateTemplateByGame}
          packages={msePackages}
          activeTemplate={activeTemplate}
          espansioniById={espansioniById}
          stylingValues={stylingValues}
          onPickFile={onDynamicFilePicked}
          onStatusMessage={setMsg}
          onMseCampiSync={(mse) => setMseCampiText(JSON.stringify(mse, null, 2))}
        />
      )}

      {!loading && tab === "style" && (
        <MseStyleTab
          templates={templates}
          selectedGameId={selectedGameId}
          previewTemplateId={stylePreviewTemplateId || cardForm.studio_template || ""}
          onSelectTemplate={setStylePreviewTemplateId}
          cardForm={cardForm}
          gameCardFields={gameCardFields}
          stylingValues={stylingValues}
          onStylingChange={patchStylingValue}
          packages={msePackages}
          espansioniById={espansioniById}
          importGameId={giocoForm.id}
          onImportGameChange={(id) => {
            const g = giochi.find((x) => x.id === id);
            if (g) setGiocoForm(g);
          }}
          giochi={giochi}
          mseStyleFile={mseStyleFile}
          onMseStyleFile={setMseStyleFile}
          mseImportName={mseImportName}
          onMseImportName={setMseImportName}
          mseImportSlug={mseImportSlug}
          onMseImportSlug={setMseImportSlug}
          mseImportDefault={mseImportDefault}
          onMseImportDefault={setMseImportDefault}
          onImport={handleImportMseStyle}
        />
      )}

      {!loading && tab === "set_info" && (
        <MseSetTab
          espansioni={espansioniForWorkspace}
          espId={espId}
          isNewSet={!espId}
          onSelectSet={onEditEsp}
          onNewSet={onNewEsp}
          onDeleteSet={handleDeleteEsp}
          onSaveSet={handleSaveEsp}
          saveSetLabel={espId ? "Salva set" : "Crea set"}
          canDeleteSet={Boolean(espId)}
          gameSetFields={gameSetFields}
          getSetSpecValue={getSetSpecValue}
          setSetSpecValue={setSetSpecValue}
          packages={msePackages}
          espForm={espForm}
          setEspForm={setEspForm}
          giochi={giochi}
          templates={templates}
          importGameId={selectedGameId || giocoForm.id}
          onImportGameChange={(id) => {
            setSelectedGameId(id);
            const g = giochi.find((x) => x.id === id);
            if (g) setGiocoForm(g);
          }}
          mseSetFile={mseSetFile}
          onMseSetFile={setMseSetFile}
          mseSetImportName={mseSetImportName}
          onMseSetImportName={setMseSetImportName}
          mseSetImportSlug={mseSetImportSlug}
          onMseSetImportSlug={setMseSetImportSlug}
          onImportSet={handleImportMseSet}
          importingSet={importingSet}
        />
      )}

      {!loading && tab === "keywords" && (
        <MseKeywordsTab
          keywords={keywords}
          kwId={kwId}
          kwForm={kwForm}
          setKwForm={setKwForm}
          gameKeywordModes={gameKeywordModes}
          effectScriptText={effectScriptText}
          setEffectScriptText={setEffectScriptText}
          onSelectKeyword={onEditKw}
          onNewKeyword={onNewKeyword}
        />
      )}

      {!loading && tab === "statistics" && (
        <MseStatisticsTab
          statisticsReport={statisticsReport}
          selectedExpansionId={selectedExpansionId}
          onStatsEspansioneId={setSelectedExpansionId}
          espansioni={espansioni}
          selectedGameId={selectedGameId}
          metaCounts={{ sets: espansioni.length, keywords: keywords.length, templates: templates.length }}
        />
      )}

      {!loading && tab === "random_pack" && (
        <MseRandomPackTab
          selectedGameId={selectedGameId}
          draft={packDraft}
          onChange={setPackDraft}
          onSave={savePackSpec}
          saving={packSaving}
          dirty={packDraftDirty}
          selectablePacks={selectablePacks}
          allPackTypes={gamePackSpec?.pack_types || []}
          selectedPackName={selectedPackName}
          onSelectPackName={setSelectedPackName}
          packCopies={packCopies}
          onPackCopies={setPackCopies}
          poolExpansionId={selectedExpansionId}
          onPoolExpansion={setSelectedExpansionId}
          espansioni={espansioni}
          packCardPool={packCardPool}
          packSummaryRows={packSummaryRows}
          onGenerate={runRandomPack}
          generatedPackResult={generatedPackResult}
          onOpenCard={(card) => {
            onEditCard(card);
            setTab("cards");
          }}
        />
      )}

      {!loading && tab === "console" && (
        <section className="single-panel">
          <h2>Console</h2>
          <p>Output operativo import/export e validazioni mapping MSE.</p>
          <pre>{msg || "Nessun messaggio."}</pre>
        </section>
      )}
    </main>
  );
}
