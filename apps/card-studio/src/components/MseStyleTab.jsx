import { useMemo, useState } from "react";
import MseCardPreview from "./MseCardPreview";
import MseFieldTable from "./MseFieldTable";
import { readCardFieldValue } from "../mse/cardFieldBridge";
import { normFieldKey } from "../mse/fieldUtils";

export default function MseStyleTab({
  templates,
  selectedGameId,
  previewTemplateId,
  onSelectTemplate,
  cardForm,
  gameCardFields,
  stylingValues,
  onStylingChange,
  packages,
  espansioniById,
  importGameId,
  onImportGameChange,
  giochi,
  mseStyleFile,
  onMseStyleFile,
  mseImportName,
  onMseImportName,
  mseImportSlug,
  onMseImportSlug,
  mseImportDefault,
  onMseImportDefault,
  onImport,
}) {
  const [statusText, setStatusText] = useState("");

  const previewTemplate = useMemo(
    () => templates.find((t) => t.id === previewTemplateId) || null,
    [templates, previewTemplateId]
  );
  const mseV1 = previewTemplate?.layout_spec?.mse_v1 || null;
  const stylingFields = useMemo(
    () =>
      (mseV1?.styling_fields || []).map((f) => ({
        ...f,
        description:
          f.description ||
          "Styling field from stylesheet — affects card appearance for the current card.",
      })),
    [mseV1]
  );

  const cardFrameSize = useMemo(() => {
    const w = previewTemplate?.layout_spec?.card_width_px || mseV1?.card_size?.width || 375;
    const h = previewTemplate?.layout_spec?.card_height_px || mseV1?.card_size?.height || 523;
    return { width: Math.round(Number(w) || 375), height: Math.round(Number(h) || 523) };
  }, [previewTemplate, mseV1]);

  const filteredTemplates = templates.filter(
    (t) => !selectedGameId || t.gioco_definizione === selectedGameId
  );

  const getStylingValue = (field) => {
    const k = field.name;
    return stylingValues[k] ?? stylingValues[normFieldKey(k)] ?? field.initial ?? "";
  };

  const setStylingValue = (field, raw) => {
    onStylingChange(field, raw);
  };

  const getCardValue = (field) => readCardFieldValue(cardForm, field);
  const setData = cardForm.espansione
    ? espansioniById[cardForm.espansione]?.studio_set_spec?.mse_set_fields || {}
    : {};

  return (
    <section className="mse-style-tab">
      <aside className="mse-pane mse-pane-list">
        <h2 className="mse-pane-title">Stylesheets</h2>
        <div className="mse-card-list-scroll">
          <table className="mse-card-list-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Slug</th>
              </tr>
            </thead>
            <tbody>
              {filteredTemplates.map((t) => (
                <tr
                  key={t.id}
                  className={t.id === previewTemplateId ? "selected" : ""}
                  onClick={() => onSelectTemplate(t.id)}
                >
                  <td>
                    {t.nome}
                    {t.is_default_for_new_cards ? " *" : ""}
                  </td>
                  <td>{t.slug}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {!filteredTemplates.length && (
            <p className="mse-empty-hint">
              Nessuno stylesheet per il gioco selezionato. Gli import MTG (328) sono sul gioco{" "}
              <strong>Magic</strong>; il template KOR35 (<code>kor35-standard</code>) è sul gioco{" "}
              <strong>KOR35</strong>. Non serve re-importare: cambia gioco nella barra in alto.
            </p>
          )}
        </div>
        <details className="mse-kor35-panel mse-inline-details">
          <summary>Import stylesheet</summary>
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
            <span>Package file (.mse-style / .zip)</span>
            <input type="file" accept=".mse-style,.zip,application/zip" onChange={(e) => onMseStyleFile(e.target.files?.[0] || null)} />
          </label>
          <label>
            <span>Name override</span>
            <input value={mseImportName} onChange={(e) => onMseImportName(e.target.value)} />
          </label>
          <label>
            <span>Slug override</span>
            <input value={mseImportSlug} onChange={(e) => onMseImportSlug(e.target.value)} />
          </label>
          <label className="field-checkbox">
            <input type="checkbox" checked={mseImportDefault} onChange={(e) => onMseImportDefault(e.target.checked)} />
            <span>Default for new cards</span>
          </label>
          <button type="button" onClick={onImport}>
            Import
          </button>
        </details>
      </aside>

      <div className="mse-pane mse-pane-fields">
        <h2 className="mse-pane-title">Styling fields</h2>
        {stylingFields.length ? (
          <MseFieldTable
            fields={stylingFields}
            getValue={getStylingValue}
            setValue={setStylingValue}
            packages={packages}
            onStatusChange={setStatusText}
          />
        ) : (
          <p className="mse-empty-hint">
            {previewTemplate
              ? "This stylesheet has no styling fields in layout_spec.mse_v1."
              : "Select a stylesheet to edit styling fields."}
          </p>
        )}
        {mseV1 && (
          <p className="mse-preview-meta">
            {Object.keys(mseV1.card_styles || {}).length} card styles ·{" "}
            {Object.keys(mseV1.extra_card_styles || {}).length} extra · DPI {mseV1.card_size?.dpi || 96}
          </p>
        )}
      </div>

      <aside className="mse-pane mse-pane-preview">
        <h2 className="mse-pane-title">Preview (current card)</h2>
        <div
          className="mse-preview-frame"
          style={{ width: `${cardFrameSize.width}px`, height: `${cardFrameSize.height}px` }}
        >
          {mseV1?.card_styles ? (
            <MseCardPreview
              template={previewTemplate}
              cardForm={cardForm}
              gameCardFields={gameCardFields}
              styling={stylingValues}
              setData={setData}
              getFieldValue={getCardValue}
              packages={packages}
              className="mse-fill"
            />
          ) : (
            <div className="mse-preview-fallback">
              <p>Import or select a stylesheet with MSE layout to preview.</p>
            </div>
          )}
        </div>
      </aside>

      <footer className="mse-statusbar">
        {statusText || "Styling fields control template appearance; values are saved on the current card."}
      </footer>
    </section>
  );
}
