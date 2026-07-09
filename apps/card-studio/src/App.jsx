import { useEffect, useMemo, useState } from "react";
import {
  importMseStyleTemplate,
  loadInitialData,
  saveCarta,
  saveEspansione,
  saveGioco,
  saveKeyword,
} from "./api/client";
import { resolveCardListRowColor } from "./mse/cardListColor";
import { resolveTemplateBackground } from "./mse/assetUrl";
import { defaultStylingFromSpec } from "./mse/resolveLayers";
import MseCardPreview from "./components/MseCardPreview";
import PackSpecEditor from "./components/PackSpecEditor";
import {
  cardFieldValue,
  mseColorToCss,
  normFieldKey,
  wildcardMatch,
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
};

const DEFAULT_LAYOUT = {
  frame: { width: 320, height: 448 },
  slots: {
    title: { x: 12, y: 12, w: 216, h: 32 },
    code: { x: 236, y: 12, w: 72, h: 32 },
    rules: { x: 12, y: 264, w: 296, h: 120 },
    stats: { x: 182, y: 392, w: 126, h: 44 },
  },
};

const PRESET_LAYOUTS = {
  std: DEFAULT_LAYOUT.slots,
  mtg: {
    title: { x: 14, y: 10, w: 210, h: 30 },
    code: { x: 228, y: 10, w: 78, h: 30 },
    rules: { x: 14, y: 278, w: 292, h: 110 },
    stats: { x: 184, y: 392, w: 122, h: 44 },
  },
  kor35: {
    title: { x: 12, y: 12, w: 216, h: 32 },
    code: { x: 236, y: 12, w: 72, h: 32 },
    rules: { x: 12, y: 264, w: 296, h: 120 },
    stats: { x: 182, y: 392, w: 126, h: 44 },
  },
};

const SNAP_GRID = 4;
const TYPE_OPTIONS = ["PG", "Creatura", "Evento", "Supporto", "Incantesimo"];
const ENERGY_OPTIONS = ["MAR", "FUO", "NAT", "OMB", "LUC", "ARC"];
const RARITY_OPTIONS = ["COM", "NON", "RAR", "MIT", "UNI"];
const COST_OPTIONS = Array.from({ length: 16 }, (_, i) => i);

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

function parseJsonOrThrow(raw, label) {
  if (!raw || !String(raw).trim()) return {};
  const parsed = JSON.parse(raw);
  if (typeof parsed !== "object" || Array.isArray(parsed) || parsed === null) {
    throw new Error(`${label}: atteso oggetto JSON.`);
  }
  return parsed;
}

const LORE_FIELD_KEYS = new Set(["lore", "flavor", "flavor_text"]);

const LEGACY_SLOT_ALIASES = {
  name: "title",
  card_name: "title",
  title: "title",
  codice: "code",
  code: "code",
  rules: "rules",
  rules_text: "rules",
  text: "rules",
  card_text: "rules",
  type: "type_slot",
  card_type: "type_slot",
  energy: "energy_slot",
  mana: "energy_slot",
  resource: "energy_slot",
  rarity: "rarity_slot",
  cost: "stats",
  mana_cost: "stats",
  attack: "stats",
  power: "stats",
  forza: "stats",
  health: "stats",
  toughness: "stats",
  robustezza: "stats",
  initiative: "stats",
  iniziativa: "stats",
};

const DEFAULT_FIELD_SLOTS = {
  title: { x: 12, y: 12, w: 216, h: 32 },
  code: { x: 236, y: 12, w: 72, h: 32 },
  type_slot: { x: 12, y: 48, w: 120, h: 24 },
  energy_slot: { x: 136, y: 48, w: 80, h: 24 },
  rarity_slot: { x: 220, y: 48, w: 88, h: 24 },
  rules: { x: 12, y: 264, w: 296, h: 120 },
  stats: { x: 182, y: 392, w: 126, h: 44 },
};

function slotToStyle(slot) {
  if (!slot) return {};
  return {
    position: "absolute",
    left: slot.x,
    top: slot.y,
    width: slot.w,
    height: slot.h,
  };
}

function JsonField({ label, value, setValue }) {
  return (
    <label className="field">
      <span>{label}</span>
      <textarea
        rows={5}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="{}"
      />
    </label>
  );
}

const PANELS = [
  { id: "cards", label: "Cards" },
  { id: "style", label: "Style" },
  { id: "set_info", label: "Set info" },
  { id: "keywords", label: "Keywords" },
  { id: "statistics", label: "Statistics" },
  { id: "random_pack", label: "Random pack" },
  { id: "console", label: "Console" },
];

const DEFAULT_CARD_LIST_COLUMNS = [
  { key: "nome", label: "Name" },
  { key: "codice", label: "Code" },
];

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
  const [previewMode, setPreviewMode] = useState("edit");
  const [layoutSlots, setLayoutSlots] = useState(DEFAULT_LAYOUT.slots);
  const [layoutPreset, setLayoutPreset] = useState("kor35");
  const [lockedSlots, setLockedSlots] = useState({});
  const [dragState, setDragState] = useState(null);
  const [showExtraFields, setShowExtraFields] = useState(false);
  const [cardFace, setCardFace] = useState("front");
  const [selectedGameId, setSelectedGameId] = useState("");
  const [defaultsAppliedGameId, setDefaultsAppliedGameId] = useState("");
  const [statsEspansioneId, setStatsEspansioneId] = useState("");
  const [stylingValues, setStylingValues] = useState({});
  const [selectedPackName, setSelectedPackName] = useState("");
  const [packCopies, setPackCopies] = useState(1);
  const [generatedPackResult, setGeneratedPackResult] = useState(null);
  const [packDraft, setPackDraft] = useState({ pack_items: [], pack_types: [] });
  const [packDraftBaseline, setPackDraftBaseline] = useState("");
  const [packSaving, setPackSaving] = useState(false);

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await loadInitialData();
      setEspansioni(data.espansioni);
      setCarte(data.carte);
      setKeywords(data.keywords);
      setTemplates(data.templates);
      setMsePackages(data.packages || []);
      setGiochi(data.giochi);
      if (data.giochi[0]) {
        setGiocoForm(data.giochi[0]);
        setSelectedGameId((prev) => prev || data.giochi[0].id);
      }
    } catch (err) {
      setMsg(err.message || "Errore caricamento.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const espansioniById = useMemo(
    () => Object.fromEntries(espansioni.map((e) => [e.id, e])),
    [espansioni]
  );
  const filteredCards = useMemo(() => {
    const q = cardFilter.trim().toLowerCase();
    if (!q) return carte;
    return carte.filter((c) =>
      [c.nome, c.codice, c.tipo, c.energia, c.rarita].some((v) =>
        String(v || "").toLowerCase().includes(q)
      )
    );
  }, [carte, cardFilter]);
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
      if (statsEspansioneId && c.espansione !== statsEspansioneId) return false;
      if (!statsEspansioneId && selectedGameId) {
        const esp = espansioniById[c.espansione];
        if (esp?.gioco_definizione && esp.gioco_definizione !== selectedGameId) return false;
      }
      return true;
    });
  }, [carte, statsEspansioneId, selectedGameId, espansioniById]);

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
      if (statsEspansioneId && c.espansione !== statsEspansioneId) return false;
      if (!statsEspansioneId && selectedGameId) {
        const esp = espansioniById[c.espansione];
        if (esp?.gioco_definizione && esp.gioco_definizione !== selectedGameId) return false;
      }
      return true;
    });
    return buildSetStatistics({ cards: pool, cardFields: gameCardFields });
  }, [carte, statsEspansioneId, selectedGameId, espansioniById, gameCardFields]);

  const previewFields = useMemo(() => {
    if (!gameCardFields.length) return [];
    return gameCardFields.filter((f) => {
      const k = normFieldKey(f.name);
      if (cardFace === "back") return LORE_FIELD_KEYS.has(k);
      return !LORE_FIELD_KEYS.has(k);
    });
  }, [gameCardFields, cardFace]);

  const packageOptionsForField = (field) => {
    const staticChoices = (field.choices || []).map((c) => c.name).filter(Boolean);
    const match = String(field.match || "").trim();
    if (!match) return staticChoices;
    return msePackages
      .filter((pkg) => wildcardMatch(match, pkg.package_name))
      .map((pkg) => pkg.package_name)
      .sort((a, b) => a.localeCompare(b));
  };

  const resolvePreviewSlot = (fieldKey) => {
    if (layoutSlots[fieldKey]) return layoutSlots[fieldKey];
    const alias = LEGACY_SLOT_ALIASES[fieldKey];
    if (alias && layoutSlots[alias]) return layoutSlots[alias];
    if (alias && DEFAULT_FIELD_SLOTS[alias]) return DEFAULT_FIELD_SLOTS[alias];
    if (DEFAULT_FIELD_SLOTS[fieldKey]) return DEFAULT_FIELD_SLOTS[fieldKey];
    const idx = previewFields.findIndex((f) => normFieldKey(f.name) === fieldKey);
    const row = Math.max(0, idx);
    return { x: 12, y: 72 + row * 34, w: 280, h: 28 };
  };

  const cardListRowStyle = (row) =>
    resolveCardListRowColor({
      gameSpec: selectedGame?.meta?.mse_game_spec,
      cardFields: gameCardFields,
      row,
    });

  const renderPackageChoiceSelect = (field, val, onChange) => {
    const options = packageOptionsForField(field);
    const required = field.required !== false;
    const emptyLabel = field.empty_name || "None";
    return (
      <select value={String(val || "")} onChange={(e) => onChange(e.target.value)}>
        {!required && <option value="">{emptyLabel}</option>}
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  };

  const renderPreviewFieldEditor = (field) => {
    const fieldKey = normFieldKey(field.name);
    const fType = String(field.type || "text").toLowerCase();
    const val = dynamicFieldValue(field);
    const slot = resolvePreviewSlot(fieldKey);
    const slotStyle = slotToStyle(slot);
    const commonProps = {
      style: slotStyle,
      onMouseDown: (e) => beginDrag(fieldKey, e),
      title: field.name,
    };

    if (previewMode === "preview") {
      const display =
        fType === "multiple choice"
          ? (Array.isArray(val) ? val : String(val || "").split(",")).join(", ")
          : fType === "color"
            ? ""
            : String(val || "");
      return (
        <div
          key={`pv-${fieldKey}`}
          className={`incard-field-preview incard-field-${fType.replace(/\s+/g, "-")}`}
          style={{
            ...slotStyle,
            ...(fType === "color" ? { backgroundColor: mseColorToCss(val) || "#000" } : {}),
          }}
        >
          {fType !== "color" ? display : null}
        </div>
      );
    }

    if (fType === "multiple choice") {
      const options = (field.choices || []).map((c) => c.name).filter(Boolean);
      const selected = Array.isArray(val)
        ? val.map(String)
        : String(val || "")
            .split(",")
            .map((x) => x.trim())
            .filter(Boolean);
      return (
        <select
          key={`pv-${fieldKey}`}
          multiple
          className="incard-field-input"
          {...commonProps}
          value={selected}
          onChange={(e) =>
            setDynamicFieldValue(field, Array.from(e.target.selectedOptions).map((o) => o.value))
          }
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    }
    if (fType === "choice") {
      const options = (field.choices || []).map((c) => c.name).filter(Boolean);
      return (
        <select
          key={`pv-${fieldKey}`}
          className="incard-field-input"
          {...commonProps}
          value={String(val || "")}
          onChange={(e) => setDynamicFieldValue(field, e.target.value)}
        >
          {options.map((opt) => (
            <option key={opt} value={opt}>
              {opt}
            </option>
          ))}
        </select>
      );
    }
    if (fType === "package choice") {
      return (
        <div key={`pv-${fieldKey}`} className="incard-field-input-wrap" style={slotStyle}>
          {renderPackageChoiceSelect(field, val, (v) => setDynamicFieldValue(field, v))}
        </div>
      );
    }
    if (fType === "color") {
      return (
        <input
          key={`pv-${fieldKey}`}
          type="color"
          className="incard-field-input"
          {...commonProps}
          value={String(val || "#000000")}
          onChange={(e) => setDynamicFieldValue(field, e.target.value)}
        />
      );
    }
    if (field.multi_line || fType === "text") {
      return (
        <textarea
          key={`pv-${fieldKey}`}
          className={`incard-field-input ${fType === "text" && fieldKey.includes("rule") ? "incard-rules" : ""}`}
          {...commonProps}
          value={String(val || "")}
          onChange={(e) => setDynamicFieldValue(field, e.target.value)}
        />
      );
    }
    if (["number", "int"].includes(fType)) {
      return (
        <input
          key={`pv-${fieldKey}`}
          type="number"
          className="incard-field-input"
          {...commonProps}
          value={Number(val || 0)}
          onChange={(e) => setDynamicFieldValue(field, e.target.value)}
        />
      );
    }
    return (
      <input
        key={`pv-${fieldKey}`}
        className={`incard-field-input ${fieldKey === "title" || fieldKey === "name" ? "incard-title" : fieldKey === "code" ? "incard-code" : ""}`}
        {...commonProps}
        value={String(val || "")}
        onChange={(e) => setDynamicFieldValue(field, e.target.value)}
      />
    );
  };

  const renderPreviewSlotChrome = (fieldKey) => {
    if (previewMode !== "edit") return null;
    const slot = resolvePreviewSlot(fieldKey);
    return (
      <>
        <button
          type="button"
          className={`slot-lock ${lockedSlots[fieldKey] ? "locked" : ""}`}
          style={{ left: slot.x + slot.w - 18, top: slot.y - 10 }}
          onClick={() => setLockedSlots((p) => ({ ...p, [fieldKey]: !p[fieldKey] }))}
        >
          🔒
        </button>
        <span
          className="resize-handle"
          style={{ left: slot.x + slot.w - 8, top: slot.y + slot.h - 8 }}
          onMouseDown={(e) => beginResize(fieldKey, e)}
        />
      </>
    );
  };

  useEffect(() => {
    if (!visiblePanels.some((p) => p.id === tab)) {
      setTab("cards");
    }
  }, [visiblePanels, tab]);
  const templatesForSelectedGame = useMemo(
    () => templates.filter((t) => !selectedGameId || t.gioco_definizione === selectedGameId),
    [templates, selectedGameId]
  );

  const activeTemplate = useMemo(
    () => (cardForm.studio_template ? templatesById[cardForm.studio_template] : null),
    [cardForm.studio_template, templatesById]
  );

  const mseV1 = useMemo(() => activeTemplate?.layout_spec?.mse_v1 || null, [activeTemplate]);
  const hasMsePreview = useMemo(
    () => Boolean(mseV1 && Object.keys(mseV1.card_styles || {}).length > 0),
    [mseV1]
  );
  const cardFrameSize = useMemo(() => {
    const w = activeTemplate?.layout_spec?.card_width_px || mseV1?.card_size?.width || 320;
    const h = activeTemplate?.layout_spec?.card_height_px || mseV1?.card_size?.height || 448;
    return { width: w, height: h };
  }, [activeTemplate, mseV1]);

  const templateBackgroundImage = useMemo(
    () => resolveTemplateBackground(activeTemplate),
    [activeTemplate]
  );

  useEffect(() => {
    if (!mseV1) {
      setStylingValues({});
      return;
    }
    const saved = cardForm.studio_carta_spec?.styling || {};
    setStylingValues({ ...defaultStylingFromSpec(mseV1), ...saved });
  }, [mseV1, cardForm.studio_template, cardId, cardForm.studio_carta_spec]);

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
    setEspForm({ ...emptyEspansione, ...row });
    setEspSetSpecText(JSON.stringify(row.studio_set_spec || {}, null, 2));
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

  useEffect(() => {
    try {
      const spec = parseJsonOrThrow(studioSpecText, "studio_carta_spec");
      const slots = spec?.layout?.slots;
      if (slots && typeof slots === "object") {
        setLayoutSlots((prev) => ({ ...prev, ...slots }));
      } else {
        setLayoutSlots(DEFAULT_LAYOUT.slots);
      }
    } catch {
      // ignore while typing invalid json
    }
  }, [studioSpecText]);

  const patchStudioLayoutSlots = (slots) => {
    let spec = {};
    try {
      spec = parseJsonOrThrow(studioSpecText, "studio_carta_spec");
    } catch {
      spec = {};
    }
    spec.layout = spec.layout || {};
    spec.layout.slots = slots;
    const txt = JSON.stringify(spec, null, 2);
    setStudioSpecText(txt);
    setCardForm((p) => ({ ...p, studio_carta_spec: spec }));
  };

  const beginDrag = (slotKey, ev) => {
    if (previewMode !== "edit") return;
    if (lockedSlots[slotKey]) return;
    const slot = layoutSlots[slotKey] || resolvePreviewSlot(slotKey);
    if (!slot) return;
    setDragState({
      mode: "move",
      slotKey,
      startX: ev.clientX,
      startY: ev.clientY,
      originX: slot.x,
      originY: slot.y,
    });
  };

  const beginResize = (slotKey, ev) => {
    if (previewMode !== "edit") return;
    if (lockedSlots[slotKey]) return;
    ev.stopPropagation();
    const slot = layoutSlots[slotKey] || resolvePreviewSlot(slotKey);
    if (!slot) return;
    setDragState({
      mode: "resize",
      slotKey,
      startX: ev.clientX,
      startY: ev.clientY,
      originW: slot.w,
      originH: slot.h,
    });
  };

  const onCardMouseMove = (ev) => {
    if (!dragState) return;
    const dx = ev.clientX - dragState.startX;
    const dy = ev.clientY - dragState.startY;
    const snap = (n) => Math.round(n / SNAP_GRID) * SNAP_GRID;
    let updatedSlot = { ...layoutSlots[dragState.slotKey] };
    if (dragState.mode === "resize") {
      updatedSlot.w = Math.max(24, snap(dragState.originW + dx));
      updatedSlot.h = Math.max(24, snap(dragState.originH + dy));
    } else {
      updatedSlot.x = Math.max(0, snap(dragState.originX + dx));
      updatedSlot.y = Math.max(0, snap(dragState.originY + dy));
    }
    const next = { ...layoutSlots, [dragState.slotKey]: updatedSlot };
    setLayoutSlots(next);
  };

  const endDrag = () => {
    if (!dragState) return;
    patchStudioLayoutSlots(layoutSlots);
    setDragState(null);
  };

  const applyPreset = (presetKey) => {
    const slots = PRESET_LAYOUTS[presetKey] || PRESET_LAYOUTS.kor35;
    const cloned = JSON.parse(JSON.stringify(slots));
    setLayoutPreset(presetKey);
    setLayoutSlots(cloned);
    patchStudioLayoutSlots(cloned);
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
      const payload = {
        ...espForm,
        studio_set_spec: parseJsonOrThrow(espSetSpecText, "studio_set_spec"),
      };
      await saveEspansione(espForm.id, payload);
      setMsg("Espansione salvata.");
      setEspForm(emptyEspansione);
      setEspSetSpecText("{}");
      await refresh();
    } catch (err) {
      setMsg(err.message || "Salvataggio espansione fallito.");
    }
  };

  const handleSaveCard = async () => {
    try {
      const payload = {
        ...cardForm,
        studio_carta_spec: parseJsonOrThrow(studioSpecText, "studio_carta_spec"),
        arena_playable_spec: parseJsonOrThrow(playableSpecText, "arena_playable_spec"),
        mse_campi: parseJsonOrThrow(mseCampiText, "mse_campi"),
      };
      await saveCarta(cardId, payload);
      setMsg("Carta salvata.");
      setCardId(null);
      setCardForm(emptyCarta);
      setStudioSpecText("{}");
      setPlayableSpecText("{}");
      setMseCampiText("{}");
      await refresh();
    } catch (err) {
      setMsg(err.message || "Salvataggio carta fallito.");
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

  const dynamicFieldValue = (field) => {
    const k = normFieldKey(field?.name);
    if (["name", "card_name", "title"].includes(k)) return cardForm.nome || "";
    if (["rules", "rules_text", "text", "card_text"].includes(k)) return cardForm.testo_gioco || "";
    if (["lore", "flavor", "flavor_text"].includes(k)) return cardForm.testo_lore || "";
    if (["type", "card_type"].includes(k)) return cardForm.tipo || "";
    if (["energy", "mana", "resource"].includes(k)) return cardForm.energia || "";
    if (["rarity"].includes(k)) return cardForm.rarita || "";
    if (["cost", "mana_cost"].includes(k)) return cardForm.costo_gioco ?? 0;
    if (["attack", "power", "forza"].includes(k)) return cardForm.attacco ?? 0;
    if (["health", "toughness", "robustezza"].includes(k)) return cardForm.salute ?? 0;
    if (["initiative", "iniziativa"].includes(k)) return cardForm.iniziativa ?? 0;
    return cardForm.mse_campi?.[k] ?? field.initial ?? "";
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
      await refresh();
    } catch (err) {
      setMsg(err.message || "Salvataggio keyword fallito.");
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
      await refresh();
    } catch (err) {
      setMsg(err.message || "Import .mse-style fallito.");
    }
  };

  return (
    <main className="app mse">
      <header className="header">
        <h1>Card Set Editor</h1>
        <p>UI ispirata a MSE: pannelli dedicati per Cards, Style, Set info, Keywords, Stats.</p>
      </header>

      <div className="toolbar">
        <button type="button" onClick={refresh}>Refresh</button>
        <button type="button" onClick={handleSaveCard}>Save card</button>
        <button type="button" onClick={handleSaveEsp}>Save set info</button>
        <button type="button" onClick={handleSaveKeyword}>Save keyword</button>
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

      {msg && <p className="msg">{msg}</p>}
      {loading && <p>Caricamento…</p>}

      {!loading && tab === "cards" && (
        <section className="cards-layout">
          <aside className="cards-list-panel">
            <h2>Card list</h2>
            <label className="field">
              <span>Search cards</span>
              <input
                value={cardFilter}
                onChange={(e) => setCardFilter(e.target.value)}
                placeholder="name, code, type..."
              />
            </label>
            <div className="row-actions">
              <button type="button" onClick={() => selectNeighborCard(-1)}>Prev</button>
              <button type="button" onClick={() => selectNeighborCard(1)}>Next</button>
            </div>
            <ul>
              {filteredCards.map((row) => (
                <li key={row.id} style={cardListRowStyle(row)}>
                  <button type="button" onClick={() => onEditCard(row)}>
                    {gameCardListColumns.map((c) => {
                      const val =
                        c.key === "nome"
                          ? row.nome
                          : c.key === "codice"
                            ? row.codice
                            : cardFieldValue(row, { name: c.key }) ||
                              row.mse_campi?.[c.key];
                      return (
                        <span
                          key={c.key}
                          className="list-col"
                          style={{
                            width: `${Math.max(60, Number(c.width || 100))}px`,
                            textAlign: c.align,
                          }}
                        >
                          <strong>{c.label}:</strong> {String(val || "—")}
                        </span>
                      );
                    })}
                  </button>
                </li>
              ))}
            </ul>
          </aside>
          <article className="cards-editor-panel">
            <h2>Card editor</h2>
            <section className="incard-section">
              <p className="sub">In-card direct edit</p>
              <div className="row-actions">
                <button type="button" className={previewMode === "edit" ? "active" : ""} onClick={() => setPreviewMode("edit")}>Edit overlay</button>
                <button type="button" className={previewMode === "preview" ? "active" : ""} onClick={() => setPreviewMode("preview")}>Render preview</button>
                <select value={layoutPreset} onChange={(e) => applyPreset(e.target.value)}>
                  <option value="kor35">Preset kor35</option>
                  <option value="mtg">Preset mtg</option>
                  <option value="std">Preset std</option>
                </select>
                <button type="button" onClick={() => {
                  setLayoutSlots(DEFAULT_LAYOUT.slots);
                  patchStudioLayoutSlots(DEFAULT_LAYOUT.slots);
                }}>Reset layout</button>
                <button type="button" className={cardFace === "front" ? "active" : ""} onClick={() => setCardFace("front")}>Front</button>
                <button type="button" className={cardFace === "back" ? "active" : ""} onClick={() => setCardFace("back")}>Back/Lore</button>
                <button type="button" onClick={() => setShowExtraFields(true)}>Extra fields</button>
              </div>
              <div className="mse-workbench">
                <div className="mse-card-table">
                  <h3>Card table</h3>
                  <label className="field"><span>Code</span><input value={cardForm.codice || ""} onChange={(e) => updateCardField("codice", e.target.value)} /></label>
                  {gameCardFields.length > 0 ? (
                    gameCardFields
                      .filter((f) => f.editable !== false)
                      .map((field) => {
                        const fType = String(field.type || "text").toLowerCase();
                        const val = dynamicFieldValue(field);
                        const options = (field.choices || []).map((c) => c.name).filter(Boolean);
                        return (
                          <label className="field" key={`${field.name}-${fType}`}>
                            <span>{field.name}</span>
                            {fType === "multiple choice" ? (
                              <select
                                multiple
                                value={
                                  Array.isArray(val)
                                    ? val.map(String)
                                    : String(val || "")
                                        .split(",")
                                        .map((x) => x.trim())
                                        .filter(Boolean)
                                }
                                onChange={(e) =>
                                  setDynamicFieldValue(
                                    field,
                                    Array.from(e.target.selectedOptions).map((o) => o.value)
                                  )
                                }
                              >
                                {options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                              </select>
                            ) : fType === "choice" ? (
                              <select value={String(val || "")} onChange={(e) => setDynamicFieldValue(field, e.target.value)}>
                                {options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                              </select>
                            ) : fType === "package choice" ? (
                              renderPackageChoiceSelect(field, val, (v) => setDynamicFieldValue(field, v))
                            ) : fType === "color" ? (
                              <input type="color" value={String(val || "#000000")} onChange={(e) => setDynamicFieldValue(field, e.target.value)} />
                            ) : fType === "image" || fType === "symbol" ? (
                              <>
                                <input type="file" onChange={(e) => onDynamicFilePicked(field, e.target.files?.[0] || null)} />
                                <input value={String(val || "")} onChange={(e) => setDynamicFieldValue(field, e.target.value)} placeholder="asset path..." />
                              </>
                            ) : fType === "boolean" ? (
                              <select value={String(val || "no")} onChange={(e) => setDynamicFieldValue(field, e.target.value)}>
                                <option value="yes">yes</option>
                                <option value="no">no</option>
                              </select>
                            ) : field.multi_line ? (
                              <textarea rows={4} value={String(val || "")} onChange={(e) => setDynamicFieldValue(field, e.target.value)} />
                            ) : (
                              <input value={String(val || "")} onChange={(e) => setDynamicFieldValue(field, e.target.value)} />
                            )}
                          </label>
                        );
                      })
                  ) : (
                    <>
                      <p className="hint">Nessun `card field` disponibile nel game MSE selezionato: fallback schema base.</p>
                      <label className="field"><span>Name</span><input value={cardForm.nome || ""} onChange={(e) => updateCardField("nome", e.target.value)} /></label>
                      <label className="field"><span>Type</span><select value={cardForm.tipo || "PG"} onChange={(e) => updateCardField("tipo", e.target.value)}>{TYPE_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
                      <label className="field"><span>Energy</span><select value={cardForm.energia || "MAR"} onChange={(e) => updateCardField("energia", e.target.value)}>{ENERGY_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
                      <label className="field"><span>Rarity</span><select value={cardForm.rarita || "COM"} onChange={(e) => updateCardField("rarita", e.target.value)}>{RARITY_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
                    </>
                  )}
                </div>
                <div className="incard-preview">
                <div
                  className={`incard-frame ${previewMode === "preview" ? "preview-mode" : ""} ${hasMsePreview ? "has-mse-preview" : ""}`}
                  onAuxClick={() => setCardFace((prev) => (prev === "front" ? "back" : "front"))}
                  onMouseMove={onCardMouseMove}
                  onMouseUp={endDrag}
                  onMouseLeave={endDrag}
                  style={{
                    width: `${cardFrameSize.width}px`,
                    height: `${cardFrameSize.height}px`,
                    ...(!(hasMsePreview && previewMode === "preview") && templateBackgroundImage
                      ? {
                          backgroundImage: `url(${templateBackgroundImage})`,
                          backgroundSize: "cover",
                          backgroundPosition: "center",
                        }
                      : {}),
                  }}
                >
                  {cardFace === "front" ? (
                    hasMsePreview && previewMode === "preview" ? (
                      <MseCardPreview
                        template={activeTemplate}
                        cardForm={cardForm}
                        gameCardFields={gameCardFields}
                        styling={stylingValues}
                        setData={
                          cardForm.espansione
                            ? espansioniById[cardForm.espansione]?.studio_set_spec?.mse_set_fields || {}
                            : {}
                        }
                        getFieldValue={dynamicFieldValue}
                        className="mse-fill"
                      />
                    ) : (
                    <>
                  {previewFields.length > 0 ? (
                    <>
                      {previewFields
                        .filter((f) => f.editable !== false)
                        .map((field) => {
                          const fieldKey = normFieldKey(field.name);
                          return (
                            <div key={`wrap-${fieldKey}`}>
                              {renderPreviewFieldEditor(field)}
                              {renderPreviewSlotChrome(fieldKey)}
                            </div>
                          );
                        })}
                      {!previewFields.some((f) => ["codice", "code"].includes(normFieldKey(f.name))) && (
                        <>
                          <input
                            className="incard-code"
                            style={slotToStyle(resolvePreviewSlot("code"))}
                            value={cardForm.codice || ""}
                            onChange={(e) => updateCardField("codice", e.target.value)}
                            placeholder="CODE-001"
                            onMouseDown={(e) => beginDrag("code", e)}
                          />
                          {renderPreviewSlotChrome("code")}
                        </>
                      )}
                      {previewMode === "edit" && (
                        <div className="overlay-hint">
                          Drag/resize con snap grid {SNAP_GRID}px. Slot da game fields + studio_carta_spec.layout.slots.
                        </div>
                      )}
                    </>
                  ) : (
                    <>
                  <input
                    className="incard-title"
                    style={layoutSlots.title}
                    value={cardForm.nome || ""}
                    onChange={(e) => updateCardField("nome", e.target.value)}
                    placeholder="Card name"
                    onMouseDown={(e) => beginDrag("title", e)}
                  />
                  {previewMode === "edit" && (
                    <>
                      <button type="button" className={`slot-lock ${lockedSlots.title ? "locked" : ""}`} style={{ left: layoutSlots.title.x + layoutSlots.title.w - 18, top: layoutSlots.title.y - 10 }} onClick={() => setLockedSlots((p) => ({ ...p, title: !p.title }))}>🔒</button>
                      <span className="resize-handle" style={{ left: layoutSlots.title.x + layoutSlots.title.w - 8, top: layoutSlots.title.y + layoutSlots.title.h - 8 }} onMouseDown={(e) => beginResize("title", e)} />
                    </>
                  )}
                  <input
                    className="incard-code"
                    style={layoutSlots.code}
                    value={cardForm.codice || ""}
                    onChange={(e) => updateCardField("codice", e.target.value)}
                    placeholder="CODE-001"
                    onMouseDown={(e) => beginDrag("code", e)}
                  />
                  {previewMode === "edit" && (
                    <>
                      <button type="button" className={`slot-lock ${lockedSlots.code ? "locked" : ""}`} style={{ left: layoutSlots.code.x + layoutSlots.code.w - 18, top: layoutSlots.code.y - 10 }} onClick={() => setLockedSlots((p) => ({ ...p, code: !p.code }))}>🔒</button>
                      <span className="resize-handle" style={{ left: layoutSlots.code.x + layoutSlots.code.w - 8, top: layoutSlots.code.y + layoutSlots.code.h - 8 }} onMouseDown={(e) => beginResize("code", e)} />
                    </>
                  )}
                  <textarea
                    className="incard-rules"
                    style={layoutSlots.rules}
                    value={cardForm.testo_gioco || ""}
                    onChange={(e) => updateCardField("testo_gioco", e.target.value)}
                    placeholder="Rules text..."
                    onMouseDown={(e) => beginDrag("rules", e)}
                  />
                  {previewMode === "edit" && (
                    <>
                      <button type="button" className={`slot-lock ${lockedSlots.rules ? "locked" : ""}`} style={{ left: layoutSlots.rules.x + layoutSlots.rules.w - 18, top: layoutSlots.rules.y - 10 }} onClick={() => setLockedSlots((p) => ({ ...p, rules: !p.rules }))}>🔒</button>
                      <span className="resize-handle" style={{ left: layoutSlots.rules.x + layoutSlots.rules.w - 8, top: layoutSlots.rules.y + layoutSlots.rules.h - 8 }} onMouseDown={(e) => beginResize("rules", e)} />
                    </>
                  )}
                  <div
                    className="incard-stats"
                    style={{
                      left: layoutSlots.stats.x,
                      top: layoutSlots.stats.y,
                      width: layoutSlots.stats.w,
                      height: layoutSlots.stats.h,
                    }}
                    onMouseDown={(e) => beginDrag("stats", e)}
                  >
                    <input
                      type="number"
                      value={cardForm.costo_gioco ?? 0}
                      onChange={(e) => updateCardField("costo_gioco", Number(e.target.value))}
                      title="Cost"
                    />
                    <input
                      type="number"
                      value={cardForm.attacco ?? 0}
                      onChange={(e) => updateCardField("attacco", Number(e.target.value))}
                      title="Attack"
                    />
                    <input
                      type="number"
                      value={cardForm.salute ?? 0}
                      onChange={(e) => updateCardField("salute", Number(e.target.value))}
                      title="Health"
                    />
                    <input
                      type="number"
                      value={cardForm.iniziativa ?? 0}
                      onChange={(e) => updateCardField("iniziativa", Number(e.target.value))}
                      title="Initiative"
                    />
                  </div>
                  {previewMode === "edit" && (
                    <>
                      <button type="button" className={`slot-lock ${lockedSlots.stats ? "locked" : ""}`} style={{ left: layoutSlots.stats.x + layoutSlots.stats.w - 18, top: layoutSlots.stats.y - 10 }} onClick={() => setLockedSlots((p) => ({ ...p, stats: !p.stats }))}>🔒</button>
                      <span className="resize-handle" style={{ left: layoutSlots.stats.x + layoutSlots.stats.w - 8, top: layoutSlots.stats.y + layoutSlots.stats.h - 8 }} onMouseDown={(e) => beginResize("stats", e)} />
                    </>
                  )}
                  {previewMode === "edit" && (
                    <div className="overlay-hint">
                      Drag/resize con snap grid {SNAP_GRID}px. Usa lock per bloccare slot.
                    </div>
                  )}
                    </>
                  )}
                    </>
                    )
                  ) : (
                    <div className="card-back">
                      {previewFields.length > 0 ? (
                        previewFields
                          .filter((f) => f.editable !== false)
                          .map((field) => renderPreviewFieldEditor(field))
                      ) : (
                        <>
                          <h3>{cardForm.nome || "Card name"}</h3>
                          <p>{cardForm.testo_lore || "Lore non ancora compilata."}</p>
                        </>
                      )}
                      <div className="back-thumb">{activeTemplate?.nome || "Template"}</div>
                    </div>
                  )}
                </div>
                </div>
              </div>
            </section>
            <div className="fields-2">
              <label className="field"><span>Code</span><input value={cardForm.codice} onChange={(e) => setCardForm((p) => ({ ...p, codice: e.target.value }))} /></label>
              <label className="field"><span>Name</span><input value={cardForm.nome} onChange={(e) => setCardForm((p) => ({ ...p, nome: e.target.value }))} /></label>
              <label className="field">
                <span>Game</span>
                <select
                  value={selectedGameId || ""}
                  onChange={(e) => {
                    const gid = e.target.value;
                    setSelectedGameId(gid);
                    if (!cardId && !cardForm.espansione) {
                      const fallback = defaultTemplateByGame[gid] || templates.find((t) => t.gioco_definizione === gid)?.id || null;
                      updateCardField("studio_template", fallback);
                    }
                  }}
                  disabled={Boolean(cardId || cardForm.espansione)}
                >
                  <option value="">— Select game —</option>
                  {giochi.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Set / Expansion</span>
                <select value={cardForm.espansione || ""} onChange={(e) => setCardForm((p) => ({ ...p, espansione: e.target.value || null }))}>
                  <option value="">— None —</option>
                  {espansioni
                    .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                    .map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Template</span>
                <select value={cardForm.studio_template || ""} onChange={(e) => updateTemplateByGame(e.target.value)} disabled={!selectedGameId}>
                  <option value="">— None —</option>
                  {templatesForSelectedGame.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                </select>
              </label>
              <label className="field"><span>Type</span><select value={cardForm.tipo || "PG"} onChange={(e) => updateCardField("tipo", e.target.value)}>{TYPE_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
              <label className="field"><span>Energy</span><select value={cardForm.energia || "MAR"} onChange={(e) => updateCardField("energia", e.target.value)}>{ENERGY_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
              <label className="field"><span>Rarity</span><select value={cardForm.rarita || "COM"} onChange={(e) => updateCardField("rarita", e.target.value)}>{RARITY_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
              <label className="field"><span>Cost</span><select value={cardForm.costo_gioco ?? 0} onChange={(e) => updateCardField("costo_gioco", Number(e.target.value))}>{COST_OPTIONS.map((opt) => <option key={opt} value={opt}>{opt}</option>)}</select></label>
              <label className="field"><span>Forza</span><input type="number" value={cardForm.attacco ?? 0} onChange={(e) => updateCardField("attacco", Number(e.target.value))} /></label>
              <label className="field"><span>Robustezza</span><input type="number" value={cardForm.salute ?? 0} onChange={(e) => updateCardField("salute", Number(e.target.value))} /></label>
              <label className="field"><span>Iniziativa</span><input type="number" value={cardForm.iniziativa ?? 0} onChange={(e) => updateCardField("iniziativa", Number(e.target.value))} /></label>
            </div>
            <label className="field"><span>Rules text</span><textarea rows={5} value={cardForm.testo_gioco || ""} onChange={(e) => updateCardField("testo_gioco", e.target.value)} /></label>
            <label className="field"><span>Lore text (retro)</span><textarea rows={4} value={cardForm.testo_lore || ""} onChange={(e) => updateCardField("testo_lore", e.target.value)} /></label>
            <details open>
              <summary>Advanced data (MSE/Arena mapping)</summary>
              <JsonField label="studio_carta_spec" value={studioSpecText} setValue={setStudioSpecText} />
              <JsonField label="arena_playable_spec" value={playableSpecText} setValue={setPlayableSpecText} />
              <JsonField label="mse_campi" value={mseCampiText} setValue={setMseCampiText} />
            </details>
            {cardForm.espansione && (
              <p className="hint">Set attivo: {espansioniById[cardForm.espansione]?.nome || "n/d"}</p>
            )}
            {!cardForm.espansione && selectedGame && (
              <p className="hint">Gioco selezionato: {selectedGame.nome}</p>
            )}
            {showExtraFields && (
              <div className="modal-backdrop" onClick={() => setShowExtraFields(false)}>
                <div className="modal-card" onClick={(e) => e.stopPropagation()}>
                  <h3>Campi extra non visibili sulla carta</h3>
                  <JsonField label="mse_campi" value={mseCampiText} setValue={setMseCampiText} />
                  <button type="button" onClick={() => setShowExtraFields(false)}>Chiudi</button>
                </div>
              </div>
            )}
          </article>
        </section>
      )}

      {!loading && tab === "style" && (
        <section className="grid">
          <article>
            <h2>Stylesheets (templates)</h2>
            <ul>
              {templates.map((t) => (
                <li key={t.id}>
                  <button type="button">
                    {t.nome} <small>({t.slug})</small>
                  </button>
                </li>
              ))}
            </ul>
          </article>
          <article>
            <h2>Import .mse-style / .zip</h2>
            <label className="field"><span>Game</span>
              <select value={giocoForm.id || ""} onChange={(e) => {
                const g = giochi.find((x) => x.id === e.target.value);
                if (g) setGiocoForm(g);
              }}>
                <option value="">— Select game —</option>
                {giochi.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Template package file</span>
              <input type="file" accept=".mse-style,.zip,application/zip" onChange={(e) => setMseStyleFile(e.target.files?.[0] || null)} />
            </label>
            <label className="field"><span>Name override</span><input value={mseImportName} onChange={(e) => setMseImportName(e.target.value)} /></label>
            <label className="field"><span>Slug override</span><input value={mseImportSlug} onChange={(e) => setMseImportSlug(e.target.value)} /></label>
            <label className="field-checkbox">
              <input type="checkbox" checked={mseImportDefault} onChange={(e) => setMseImportDefault(e.target.checked)} />
              Set as default template for new cards
            </label>
            <button type="button" onClick={handleImportMseStyle}>Import stylesheet</button>
            <p className="hint">Importa asset grafici/non grafici e costruisce manifest + layout_spec.mse_v1.</p>
            {mseV1?.styling_fields?.length > 0 && (
              <>
                <h3>Styling fields (template carta corrente)</h3>
                {mseV1.styling_fields.map((field) => {
                  const fType = String(field.type || "text").toLowerCase();
                  const val = stylingValues[field.name] ?? stylingValues[normFieldKey(field.name)] ?? "";
                  return (
                    <label className="field" key={`styling-${field.name}`}>
                      <span>{field.name}</span>
                      {fType === "boolean" ? (
                        <select
                          value={val ? "yes" : "no"}
                          onChange={(e) => patchStylingValue(field, e.target.value === "yes")}
                        >
                          <option value="yes">yes</option>
                          <option value="no">no</option>
                        </select>
                      ) : fType === "choice" ? (
                        <select
                          value={String(val)}
                          onChange={(e) => patchStylingValue(field, e.target.value)}
                        >
                          {(field.choices || []).map((c) => (
                            <option key={c.name} value={c.name}>
                              {c.name}
                            </option>
                          ))}
                        </select>
                      ) : (
                        <input value={String(val)} onChange={(e) => patchStylingValue(field, e.target.value)} />
                      )}
                    </label>
                  );
                })}
              </>
            )}
            {activeTemplate?.layout_spec?.mse_v1 && (
              <p className="hint">
                MSE preview: {Object.keys(activeTemplate.layout_spec.mse_v1.card_styles || {}).length} card style,{" "}
                {Object.keys(activeTemplate.layout_spec.mse_v1.extra_card_styles || {}).length} extra.
              </p>
            )}
          </article>
        </section>
      )}

      {!loading && tab === "set_info" && (
        <section className="grid">
          <article>
            <h2>Set list</h2>
            <ul>
              {espansioni.map((row) => (
                <li key={row.id}>
                  <button type="button" onClick={() => onEditEsp(row)}>
                    {row.nome} <small>({row.slug})</small>
                  </button>
                </li>
              ))}
            </ul>
          </article>
          <article>
            <h2>Set info editor</h2>
            <div className="fields-2">
              <label className="field"><span>Name</span><input value={espForm.nome} onChange={(e) => setEspForm((p) => ({ ...p, nome: e.target.value }))} /></label>
              <label className="field"><span>Slug</span><input value={espForm.slug} onChange={(e) => setEspForm((p) => ({ ...p, slug: e.target.value }))} /></label>
              <label className="field">
                <span>Game definition</span>
                <select value={espForm.gioco_definizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, gioco_definizione: e.target.value || null }))}>
                  <option value="">— None —</option>
                  {giochi.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Default template</span>
                <select value={espForm.default_studio_template || ""} onChange={(e) => setEspForm((p) => ({ ...p, default_studio_template: e.target.value || null }))}>
                  <option value="">— None (fallback game default) —</option>
                  {templates.filter((t) => !espForm.gioco_definizione || t.gioco_definizione === espForm.gioco_definizione).map((t) => (
                    <option key={t.id} value={t.id}>{t.nome}{t.is_default_for_new_cards ? " [game default]" : ""}</option>
                  ))}
                </select>
              </label>
            </div>
            <label className="field"><span>Description</span><textarea rows={4} value={espForm.descrizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, descrizione: e.target.value }))} /></label>
            <label className="field"><span>MSE set reference</span><input value={espForm.mse_set_riferimento || ""} onChange={(e) => setEspForm((p) => ({ ...p, mse_set_riferimento: e.target.value }))} /></label>
            <JsonField label="studio_set_spec" value={espSetSpecText} setValue={setEspSetSpecText} />
            {gameSetFields.length > 0 && (
              <>
                <p className="sub">Set fields from selected game</p>
                {gameSetFields
                  .filter((f) => f.editable !== false)
                  .map((field) => {
                    const fType = String(field.type || "text").toLowerCase();
                    const val = getSetSpecValue(field);
                    const options = (field.choices || []).map((c) => c.name).filter(Boolean);
                    return (
                      <label className="field" key={`set-${field.name}-${fType}`}>
                        <span>{field.name}</span>
                        {fType === "multiple choice" ? (
                          <select
                            multiple
                            value={
                              Array.isArray(val)
                                ? val.map(String)
                                : String(val || "")
                                    .split(",")
                                    .map((x) => x.trim())
                                    .filter(Boolean)
                            }
                            onChange={(e) =>
                              setSetSpecValue(
                                field,
                                Array.from(e.target.selectedOptions).map((o) => o.value)
                              )
                            }
                          >
                            {options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                          </select>
                        ) : fType === "choice" || fType === "package choice" ? (
                          fType === "package choice" ? (
                            renderPackageChoiceSelect(field, val, (v) => setSetSpecValue(field, v))
                          ) : (
                            <select value={String(val || "")} onChange={(e) => setSetSpecValue(field, e.target.value)}>
                              {options.map((opt) => <option key={opt} value={opt}>{opt}</option>)}
                            </select>
                          )
                        ) : fType === "color" ? (
                          <input type="color" value={String(val || "#000000")} onChange={(e) => setSetSpecValue(field, e.target.value)} />
                        ) : field.multi_line ? (
                          <textarea rows={3} value={String(val || "")} onChange={(e) => setSetSpecValue(field, e.target.value)} />
                        ) : (
                          <input value={String(val || "")} onChange={(e) => setSetSpecValue(field, e.target.value)} />
                        )}
                      </label>
                    );
                  })}
              </>
            )}
          </article>
        </section>
      )}

      {!loading && tab === "keywords" && (
        <section className="grid">
          <article>
            <h2>Keywords</h2>
            <ul>
              {keywords.map((row) => (
                <li key={row.id}>
                  <button type="button" onClick={() => onEditKw(row)}>
                    {row.nome} <small>({row.codice})</small>
                  </button>
                </li>
              ))}
            </ul>
          </article>
          <article>
            <h2>Keyword editor</h2>
            <div className="fields-2">
              <label className="field"><span>Code</span><input value={kwForm.codice} onChange={(e) => setKwForm((p) => ({ ...p, codice: e.target.value.toUpperCase() }))} /></label>
              <label className="field"><span>Name</span><input value={kwForm.nome} onChange={(e) => setKwForm((p) => ({ ...p, nome: e.target.value }))} /></label>
              <label className="field"><span>Reminder</span><input value={kwForm.reminder_breve || ""} onChange={(e) => setKwForm((p) => ({ ...p, reminder_breve: e.target.value }))} /></label>
              <label className="field">
                <span>MSE export mode</span>
                <select value={kwForm.mse_export_mode} onChange={(e) => setKwForm((p) => ({ ...p, mse_export_mode: e.target.value }))}>
                  <option value="kor35">kor35</option>
                  <option value="mse_compat">mse_compat</option>
                  <option value="both">both</option>
                </select>
              </label>
              {gameKeywordModes.length > 0 && (
                <label className="field">
                  <span>Keyword mode (from game)</span>
                  <select value={kwForm.mse_match_pattern || gameKeywordModes[0]} onChange={(e) => setKwForm((p) => ({ ...p, mse_match_pattern: e.target.value }))}>
                    {gameKeywordModes.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </label>
              )}
            </div>
            <label className="field"><span>Rules text</span><textarea rows={4} value={kwForm.testo_regola || ""} onChange={(e) => setKwForm((p) => ({ ...p, testo_regola: e.target.value }))} /></label>
            <label className="field"><span>MSE match pattern</span><input value={kwForm.mse_match_pattern || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_match_pattern: e.target.value }))} /></label>
            <label className="field"><span>MSE reminder template</span><textarea rows={3} value={kwForm.mse_reminder_template || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_reminder_template: e.target.value }))} /></label>
            <JsonField label="effect_script" value={effectScriptText} setValue={setEffectScriptText} />
          </article>
        </section>
      )}

      {!loading && tab === "statistics" && (
        <section className="single-panel statistics-panel">
          <h2>Set statistics</h2>
          <div className="row-actions">
            <label className="field inline">
              <span>Filter by expansion</span>
              <select
                value={statsEspansioneId}
                onChange={(e) => setStatsEspansioneId(e.target.value)}
              >
                <option value="">All (current game)</option>
                {espansioni
                  .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.nome}
                    </option>
                  ))}
              </select>
            </label>
            <div className="stats-summary-pill">
              <strong>{statisticsReport.total}</strong> cards
            </div>
          </div>
          <div className="stats-grid">
            <div><strong>Sets</strong><span>{espansioni.length}</span></div>
            <div><strong>Keywords</strong><span>{keywords.length}</span></div>
            <div><strong>Stylesheets</strong><span>{templates.length}</span></div>
            <div><strong>Dimensions</strong><span>{statisticsReport.dimensions.length}</span></div>
          </div>
          {statisticsReport.dimensions.map((dim) => (
            <article key={dim.key} className="stats-dimension">
              <h3>{dim.label}</h3>
              <table className="stats-table">
                <thead>
                  <tr>
                    <th>Value</th>
                    <th>Count</th>
                    <th>%</th>
                    <th>Distribution</th>
                  </tr>
                </thead>
                <tbody>
                  {dim.rows.map((row) => (
                    <tr key={`${dim.key}-${row.label}`}>
                      <td>{row.label}</td>
                      <td>{row.count}</td>
                      <td>{row.pct}%</td>
                      <td>
                        <div className="stats-bar-track">
                          <div
                            className="stats-bar-fill"
                            style={{
                              width: `${Math.max(4, row.pct)}%`,
                              backgroundColor: row.color || "#6d28d9",
                            }}
                          />
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </article>
          ))}
        </section>
      )}

      {!loading && tab === "random_pack" && (
        <section className="single-panel random-pack-panel">
          <h2>Random pack</h2>
          {!selectedGameId ? (
            <p className="hint">Seleziona un gioco (tab Cards) per definire o simulare i pack.</p>
          ) : (
            <>
          <PackSpecEditor
            draft={packDraft}
            onChange={setPackDraft}
            onSave={savePackSpec}
            saving={packSaving}
            dirty={packDraftDirty}
          />
          <h3>Simulator</h3>
          <div className="row-actions">
            <label className="field inline">
              <span>Pack type</span>
              <select value={selectedPackName} onChange={(e) => setSelectedPackName(e.target.value)}>
                {selectablePacks.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field inline">
              <span>Copies</span>
              <input
                type="number"
                min={1}
                max={100}
                value={packCopies}
                onChange={(e) => setPackCopies(Math.max(1, Number(e.target.value) || 1))}
              />
            </label>
            <label className="field inline">
              <span>Card pool</span>
              <select value={statsEspansioneId} onChange={(e) => setStatsEspansioneId(e.target.value)}>
                <option value="">All (current game)</option>
                {espansioni
                  .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                  .map((e) => (
                    <option key={e.id} value={e.id}>
                      {e.nome}
                    </option>
                  ))}
              </select>
            </label>
            <button type="button" onClick={runRandomPack}>Generate</button>
          </div>
          <p className="hint">
            Pool: {packCardPool.length} carte · Pack types: {selectablePacks.length} selezionabili /{" "}
            {(gamePackSpec?.pack_types || []).length} totali
          </p>
          <div className="random-pack-layout">
            <article className="pack-summary">
              <h3>Summary</h3>
              <table className="stats-table">
                <thead>
                  <tr>
                    <th>Pack type</th>
                    <th>Cards (est.)</th>
                  </tr>
                </thead>
                <tbody>
                  {packSummaryRows.map((row) => (
                    <tr key={row.name}>
                      <td>{row.name}</td>
                      <td>{row.count}</td>
                    </tr>
                  ))}
                  <tr>
                    <td><strong>Total</strong></td>
                    <td><strong>{packSummaryRows.reduce((s, r) => s + r.count, 0)}</strong></td>
                  </tr>
                </tbody>
              </table>
            </article>
            <article className="pack-output">
              <h3>Generated cards</h3>
              {!generatedPackResult ? (
                <p className="hint">Clicca Generate per simulare bustine.</p>
              ) : (
                generatedPackResult.packs.map((pack, idx) => (
                  <div key={`pack-${idx}`} className="pack-instance">
                    <h4>Pack #{idx + 1}</h4>
                    <ul>
                      {pack.map((card) => (
                        <li key={`${idx}-${card.id}`}>
                          <button type="button" onClick={() => onEditCard(card)}>
                            {card.nome} <small>({card.codice})</small>
                            {card._pack_from ? <em> · {card._pack_from}</em> : null}
                          </button>
                        </li>
                      ))}
                    </ul>
                  </div>
                ))
              )}
            </article>
          </div>
            </>
          )}
        </section>
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
