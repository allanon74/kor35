"""Gestione media multi-immagine per post InstaFame."""

from django.core.exceptions import ValidationError
from django.db import transaction

from .models import MAX_POST_IMAGES, SocialPost, SocialPostImage

IMAGE_FIELD_NAMES = ("immagini", "immagine")


def _image_files_from_request(request):
    files = list(request.FILES.getlist("immagini"))
    if not files and request.FILES.get("immagine"):
        files = [request.FILES["immagine"]]
    return [f for f in files if f]


def post_has_gallery_images(post: SocialPost) -> bool:
    if post.post_images.exists():
        return True
    return bool(post.immagine)


def sync_post_cover_image(post: SocialPost):
    """Mantiene post.immagine allineata alla prima foto della galleria (retrocompatibilità)."""
    first = post.post_images.order_by("ordine", "id").first()
    cover = first.immagine if first and first.immagine else None
    if post.immagine == cover:
        return
    post.immagine = cover
    post.save(update_fields=["immagine", "updated_at"])


@transaction.atomic
def apply_post_media_from_request(post: SocialPost, request, *, replace_gallery: bool = False):
    """
    Applica upload da multipart:
    - ``immagini`` (lista) o legacy ``immagine``
    - ``video`` (esclusivo rispetto alle immagini)
    - ``clear_immagini=1`` per svuotare la galleria (update admin)
    """
    clear_flag = str(request.data.get("clear_immagini", "")).lower() in {"1", "true", "yes"}
    video_file = request.FILES.get("video")
    image_files = _image_files_from_request(request)

    if video_file:
        if image_files or (not replace_gallery and post_has_gallery_images(post)):
            raise ValidationError("Un post non può avere video e immagini insieme.")
        post.video = video_file
        if replace_gallery or clear_flag:
            post.post_images.all().delete()
        post.immagine = None
        post.save(update_fields=["video", "immagine", "updated_at"])
        return

    if str(request.data.get("video", "")).strip() == "" and "video" in request.data:
        post.video = None
        post.save(update_fields=["video", "updated_at"])

    if clear_flag:
        post.post_images.all().delete()
        post.immagine = None
        post.save(update_fields=["immagine", "updated_at"])

    if not image_files:
        sync_post_cover_image(post)
        return

    if post.video:
        raise ValidationError("Rimuovi il video prima di aggiungere immagini.")

    if replace_gallery:
        post.post_images.all().delete()
        start_ordine = 0
    else:
        start_ordine = post.post_images.count()

    if start_ordine + len(image_files) > MAX_POST_IMAGES:
        raise ValidationError(f"Massimo {MAX_POST_IMAGES} immagini per post.")

    for offset, uploaded in enumerate(image_files):
        SocialPostImage.objects.create(post=post, immagine=uploaded, ordine=start_ordine + offset)

    sync_post_cover_image(post)
