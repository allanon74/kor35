"""Media degli articoli di rubrica: hero, galleria e video da richieste multipart."""

import json

from django.core.exceptions import ValidationError
from django.db import transaction

from .models_rubriche import (
    MAX_ARTICOLO_IMAGES,
    RUBRICA_IMG_LAYOUT_CHOICES,
    RUBRICA_IMG_LAYOUT_FULL,
    RubricaArticolo,
    RubricaArticoloImmagine,
)

_LAYOUT_VALIDI = {c[0] for c in RUBRICA_IMG_LAYOUT_CHOICES}


def _flag(request, nome: str) -> bool:
    return str(request.data.get(nome, "")).lower() in {"1", "true", "yes"}


def _lista_request(request, nome: str) -> list:
    if hasattr(request.data, "getlist"):
        return list(request.data.getlist(nome) or [])
    valore = request.data.get(nome)
    if valore is None:
        return []
    if isinstance(valore, list):
        return valore
    return [valore]


def _parse_immagini_meta(request) -> list[dict]:
    """
    Aggiornamenti metadati galleria esistente.
    Accetta JSON string o lista: [{"id": "...", "layout": "wide", "didascalia": "...", "ordine": 0}, ...]
    """
    grezzo = request.data.get("immagini_meta")
    if grezzo in (None, ""):
        return []
    if isinstance(grezzo, (list, tuple)):
        return [x for x in grezzo if isinstance(x, dict)]
    if isinstance(grezzo, str):
        try:
            parsed = json.loads(grezzo)
        except json.JSONDecodeError as exc:
            raise ValidationError("immagini_meta non è JSON valido.") from exc
        if not isinstance(parsed, list):
            raise ValidationError("immagini_meta deve essere una lista.")
        return [x for x in parsed if isinstance(x, dict)]
    raise ValidationError("immagini_meta non valido.")


def apply_immagini_meta(articolo: RubricaArticolo, meta_rows: list[dict]) -> None:
    if not meta_rows:
        return
    by_id = {str(r.id): r for r in articolo.immagini.all()}
    for row in meta_rows:
        img_id = str(row.get("id") or "").strip()
        if not img_id or img_id not in by_id:
            continue
        istanza = by_id[img_id]
        campi = []
        if "didascalia" in row:
            istanza.didascalia = str(row.get("didascalia") or "")[:300]
            campi.append("didascalia")
        if "layout" in row:
            layout = str(row.get("layout") or RUBRICA_IMG_LAYOUT_FULL)
            if layout not in _LAYOUT_VALIDI:
                raise ValidationError(f"Layout immagine non valido: {layout}")
            istanza.layout = layout
            campi.append("layout")
        if "ordine" in row and row.get("ordine") is not None:
            try:
                istanza.ordine = max(0, int(row["ordine"]))
            except (TypeError, ValueError) as exc:
                raise ValidationError("ordine immagine non valido.") from exc
            campi.append("ordine")
        if campi:
            campi.append("updated_at")
            istanza.save(update_fields=campi)


@transaction.atomic
def apply_articolo_media_from_request(
    articolo: RubricaArticolo, request, *, replace_gallery: bool = False
):
    """
    Applica upload multipart:
    - ``hero_immagine`` (singola) / ``clear_hero=1``
    - ``immagini`` (lista, max 8) / ``clear_immagini=1``
    - ``layout`` / ``layouts`` per le nuove immagini caricate
    - ``immagini_meta`` JSON per aggiornare didascalia/layout/ordine esistenti
    - ``video`` (esclusivo rispetto alla galleria) / ``clear_video=1``

    Di default le nuove ``immagini`` vengono *aggiunte* alla galleria.
    ``replace_gallery=True`` (o ``clear_immagini``) svuota prima le esistenti.
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

    clear_gallery = replace_gallery or _flag(request, "clear_immagini")
    if clear_gallery:
        articolo.immagini.all().delete()

    apply_immagini_meta(articolo, _parse_immagini_meta(request))

    if not image_files:
        return

    if articolo.video:
        raise ValidationError("Rimuovi il video prima di aggiungere immagini all'articolo.")

    ordine_iniziale = 0 if clear_gallery else articolo.immagini.count()

    if ordine_iniziale + len(image_files) > MAX_ARTICOLO_IMAGES:
        raise ValidationError(f"Massimo {MAX_ARTICOLO_IMAGES} immagini per articolo.")

    didascalie = _lista_request(request, "didascalie")
    layouts = _lista_request(request, "layouts")
    layout_unico = request.data.get("layout")
    if layout_unico and not layouts:
        layouts = [layout_unico] * len(image_files)

    for offset, uploaded in enumerate(image_files):
        didascalia = didascalie[offset] if offset < len(didascalie) else ""
        layout = layouts[offset] if offset < len(layouts) else RUBRICA_IMG_LAYOUT_FULL
        layout = str(layout or RUBRICA_IMG_LAYOUT_FULL)
        if layout not in _LAYOUT_VALIDI:
            raise ValidationError(f"Layout immagine non valido: {layout}")
        RubricaArticoloImmagine.objects.create(
            articolo=articolo,
            immagine=uploaded,
            didascalia=didascalia or "",
            layout=layout,
            ordine=ordine_iniziale + offset,
        )
