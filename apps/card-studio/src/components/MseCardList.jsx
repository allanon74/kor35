import { cardFieldValue, formatFieldValueForDisplay } from "../mse/fieldUtils";

export default function MseCardList({
  columns,
  cards,
  selectedId,
  onSelect,
  rowStyle,
  filter,
  onFilterChange,
  onPrev,
  onNext,
}) {
  return (
    <div className="mse-card-list">
      <div className="mse-card-list-toolbar">
        <input
          className="mse-field-input"
          value={filter}
          onChange={(e) => onFilterChange(e.target.value)}
          placeholder="Filter cards…"
        />
        <div className="mse-card-list-nav">
          <button type="button" className="mse-btn-small" onClick={onPrev}>
            ◀
          </button>
          <button type="button" className="mse-btn-small" onClick={onNext}>
            ▶
          </button>
        </div>
      </div>
      <div className="mse-card-list-scroll">
        <table className="mse-card-list-table">
          <thead>
            <tr>
              {columns.map((c) => (
                <th key={c.key} style={{ width: `${Math.max(48, Number(c.width || 100))}px`, textAlign: c.align || "left" }}>
                  {c.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {cards.map((row) => {
              const active = row.id === selectedId;
              return (
                <tr
                  key={row.id}
                  className={active ? "selected" : ""}
                  style={rowStyle?.(row)}
                  onClick={() => onSelect(row)}
                >
                  {columns.map((c) => {
                    const val =
                      c.key === "nome"
                        ? row.nome
                        : c.key === "codice"
                          ? row.codice
                          : cardFieldValue(row, { name: c.key }) || row.mse_campi?.[c.key];
                    return (
                      <td key={c.key} style={{ textAlign: c.align || "left" }}>
                        {formatFieldValueForDisplay(val, { name: c.key })}
                      </td>
                    );
                  })}
                </tr>
              );
            })}
          </tbody>
        </table>
        {!cards.length && <p className="mse-empty-hint">Nessuna carta nel pool corrente.</p>}
      </div>
    </div>
  );
}
