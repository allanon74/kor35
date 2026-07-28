import { useMemo, useState } from "react";
import MseFieldTable from "./MseFieldTable";

const CORE_KEYWORD_FIELDS = [
  {
    name: "code",
    type: "text",
    description: "Short keyword code (KOR35: codice).",
  },
  {
    name: "name",
    type: "text",
    identifying: true,
    description: "Keyword name as it appears in rules text.",
  },
  {
    name: "reminder",
    type: "text",
    description: "Brief reminder text shown to players.",
  },
  {
    name: "rules",
    type: "text",
    multi_line: true,
    description: "Full keyword rules (KOR35: testo_regola).",
  },
];

export default function MseKeywordsTab({
  keywords,
  kwId,
  kwForm,
  setKwForm,
  gameKeywordModes,
  effectScriptText,
  setEffectScriptText,
  onSelectKeyword,
  onNewKeyword,
}) {
  const [statusText, setStatusText] = useState("");

  const fields = useMemo(() => {
    const rows = [...CORE_KEYWORD_FIELDS];
    if (gameKeywordModes.length) {
      rows.push({
        name: "mode",
        type: "choice",
        choices: gameKeywordModes.map((m) => ({ name: m })),
        description: "Keyword mode from game definition (MSE keyword mode).",
      });
    }
    return rows;
  }, [gameKeywordModes]);

  const getValue = (field) => {
    const k = field.name;
    if (k === "code") return kwForm.codice || "";
    if (k === "name") return kwForm.nome || "";
    if (k === "reminder") return kwForm.reminder_breve || "";
    if (k === "rules") return kwForm.testo_regola || "";
    if (k === "mode") return kwForm.mse_match_pattern || gameKeywordModes[0] || "";
    return "";
  };

  const setValue = (field, raw) => {
    const k = field.name;
    if (k === "code") return setKwForm((p) => ({ ...p, codice: String(raw).toUpperCase() }));
    if (k === "name") return setKwForm((p) => ({ ...p, nome: String(raw) }));
    if (k === "reminder") return setKwForm((p) => ({ ...p, reminder_breve: String(raw) }));
    if (k === "rules") return setKwForm((p) => ({ ...p, testo_regola: String(raw) }));
    if (k === "mode") return setKwForm((p) => ({ ...p, mse_match_pattern: String(raw) }));
    return undefined;
  };

  return (
    <section className="mse-keywords-tab">
      <aside className="mse-pane mse-pane-list">
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Keywords</h2>
          <button type="button" className="mse-btn-small" onClick={onNewKeyword}>
            +
          </button>
        </div>
        <div className="mse-card-list-scroll">
          <table className="mse-card-list-table">
            <thead>
              <tr>
                <th>Code</th>
                <th>Name</th>
              </tr>
            </thead>
            <tbody>
              {keywords.map((row) => (
                <tr
                  key={row.id}
                  className={row.id === kwId ? "selected" : ""}
                  onClick={() => onSelectKeyword(row)}
                >
                  <td>{row.codice}</td>
                  <td>{row.nome}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </aside>

      <div className="mse-pane mse-pane-fields">
        <h2 className="mse-pane-title">Keyword fields</h2>
        <MseFieldTable fields={fields} getValue={getValue} setValue={setValue} onStatusChange={setStatusText} />
        <details className="mse-kor35-panel">
          <summary>KOR35 / MSE export (optional)</summary>
          <div className="mse-kor35-grid">
            <label>
              <span>MSE export mode</span>
              <select
                value={kwForm.mse_export_mode || "kor35"}
                onChange={(e) => setKwForm((p) => ({ ...p, mse_export_mode: e.target.value }))}
              >
                <option value="kor35">kor35</option>
                <option value="mse_compat">mse_compat</option>
                <option value="both">both</option>
              </select>
            </label>
            <label>
              <span>MSE match pattern</span>
              <input
                value={kwForm.mse_match_pattern || ""}
                onChange={(e) => setKwForm((p) => ({ ...p, mse_match_pattern: e.target.value }))}
              />
            </label>
            <label>
              <span>MSE reminder template</span>
              <textarea
                rows={2}
                value={kwForm.mse_reminder_template || ""}
                onChange={(e) => setKwForm((p) => ({ ...p, mse_reminder_template: e.target.value }))}
              />
            </label>
            <label>
              <span>effect_script (JSON)</span>
              <textarea rows={4} value={effectScriptText} onChange={(e) => setEffectScriptText(e.target.value)} />
            </label>
          </div>
        </details>
      </div>

      <footer className="mse-statusbar">{statusText || "Keywords expand in rules text according to the game keyword modes."}</footer>
    </section>
  );
}
