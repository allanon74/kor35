"""Path foto profilo social: niente annidamento upload_to a ogni save."""

from io import BytesIO

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from personaggi.models import Personaggio
from social.models import SocialProfile, prepare_image_upload


def _tiny_jpeg_upload(name="avatar.jpg"):
    buf = BytesIO()
    Image.new("RGB", (8, 8), color="red").save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


class SocialProfileImagePathTests(TestCase):
    def test_optimize_uses_basename_only(self):
        upload = _tiny_jpeg_upload("nested/path/photo.png")
        upload.name = "social/profiles/99/social/profiles/99/photo.png"
        optimized = prepare_image_upload(upload, "social/profiles/99")
        self.assertEqual(optimized.name, "photo.jpg")

    def test_save_nickname_does_not_nest_existing_foto_path(self):
        personaggio = Personaggio.objects.first()
        if not personaggio:
            self.skipTest("Nessun personaggio nel DB di test")
        profile, _ = SocialProfile.objects.get_or_create(personaggio=personaggio)
        prefix = f"social/profiles/{personaggio.id}"
        nested = f"{prefix}/{prefix}/nested_avatar.jpg"
        default_storage.save(nested, _tiny_jpeg_upload())
        profile.foto_principale.name = nested
        profile.save(update_fields=["foto_principale"])

        profile.nickname = "Nickname test"
        profile.save()
        profile.refresh_from_db()

        self.assertEqual(profile.foto_principale.name, f"{prefix}/nested_avatar.jpg")
        self.assertEqual(profile.foto_principale.name.count("social/profiles/"), 1)
        self.assertTrue(default_storage.exists(profile.foto_principale.name))
        default_storage.delete(profile.foto_principale.name)
