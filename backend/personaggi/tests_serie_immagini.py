"""Test upload staff immagini serie e regole di assegnazione."""
from io import BytesIO

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from personaggi.models import (
    Campagna,
    SerieCollezione,
    SerieImmagine,
)


def _jpeg(name="x.jpg"):
    buf = BytesIO()
    Image.new("RGB", (16, 16), (10, 120, 200)).save(buf, format="JPEG", quality=85)
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/jpeg")


class SerieImmaginiStaffApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="staffserie", password="pass", is_superuser=True
        )
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "Kor35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}
        self.serie = SerieCollezione.objects.create(
            nome="Collezione Img",
            totale=2,
            campagna=self.campagna,
        )

    def test_upload_max_pari_al_totale(self):
        url = f"/api/personaggi/api/staff/serie-collezioni/{self.serie.id}/immagini/"
        r1 = self.client.post(
            url,
            {"immagini": [_jpeg("a.jpg"), _jpeg("b.jpg")]},
            format="multipart",
            **self.headers,
        )
        self.assertEqual(r1.status_code, 201, r1.data)
        self.assertEqual(r1.data["immagini_count"], 2)
        self.assertEqual(SerieImmagine.objects.filter(serie=self.serie).count(), 2)

        r2 = self.client.post(
            url,
            {"immagini": [_jpeg("c.jpg")]},
            format="multipart",
            **self.headers,
        )
        self.assertEqual(r2.status_code, 400)

    def test_delete_immagine(self):
        img = SerieImmagine.objects.create(
            serie=self.serie,
            immagine=_jpeg("del.jpg"),
            nome_file_originale="del.jpg",
        )
        url = (
            f"/api/personaggi/api/staff/serie-collezioni/{self.serie.id}/"
            f"immagini/{img.id}/"
        )
        r = self.client.delete(url, **self.headers)
        self.assertEqual(r.status_code, 200)
        self.assertFalse(SerieImmagine.objects.filter(pk=img.pk).exists())

    def test_list_include_immagini(self):
        SerieImmagine.objects.create(
            serie=self.serie,
            immagine=_jpeg("list.jpg"),
            nome_file_originale="list.jpg",
        )
        r = self.client.get("/api/personaggi/api/staff/serie-collezioni/", **self.headers)
        self.assertEqual(r.status_code, 200)
        rows = r.data if isinstance(r.data, list) else r.data.get("results", [])
        match = next(x for x in rows if str(x["id"]) == str(self.serie.id))
        self.assertEqual(match["immagini_count"], 1)
        self.assertEqual(len(match["immagini"]), 1)
        self.assertTrue(match["immagini"][0]["url"])
