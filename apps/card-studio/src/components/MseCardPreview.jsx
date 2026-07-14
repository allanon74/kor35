import { useMemo } from "react";
import { resolveTemplateBackground } from "../mse/assetUrl";
import { buildCardScriptContext } from "../mse/scriptEngine";
import { resolveMseLayers } from "../mse/resolveLayers";
import { resolveSelectedSymbolFontPackage } from "../mse/symbolFonts";

function alignmentStyle(alignment) {
  const parts = String(alignment || "left top").toLowerCase().split(/\s+/);
  let justifyContent = "flex-start";
  let alignItems = "flex-start";
  if (parts.some((p) => p === "center" || p === "middle")) {
    justifyContent = "center";
    alignItems = "center";
  }
  if (parts.includes("right")) justifyContent = "flex-end";
  if (parts.includes("bottom")) alignItems = "flex-end";
  return { justifyContent, alignItems };
}

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
    () => resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm),
    [packages, gameCardFields, cardForm]
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
        symbolFontPackage,
      }),
    [mseV1, card, styling, setData, gameCardFields, template?.mse_extracted_root, symbolFontPackage]
  );

  const bgImage = useMemo(() => resolveTemplateBackground(template), [template]);

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
        backgroundImage: bgImage ? `url(${bgImage})` : undefined,
        backgroundSize: "cover",
        backgroundPosition: "center",
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
        if (layer.type === "image") {
          return (
            <img
              key={`${layer.fieldName}-${layer.z}-${layer.src}`}
              className="mse-layer mse-layer-image"
              src={layer.src}
              alt={layer.fieldName}
              style={boxStyle}
              draggable={false}
            />
          );
        }
        if (layer.type === "symbols") {
          return (
            <div
              key={`${layer.fieldName}-${layer.z}-sym`}
              className="mse-layer mse-layer-symbols"
              style={{
                ...boxStyle,
                ...alignmentStyle(layer.alignment),
                display: "flex",
                flexDirection: "row",
                flexWrap: "wrap",
                alignItems: "center",
                gap: "2px",
              }}
            >
              {(layer.glyphs || []).map((g, idx) =>
                g.type === "image" && g.src ? (
                  <img
                    key={`${layer.fieldName}-g-${idx}`}
                    src={g.src}
                    alt={g.value}
                    style={{ width: g.size, height: g.size }}
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
                    }}
                  >
                    {g.value}
                  </span>
                )
              )}
            </div>
          );
        }
        return (
          <div
            key={`${layer.fieldName}-${layer.z}`}
            className="mse-layer mse-layer-text"
            style={{
              ...boxStyle,
              ...alignmentStyle(layer.alignment),
              fontFamily: layer.font.family,
              fontSize: `${layer.font.size}px`,
              color: layer.font.color,
              fontWeight: layer.font.weight,
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
  const symbolFontPackage = resolveSelectedSymbolFontPackage(packages, gameCardFields, cardForm);
  return resolveMseLayers({
    mseV1,
    card,
    styling,
    set: setData,
    cardFields: gameCardFields,
    extractedRoot: template?.mse_extracted_root || "",
    symbolFontPackage,
  });
}
