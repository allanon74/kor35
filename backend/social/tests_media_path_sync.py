"""
Regressione: path media da edge sync non devono essere riscritti col PK locale.

Senza questo fix, al save() dopo update_or_create sul mirror i path tipo
``social/rubriche/<uuid-master>/articoli/<uuid-master>/hero.jpg`` venivano
sostituiti con il PK locale: il file rsync resta sul path master → 404.
"""

from io import BytesIO
from unittest.mock import MagicMock
from uuid import uuid4

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from social.models import normalize_media_field_path, prepare_image_upload
from social.models_rubriche import Rubrica, RubricaArticolo


def _jpeg_bytes(color="blue"):
    buf = BytesIO()
    Image.new("RGB", (8, 8), color=color).save(buf, format="JPEG")
    return buf.getvalue()


def _committed_field(name: str):
    field = MagicMock()
    field.name = name
    field._committed = True
    field.storage = default_storage
    return field


@override_settings(MEDIA_ROOT="/tmp/kor35_test_media_path_sync")
class NormalizeMediaPathSyncTests(TestCase):
    def test_preserves_remote_sync_path_with_different_uuid(self):
        """Path da master (UUID diverso dal prefisso locale) resta invariato."""
        remote = (
            "social/rubriche/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/"
            "articoli/bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb/hero.jpg"
        )
        local_prefix = (
            "social/rubriche/aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa/"
            "articoli/cccccccc-cccc-cccc-cccc-cccccccccccc"
        )
        field = _committed_field(remote)
        normalize_media_field_path(field, local_prefix)
        self.assertEqual(field.name, remote)

    def test_preserves_logo_path_from_other_node(self):
        remote = "social/rubriche/11111111-1111-1111-1111-111111111111/logo/cover.jpg"
        local_prefix = "social/rubriche/22222222-2222-2222-2222-222222222222/logo"
        field = _committed_field(remote)
        normalize_media_field_path(field, local_prefix)
        self.assertEqual(field.name, remote)

    def test_still_repairs_nested_upload_to(self):
        prefix = "social/profiles/99"
        nested = f"{prefix}/{prefix}/avatar.jpg"
        default_storage.save(nested, ContentFile(_jpeg_bytes()))
        field = _committed_field(nested)
        normalize_media_field_path(field, prefix)
        self.assertEqual(field.name, f"{prefix}/avatar.jpg")
        self.assertTrue(default_storage.exists(field.name))
        default_storage.delete(field.name)

    def test_new_upload_keeps_basename_only(self):
        upload = SimpleUploadedFile(
            "social/rubriche/x/articoli/y/photo.png",
            _jpeg_bytes("green"),
            content_type="image/png",
        )
        upload.name = "social/rubriche/x/articoli/y/photo.png"
        optimized = prepare_image_upload(upload, "social/rubriche/x/articoli/y")
        self.assertEqual(optimized.name, "photo.jpg")


@override_settings(MEDIA_ROOT="/tmp/kor35_test_rubrica_path_sync")
class RubricaArticoloSyncPathTests(TestCase):
    def test_save_keeps_hero_path_from_master_uuid(self):
        """Simula apply sync: PK locale ≠ UUID nel path master."""
        rubrica = Rubrica.objects.create(nome="Cronache Sync Path")
        articolo = RubricaArticolo.objects.create(
            rubrica=rubrica,
            titolo="Pezzo sync",
            firma_libera="Redazione",
            stato="PUBBLICATO",
        )
        remote_articolo_id = uuid4()
        remote_path = (
            f"social/rubriche/{rubrica.id}/articoli/{remote_articolo_id}/hero.jpg"
        )
        # Come edge sync: scrive il path stringa senza passare da upload locale.
        RubricaArticolo.objects.filter(pk=articolo.pk).update(hero_immagine=remote_path)
        articolo.refresh_from_db()
        self.assertEqual(articolo.hero_immagine.name, remote_path)
        # save() non deve riscrivere col PK locale (bug mirror Pi).
        articolo.titolo = "Pezzo sync aggiornato"
        articolo.save()
        articolo.refresh_from_db()
        self.assertEqual(articolo.hero_immagine.name, remote_path)
        self.assertEqual(articolo.titolo, "Pezzo sync aggiornato")
