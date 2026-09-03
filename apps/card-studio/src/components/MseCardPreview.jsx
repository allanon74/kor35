import { useMemo } from "react";
import { buildCardScriptContext } from "../mse/scriptEngine";
import { resolveMseLayers } from "../mse/resolveLayers";
import { parseFlexAlignment } from "../mse/layerAlignment";
import { resolveSelectedSymbolFontPackage, splitGlyphsIntoWrappableUnits } from "../mse/symbolFonts";

export default function MseCardPreview({
  template,
  cardForm,
  gameCardFields,
  styling = {},
  setData = {},
  getFieldValue,
  packages = [],
  className = "",
  previewRef,
}) {
  const mseV1 = template?.layout_spec?.mse_v1;

  const card = useMemo(
    () => buildCardScriptContext(cardForm, gameCardFields, getFieldValue),
    [cardForm, gameCardFields, getFieldValue]
  );

  const symbolFontPackage = useMemo(
    () =>
      resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm, {
        mseV1,
        styling,
      }),
    [packages, gameCardFields, cardForm, mseV1, styling]
  );

  const render = useMemo(
    () =>
      resolveMseLayers({
        mseV1,
        card,
        styling,
        set: setData,
        cardFields: gameCardFields,
        extractedRoot: template?.mse_extracted_root || "",
        assetsManifest: template?.mse_assets_manifest || null,
        symbolFontPackage,
        packages,
      }),
    [mseV1, card, styling, setData, gameCardFields, template?.mse_extracted_root, template?.mse_assets_manifest, symbolFontPackage, packages]
  );

  if (!mseV1 || !Object.keys(mseV1.card_styles || {}).length) {
    return null;
  }

  const scale = 1;

  return (
    <div
      ref={previewRef}
      className={`mse-card-preview ${className}`.trim()}
      style={{
        width: render.width * scale,
        height: render.height * scale,
        backgroundColor: render.background,
      }}
    >
      {render.layers.map((layer) => {
        const boxStyle = {
          left: layer.box.left * scale,
          top: layer.box.top * scale,
          width: layer.box.width * scale,
          height: layer.box.height * scale,
          zIndex: layer.z,
          transform: layer.box.angle ? `rotate(${layer.box.angle}deg)` : undefined,
        };
        const flexAlign = parseFlexAlignment(layer.alignment);

        if (layer.type === "image") {
          const cover = /^(art|image|illustration|__frame__|card_frame)$/i.test(layer.fieldName);
          return (
            <img
              key={`${layer.fieldName}-${layer.z}-${layer.src}`}
              className={`mse-layer mse-layer-image${cover ? " mse-layer-cover" : ""}`}
              src={layer.src}
              alt={layer.fieldName}
              style={{
                ...boxStyle,
                objectFit: cover ? "cover" : "contain",
              }}
              draggable={false}
            />
          );
        }

        if (layer.type === "symbols") {
          const glyphs = layer.wrap
            ? splitGlyphsIntoWrappableUnits(layer.glyphs || [])
            : layer.glyphs || [];
          return (
            <div
              key={`${layer.fieldName}-${layer.z}-sym`}
              className="mse-layer mse-layer-symbols"
              style={{
                ...boxStyle,
                display: "flex",
                flexDirection: "row",
                flexWrap: layer.wrap ? "wrap" : "nowrap",
                alignContent: layer.wrap ? "flex-start" : "stretch",
                justifyContent: flexAlign.justifyContent,
                alignItems: flexAlign.alignItems,
                gap: "2px",
                overflow: "hidden",
              }}
            >
              {glyphs.map((g, idx) =>
                g.type === "image" && g.src ? (
                  <img
                    key={`${layer.fieldName}-g-${idx}`}
                    src={g.src}
                    alt={g.value}
                    style={{ width: g.size, height: g.size, flexShrink: 0 }}
                    draggable={false}
                  />
                ) : (
                  <span
                    key={`${layer.fieldName}-t-${idx}`}
                    style={{
                      fontFamily: layer.font.family,
                      fontSize: `${layer.font.size}px`,
                      color: layer.font.color,
                      fontWeight: layer.font.weight,
                      fontStyle: layer.font.style || "normal",
                      lineHeight: 1.25,
                      whiteSpace: layer.wrap ? "pre-wrap" : "pre",
                    }}
                  >
                    {g.value}
                  </span>
                )
              )}
            </div>
          );
        }

        const isMultiline = /^(rules|rule_text|text|lore|testo_gioco)$/i.test(layer.fieldName);
        const isLore = /^lore$/i.test(layer.fieldName);
        return (
          <div
            key={`${layer.fieldName}-${layer.z}`}
            className={`mse-layer mse-layer-text${isLore ? " mse-layer-lore" : ""}`}
            style={{
              ...boxStyle,
              display: "flex",
              overflow: "hidden",
              justifyContent: flexAlign.justifyContent,
              alignItems: flexAlign.alignItems,
              fontFamily: layer.font.family,
              fontSize: `${layer.font.size}px`,
              color: layer.font.color,
              fontWeight: layer.font.weight,
              fontStyle: layer.font.style || "normal",
              lineHeight: 1.25,
              whiteSpace: isMultiline ? "pre-wrap" : "nowrap",
              wordBreak: isMultiline ? "break-word" : "normal",
            }}
          >
            {layer.text}
          </div>
        );
      })}
    </div>
  );
}

export function useMseCardRender(props) {
  const {
    template,
    cardForm,
    gameCardFields,
    styling = {},
    setData = {},
    getFieldValue,
    packages = [],
  } = props;
  const mseV1 = template?.layout_spec?.mse_v1;
  const card = buildCardScriptContext(cardForm, gameCardFields, getFieldValue);
  const symbolFontPackage = resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm, {
    mseV1,
    styling,
  });
  return resolveMseLayers({
    mseV1,
    card,
    styling,
    set: setData,
    cardFields: gameCardFields,
    extractedRoot: template?.mse_extracted_root || "",
    assetsManifest: template?.mse_assets_manifest || null,
    symbolFontPackage,
    packages,
  });
}
