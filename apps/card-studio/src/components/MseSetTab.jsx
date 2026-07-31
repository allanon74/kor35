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
  const gameId = espForm.gioco_definizione || "";
  const templatesForSet = (templates || []).filter(
    (t) => !gameId || t.gioco_definizione === gameId
  );
  const selectedTemplate = templatesForSet.find((t) => t.id === espForm.default_studio_template);

  const onGameChange = (nextGameId) => {
    const gid = nextGameId || null;
    setEspForm((p) => {
      const next = { ...p, gioco_definizione: gid };
      // Se il template attuale non appartiene al nuovo gioco, azzera.
      if (gid && p.default_studio_template) {
        const stillOk = (templates || []).some(
          (t) => t.id === p.default_studio_template && t.gioco_definizione === gid
        );
        if (!stillOk) next.default_studio_template = null;
      }
      if (!gid) next.default_studio_template = null;
      return next;
    });
  };

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
                  <td>{row.sigla || row.slug}</td>
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

        <div className="mse-set-defaults-panel" role="group" aria-label="Default rendering del set">
          <p className="mse-set-defaults-lead">
            Stylesheet di default per le carte di questo set. Le carte ereditanlo finché non scelgono un override.
          </p>
          <div className="mse-kor35-grid">
            <label>
              <span>Gioco del set</span>
              <select value={gameId} onChange={(e) => onGameChange(e.target.value)}>
                <option value="">— none —</option>
                {giochi.map((g) => (
                  <option key={g.id} value={g.id}>
                    {g.nome}
                  </option>
                ))}
              </select>
            </label>
            <label>
              <span>Default stylesheet (template carte)</span>
              <select
                value={espForm.default_studio_template || ""}
                onChange={(e) =>
                  setEspForm((p) => ({ ...p, default_studio_template: e.target.value || null }))
                }
                disabled={!gameId && templatesForSet.length === 0}
              >
                <option value="">— default del gioco —</option>
                {templatesForSet.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.nome}
                    {t.is_default_for_new_cards ? " *" : ""}
                  </option>
                ))}
              </select>
            </label>
          </div>
          {!gameId && (
            <p className="mse-empty-hint">Seleziona un gioco per elencare gli stylesheet disponibili.</p>
          )}
          {gameId && templatesForSet.length === 0 && (
            <p className="mse-empty-hint">
              Nessuno stylesheet per questo gioco — importane uno dal tab Style.
            </p>
          )}
          {selectedTemplate && (
            <p className="mse-set-defaults-current">
              Default attuale: <strong>{selectedTemplate.nome}</strong>
            </p>
          )}
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
              <input
                value={espForm.nome}
                onChange={(e) => {
                  const nome = e.target.value;
                  setEspForm((p) => {
                    const next = { ...p, nome };
                    if (!p.sigla) {
                      next.sigla = nome
                        .normalize("NFD")
                        .replace(/[\u0300-\u036f]/g, "")
                        .split(/[^A-Za-z0-9]+/)
                        .filter((t) => t && !["the", "a", "an", "of", "and", "di", "del", "la", "il", "e"].includes(t.toLowerCase()))
                        .map((t) => t[0])
                        .join("")
                        .toUpperCase()
                        .slice(0, 3);
                    }
                    return next;
                  });
                }}
              />
            </label>
            <label>
              <span>sigla (es. KBE)</span>
              <input
                value={espForm.sigla || ""}
                onChange={(e) =>
                  setEspForm((p) => ({
                    ...p,
                    sigla: e.target.value.replace(/[^A-Za-z0-9]/g, "").toUpperCase().slice(0, 8),
                  }))
                }
                placeholder="KBE"
              />
            </label>
            <label>
              <span>slug</span>
              <input value={espForm.slug} onChange={(e) => setEspForm((p) => ({ ...p, slug: e.target.value }))} />
            </label>
            <label>
              <span>description</span>
              <textarea rows={4} value={espForm.descrizione || ""} onChange={(e) => setEspForm((p) => ({ ...p, descrizione: e.target.value }))} />
            </label>
          </div>
        )}

        <details className="mse-kor35-panel">
          <summary>Riferimento MSE (opzionale)</summary>
          <div className="mse-kor35-grid">
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
        Tab Set → «Default stylesheet»: template MSE ereditato da tutte le carte del set (salvo override sulla carta).
      </footer>
    </section>
  );
}
