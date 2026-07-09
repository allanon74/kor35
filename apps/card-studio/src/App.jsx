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

export default function App() {
  const [tab, setTab] = useState("giochi");
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
  const [espId, setEspId] = useState(null);

  const [cardForm, setCardForm] = useState(emptyCarta);
  const [cardId, setCardId] = useState(null);
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
    setEspId(row.id);
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
      await saveEspansione(espId, payload);
      setMsg("Espansione salvata.");
      setEspId(null);
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
    <main className="app">
      <header className="header">
        <h1>Card Editor (MSE-first)</h1>
        <p>Editor separato per set, carte, keyword e campi platform.</p>
      </header>

      <nav className="tabs">
        {["giochi", "espansioni", "carte", "keywords"].map((name) => (
          <button
            key={name}
            type="button"
            className={tab === name ? "active" : ""}
            onClick={() => setTab(name)}
          >
            {name}
          </button>
        ))}
      </nav>

      {msg && <p className="msg">{msg}</p>}
      {loading && <p>Caricamento…</p>}

      {!loading && tab === "espansioni" && (
        <section className="grid">
          <article>
            <h2>Espansioni</h2>
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
            <h2>{espId ? "Modifica espansione" : "Nuova espansione"}</h2>
            <label className="field"><span>Nome</span><input value={espForm.nome} onChange={(e) => setEspForm((p) => ({ ...p, nome: e.target.value }))} /></label>
            <label className="field"><span>Slug</span><input value={espForm.slug} onChange={(e) => setEspForm((p) => ({ ...p, slug: e.target.value }))} /></label>
            <label className="field"><span>Descrizione</span><textarea rows={3} value={espForm.descrizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, descrizione: e.target.value }))} /></label>
            <label className="field">
              <span>Game definition</span>
              <select value={espForm.gioco_definizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, gioco_definizione: e.target.value || null }))}>
                <option value="">— Nessuna —</option>
                {giochi.map((g) => <option key={g.id} value={g.id}>{g.nome}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Template default nuove carte</span>
              <select
                value={espForm.default_studio_template || ""}
                onChange={(e) =>
                  setEspForm((p) => ({
                    ...p,
                    default_studio_template: e.target.value || null,
                  }))
                }
              >
                <option value="">— Nessuno (usa default gioco) —</option>
                {templates
                  .filter((t) => !espForm.gioco_definizione || t.gioco_definizione === espForm.gioco_definizione)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nome}
                      {t.is_default_for_new_cards ? " [default gioco]" : ""}
                    </option>
                  ))}
              </select>
            </label>
            <label className="field"><span>MSE set riferimento</span><input value={espForm.mse_set_riferimento || ""} onChange={(e) => setEspForm((p) => ({ ...p, mse_set_riferimento: e.target.value }))} /></label>
            <JsonField label="studio_set_spec" value={espSetSpecText} setValue={setEspSetSpecText} />
            <button type="button" onClick={handleSaveEsp}>Salva espansione</button>
          </article>
        </section>
      )}

      {!loading && tab === "carte" && (
        <section className="grid">
          <article>
            <h2>Catalogo carte</h2>
            <ul>
              {carte.map((row) => (
                <li key={row.id}>
                  <button type="button" onClick={() => onEditCard(row)}>
                    {row.nome} <small>({row.codice})</small>
                  </button>
                </li>
              ))}
            </ul>
          </article>
          <article>
            <h2>{cardId ? "Modifica carta" : "Nuova carta"}</h2>
            <label className="field"><span>Codice</span><input value={cardForm.codice} onChange={(e) => setCardForm((p) => ({ ...p, codice: e.target.value }))} /></label>
            <label className="field"><span>Nome</span><input value={cardForm.nome} onChange={(e) => setCardForm((p) => ({ ...p, nome: e.target.value }))} /></label>
            <label className="field">
              <span>Espansione</span>
              <select value={cardForm.espansione || ""} onChange={(e) => setCardForm((p) => ({ ...p, espansione: e.target.value || null }))}>
                <option value="">— Nessuna —</option>
                {espansioni.map((e) => <option key={e.id} value={e.id}>{e.nome}</option>)}
              </select>
            </label>
            <label className="field">
              <span>Template Studio</span>
              <select value={cardForm.studio_template || ""} onChange={(e) => setCardForm((p) => ({ ...p, studio_template: e.target.value || null }))}>
                <option value="">— Nessuno —</option>
                {templates.map((t) => <option key={t.id} value={t.id}>{t.nome}</option>)}
              </select>
            </label>
            <label className="field"><span>Tipo</span><input value={cardForm.tipo} onChange={(e) => setCardForm((p) => ({ ...p, tipo: e.target.value }))} /></label>
            <label className="field"><span>Energia</span><input value={cardForm.energia} onChange={(e) => setCardForm((p) => ({ ...p, energia: e.target.value }))} /></label>
            <label className="field"><span>Rarita</span><input value={cardForm.rarita} onChange={(e) => setCardForm((p) => ({ ...p, rarita: e.target.value }))} /></label>
            <label className="field"><span>Costo gioco</span><input type="number" value={cardForm.costo_gioco ?? 0} onChange={(e) => setCardForm((p) => ({ ...p, costo_gioco: Number(e.target.value) }))} /></label>
            <label className="field"><span>Testo gioco</span><textarea rows={4} value={cardForm.testo_gioco || ""} onChange={(e) => setCardForm((p) => ({ ...p, testo_gioco: e.target.value }))} /></label>
            <p className="sub">Campi avanzati (MSE / Arena):</p>
            <JsonField label="studio_carta_spec" value={studioSpecText} setValue={setStudioSpecText} />
            <JsonField label="arena_playable_spec" value={playableSpecText} setValue={setPlayableSpecText} />
            <JsonField label="mse_campi" value={mseCampiText} setValue={setMseCampiText} />
            <button type="button" onClick={handleSaveCard}>Salva carta</button>
            {cardForm.espansione && (
              <p className="hint">Espansione selezionata: {espansioniById[cardForm.espansione]?.nome || "n/d"}</p>
            )}
          </article>
        </section>
      )}

      {!loading && tab === "keywords" && (
        <section className="grid">
          <article>
            <h2>Keyword</h2>
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
            <h2>{kwId ? "Modifica keyword" : "Nuova keyword"}</h2>
            <label className="field"><span>Codice</span><input value={kwForm.codice} onChange={(e) => setKwForm((p) => ({ ...p, codice: e.target.value.toUpperCase() }))} /></label>
            <label className="field"><span>Nome</span><input value={kwForm.nome} onChange={(e) => setKwForm((p) => ({ ...p, nome: e.target.value }))} /></label>
            <label className="field"><span>Testo regola</span><textarea rows={4} value={kwForm.testo_regola || ""} onChange={(e) => setKwForm((p) => ({ ...p, testo_regola: e.target.value }))} /></label>
            <label className="field"><span>Reminder breve</span><input value={kwForm.reminder_breve || ""} onChange={(e) => setKwForm((p) => ({ ...p, reminder_breve: e.target.value }))} /></label>
            <label className="field"><span>MSE export mode</span><select value={kwForm.mse_export_mode} onChange={(e) => setKwForm((p) => ({ ...p, mse_export_mode: e.target.value }))}><option value="kor35">kor35</option><option value="mse_compat">mse_compat</option><option value="both">both</option></select></label>
            <label className="field"><span>MSE match pattern</span><input value={kwForm.mse_match_pattern || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_match_pattern: e.target.value }))} /></label>
            <label className="field"><span>MSE reminder template</span><textarea rows={3} value={kwForm.mse_reminder_template || ""} onChange={(e) => setKwForm((p) => ({ ...p, mse_reminder_template: e.target.value }))} /></label>
            <JsonField label="effect_script" value={effectScriptText} setValue={setEffectScriptText} />
            <button type="button" onClick={handleSaveKeyword}>Salva keyword</button>
          </article>
        </section>
      )}
      {!loading && tab === "giochi" && (
        <section className="grid">
          <article>
            <h2>Giochi supportati</h2>
            <ul>
              {giochi.map((g) => (
                <li key={g.id}>
                  <button type="button" onClick={() => setGiocoForm(g)}>
                    {g.nome} <small>({g.modello_base || "kor35"})</small>
                  </button>
                </li>
              ))}
            </ul>
          </article>
          <article>
            <h2>Definizione gioco (MSE Game)</h2>
            <label className="field"><span>Slug</span><input value={giocoForm.slug || ""} onChange={(e) => setGiocoForm((p) => ({ ...p, slug: e.target.value }))} /></label>
            <label className="field"><span>Nome</span><input value={giocoForm.nome || ""} onChange={(e) => setGiocoForm((p) => ({ ...p, nome: e.target.value }))} /></label>
            <label className="field">
              <span>Modello base</span>
              <select value={giocoForm.modello_base || "kor35"} onChange={(e) => setGiocoForm((p) => ({ ...p, modello_base: e.target.value }))}>
                <option value="kor35">kor35</option>
                <option value="mtg">mtg</option>
                <option value="custom">custom</option>
              </select>
            </label>
            <label className="field"><span>MSE game package</span><input value={giocoForm.mse_game_name || ""} onChange={(e) => setGiocoForm((p) => ({ ...p, mse_game_name: e.target.value }))} /></label>
            <p className="hint">Questo abilita giochi multipli (KOR35, MTG, custom) con template multipli nello stesso game.</p>
            <hr />
            <h3>Import template MSE (.mse-style/.zip)</h3>
            <label className="field">
              <span>File template</span>
              <input
                type="file"
                accept=".mse-style,.zip,application/zip"
                onChange={(e) => setMseStyleFile(e.target.files?.[0] || null)}
              />
            </label>
            <label className="field"><span>Nome template (opzionale)</span><input value={mseImportName} onChange={(e) => setMseImportName(e.target.value)} /></label>
            <label className="field"><span>Slug template (opzionale)</span><input value={mseImportSlug} onChange={(e) => setMseImportSlug(e.target.value)} /></label>
            <label className="field-checkbox">
              <input
                type="checkbox"
                checked={mseImportDefault}
                onChange={(e) => setMseImportDefault(e.target.checked)}
              />
              Imposta come default per nuove carte del gioco
            </label>
            <button type="button" onClick={handleImportMseStyle}>Importa template MSE</button>
          </article>
        </section>
      )}
    </main>
  );
}
