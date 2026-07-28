import { useState } from "react";
import { packageDisplayName } from "../mse/symbolFonts";
import { mseColorToCss, normFieldKey, wildcardMatch } from "../mse/fieldUtils";
import { fieldStatusDescription, fieldTypeLabel, sortCardFieldsForEditor } from "../mse/fieldMeta";

function packageOptions(field, packages) {
  const staticChoices = (field.choices || []).map((c) => c.name).filter(Boolean);
  const match = String(field.match || "").trim();
  if (!match) return staticChoices;
  return (packages || [])
    .map((p) => packageDisplayName(p))
    .filter(Boolean)
    .filter((name) => wildcardMatch(match, name));
}

function FieldValueEditor({ field, value, packages, onChange, onPickFile }) {
  const fType = String(field.type || "text").toLowerCase();
  const editable = field.editable !== false;
  const options = (field.choices || []).map((c) => c.name).filter(Boolean);

  if (!editable) {
    return <span className="mse-field-readonly">{String(value ?? "—")}</span>;
  }

  if (fType === "info") {
    return <span className="mse-field-info">{field.description || field.name}</span>;
  }

  if (fType === "choice" || fType === "boolean") {
    const choiceOpts = fType === "boolean" ? ["yes", "no"] : options;
    const required = fType === "boolean" ? true : field.required !== false;
    const emptyLabel = field.empty_name || "None";
    const strVal = fType === "boolean" ? (value === true || value === "yes" ? "yes" : "no") : String(value || "");
    return (
      <select className="mse-field-input" value={strVal} onChange={(e) => onChange(e.target.value)}>
        {!required && fType !== "boolean" && <option value="">{emptyLabel}</option>}
        {choiceOpts.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  if (fType === "multiple choice") {
    const selected = Array.isArray(value)
      ? value.map(String)
      : String(value || "")
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean);
    return (
      <select
        className="mse-field-input"
        multiple
        size={Math.min(6, Math.max(3, options.length))}
        value={selected}
        onChange={(e) => onChange(Array.from(e.target.selectedOptions).map((o) => o.value))}
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
    const pkgOpts = packageOptions(field, packages);
    const required = field.required !== false;
    const emptyLabel = field.empty_name || "None";
    return (
      <select className="mse-field-input" value={String(value || "")} onChange={(e) => onChange(e.target.value)}>
        {!required && <option value="">{emptyLabel}</option>}
        {pkgOpts.map((opt) => (
          <option key={opt} value={opt}>
            {opt}
          </option>
        ))}
      </select>
    );
  }

  if (fType === "color") {
    const css = mseColorToCss(value) || "#808080";
    return (
      <div className="mse-color-row">
        <input type="color" value={css.startsWith("#") ? css : "#808080"} onChange={(e) => onChange(e.target.value)} />
        {options.length > 0 ? (
          <select className="mse-field-input" value={String(value || "")} onChange={(e) => onChange(e.target.value)}>
            <option value="">— custom —</option>
            {options.map((opt) => (
              <option key={opt} value={opt}>
                {opt}
              </option>
            ))}
          </select>
        ) : (
          <input className="mse-field-input" value={String(value || "")} onChange={(e) => onChange(e.target.value)} />
        )}
      </div>
    );
  }

  if (fType === "image" || fType === "symbol") {
    return (
      <div className="mse-path-row">
        <input className="mse-field-input" value={String(value || "")} onChange={(e) => onChange(e.target.value)} />
        <button type="button" className="mse-btn-small" onClick={() => onPickFile?.(field)}>
          Browse…
        </button>
      </div>
    );
  }

  if (fType === "number" || fType === "int") {
    return (
      <input
        className="mse-field-input"
        type="number"
        value={value ?? 0}
        onChange={(e) => onChange(Number(e.target.value))}
      />
    );
  }

  if (field.multi_line) {
    return (
      <textarea
        className="mse-field-input mse-field-textarea"
        rows={5}
        value={String(value || "")}
        onChange={(e) => onChange(e.target.value)}
      />
    );
  }

  return <input className="mse-field-input" value={String(value || "")} onChange={(e) => onChange(e.target.value)} />;
}

export default function MseFieldTable({
  fields,
  getValue,
  setValue,
  packages,
  onPickFile,
  onStatusChange,
  extraRows,
}) {
  const [hoverField, setHoverField] = useState(null);
  const sorted = sortCardFieldsForEditor(fields);

  const showStatus = (field) => {
    setHoverField(field);
    onStatusChange?.(fieldStatusDescription(field));
  };

  return (
    <div className="mse-field-table-wrap">
      <table className="mse-field-table">
        <thead>
          <tr>
            <th>Field</th>
            <th>Value</th>
          </tr>
        </thead>
        <tbody>
          {(extraRows || []).map((row) => (
            <tr key={row.key} onMouseEnter={() => onStatusChange?.(row.status || row.label)}>
              <td className="mse-field-name">{row.label}</td>
              <td>{row.render()}</td>
            </tr>
          ))}
          {sorted.map((field) => {
            const fType = String(field.type || "text").toLowerCase();
            if (fType === "info") {
              return (
                <tr key={`info-${field.name}`} className="mse-field-info-row">
                  <td colSpan={2}>{field.description || field.name}</td>
                </tr>
              );
            }
            const val = getValue(field);
            return (
              <tr
                key={field.name}
                className={field.editable === false ? "mse-field-row-readonly" : ""}
                onMouseEnter={() => showStatus(field)}
                onMouseLeave={() => {
                  setHoverField(null);
                  onStatusChange?.("");
                }}
              >
                <td className="mse-field-name">
                  {field.name}
                  <span className="mse-field-type">{fieldTypeLabel(field)}</span>
                </td>
                <td>
                  <FieldValueEditor
                    field={field}
                    value={val}
                    packages={packages}
                    onChange={(v) => setValue(field, v)}
                    onPickFile={onPickFile}
                  />
                </td>
              </tr>
            );
          })}
          {!sorted.length && (
            <tr>
              <td colSpan={2} className="mse-empty-hint">
                Nessun card field nel game selezionato.
              </td>
            </tr>
          )}
        </tbody>
      </table>
      {hoverField && <p className="mse-field-hover-hint">{fieldStatusDescription(hoverField)}</p>}
    </div>
  );
}
