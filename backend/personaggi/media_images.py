"""
Ottimizzazione immagini caricate (manifesto / serie QR).
Sottoscala e comprime in JPEG per limitare lo spazio su disco (edge Pi + rsync).
"""
from __future__ import annotations

import os
from io import BytesIO

from django.core.files.base import ContentFile

try:
    from PIL import Image
except Exception:  # pragma: no cover
    Image = None

# Display telefono: 1280px lato lungo basta; qualità media per risparmiare disco.
MAX_QR_IMAGE_SIZE = (1280, 1280)
JPEG_QUALITY = 78


def optimize_uploaded_image(
    uploaded_file,
    *,
    max_size=MAX_QR_IMAGE_SIZE,
    quality=JPEG_QUALITY,
):
    """
    Ridimensiona e comprime un file immagine; ritorna ContentFile JPEG.
    In caso di errore restituisce il file originale.
    """
    if not uploaded_file or Image is None:
        return uploaded_file
    try:
        # Se il file è già stato letto, riparti dall'inizio
        if hasattr(uploaded_file, "seek"):
            try:
                uploaded_file.seek(0)
            except Exception:
                pass
        image = Image.open(uploaded_file)
        if image.mode not in ("RGB", "L"):
            image = image.convert("RGB")
        else:
            image = image.convert("RGB")
        image.thumbnail(max_size, Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(output, format="JPEG", quality=quality, optimize=True)
        output.seek(0)

        original_name = getattr(uploaded_file, "name", "") or "immagine.jpg"
        base_name = os.path.splitext(os.path.basename(original_name))[0] or "immagine"
        return ContentFile(output.read(), name=f"{base_name}.jpg")
    except Exception:
        return uploaded_file


def original_filename_from_upload(uploaded_file) -> str:
    """Nome file originale (basename) per ordinamento alfabetico serie."""
    name = getattr(uploaded_file, "name", "") or ""
    return os.path.basename(name) or "immagine.jpg"
