import { useState } from "react";

export default function MseStatisticsTab({
  statisticsReport,
  statsEspansioneId,
  onStatsEspansioneId,
  espansioni,
  selectedGameId,
  metaCounts,
}) {
  const [statusText, setStatusText] = useState("");

  return (
    <section className="mse-stats-tab">
      <div className="mse-pane mse-pane-fields mse-stats-main">
        <h2 className="mse-pane-title">Set statistics</h2>
        <div className="mse-stats-toolbar">
          <label>
            <span>Card pool</span>
            <select value={statsEspansioneId} onChange={(e) => onStatsEspansioneId(e.target.value)}>
              <option value="">All cards (current game)</option>
              {espansioni
                .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
            </select>
          </label>
          <span className="mse-stats-total">
            <strong>{statisticsReport.total}</strong> cards
          </span>
        </div>

        <table className="mse-field-table mse-stats-meta-table">
          <tbody>
            <tr>
              <td>Sets</td>
              <td>{metaCounts.sets}</td>
            </tr>
            <tr>
              <td>Keywords</td>
              <td>{metaCounts.keywords}</td>
            </tr>
            <tr>
              <td>Stylesheets</td>
              <td>{metaCounts.templates}</td>
            </tr>
            <tr>
              <td>Dimensions</td>
              <td>{statisticsReport.dimensions.length}</td>
            </tr>
          </tbody>
        </table>

        {statisticsReport.dimensions.map((dim) => (
          <article
            key={dim.key}
            className="stats-dimension"
            onMouseEnter={() => setStatusText(`Statistics dimension: ${dim.label} (show_statistics card field)`)}
          >
            <h3 className="mse-sub-title">{dim.label}</h3>
            <table className="stats-table">
              <thead>
                <tr>
                  <th>Value</th>
                  <th>Count</th>
                  <th>%</th>
                  <th>Graph</th>
                </tr>
              </thead>
              <tbody>
                {dim.rows.map((row) => (
                  <tr key={`${dim.key}-${row.label}`}>
                    <td>{row.label}</td>
                    <td>{row.count}</td>
                    <td>{row.pct}%</td>
                    <td>
                      <div className="stats-bar-track">
                        <div
                          className="stats-bar-fill"
                          style={{
                            width: `${Math.max(4, row.pct)}%`,
                            backgroundColor: row.color || "#316ac5",
                          }}
                        />
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </article>
        ))}
        {!statisticsReport.dimensions.length && (
          <p className="mse-empty-hint">No statistics dimensions — enable show_statistics on choice fields in the game spec.</p>
        )}
      </div>

      <footer className="mse-statusbar">
        {statusText || "Statistics use card fields with show_statistics from the game definition."}
      </footer>
    </section>
  );
}
