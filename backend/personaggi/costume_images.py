"""
Ottimizzazione foto costume staff (trucco / outfit).
Risoluzione leggermente superiore a InstaFame (1600px) per dettaglio makeup e abiti.
"""
import os
from io import BytesIO

from django.core.files.base import ContentFile
from PIL import Image

# InstaFame: 1600px; Instagram feed ~1080px → 1800px per reference makeup/outfit staff.
MAX_COSTUME_IMAGE_SIZE = (1800, 1800)
JPEG_QUALITY = 82


def optimize_costume_image_field(uploaded_file):
    """Ridimensiona e comprime un file immagine costume; ritorna ContentFile JPEG."""
    if not uploaded_file:
        return uploaded_file
    try:
        image = Image.open(uploaded_file)
        image = image.convert("RGB")
        image.thumbnail(MAX_COSTUME_IMAGE_SIZE, Image.Resampling.LANCZOS)

        output = BytesIO()
        image.save(output, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        output.seek(0)

        original_name = getattr(uploaded_file, "name", "") or "costume.jpg"
        base_name = os.path.splitext(os.path.basename(original_name))[0]
        return ContentFile(output.read(), name=f"{base_name}.jpg")
    except Exception:
        return uploaded_file
