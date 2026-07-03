import os
from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from PIL import Image

from personaggi.models import Personaggio
from social.models import SocialPost, SocialPostImage
from social.post_media import sync_post_cover_image


def _jpeg_upload(name="photo.jpg"):
    buf = BytesIO()
    Image.new("RGB", (40, 30), color=(200, 50, 50)).save(buf, format="JPEG")
    buf.seek(0)
    return SimpleUploadedFile(name, buf.read(), content_type="image/jpeg")


@override_settings(MEDIA_ROOT="/tmp/kor35_test_post_media")
class SocialPostCoverSyncTests(TestCase):
    def setUp(self):
        os.makedirs("/tmp/kor35_test_post_media", exist_ok=True)
        self.autore = Personaggio.objects.create(nome="Autore Test")

    def test_sync_cover_copies_gallery_file_without_moving_it(self):
        post = SocialPost.objects.create(autore=self.autore, titolo="Post galleria", testo="x")
        gallery = SocialPostImage.objects.create(
            post=post,
            immagine=_jpeg_upload("gallery.jpg"),
            ordine=0,
        )
        gallery.refresh_from_db()
        post.refresh_from_db()

        gallery_path = gallery.immagine.path
        cover_path = post.immagine.path

        self.assertTrue(os.path.isfile(gallery_path), "file galleria mancante")
        self.assertTrue(os.path.isfile(cover_path), "file cover mancante")
        self.assertNotEqual(gallery_path, cover_path)
        self.assertIn(f"/social/posts/{self.autore.id}/", cover_path)

        sync_post_cover_image(post)
        post.refresh_from_db()
        gallery.refresh_from_db()

        self.assertTrue(os.path.isfile(gallery_path), "sync cover non deve spostare il file galleria")
        self.assertTrue(os.path.isfile(cover_path), "cover deve restare disponibile")
