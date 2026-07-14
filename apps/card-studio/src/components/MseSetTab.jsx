import MseFieldTable from "./MseFieldTable";

import MseEditorActions from "./MseEditorActions";

export default function MseSetTab({
  espansioni,
  espId,
  isNewSet,
  onSelectSet,
  onNewSet,
  onDeleteSet,
  onSaveSet,
  saveSetLabel,
  canDeleteSet,
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
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Sets (espansioni)</h2>
          <div className="mse-crud-actions">
            <button type="button" className="mse-btn-small" onClick={onNewSet} title="Nuovo set">
              + Nuovo
            </button>
            {canDeleteSet && (
              <button type="button" className="mse-btn-small mse-btn-danger" onClick={onDeleteSet} title="Elimina set">
                Elimina
              </button>
            )}
          </div>
        </div>
        {isNewSet && (
          <p className="mse-crud-hint">Nuovo set: titolo e codice obbligatori — poi «Crea set» (barra blu sotto i tab).</p>
        )}
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
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Set fields</h2>
        </div>
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
        <MseEditorActions
          saveLabel={saveSetLabel}
          onSave={onSaveSet}
          deleteLabel={canDeleteSet ? "Elimina set" : ""}
          onDelete={canDeleteSet ? onDeleteSet : null}
        />
      </div>

      <footer className="mse-statusbar">
        Set = espansione KOR35 (stesso record DB). Collega gioco e stylesheet default per le carte del set.
      </footer>
    </section>
  );
}
