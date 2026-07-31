const FRAME_HINTS = ["frame", "card", "background", "preview", "template", "border"];

export function mediaUrl(extractedRoot, relPath) {
  if (!extractedRoot || !relPath) return "";
  const root = String(extractedRoot).replace(/^\/+/, "");
  const rel = String(relPath).replace(/^\/+/, "");
  return `/media/${root}/${rel}`;
}

/** Normalizza URL media assoluti/relativi a path same-origin `/media/...`. */
export function normalizeMediaUrl(url) {
  if (!url) return "";
  const s = String(url).trim();
  if (!s) return "";
  if (s.startsWith("blob:") || s.startsWith("data:")) return s;
  try {
    if (/^https?:\/\//i.test(s)) {
      const u = new URL(s);
      return `${u.pathname}${u.search || ""}`;
    }
  } catch {
    // ignore
  }
  if (s.startsWith("/media/")) return s;
  if (s.startsWith("media/")) return `/${s}`;
  if (s.startsWith("/")) return s;
  return `/media/${s.replace(/^\/+/, "")}`;
}

export function findManifestImage(manifest, hints = FRAME_HINTS) {
  if (!manifest) return "";
  if (!Array.isArray(manifest)) {
    return (
      manifest.preview_image ||
      manifest.card_frame ||
      manifest.background ||
      manifest.cover ||
      ""
    );
  }
  const images = manifest.filter((a) => a?.asset_type === "image");
  if (!images.length) return "";
  for (const hint of hints) {
    const hit = images.find((a) => String(a.path || "").toLowerCase().includes(hint));
    if (hit) return hit.path;
  }
  return images[0]?.path || "";
}

export function resolveTemplateBackground(template) {
  if (!template?.mse_extracted_root) return "";
  const path = findManifestImage(template.mse_assets_manifest);
  return mediaUrl(template.mse_extracted_root, path);
}
