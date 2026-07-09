import { useEffect, useMemo, useState } from "react";
import {
  importMseStyleTemplate,
  loadInitialData,
  saveCarta,
  saveEspansione,
  saveKeyword,
} from "./api/client";

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
  testo_gioco: "",
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

export default function App() {
  const [tab, setTab] = useState("cards");
  const [loading, setLoading] = useState(true);
  const [msg, setMsg] = useState("");

  const [espansioni, setEspansioni] = useState([]);
  const [carte, setCarte] = useState([]);
  const [keywords, setKeywords] = useState([]);
  const [templates, setTemplates] = useState([]);
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

  const refresh = async () => {
    setLoading(true);
    try {
      const data = await loadInitialData();
      setEspansioni(data.espansioni);
      setCarte(data.carte);
      setKeywords(data.keywords);
      setTemplates(data.templates);
      setGiochi(data.giochi);
      if (data.giochi[0]) setGiocoForm(data.giochi[0]);
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
    const slot = layoutSlots[slotKey];
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
    const slot = layoutSlots[slotKey];
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
        <h1>Magic Set Editor — Web (Card Studio)</h1>
        <p>UI ispirata a MSE: pannelli dedicati per Cards, Style, Set info, Keywords, Stats.</p>
      </header>

      <div className="toolbar">
        <button type="button" onClick={refresh}>Refresh</button>
        <button type="button" onClick={handleSaveCard}>Save card</button>
        <button type="button" onClick={handleSaveEsp}>Save set info</button>
        <button type="button" onClick={handleSaveKeyword}>Save keyword</button>
      </div>

      <nav className="tabs mse-tabs">
        {PANELS.map((p) => (
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
                <li key={row.id}>
                  <button type="button" onClick={() => onEditCard(row)}>
                    {row.nome} <small>({row.codice})</small>
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
              </div>
              <div className="incard-preview">
                <div
                  className={`incard-frame ${previewMode === "preview" ? "preview-mode" : ""}`}
                  onMouseMove={onCardMouseMove}
                  onMouseUp={endDrag}
                  onMouseLeave={endDrag}
                >
                  <input
                    className="incard-title"
                    style={layoutSlots.title}
                    value={cardForm.nome || ""}
                    onChange={(e) => setCardForm((p) => ({ ...p, nome: e.target.value }))}
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
                    onChange={(e) => setCardForm((p) => ({ ...p, codice: e.target.value }))}
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
                    onChange={(e) => setCardForm((p) => ({ ...p, testo_gioco: e.target.value }))}
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
                      onChange={(e) => setCardForm((p) => ({ ...p, costo_gioco: Number(e.target.value) }))}
                      title="Cost"
                    />
                    <input
                      type="number"
                      value={cardForm.attacco ?? 0}
                      onChange={(e) => setCardForm((p) => ({ ...p, attacco: Number(e.target.value) }))}
                      title="Attack"
                    />
                    <input
                      type="number"
                      value={cardForm.salute ?? 0}
                      onChange={(e) => setCardForm((p) => ({ ...p, salute: Number(e.target.value) }))}
                      title="Health"
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
                </div>
              </div>
            </section>
            <div className="fields-2">
              <label className="field"><span>Code</span><input value={cardForm.codice} onChange={(e) => setCardForm((p) => ({ ...p, codice: e.target.value }))} /></label>
              <label className="field"><span>Name</span><input value={cardForm.nome} onChange={(e) => setCardForm((p) => ({ ...p, nome: e.target.value }))} /></label>
              <label className="field">
                <span>Set / Expansion</span>
                <select value={cardForm.espansione || ""} onChange={(e) => setCardForm((p) => ({ ...p, espansione: e.target.value || null }))}>
                  <option value="">— None —</option>
                  {espansioni.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
                </select>
              </label>
              <label className="field">
                <span>Template</span>
                <select value={cardForm.studio_template || ""} onChange={(e) => setCardForm((p) => ({ ...p, studio_template: e.target.value || null }))}>
                  <option value="">— None —</option>
                  {templates.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
                </select>
              </label>
              <label className="field"><span>Type</span><input value={cardForm.tipo} onChange={(e) => setCardForm((p) => ({ ...p, tipo: e.target.value }))} /></label>
              <label className="field"><span>Energy</span><input value={cardForm.energia} onChange={(e) => setCardForm((p) => ({ ...p, energia: e.target.value }))} /></label>
              <label className="field"><span>Rarity</span><input value={cardForm.rarita} onChange={(e) => setCardForm((p) => ({ ...p, rarita: e.target.value }))} /></label>
              <label className="field"><span>Cost</span><input type="number" value={cardForm.costo_gioco ?? 0} onChange={(e) => setCardForm((p) => ({ ...p, costo_gioco: Number(e.target.value) }))} /></label>
            </div>
            <label className="field"><span>Rules text</span><textarea rows={5} value={cardForm.testo_gioco || ""} onChange={(e) => setCardForm((p) => ({ ...p, testo_gioco: e.target.value }))} /></label>
            <details open>
              <summary>Advanced data (MSE/Arena mapping)</summary>
              <JsonField label="studio_carta_spec" value={studioSpecText} setValue={setStudioSpecText} />
              <JsonField label="arena_playable_spec" value={playableSpecText} setValue={setPlayableSpecText} />
              <JsonField label="mse_campi" value={mseCampiText} setValue={setMseCampiText} />
            </details>
            {cardForm.espansione && (
              <p className="hint">Set attivo: {espansioniById[cardForm.espansione]?.nome || "n/d"}</p>
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
            <p className="hint">Importa asset grafici/non grafici e costruisce manifest.</p>
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
            </div>
            <label className="field"><span>Rules text</span><textarea rows={4} value={kwForm.testo_regola || ""} onChange={(e) => setKwForm((p) => ({ ...p, testo_regola: e.target.value }))} /></label>
            <label className="field"><span>MSE match pattern</span><input value={kwForm.mse_match_pattern || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_match_pattern: e.target.value }))} /></label>
            <label className="field"><span>MSE reminder template</span><textarea rows={3} value={kwForm.mse_reminder_template || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_reminder_template: e.target.value }))} /></label>
            <JsonField label="effect_script" value={effectScriptText} setValue={setEffectScriptText} />
          </article>
        </section>
      )}

      {!loading && tab === "statistics" && (
        <section className="single-panel">
          <h2>Set statistics</h2>
          <div className="stats-grid">
            <div><strong>Cards</strong><span>{carte.length}</span></div>
            <div><strong>Sets</strong><span>{espansioni.length}</span></div>
            <div><strong>Keywords</strong><span>{keywords.length}</span></div>
            <div><strong>Stylesheets</strong><span>{templates.length}</span></div>
          </div>
        </section>
      )}

      {!loading && tab === "random_pack" && (
        <section className="single-panel">
          <h2>Random pack (roadmap)</h2>
          <p>Pannello previsto stile MSE. Qui andrà la simulazione bustine/set pack types.</p>
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
