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
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaNave,
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

    def test_scan_senza_sessione_console_mostra_stato_nave(self):
        self.sessione.stato = "arrivata"
        self.sessione.save()
        res = self._scan(personaggio_id=self.pg.id)
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertFalse(body["dati"]["sessione_attiva"])
        self.assertTrue(body["dati"]["bus_telemetria_attivo"])
        self.assertTrue(body["dati"]["guasto"])
        nave = StatoSottosistemaNave.objects.get(sottosistema=self.sottos)
        self.assertFalse(nave.online)

    def test_sabota_e_ripara_in_riposo(self):
        self.sessione.stato = SESSIONE_STATO_IDLE
        self.sessione.save()
        _crea_stat_per_pg(self.pg, "0SA", 1, "Sabotaggio")
        StatoSottosistemaSessione.objects.filter(sessione=self.sessione, sottosistema=self.sottos).update(
            online=True, guasto_at=None, recovery_at=None
        )
        StatoSottosistemaNave.objects.filter(sottosistema=self.sottos).update(online=True)
        res = self.client.post(
            "/api/pilot/subsystems/qr-action/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id, "azione": "sabota"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        nave = StatoSottosistemaNave.objects.get(sottosistema=self.sottos)
        self.assertFalse(nave.online)
        _crea_stat_per_pg(self.pg, "0RI", 1, "Riparazione")
        res2 = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res2.status_code, 200, res2.content)
        nave.refresh_from_db()
        self.assertTrue(nave.online)

    def test_guasto_persiste_nuova_sessione_idle(self):
        nave = StatoSottosistemaNave.objects.get(sottosistema=self.sottos)
        nave.online = False
        nave.guasto_at = timezone.now()
        nave.save()
        self.sessione.stato = "crashed"
        self.sessione.ended_at = timezone.now()
        self.sessione.save()
        nuova = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_IDLE,
        )
        from pilotaggio.stato_nave import propaga_stati_nave_a_sessione

        propaga_stati_nave_a_sessione(nuova)
        stato = StatoSottosistemaSessione.objects.get(sessione=nuova, sottosistema=self.sottos)
        self.assertFalse(stato.online)

    def test_ripara_espulso_bloccato(self):
        nave = StatoSottosistemaNave.objects.get(sottosistema=self.sottos)
        nave.online = False
        nave.espulso = True
        nave.save()
        _crea_stat_per_pg(self.pg, "0RI", 1, "Riparazione")
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertIn("espuls", res.json().get("error", "").lower())

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


class QrSottosistemaRiparazioneComponentiTests(TestCase):
    def setUp(self):
        from django.core.management import call_command

        from pilotaggio.componenti_stiva import mattoni_componente_qs, staff_modifica_stiva
        from pilotaggio.models import PilotRuntimeConfig

        call_command("seed_componenti_nave", verbosity=0)
        cfg = PilotRuntimeConfig.get_solo()
        cfg.riparazione_componenti_abilitata = True
        cfg.save()

        self.user = User.objects.create_user(username="comp_user", password="x")
        self.pg = Personaggio.objects.create(nome="CompPG", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        codice = _codice_sottosistema_libero()
        self.manifesto = Manifesto.objects.create(nome="Reattori QR", testo="")
        self.mattone = mattoni_componente_qs().first()
        self.sottos = SottosistemaNave.objects.create(
            codice=codice,
            nome="Reattori",
            a_vista=self.manifesto,
            richiede_componenti_riparazione=True,
            requisiti_riparazione_json=[
                {"tipo": "specifico", "mattone_id": str(self.mattone.pk), "quantita": 1},
            ],
        )
        self.qr = QrCode.objects.create(vista=self.manifesto)
        staff_modifica_stiva(mattone_id=str(self.mattone.pk), delta=2)

        self.pilota_user, self.pilota = _crea_pilota_con_0pi(nome="PilotaComp", valore_0pi=1)
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
        _crea_stat_per_pg(self.pg, "0RI", 1, "Riparazione")

    def test_scan_include_requisiti_componenti(self):
        res = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(res.status_code, 200, res.content)
        req = res.json()["dati"]["requisiti_componenti"]
        self.assertTrue(req["richiede_componenti"])
        self.assertEqual(len(req["vincoli"]), 1)

    def test_repair_senza_componenti_rifiutato(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {"qr_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(res.status_code, 403, res.content)
        self.assertIn("componenti", res.json().get("error", "").lower())

    def test_repair_con_componenti_ok(self):
        res = self.client.post(
            "/api/pilot/subsystems/qr-repair/",
            {
                "qr_id": self.qr.id,
                "personaggio_id": self.pg.id,
                "componenti_scelti": [
                    {"mattone_id": str(self.mattone.pk), "quantita": 1},
                ],
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json().get("azione"), "riparato")


class PilotStivaAccessTests(TestCase):
    def setUp(self):
        from django.core.management import call_command

        from pilotaggio.componenti_stiva import staff_modifica_stiva
        from pilotaggio.models import PilotRuntimeConfig

        call_command("seed_componenti_nave", verbosity=0)
        cfg = PilotRuntimeConfig.get_solo()
        cfg.compattatore_stat_accesso_sigla = "0IN"
        cfg.save()

        self.user = User.objects.create_user(username="stiva_user", password="x")
        self.pg = Personaggio.objects.create(nome="StivaPG", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.mattone = __import__(
            "pilotaggio.componenti_stiva", fromlist=["mattoni_componente_qs"]
        ).mattoni_componente_qs().first()
        staff_modifica_stiva(mattone_id=str(self.mattone.pk), delta=1)

    def test_stiva_senza_personaggio_id_rifiutato(self):
        res = self.client.get("/api/pilot/stiva/")
        self.assertEqual(res.status_code, 400, res.content)

    def test_stiva_senza_stat_accesso_rifiutato(self):
        res = self.client.get("/api/pilot/stiva/", {"personaggio_id": self.pg.id})
        self.assertEqual(res.status_code, 403, res.content)

    def test_stiva_con_0in_ok(self):
        _crea_stat_per_pg(self.pg, "0IN", 1, "Inventario nave")
        res = self.client.get("/api/pilot/stiva/", {"personaggio_id": self.pg.id})
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertIn("righe", body)
        self.assertIn("mattoni_catalogo", body)
        self.assertEqual(body.get("stat_accesso_sigla"), "0IN")
