/** Max lato lungo: leggermente sopra InstaFame (1600px) e feed Instagram (~1080px). */
export const COSTUME_IMAGE_MAX_EDGE = 1800;

export function compressCostumeImageFile(file, maxEdge = COSTUME_IMAGE_MAX_EDGE, quality = 0.84) {
  return new Promise((resolve, reject) => {
    const url = URL.createObjectURL(file);
    const img = new Image();
    img.onload = () => {
      try {
        const w = img.naturalWidth || img.width;
        const h = img.naturalHeight || img.height;
        const scale = Math.min(1, maxEdge / Math.max(w, h));
        const tw = Math.max(1, Math.round(w * scale));
        const th = Math.max(1, Math.round(h * scale));
        const canvas = document.createElement('canvas');
        canvas.width = tw;
        canvas.height = th;
        const ctx = canvas.getContext('2d');
        if (!ctx) throw new Error('Canvas context non disponibile');
        ctx.drawImage(img, 0, 0, tw, th);
        canvas.toBlob(
          (blob) => {
            URL.revokeObjectURL(url);
            if (!blob) {
              reject(new Error('Compressione immagine fallita'));
              return;
            }
            const out = new File([blob], file.name.replace(/\.\w+$/, '.jpg'), { type: 'image/jpeg' });
            resolve(out);
          },
          'image/jpeg',
          quality,
        );
      } catch (e) {
        URL.revokeObjectURL(url);
        reject(e);
      }
    };
    img.onerror = () => {
      URL.revokeObjectURL(url);
      reject(new Error('Impossibile leggere immagine'));
    };
    img.src = url;
  });
}
