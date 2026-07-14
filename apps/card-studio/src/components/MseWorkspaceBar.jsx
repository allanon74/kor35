export default function MseWorkspaceBar({
  giochi,
  selectedGameId,
  onGameChange,
  espansioni,
  selectedExpansionId,
  onExpansionChange,
  templatesCount,
  cardsCount,
}) {
  const selectedGame = giochi.find((g) => g.id === selectedGameId);
  const expansionsForGame = espansioni.filter(
    (e) => !selectedGameId || e.gioco_definizione === selectedGameId
  );

  return (
    <section className="mse-workspace-bar">
      <label className="mse-workspace-field">
        <span>Game</span>
        <select value={selectedGameId || ""} onChange={(e) => onGameChange(e.target.value)}>
          <option value="">— select game —</option>
          {giochi.map((g) => (
            <option key={g.id} value={g.id}>
              {g.nome}
              {g.modello_base === "kor35" ? " (KOR35)" : g.modello_base === "mtg" ? " (MTG)" : ""}
            </option>
          ))}
        </select>
      </label>
      <label className="mse-workspace-field">
        <span>Expansion / set</span>
        <select
          value={selectedExpansionId || ""}
          onChange={(e) => onExpansionChange(e.target.value || "")}
          disabled={!selectedGameId}
        >
          <option value="">— all expansions —</option>
          {expansionsForGame.map((e) => (
            <option key={e.id} value={e.id}>
              {e.nome}
            </option>
          ))}
        </select>
      </label>
      <div className="mse-workspace-meta">
        {selectedGame ? (
          <>
            <span>
              <strong>{selectedGame.nome}</strong>
              {selectedGame.modello_base === "kor35" ? " · campi KOR35" : ` · ${selectedGame.modello_base}`}
            </span>
            <span>{templatesCount} stylesheet{templatesCount === 1 ? "" : "s"}</span>
            <span>{cardsCount} card{cardsCount === 1 ? "" : "s"}</span>
          </>
        ) : (
          <span className="mse-empty-hint">Seleziona un gioco per vedere stylesheet e campi carta.</span>
        )}
      </div>
    </section>
  );
}
