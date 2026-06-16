const PROFILE_IMAGE_MAX_EDGE = 1600;

export function normalizeRotationDegrees(degrees) {
  const n = ((Number(degrees) || 0) % 360 + 360) % 360;
  return (Math.round(n / 90) * 90) % 360;
}

function loadImageFromSource(source) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    let objectUrl = null;
    const cleanup = () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
    img.onload = () => {
      cleanup();
      resolve(img);
    };
    img.onerror = () => {
      cleanup();
      reject(new Error('Impossibile caricare immagine'));
    };
    if (source instanceof File || source instanceof Blob) {
      objectUrl = URL.createObjectURL(source);
      img.src = objectUrl;
      return;
    }
    img.crossOrigin = 'anonymous';
    img.src = String(source);
  });
}

export async function renderRotatedImageFile(source, rotationDegrees, options = {}) {
  const rotation = normalizeRotationDegrees(rotationDegrees);
  const maxEdge = options.maxEdge ?? PROFILE_IMAGE_MAX_EDGE;
  const quality = options.quality ?? 0.82;
  const filename = options.filename ?? 'profile.jpg';

  if (rotation === 0 && source instanceof File) {
    return source;
  }

  const img = await loadImageFromSource(source);
  const w = img.naturalWidth || img.width;
  const h = img.naturalHeight || img.height;
  const swapped = rotation === 90 || rotation === 270;
  const cw = swapped ? h : w;
  const ch = swapped ? w : h;

  const canvas = document.createElement('canvas');
  canvas.width = cw;
  canvas.height = ch;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas non disponibile');

  ctx.translate(cw / 2, ch / 2);
  ctx.rotate((rotation * Math.PI) / 180);
  ctx.drawImage(img, -w / 2, -h / 2);

  const maxDim = Math.max(cw, ch);
  if (maxDim > maxEdge) {
    const scale = maxEdge / maxDim;
    const outW = Math.max(1, Math.round(cw * scale));
    const outH = Math.max(1, Math.round(ch * scale));
    const scaled = document.createElement('canvas');
    scaled.width = outW;
    scaled.height = outH;
    const sctx = scaled.getContext('2d');
    if (!sctx) throw new Error('Canvas non disponibile');
    sctx.drawImage(canvas, 0, 0, outW, outH);
    canvas.width = outW;
    canvas.height = outH;
    const finalCtx = canvas.getContext('2d');
    finalCtx.drawImage(scaled, 0, 0);
  }

  const blob = await new Promise((resolve, reject) => {
    canvas.toBlob(
      (b) => (b ? resolve(b) : reject(new Error('Export immagine fallito'))),
      'image/jpeg',
      quality
    );
  });

  return new File([blob], filename.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' });
}

export async function prepareProfileImageForUpload({ file, remoteUrl, rotationDegrees }) {
  const rotation = normalizeRotationDegrees(rotationDegrees);
  if (file) {
    return renderRotatedImageFile(file, rotation, { filename: file.name });
  }
  if (remoteUrl && rotation !== 0) {
    return renderRotatedImageFile(remoteUrl, rotation, { filename: 'profile.jpg' });
  }
  return null;
}
