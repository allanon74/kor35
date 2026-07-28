/** Barra azioni salva/elimina visibile durante l’editing (Cards, Set, …). */
export default function MseEditorActions({
  saveLabel,
  onSave,
  deleteLabel,
  onDelete,
  hint,
}) {
  if (!onSave && !onDelete) return null;
  return (
    <div className="mse-editor-actions">
      <div className="mse-editor-actions-buttons">
        {onSave && (
          <button type="button" className="mse-btn-primary" onClick={onSave}>
            {saveLabel || "Salva"}
          </button>
        )}
        {onDelete && (
          <button type="button" className="mse-btn-danger" onClick={onDelete}>
            {deleteLabel || "Elimina"}
          </button>
        )}
      </div>
      {hint ? <p className="mse-editor-actions-hint">{hint}</p> : null}
    </div>
  );
}
