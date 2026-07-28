/** Rasterizza layer MSE preview → PNG (client-side, no extra deps). */

function loadImage(src) {
  return new Promise((resolve, reject) => {
    if (!src) {
      resolve(null);
      return;
    }
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => resolve(null);
    img.src = src;
  });
}

function parseColor(raw, fallback = "#ffffff") {
  const s = String(raw || "").trim();
  if (!s) return fallback;
  if (s.startsWith("#") || s.startsWith("rgb")) return s;
  return fallback;
}

export async function exportCardPngFromRender(render, { dpi = 300, fileName = "card.png" } = {}) {
  if (!render?.width || !render?.height) throw new Error("Render non valido per export PNG.");

  const scale = Math.max(1, dpi / 96);
  const w = Math.round(render.width * scale);
  const h = Math.round(render.height * scale);
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas non disponibile.");

  ctx.fillStyle = parseColor(render.background, "#ffffff");
  ctx.fillRect(0, 0, w, h);

  const layers = [...(render.layers || [])].sort((a, b) => (a.z || 0) - (b.z || 0));

  for (const layer of layers) {
    const box = layer.box || {};
    const x = (box.left || 0) * scale;
    const y = (box.top || 0) * scale;
    const lw = (box.width || 1) * scale;
    const lh = (box.height || 1) * scale;

    if (layer.type === "image" && layer.src) {
      const img = await loadImage(layer.src);
      if (img) ctx.drawImage(img, x, y, lw, lh);
      continue;
    }

    if (layer.type === "symbols" && layer.glyphs?.length) {
      let cursorX = x;
      const midY = y + lh / 2;
      for (const g of layer.glyphs) {
        if (g.type === "image" && g.src) {
          const img = await loadImage(g.src);
          const size = (g.size || 14) * scale;
          if (img) {
            ctx.drawImage(img, cursorX, midY - size / 2, size, size);
            cursorX += size + 2 * scale;
          }
        } else if (g.type === "text" && g.value) {
          const fs = (layer.font?.size || 14) * scale;
          ctx.font = `${layer.font?.weight || "normal"} ${fs}px ${layer.font?.family || "sans-serif"}`;
          ctx.fillStyle = parseColor(layer.font?.color, "#000000");
          ctx.textBaseline = "middle";
          ctx.fillText(g.value, cursorX, midY);
          cursorX += ctx.measureText(g.value).width + 2 * scale;
        }
      }
      continue;
    }

    if (layer.type === "text" && layer.text) {
      const fs = (layer.font?.size || 14) * scale;
      ctx.font = `${layer.font?.weight || "normal"} ${fs}px ${layer.font?.family || "sans-serif"}`;
      ctx.fillStyle = parseColor(layer.font?.color, "#000000");
      ctx.textBaseline = "top";
      const lines = String(layer.text).split("\n");
      lines.forEach((line, i) => {
        ctx.fillText(line, x, y + i * (fs * 1.2));
      });
    }
  }

  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Export PNG fallito.");
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
  return fileName;
}

export async function exportCardPngFromPreviewElement(previewEl, { width, height, dpi = 300, fileName = "card.png" } = {}) {
  if (!previewEl) throw new Error("Preview non trovato.");
  const render = {
    width: width || previewEl.offsetWidth,
    height: height || previewEl.offsetHeight,
    background: getComputedStyle(previewEl).backgroundColor || "#ffffff",
    layers: [],
  };
  const imgs = previewEl.querySelectorAll("img.mse-layer-image");
  imgs.forEach((img, idx) => {
    const st = img.style;
    render.layers.push({
      type: "image",
      z: idx,
      box: {
        left: parseFloat(st.left) || 0,
        top: parseFloat(st.top) || 0,
        width: parseFloat(st.width) || img.width,
        height: parseFloat(st.height) || img.height,
      },
      src: img.src,
    });
  });
  return exportCardPngFromRender(render, { dpi, fileName });
}
