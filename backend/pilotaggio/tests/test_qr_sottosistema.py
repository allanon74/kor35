"""
Test scansione QR sottosistema pilotaggio e riparazione.
"""
from __future__ import annotations

import string

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import Manifesto, MinigiocoQrConfig, Personaggio, QrCode
from pilotaggio.models import (
    SESSIONE_STATO_VOLO,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)
from pilotaggio.tests.test_views import _crea_pilota_con_0pi


def _codice_sottosistema_libero() -> str:
    used = set(SottosistemaNave.objects.values_list("codice", flat=True))
    for c in string.ascii_uppercase + string.digits:
        if c not in used:
            return c
    raise RuntimeError("Nessun codice sottosistema libero nei test.")


class QrSottosistemaScanTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="scan_user", password="x")
        self.pg = Personaggio.objects.create(nome="ScanPG", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        codice = _codice_sottosistema_libero()
        self.manifesto = Manifesto.objects.create(nome="Propulsione QR", testo="<p>Motori</p>")
        self.sottos = SottosistemaNave.objects.create(
            codice=codice,
            nome="Propulsione",
            a_vista=self.manifesto,
        )
        self.qr = QrCode.objects.create(vista=self.manifesto)

        self.pilota_user, self.pilota = _crea_pilota_con_0pi(nome="PilotaScan", valore_0pi=1)
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione,
            sottosistema=self.sottos,
            online=False,
            guasto_at=timezone.now(),
            livello_attuale=2,
            livello_target=4,
        )

    def _scan(self, **params):
        url = f"/api/personaggi/api/qrcode/{self.qr.id}/"
        return self.client.get(url, params)

    def test_scan_mostra_stato_runtime_non_manifesto(self):
        res = self._scan(personaggio_id=self.pg.id)
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["tipo_modello"], "pilot_sottosistema")
        self.assertTrue(body["dati"]["guasto"])
        self.assertTrue(body["dati"]["puo_riparare"])
        self.assertFalse(body["dati"]["minigioco_riparazione"])
        self.assertEqual(body["dati"]["stato"]["codice"], self.sottos.codice)

    def test_repair_senza_minigioco_riporta_online(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["azione"], "riparato")
        self.assertFalse(body["dati"]["guasto"])
        stato = StatoSottosistemaSessione.objects.get(sessione=self.sessione, sottosistema=self.sottos)
        self.assertTrue(stato.online)
        self.assertEqual(stato.livello_attuale, 4)

    def test_scan_senza_sessione_attiva(self):
        self.sessione.stato = "arrivata"
        self.sessione.save()
        res = self._scan(personaggio_id=self.pg.id)
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["tipo_modello"], "pilot_sottosistema")
        self.assertFalse(body["dati"]["sessione_attiva"])
        self.assertFalse(body["dati"]["puo_riparare"])


class QrSottosistemaMinigiocoRepairTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="mg_user", password="x")
        self.pg = Personaggio.objects.create(nome="MgPG", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        codice = _codice_sottosistema_libero()
        self.manifesto = Manifesto.objects.create(nome="Scudo QR", testo="")
        self.sottos = SottosistemaNave.objects.create(
            codice=codice,
            nome="Scudi",
            a_vista=self.manifesto,
        )
        self.qr = QrCode.objects.create(vista=self.manifesto)
        MinigiocoQrConfig.objects.create(
            qr_code=self.qr,
            attivo=True,
            sezione_attiva=True,
            tipi_abilitati=["simon"],
        )

        self.pilota_user, self.pilota = _crea_pilota_con_0pi(nome="PilotaMg", valore_0pi=1)
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione,
            sottosistema=self.sottos,
            online=False,
            guasto_at=timezone.now(),
        )

    def test_scan_normale_non_apre_minigioco(self):
        res = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["tipo_modello"], "pilot_sottosistema")
        self.assertTrue(body["dati"]["minigioco_riparazione"])

    def test_pilot_ripara_richiede_minigioco(self):
        res = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id, "pilot_ripara": "1"},
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json().get("tipo_modello"), "minigioco_richiesto")

    def test_repair_senza_sessione_minigioco_fallisce(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertIn("minigioco", res.json().get("error", "").lower())
