import MseFieldTable from "./MseFieldTable";

export default function MseSetTab({
  espansioni,
  espId,
  onSelectSet,
  gameSetFields,
  getSetSpecValue,
  setSetSpecValue,
  packages,
  espForm,
  setEspForm,
  giochi,
  templates,
  importGameId,
  onImportGameChange,
  mseSetFile,
  onMseSetFile,
  mseSetImportName,
  onMseSetImportName,
  mseSetImportSlug,
  onMseSetImportSlug,
  onImportSet,
  importingSet,
}) {
  return (
    <section className="mse-set-tab">
      <aside className="mse-pane mse-pane-list">
        <h2 className="mse-pane-title">Sets</h2>
        <div className="mse-card-list-scroll">
          <table className="mse-card-list-table">
            <thead>
              <tr>
                <th>Title</th>
                <th>Code</th>
              </tr>
            </thead>
            <tbody>
              {espansioni.map((row) => (
                <tr
                  key={row.id}
                  className={row.id === espId ? "selected" : ""}
                  onClick={() => onSelectSet(row)}
                >
                  <td>{row.nome}</td>
                  <td>{row.slug}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <details className="mse-kor35-panel mse-inline-details">
          <summary>Import set (.mse-set)</summary>
          <label>
            <span>Game</span>
            <select value={importGameId || ""} onChange={(e) => onImportGameChange(e.target.value)}>
              <option value="">— select —</option>
              {giochi.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nome}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Package file (.mse-set / .zip)</span>
            <input type="file" accept=".mse-set,.zip,application/zip" onChange={(e) => onMseSetFile(e.target.files?.[0] || null)} />
          </label>
          <label>
            <span>Title override</span>
            <input value={mseSetImportName} onChange={(e) => onMseSetImportName(e.target.value)} />
          </label>
          <label>
            <span>Code override</span>
            <input value={mseSetImportSlug} onChange={(e) => onMseSetImportSlug(e.target.value)} />
          </label>
          <button type="button" onClick={onImportSet} disabled={importingSet}>
            {importingSet ? "Importing…" : "Import set"}
          </button>
        </details>
      </aside>

      <div className="mse-pane mse-pane-fields">
        <h2 className="mse-pane-title">Set fields</h2>
        {gameSetFields.length > 0 ? (
          <MseFieldTable
            fields={gameSetFields}
            getValue={getSetSpecValue}
            setValue={setSetSpecValue}
            packages={packages}
          />
        ) : (
          <div className="mse-kor35-grid">
            <label>
              <span>title</span>
              <input value={espForm.nome} onChange={(e) => setEspForm((p) => ({ ...p, nome: e.target.value }))} />
            </label>
            <label>
              <span>code</span>
              <input value={espForm.slug} onChange={(e) => setEspForm((p) => ({ ...p, slug: e.target.value }))} />
            </label>
            <label>
              <span>description</span>
              <textarea rows={4} value={espForm.descrizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, descrizione: e.target.value }))} />
            </label>
          </div>
        )}
        <details className="mse-kor35-panel">
          <summary>KOR35 integration (optional)</summary>
          <div className="mse-kor35-grid">
            <label>
              <span>Game</span>
              <select value={espForm.gioco_definizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, gioco_definizione: e.target.value || null }))}>
                <option value="">— none —</option>
                {giochi.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.nome}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Default stylesheet</span>
              <select value={espForm.default_studio_template || ""} onChange={(e) => setEspForm((p) => ({ ...p, default_studio_template: e.target.value || null }))}>
                <option value="">— game default —</option>
                {templates
                  .filter((t) => !espForm.gioco_definizione || t.gioco_definizione === espForm.gioco_definizione)
                  .map((t) => (
                    <option key={t.id} value={t.id}>
                      {t.nome}
                      {t.is_default_for_new_cards ? " *" : ""}
                    </option>
                  ))}
              </select>
            </label>
            <label>
              <span>MSE set reference</span>
              <input
                value={espForm.mse_set_riferimento || ""}
                onChange={(e) => setEspForm((p) => ({ ...p, mse_set_riferimento: e.target.value }))}
              />
            </label>
          </div>
        </details>
      </div>

      <footer className="mse-statusbar">Set fields map to EspansioneCarte when integrated with KOR35.</footer>
    </section>
  );
}
