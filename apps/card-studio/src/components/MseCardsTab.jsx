import { useMemo, useRef, useState } from "react";
import MseCardList from "./MseCardList";
import MseCardPreview, { useMseCardRender } from "./MseCardPreview";
import MseFieldTable from "./MseFieldTable";
import { readCardFieldValue, writeCardFieldPatch } from "../mse/cardFieldBridge";
import { exportCardPngFromRender } from "../mse/exportCardPng";
import { normFieldKey } from "../mse/fieldUtils";

import MseEditorActions from "./MseEditorActions";

function findImageField(fields) {
  return (fields || []).find((f) => {
    const t = String(f?.type || "").toLowerCase();
    const k = normFieldKey(f?.name);
    return t === "image" || ["image", "art", "illustration", "immagine"].includes(k);
  });
}

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
  studioTemplateSourceLabel = "",
  resolvedStudioTemplateId = "",
  espansioniById,
  stylingValues,
  onPickFile,
  onStatusMessage,
  onMseCampiSync,
  onRenumberSetCodici,
  canRenumberSet,
  selectedExpansionId = "",
  onExpansionChange,
}) {
  const [statusText, setStatusText] = useState("");
  const [exporting, setExporting] = useState(false);
  const previewRef = useRef(null);
  const artFileRef = useRef(null);

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

  const imageField = useMemo(() => findImageField(gameCardFields), [gameCardFields]);
  const artPreview =
    cardForm.immagine_preview ||
    cardForm.immagine_url ||
    (imageField ? readCardFieldValue(cardForm, imageField) : "") ||
    "";

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

  const handleExportPng = async (targetDpi = 300) => {
    if (!hasMsePreview) {
      onStatusMessage?.("Importa uno stylesheet con layout MSE prima di esportare il PNG.");
      return;
    }
    setExporting(true);
    try {
      const dpi = Number(targetDpi) || 300;
      const safeName = String(cardForm.codice || cardForm.nome || "carta")
        .replace(/[^\w.-]+/g, "_")
        .replace(/^_+|_+$/g, "");
      const suffix = dpi >= 600 ? "-600dpi" : dpi === 300 ? "" : `-${dpi}dpi`;
      const result = await exportCardPngFromRender(cardRender, {
        dpi,
        fileName: `${safeName || "carta"}${suffix}.png`,
      });
      onStatusMessage?.(
        `PNG esportato a ${result.dpi} dpi (${result.width}×${result.height}px).`
      );
    } catch (err) {
      onStatusMessage?.(err.message || "Export PNG fallito.");
    } finally {
      setExporting(false);
    }
  };

  const handleCardSetChange = (expId) => {
    const next = expId || "";
    onExpansionChange?.(next);
    if (cardId) {
      updateCardField("espansione", next || null);
    }
  };

  return (
    <section className="mse-cards-tab">
      <div className="mse-card-context-bar">
        <label>
          <span>Card set</span>
          <select
            value={selectedExpansionId || cardForm.espansione || ""}
            onChange={(e) => handleCardSetChange(e.target.value)}
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
            title={studioTemplateSourceLabel}
          >
            <option value="">
              {(() => {
                const esp = cardForm.espansione ? espansioniById[cardForm.espansione] : null;
                const defId = esp?.default_studio_template || resolvedStudioTemplateId;
                const defName =
                  templatesForSelectedGame.find((t) => t.id === defId)?.nome ||
                  (defId ? "default del set" : "nessun default");
                return `— default del set (${defName}) —`;
              })()}
            </option>
            {templatesForSelectedGame.map((t) => (
              <option key={t.id} value={t.id}>
                {t.nome}
                {t.is_default_for_new_cards ? " (default gioco)" : ""}
                {cardForm.espansione &&
                espansioniById[cardForm.espansione]?.default_studio_template === t.id
                  ? " (default set)"
                  : ""}
              </option>
            ))}
          </select>
        </label>
        {activeTemplate ? (
          <p className="mse-empty-hint">
            Rendering: <strong>{studioTemplateSourceLabel || activeTemplate.nome}</strong>
            {!cardForm.studio_template ? " — eredita dal set (tab Set → Default stylesheet)." : " — override salvato sulla carta."}
          </p>
        ) : null}
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
            {canRenumberSet && (
              <button
                type="button"
                className="mse-btn-small"
                onClick={onRenumberSetCodici}
                title="Rinumera codici del set: aura → alfabetico (SIGLA-001…)"
              >
                Rinumera codici
              </button>
            )}
            {canDeleteCard && (
              <button type="button" className="mse-btn-small mse-btn-danger" onClick={onDeleteCard} title="Elimina carta">
                Elimina
              </button>
            )}
          </div>
        </div>
          {isNewCard && (
            <p className="mse-crud-hint">
              Modalità creazione: compila i campi e premi «Crea carta». Il codice sarà{" "}
              <code>SIGLA-NNN</code> automatico (es. KBE-002), ordinato per aura → alfabetico.
            </p>
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
        <div className="mse-art-upload-panel">
          <div className="mse-art-upload-copy">
            <strong>Illustrazione carta</strong>
            <span>Carica JPG/PNG/WebP. Poi salva la carta per memorizzarla sul server.</span>
          </div>
          <div className="mse-art-upload-actions">
            <input
              ref={artFileRef}
              type="file"
              accept="image/png,image/jpeg,image/webp,image/gif,.png,.jpg,.jpeg,.webp,.gif"
              hidden
              onChange={(e) => {
                const file = e.target.files?.[0] || null;
                e.target.value = "";
                if (!file) return;
                onPickFile?.(imageField || { name: "image", type: "image" }, file);
              }}
            />
            <button type="button" className="mse-btn-small mse-btn-upload" onClick={() => artFileRef.current?.click()}>
              Carica immagine…
            </button>
            {artPreview &&
            (artPreview.startsWith("/media/") ||
              artPreview.startsWith("http") ||
              (artPreview.startsWith("blob:") && artPreview.length > 40)) ? (
              <img className="mse-image-thumb" src={artPreview} alt="Anteprima illustrazione" />
            ) : (
              <span className="mse-empty-hint">Nessuna immagine</span>
            )}
          </div>
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
          <div className="mse-export-buttons">
            <button
              type="button"
              className="mse-btn-small"
              onClick={() => handleExportPng(300)}
              disabled={exporting || !hasMsePreview}
              title="Esporta PNG stampabile (300 dpi, 375×523 px)"
            >
              {exporting ? "…" : "PNG 300dpi"}
            </button>
            <button
              type="button"
              className="mse-btn-small"
              onClick={() => handleExportPng(600)}
              disabled={exporting || !hasMsePreview}
              title="Esporta PNG alta risoluzione (600 dpi, 750×1046 px)"
            >
              {exporting ? "…" : "PNG 600dpi"}
            </button>
          </div>
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

      <footer className="mse-statusbar mse-statusbar-static">
        {statusText ||
          "Le descrizioni dei campi compaiono nel riquadro sopra la tabella Card fields."}
      </footer>
    </section>
  );
}
