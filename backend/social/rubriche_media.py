"""Media degli articoli di rubrica: hero, galleria e video da richieste multipart."""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models_rubriche import MAX_ARTICOLO_IMAGES, RubricaArticolo, RubricaArticoloImmagine


def _flag(request, nome: str) -> bool:
    return str(request.data.get(nome, "")).lower() in {"1", "true", "yes"}


@transaction.atomic
def apply_articolo_media_from_request(
    articolo: RubricaArticolo, request, *, replace_gallery: bool = False
):
    """
    Applica upload multipart:
    - ``hero_immagine`` (singola) / ``clear_hero=1``
    - ``immagini`` (lista, max 8) / ``clear_immagini=1``
    - ``video`` (esclusivo rispetto alla galleria) / ``clear_video=1``
    """
    campi_da_salvare = []

    hero_file = request.FILES.get("hero_immagine")
    if hero_file:
        articolo.hero_immagine = hero_file
        campi_da_salvare.append("hero_immagine")
    elif _flag(request, "clear_hero"):
        articolo.hero_immagine = None
        campi_da_salvare.append("hero_immagine")

    video_file = request.FILES.get("video")
    image_files = [f for f in request.FILES.getlist("immagini") if f]

    if video_file:
        if image_files or (not replace_gallery and articolo.immagini.exists()):
            raise ValidationError("Un articolo non può avere video e galleria insieme.")
        articolo.video = video_file
        articolo.immagini.all().delete()
        campi_da_salvare.append("video")
    elif _flag(request, "clear_video"):
        articolo.video = None
        campi_da_salvare.append("video")

    if campi_da_salvare:
        articolo.save(update_fields=[*campi_da_salvare, "updated_at"])

    if _flag(request, "clear_immagini"):
        articolo.immagini.all().delete()

    if not image_files:
        return

    if articolo.video:
        raise ValidationError("Rimuovi il video prima di aggiungere immagini all'articolo.")

    if replace_gallery:
        articolo.immagini.all().delete()
        ordine_iniziale = 0
    else:
        ordine_iniziale = articolo.immagini.count()

    if ordine_iniziale + len(image_files) > MAX_ARTICOLO_IMAGES:
        raise ValidationError(f"Massimo {MAX_ARTICOLO_IMAGES} immagini per articolo.")

    didascalie = request.data.getlist("didascalie") if hasattr(request.data, "getlist") else []
    for offset, uploaded in enumerate(image_files):
        didascalia = didascalie[offset] if offset < len(didascalie) else ""
        RubricaArticoloImmagine.objects.create(
            articolo=articolo,
            immagine=uploaded,
            didascalia=didascalia or "",
            ordine=ordine_iniziale + offset,
        )
