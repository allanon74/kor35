"""Test allarme equipaggio e API LED."""
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from pilotaggio.allarme_equipaggio import (
    ALLARME_EQUIPAGGIO_GIALLO,
    ALLARME_EQUIPAGGIO_CROCIERA,
    build_allarme_led_payload,
)
from pilotaggio.models import (
    PilotConsoleToken,
    SESSIONE_STATO_VOLO,
    SessioneVolo,
)
from pilotaggio.tests.test_views import _crea_pilota_con_0pi


class AllarmeEquipaggioTests(TestCase):
    def setUp(self):
        _, self.pilota = _crea_pilota_con_0pi(nome="PilotaAllarme", valore_0pi=1)
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            decollo_completato_at=timezone.now(),
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        self.token = PilotConsoleToken.objects.create(
            pilota=self.pilota, token=PilotConsoleToken.genera_token()
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"PilotToken {self.token.token}")

    def test_imposta_allarme_giallo(self):
        res = self.client.post(
            "/api/pilot/session/allarme-equipaggio/",
            {"allarme": ALLARME_EQUIPAGGIO_GIALLO},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["allarme_equipaggio"], ALLARME_EQUIPAGGIO_GIALLO)
        self.assertIn("announcement", body)
        self.assertIn("Allarme Giallo", body["announcement"])

    def test_led_state_pubblico(self):
        self.sessione.allarme_equipaggio = ALLARME_EQUIPAGGIO_GIALLO
        self.sessione.allarme_equipaggio_at = timezone.now()
        self.sessione.save()
        client = APIClient()
        res = client.get("/api/pilot/allarme-led/state/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["allarme"], ALLARME_EQUIPAGGIO_GIALLO)
        self.assertEqual(body["schema_version"], 1)
        self.assertIn("hex", body["colore"])

    def test_build_led_crociera_default(self):
        payload = build_allarme_led_payload(None)
        self.assertTrue(payload["crociera"])
        self.assertEqual(payload["allarme"], ALLARME_EQUIPAGGIO_CROCIERA)
