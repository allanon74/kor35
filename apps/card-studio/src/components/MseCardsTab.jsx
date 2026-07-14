import { useMemo, useRef, useState } from "react";
import MseCardList from "./MseCardList";
import MseCardPreview, { useMseCardRender } from "./MseCardPreview";
import MseFieldTable from "./MseFieldTable";
import { readCardFieldValue, writeCardFieldPatch } from "../mse/cardFieldBridge";
import { exportCardPngFromRender } from "../mse/exportCardPng";

export default function MseCardsTab({
  cardForm,
  setCardForm,
  cardId,
  cardFilter,
  setCardFilter,
  filteredCards,
  gameCardFields,
  gameCardListColumns,
  cardListRowStyle,
  onSelectCard,
  selectNeighborCard,
  selectedGameId,
  giochi,
  espansioni,
  templatesForSelectedGame,
  updateCardField,
  updateTemplateByGame,
  onGameChange,
  packages,
  activeTemplate,
  espansioniById,
  stylingValues,
  onPickFile,
  onStatusMessage,
}) {
  const [statusText, setStatusText] = useState("");
  const [exporting, setExporting] = useState(false);
  const previewRef = useRef(null);

  const getValue = (field) => readCardFieldValue(cardForm, field);
  const setValue = (field, raw) => {
    setCardForm((prev) => writeCardFieldPatch(prev, field, raw));
  };

  const hasMsePreview = Boolean(activeTemplate?.layout_spec?.mse_v1?.card_styles);
  const cardFrameSize = useMemo(() => {
    const mse = activeTemplate?.layout_spec?.mse_v1;
    const w = activeTemplate?.layout_spec?.card_width_px || mse?.card_size?.width || 375;
    const h = activeTemplate?.layout_spec?.card_height_px || mse?.card_size?.height || 523;
    return { width: Math.round(Number(w) || 375), height: Math.round(Number(h) || 523) };
  }, [activeTemplate]);

  const setData = cardForm.espansione
    ? espansioniById[cardForm.espansione]?.studio_set_spec?.mse_set_fields || {}
    : {};

  const cardRender = useMseCardRender({
    template: activeTemplate,
    cardForm,
    gameCardFields,
    styling: stylingValues,
    setData,
    getFieldValue: getValue,
    packages,
  });

  const handleExportPng = async () => {
    if (!hasMsePreview) {
      onStatusMessage?.("Import a stylesheet with MSE layout before exporting PNG.");
      return;
    }
    setExporting(true);
    try {
      const dpi = activeTemplate?.layout_spec?.dpi || activeTemplate?.layout_spec?.mse_v1?.card_size?.dpi || 300;
      await exportCardPngFromRender(cardRender, {
        dpi,
        fileName: `${(cardForm.codice || cardForm.nome || "card").replace(/[^\w.-]+/g, "_")}.png`,
      });
      onStatusMessage?.("PNG exported.");
    } catch (err) {
      onStatusMessage?.(err.message || "Export PNG failed.");
    } finally {
      setExporting(false);
    }
  };

  return (
    <section className="mse-cards-tab">
      <aside className="mse-pane mse-pane-list">
        <h2 className="mse-pane-title">Card list</h2>
        <MseCardList
          columns={gameCardListColumns}
          cards={filteredCards}
          selectedId={cardId}
          onSelect={onSelectCard}
          rowStyle={cardListRowStyle}
          filter={cardFilter}
          onFilterChange={setCardFilter}
          onPrev={() => selectNeighborCard(-1)}
          onNext={() => selectNeighborCard(1)}
        />
      </aside>

      <div className="mse-pane mse-pane-fields">
        <h2 className="mse-pane-title">Card fields</h2>
        <MseFieldTable
          fields={gameCardFields}
          getValue={getValue}
          setValue={setValue}
          packages={packages}
          onPickFile={onPickFile}
          onStatusChange={(t) => {
            setStatusText(t);
            onStatusMessage?.(t);
          }}
        />
      </div>

      <aside className="mse-pane mse-pane-preview">
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Card preview</h2>
          <button type="button" className="mse-btn-small" onClick={handleExportPng} disabled={exporting || !hasMsePreview}>
            {exporting ? "…" : "PNG"}
          </button>
        </div>
        <div
          className="mse-preview-frame"
          style={{ width: `${cardFrameSize.width}px`, height: `${cardFrameSize.height}px` }}
        >
          {hasMsePreview ? (
            <MseCardPreview
              template={activeTemplate}
              cardForm={cardForm}
              gameCardFields={gameCardFields}
              styling={stylingValues}
              setData={setData}
              getFieldValue={getValue}
              packages={packages}
              previewRef={previewRef}
              className="mse-fill"
            />
          ) : (
            <div className="mse-preview-fallback">
              <p>{cardForm.nome || "Untitled card"}</p>
              <p className="mse-preview-code">{cardForm.codice || "—"}</p>
              <p className="mse-preview-rules">{cardForm.testo_gioco || "Import a stylesheet (.mse-style) for WYSIWYG preview."}</p>
            </div>
          )}
        </div>
        <p className="mse-preview-meta">
          {activeTemplate?.nome || "No stylesheet"} · {cardFrameSize.width}×{cardFrameSize.height}px
        </p>
      </aside>

      <details className="mse-kor35-panel">
        <summary>KOR35 integration (optional)</summary>
        <div className="mse-kor35-grid">
          <label>
            <span>Set / expansion</span>
            <select
              value={cardForm.espansione || ""}
              onChange={(e) => updateCardField("espansione", e.target.value || null)}
            >
              <option value="">— none —</option>
              {espansioni
                .filter((e) => !selectedGameId || e.gioco_definizione === selectedGameId)
                .map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.nome}
                  </option>
                ))}
            </select>
          </label>
          <label>
            <span>Game</span>
            <select
              value={selectedGameId || ""}
              onChange={(e) => onGameChange?.(e.target.value)}
              disabled={Boolean(cardId || cardForm.espansione)}
            >
              <option value="">— select —</option>
              {giochi.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.nome}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Stylesheet</span>
            <select
              value={cardForm.studio_template || ""}
              onChange={(e) => updateTemplateByGame(e.target.value)}
              disabled={!selectedGameId}
            >
              <option value="">— default —</option>
              {templatesForSelectedGame.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.nome}
                </option>
              ))}
            </select>
          </label>
        </div>
        <p className="mse-empty-hint">
          Collega set e stylesheet solo se la carta deve partecipare al catalogo KOR35 / sync edge.
        </p>
      </details>

      <footer className="mse-statusbar">{statusText || "Move the mouse over a field to see its description."}</footer>
    </section>
  );
}
