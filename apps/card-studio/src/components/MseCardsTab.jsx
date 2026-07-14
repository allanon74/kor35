import { useMemo, useRef, useState } from "react";
import MseCardList from "./MseCardList";
import MseCardPreview, { useMseCardRender } from "./MseCardPreview";
import MseFieldTable from "./MseFieldTable";
import { readCardFieldValue, writeCardFieldPatch } from "../mse/cardFieldBridge";
import { exportCardPngFromRender } from "../mse/exportCardPng";

import MseEditorActions from "./MseEditorActions";

export default function MseCardsTab({
  cardForm,
  setCardForm,
  cardId,
  isNewCard,
  cardFilter,
  setCardFilter,
  filteredCards,
  gameCardFields,
  gameCardListColumns,
  cardListRowStyle,
  onSelectCard,
  onNewCard,
  onDeleteCard,
  onSaveCard,
  saveCardLabel,
  canDeleteCard,
  selectNeighborCard,
  selectedGameId,
  espansioni,
  templatesForSelectedGame,
  updateCardField,
  updateTemplateByGame,
  packages,
  activeTemplate,
  espansioniById,
  stylingValues,
  onPickFile,
  onStatusMessage,
  onMseCampiSync,
}) {
  const [statusText, setStatusText] = useState("");
  const [exporting, setExporting] = useState(false);
  const previewRef = useRef(null);

  const getValue = (field) => readCardFieldValue(cardForm, field);
  const setValue = (field, raw) => {
    setCardForm((prev) => {
      const next = writeCardFieldPatch(prev, field, raw);
      if (next.mse_campi !== prev.mse_campi) {
        onMseCampiSync?.(next.mse_campi || {});
      }
      return next;
    });
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
      <div className="mse-card-context-bar">
        <label>
          <span>Card set</span>
          <select
            value={cardForm.espansione || ""}
            onChange={(e) => updateCardField("espansione", e.target.value || null)}
            disabled={!selectedGameId}
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
                {t.is_default_for_new_cards ? " (default)" : ""}
              </option>
            ))}
          </select>
        </label>
        {!selectedGameId && (
          <p className="mse-empty-hint">Seleziona un gioco nella barra in alto per campi e stylesheet corretti.</p>
        )}
        {selectedGameId && !templatesForSelectedGame.length && (
          <p className="mse-empty-hint">
            Nessuno stylesheet per questo gioco — passa a <strong>Magic</strong> (import MTG) o <strong>KOR35</strong> (
            kor35-standard).
          </p>
        )}
        {selectedGameId && !gameCardFields.length && (
          <p className="mse-empty-hint">Il gioco selezionato non espone campi carta MSE (mse_game_spec).</p>
        )}
      </div>

      <aside className="mse-pane mse-pane-list">
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Card list</h2>
          <div className="mse-crud-actions">
            <button type="button" className="mse-btn-small" onClick={onNewCard} title="Nuova carta">
              + Nuova
            </button>
            {canDeleteCard && (
              <button type="button" className="mse-btn-small mse-btn-danger" onClick={onDeleteCard} title="Elimina carta">
                Elimina
              </button>
            )}
          </div>
        </div>
        {isNewCard && (
          <p className="mse-crud-hint">Modalità creazione: compila i campi e premi «Crea carta» (barra blu sotto i tab o in fondo ai campi).</p>
        )}
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
        <div className="mse-pane-title-row">
          <h2 className="mse-pane-title">Card fields</h2>
        </div>
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
        <MseEditorActions
          saveLabel={saveCardLabel}
          onSave={onSaveCard}
          deleteLabel={canDeleteCard ? "Elimina carta" : ""}
          onDelete={canDeleteCard ? onDeleteCard : null}
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
        <summary>KOR35 sync (optional JSON)</summary>
        <p className="mse-empty-hint">
          Set e stylesheet si gestiscono sopra. Usa questa sezione solo per override JSON avanzati su sync edge.
        </p>
      </details>

      <footer className="mse-statusbar">{statusText || "Move the mouse over a field to see its description."}</footer>
    </section>
  );
}
