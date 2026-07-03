"""Test staff: manipolazione riserva scommesse personaggio."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APIClient

from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Personaggio,
    TipologiaPersonaggio,
)

User = get_user_model()


class StaffRiservaScommesseTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-riserva-staff",
            nome="Kor35 Riserva Staff",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Riserva Staff")
        cls.master = User.objects.create_user(username="master_riserva", password="x")
        CampagnaUtente.objects.create(
            user=cls.master,
            campagna=cls.campagna,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        cls.pg = Personaggio.objects.create(
            nome="PG Riserva",
            proprietario=cls.master,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
            riserva=Decimal("50.00"),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.master)
        self.url = reverse("personaggi:staff-personaggi-riserva-scommesse", kwargs={"pk": self.pg.pk})

    def test_get_riserva_e_puntate(self):
        resp = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["riserva"], "50.00")
        self.assertIn("puntate", data)

    def test_delta_riserva(self):
        resp = self.client.post(
            self.url,
            {"mode": "delta", "delta": "25.50", "motivo": "Test staff"},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, 200)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.riserva, Decimal("75.50"))

    def test_set_riserva(self):
        resp = self.client.post(
            self.url,
            {"mode": "set", "valore": "10", "motivo": "Reset test"},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, 200)
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.riserva, Decimal("10.00"))
