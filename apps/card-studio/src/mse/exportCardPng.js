/**
 * Rasterizza layer MSE preview → PNG stampabile.
 *
 * Coordinate layout = pixel alla dpi della carta (`render.dpi`, tipicamente 300
 * come `card dpi` MSE). Export a N dpi: scale = targetDpi / sourceDpi
 * (300→300 ⇒ scale 1, dimensione di stampa stabile).
 */

import { parseFlexAlignment } from "./layerAlignment";
import { splitGlyphsIntoWrappableUnits } from "./symbolFonts";

function loadImage(src) {
  return new Promise((resolve) => {
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
  if (s.startsWith("#") || s.startsWith("rgb") || s.startsWith("hsl")) return s;
  return fallback;
}

function parseAlignment(alignment) {
  return parseFlexAlignment(alignment);
}

function canvasFont(layer, size) {
  const style = layer.font?.style === "italic" ? "italic " : "";
  return `${style}${layer.font?.weight || "normal"} ${size}px ${layer.font?.family || "sans-serif"}`;
}

function measureSymbolGlyph(ctx, glyph, layer, scale) {
  if (glyph.type === "image") {
    const size = (glyph.size || 14) * scale;
    return { glyph, size, w: size, h: size };
  }
  const fs = (layer.font?.size || 14) * scale;
  ctx.font = canvasFont(layer, fs);
  const w = ctx.measureText(glyph.value || "").width;
  return { glyph, size: fs, w, h: fs * 1.25 };
}

function layoutWrappedSymbolLines(ctx, glyphs, layer, maxWidth, scale) {
  const gap = 2 * scale;
  const units = splitGlyphsIntoWrappableUnits(glyphs);
  const items = units.map((g) => measureSymbolGlyph(ctx, g, layer, scale));
  const lines = [];
  let line = [];
  let lineW = 0;
  let lineH = 0;

  for (const item of items) {
    const extra = line.length ? gap : 0;
    if (line.length && lineW + extra + item.w > maxWidth) {
      lines.push({ items: line, width: lineW, height: lineH });
      line = [item];
      lineW = item.w;
      lineH = item.h;
    } else {
      line.push(item);
      lineW += extra + item.w;
      lineH = Math.max(lineH, item.h);
    }
  }
  if (line.length) lines.push({ items: line, width: lineW, height: lineH });
  return { lines, gap };
}

function drawSymbolGlyphs(ctx, layer, x, y, lw, lh, scale, imgMap) {
  const gap = 2 * scale;
  const align = parseAlignment(layer.alignment);
  const glyphs = layer.wrap ? splitGlyphsIntoWrappableUnits(layer.glyphs || []) : layer.glyphs || [];

  if (layer.wrap) {
    const { lines, gap: lineGap } = layoutWrappedSymbolLines(ctx, glyphs, layer, lw, scale);
    const blockH = lines.reduce((acc, ln, i) => acc + ln.height + (i ? lineGap : 0), 0);
    let cursorY = y;
    if (align.alignItems === "center") cursorY = y + (lh - blockH) / 2;
    if (align.alignItems === "flex-end") cursorY = y + lh - blockH;

    for (const line of lines) {
      let cursorX = x;
      if (align.justifyContent === "center") cursorX = x + (lw - line.width) / 2;
      if (align.justifyContent === "flex-end") cursorX = x + lw - line.width;
      const midY = cursorY + line.height / 2;
      for (const item of line.items) {
        if (item.glyph.type === "image" && item.glyph.src) {
          const img = imgMap.get(item.glyph.src);
          if (img) ctx.drawImage(img, cursorX, midY - item.size / 2, item.size, item.size);
        } else if (item.glyph.value) {
          ctx.font = canvasFont(layer, item.size);
          ctx.fillStyle = parseColor(layer.font?.color, "#000000");
          ctx.textBaseline = "middle";
          ctx.fillText(item.glyph.value, cursorX, midY);
        }
        cursorX += item.w + gap;
      }
      cursorY += line.height + lineGap;
    }
    return;
  }

  const sized = glyphs.map((g) => measureSymbolGlyph(ctx, g, layer, scale));
  const totalW = sized.reduce((acc, it) => acc + it.w, 0) + Math.max(0, sized.length - 1) * gap;
  let cursorX = x;
  if (align.justifyContent === "center") cursorX = x + (lw - totalW) / 2;
  if (align.justifyContent === "flex-end") cursorX = x + lw - totalW;
  const baseSize = sized[0]?.size || 14 * scale;
  const midY =
    align.alignItems === "flex-start"
      ? y + baseSize / 2
      : align.alignItems === "flex-end"
        ? y + lh - baseSize / 2
        : y + lh / 2;
  for (const item of sized) {
    if (item.glyph.type === "image" && item.glyph.src) {
      const img = imgMap.get(item.glyph.src);
      if (img) ctx.drawImage(img, cursorX, midY - item.size / 2, item.size, item.size);
      cursorX += item.size + gap;
    } else if (item.glyph.value) {
      ctx.font = canvasFont(layer, item.size);
      ctx.fillStyle = parseColor(layer.font?.color, "#000000");
      ctx.textBaseline = "middle";
      ctx.fillText(item.glyph.value, cursorX, midY);
      cursorX += item.w + gap;
    }
  }
}

function wrapTextLines(ctx, text, maxWidth) {
  const rawLines = String(text || "").split(/\n/);
  const out = [];
  for (const raw of rawLines) {
    const words = raw.split(/\s+/).filter(Boolean);
    if (!words.length) {
      out.push("");
      continue;
    }
    let line = words[0];
    for (let i = 1; i < words.length; i += 1) {
      const test = `${line} ${words[i]}`;
      if (ctx.measureText(test).width <= maxWidth) line = test;
      else {
        out.push(line);
        line = words[i];
      }
    }
    out.push(line);
  }
  return out;
}

function drawImageCover(ctx, img, x, y, w, h) {
  const ir = img.width / Math.max(img.height, 1);
  const br = w / Math.max(h, 1);
  let dw;
  let dh;
  let dx;
  let dy;
  if (ir > br) {
    dh = h;
    dw = h * ir;
    dx = x - (dw - w) / 2;
    dy = y;
  } else {
    dw = w;
    dh = w / Math.max(ir, 0.0001);
    dx = x;
    dy = y - (dh - h) / 2;
  }
  ctx.save();
  ctx.beginPath();
  ctx.rect(x, y, w, h);
  ctx.clip();
  ctx.drawImage(img, dx, dy, dw, dh);
  ctx.restore();
}

function isArtField(fieldName) {
  return /^(art|image|illustration|picture|immagine)$/i.test(String(fieldName || ""));
}

function crc32(buf) {
  let c = ~0;
  for (let i = 0; i < buf.length; i += 1) {
    c ^= buf[i];
    for (let k = 0; k < 8; k += 1) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
  }
  return ~c >>> 0;
}

/** Inserisce chunk pHYs (pixel/metro) prima di IEND — metadato DPI per stampa. */
export function injectPngDpiMetadata(pngArrayBuffer, dpi = 300) {
  const src = new Uint8Array(pngArrayBuffer);
  if (src.length < 24 || src[0] !== 0x89) return pngArrayBuffer;
  const ppm = Math.round(Number(dpi) / 0.0254);

  let iend = -1;
  for (let i = 8; i + 12 <= src.length; ) {
    const len = (src[i] << 24) | (src[i + 1] << 16) | (src[i + 2] << 8) | src[i + 3];
    const type = String.fromCharCode(src[i + 4], src[i + 5], src[i + 6], src[i + 7]);
    if (type === "IEND") {
      iend = i;
      break;
    }
    if (len < 0 || i + 12 + len > src.length) break;
    i += 12 + len;
  }
  if (iend < 0) return pngArrayBuffer;

  const data = new Uint8Array(9);
  const view = new DataView(data.buffer);
  view.setUint32(0, ppm);
  view.setUint32(4, ppm);
  data[8] = 1;
  const typeBytes = new TextEncoder().encode("pHYs");
  const forCrc = new Uint8Array(13);
  forCrc.set(typeBytes, 0);
  forCrc.set(data, 4);
  const crc = crc32(forCrc);
  const chunk = new Uint8Array(21);
  const cv = new DataView(chunk.buffer);
  cv.setUint32(0, 9);
  chunk.set(typeBytes, 4);
  chunk.set(data, 8);
  cv.setUint32(17, crc);

  const out = new Uint8Array(src.length + chunk.length);
  out.set(src.subarray(0, iend), 0);
  out.set(chunk, iend);
  out.set(src.subarray(iend), iend + chunk.length);
  return out.buffer;
}

export function resolveExportScale(render, targetDpi = 300) {
  const sourceDpi = Number(render?.dpi) || 300;
  const dpi = Number(targetDpi) || 300;
  return Math.max(0.25, dpi / sourceDpi);
}

async function canvasToPngBlob(canvas, dpi) {
  const blob = await new Promise((resolve) => canvas.toBlob(resolve, "image/png"));
  if (!blob) throw new Error("Export PNG fallito.");
  const buf = await blob.arrayBuffer();
  return new Blob([injectPngDpiMetadata(buf, dpi)], { type: "image/png" });
}

function downloadBlob(blob, fileName) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = fileName;
  a.click();
  URL.revokeObjectURL(url);
}

export async function renderCardToCanvas(render, { dpi = 300 } = {}) {
  if (!render?.width || !render?.height) {
    throw new Error("Render non valido per export PNG.");
  }

  const scale = resolveExportScale(render, dpi);
  const w = Math.max(1, Math.round(render.width * scale));
  const h = Math.max(1, Math.round(render.height * scale));
  const canvas = document.createElement("canvas");
  canvas.width = w;
  canvas.height = h;
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("Canvas non disponibile.");

  ctx.fillStyle = parseColor(render.background, "#ffffff");
  ctx.fillRect(0, 0, w, h);
  ctx.imageSmoothingEnabled = true;
  ctx.imageSmoothingQuality = "high";

  const layers = [...(render.layers || [])].sort((a, b) => (a.z || 0) - (b.z || 0));
  const imageSrcs = new Set();
  layers.forEach((layer) => {
    if (layer.type === "image" && layer.src) imageSrcs.add(layer.src);
    if (layer.type === "symbols") {
      (layer.glyphs || []).forEach((g) => {
        if (g.type === "image" && g.src) imageSrcs.add(g.src);
      });
    }
  });
  const imgMap = new Map();
  await Promise.all(
    [...imageSrcs].map(async (src) => {
      imgMap.set(src, await loadImage(src));
    })
  );

  for (const layer of layers) {
    const box = layer.box || {};
    const x = (box.left || 0) * scale;
    const y = (box.top || 0) * scale;
    const lw = Math.max(1, (box.width || 1) * scale);
    const lh = Math.max(1, (box.height || 1) * scale);
    const angle = Number(box.angle || 0);

    const withAngle = (fn) => {
      if (!angle) {
        fn();
        return;
      }
      ctx.save();
      ctx.translate(x + lw / 2, y + lh / 2);
      ctx.rotate((angle * Math.PI) / 180);
      ctx.translate(-(x + lw / 2), -(y + lh / 2));
      fn();
      ctx.restore();
    };

    if (layer.type === "image" && layer.src) {
      const img = imgMap.get(layer.src);
      if (!img) continue;
      withAngle(() => {
        if (isArtField(layer.fieldName)) drawImageCover(ctx, img, x, y, lw, lh);
        else ctx.drawImage(img, x, y, lw, lh);
      });
      continue;
    }

    if (layer.type === "symbols" && layer.glyphs?.length) {
      withAngle(() => {
        drawSymbolGlyphs(ctx, layer, x, y, lw, lh, scale, imgMap);
      });
      continue;
    }

    if (layer.type === "text" && layer.text) {
      withAngle(() => {
        const fs = (layer.font?.size || 14) * scale;
        ctx.font = canvasFont(layer, fs);
        ctx.fillStyle = parseColor(layer.font?.color, "#000000");
        const lines = wrapTextLines(ctx, layer.text, lw);
        const lineH = fs * 1.25;
        const blockH = lines.length * lineH;
        const align = parseAlignment(layer.alignment);
        let startY = y;
        if (align.alignItems === "center") startY = y + (lh - blockH) / 2;
        if (align.alignItems === "flex-end") startY = y + lh - blockH;
        ctx.textBaseline = "top";
        lines.forEach((line, i) => {
          let tx = x;
          const tw = ctx.measureText(line).width;
          if (align.justifyContent === "center") tx = x + (lw - tw) / 2;
          if (align.justifyContent === "flex-end") tx = x + lw - tw;
          ctx.fillText(line, tx, startY + i * lineH);
        });
      });
    }
  }

  return canvas;
}

export async function exportCardPngFromRender(
  render,
  { dpi = 300, fileName = "card.png", download = true } = {}
) {
  const canvas = await renderCardToCanvas(render, { dpi });
  const blob = await canvasToPngBlob(canvas, dpi);
  if (download) downloadBlob(blob, fileName);
  return { fileName, blob, width: canvas.width, height: canvas.height, dpi };
}

export async function exportCardPngFromPreviewElement(
  previewEl,
  { width, height, dpi = 300, fileName = "card.png" } = {}
) {
  if (!previewEl) throw new Error("Preview non trovata.");
  const render = {
    width: width || previewEl.offsetWidth,
    height: height || previewEl.offsetHeight,
    dpi: 96,
    background: getComputedStyle(previewEl).backgroundColor || "#ffffff",
    layers: [],
  };
  const imgs = previewEl.querySelectorAll("img.mse-layer-image, img.mse-layer, img.mse-layer-cover");
  imgs.forEach((img, idx) => {
    const st = img.style;
    render.layers.push({
      type: "image",
      fieldName: img.alt || `img-${idx}`,
      z: Number(st.zIndex) || idx,
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
