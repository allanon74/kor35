"""
Test scansione QR sottosistema pilotaggio e riparazione.
"""
from __future__ import annotations

import string

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import Manifesto, MinigiocoQrConfig, Personaggio, PersonaggioStatisticaBase, QrCode, Statistica
from pilotaggio.models import (
    SESSIONE_STATO_VOLO,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)
from pilotaggio.tests.test_views import _crea_pilota_con_0pi


def _crea_stat_per_pg(pg, sigla: str, valore: int, nome: str = ""):
    stat, _ = Statistica.objects.update_or_create(
        sigla=sigla,
        defaults={"nome": nome or sigla, "parametro": sigla.lower()},
    )
    PersonaggioStatisticaBase.objects.update_or_create(
        personaggio=pg, statistica=stat, defaults={"valore_base": valore}
    )
    if hasattr(pg, "_punteggi_base_cache"):
        del pg._punteggi_base_cache


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

    def test_scan_mostra_telemetria_senza_stat_riparazione(self):
        res = self._scan(personaggio_id=self.pg.id)
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["tipo_modello"], "pilot_sottosistema")
        self.assertTrue(body["dati"]["guasto"])
        self.assertFalse(body["dati"]["puo_riparare"])
        self.assertIn("telemetria", body["dati"])
        self.assertEqual(body["dati"]["telemetria"]["codice"], "fault")
        self.assertEqual(body["dati"]["stato"]["codice"], self.sottos.codice)

    def test_scan_con_0ri_mostra_pulsante_ripara(self):
        _crea_stat_per_pg(self.pg, "0RI", 2, "Riparazione")
        res = self._scan(personaggio_id=self.pg.id)
        self.assertEqual(res.status_code, 200, res.content)
        self.assertTrue(res.json()["dati"]["puo_riparare"])

    def test_repair_senza_0ri_rifiutato(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertIn("0RI", res.json().get("error", ""))

    def test_repair_con_0ri_riporta_online(self):
        _crea_stat_per_pg(self.pg, "0RI", 1, "Riparazione")
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

    def test_sabota_con_0sa(self):
        _crea_stat_per_pg(self.pg, "0SA", 1, "Sabotaggio")
        StatoSottosistemaSessione.objects.filter(sessione=self.sessione, sottosistema=self.sottos).update(
            online=True,
            guasto_at=None,
            recovery_at=None,
        )
        res = self.client.post(
            "/api/pilot/subsystems/qr-action/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id, "azione": "sabota"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["azione"], "sabotato")
        self.assertTrue(body["dati"]["guasto"])
        stato = StatoSottosistemaSessione.objects.get(sessione=self.sessione, sottosistema=self.sottos)
        self.assertFalse(stato.online)

    def test_sabota_senza_0sa_rifiutato(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-action/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id, "azione": "sabota"},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)

    def test_scan_senza_personaggio_mostra_solo_telemetria(self):
        res = self._scan()
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["dati"]["telemetria"]["codice"], "fault")
        self.assertFalse(body["dati"]["puo_riparare"])
        self.assertFalse(body["dati"]["puo_sabotare"])

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
        _crea_stat_per_pg(self.pg, "0RI", 1, "Riparazione")
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertIn("minigioco", res.json().get("error", "").lower())
