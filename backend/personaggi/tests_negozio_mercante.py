"""Test negozi mercante: anteprima vendita e associazione QR staff."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import Campagna, Oggetto, OggettoInInventario, Personaggio, QrCode
from personaggi.negozio_mercante_models import NegozioMercante
from personaggi.negozio_mercante_service import preview_vendita_oggetto


class NegozioMercanteServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "KOR35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        cls.user = User.objects.create_user(username="negozio_pg", password="test")
        cls.pg = Personaggio.objects.create(nome="Venditore", proprietario=cls.user, campagna=cls.campagna)
        cls.negozio = NegozioMercante.objects.create(
            nome="Mercante test",
            campagna=cls.campagna,
            saldo_crediti=Decimal("5000"),
            regole_apertura={"modalita": "sempre_aperto"},
        )
        cls.oggetto = Oggetto.objects.create(nome="Pugnale", costo_acquisto=100)
        OggettoInInventario.objects.create(oggetto=cls.oggetto, inventario=cls.pg)

    def test_preview_vendita_fascia_offerta(self):
        data = preview_vendita_oggetto(self.negozio, self.pg, self.oggetto.id)
        self.assertEqual(data["nome"], "Pugnale")
        self.assertGreaterEqual(data["offerta_max"], data["offerta_min"])
        self.assertTrue(data["cassa_sufficiente"])


class NegozioMercanteAssociaQrApiTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "KOR35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        cls.staff = User.objects.create_superuser(
            username="staff_negozio",
            password="test",
            email="staff@test.local",
        )
        cls.negozio = NegozioMercante.objects.create(nome="Bottega QR", campagna=cls.campagna)
        cls.qr = QrCode.objects.create(testo="NEGOZIO-TEST-QR")

    def test_associa_e_scollega_qr(self):
        client = APIClient()
        client.force_authenticate(user=self.staff)
        url = f"/api/personaggi/api/staff/negozi-mercante/{self.negozio.id}/associa-qr/"
        res = client.post(url, {"qr_id": self.qr.id}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res.status_code, 200)
        self.negozio.refresh_from_db()
        self.assertEqual(self.negozio.qr_code_id, self.qr.id)

        res2 = client.post(url, {"qr_id": None}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res2.status_code, 200)
        self.negozio.refresh_from_db()
        self.assertIsNone(self.negozio.qr_code_id)

    def test_associa_qr_imposta_vista_portale(self):
        from personaggi.models import NegozioMercantePortale

        client = APIClient()
        client.force_authenticate(user=self.staff)
        url = f"/api/personaggi/api/staff/negozi-mercante/{self.negozio.id}/associa-qr/"
        res = client.post(url, {"qr_id": self.qr.id}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res.status_code, 200)
        self.negozio.refresh_from_db()
        self.qr.refresh_from_db()
        portale = NegozioMercantePortale.objects.get(negozio=self.negozio)
        self.assertEqual(self.qr.vista_id, portale.pk)
        self.assertEqual(self.negozio.qr_code_id, self.qr.id)
