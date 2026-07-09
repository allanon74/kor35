import { useMemo } from "react";
import { resolveTemplateBackground } from "../mse/assetUrl";
import { buildCardScriptContext } from "../mse/scriptEngine";
import { resolveMseLayers } from "../mse/resolveLayers";

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
  className = "",
}) {
  const mseV1 = template?.layout_spec?.mse_v1;

  const card = useMemo(
    () => buildCardScriptContext(cardForm, gameCardFields, getFieldValue),
    [cardForm, gameCardFields, getFieldValue]
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
      }),
    [mseV1, card, styling, setData, gameCardFields, template?.mse_extracted_root]
  );

  const bgImage = useMemo(() => resolveTemplateBackground(template), [template]);

  if (!mseV1 || !Object.keys(mseV1.card_styles || {}).length) {
    return null;
  }

  const scale = 1;

  return (
    <div
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
