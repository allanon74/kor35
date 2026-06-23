"""
Test integrazione viste pilotaggio: login QR pilota, start/state/command.
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import (
    A_vista,
    Era,
    Manifesto,
    Personaggio,
    PersonaggioStatisticaBase,
    Prefettura,
    QrCode,
    Statistica,
)
from pilotaggio.models import (
    EventoNave,
    PilotConsoleToken,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_DECOLLO,
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SEQUENZA_DECOLLO,
)


def _crea_pilota_con_0pi(nome="Pilota", valore_0pi=2):
    """Crea utente, personaggio e PersonaggioStatisticaBase per 0PI."""
    user = User.objects.create_user(username=f"u_{nome}", password="x")
    pg = Personaggio.objects.create(nome=nome, proprietario=user)
    stat, _ = Statistica.objects.update_or_create(
        sigla="0PI",
        defaults={"nome": "Pilotaggio", "parametro": "pilotaggio"},
    )
    PersonaggioStatisticaBase.objects.update_or_create(
        personaggio=pg, statistica=stat, defaults={"valore_base": valore_0pi}
    )
    if hasattr(pg, "_punteggi_base_cache"):
        del pg._punteggi_base_cache
    return user, pg


def _crea_qr_per_personaggio(pg):
    qr = QrCode.objects.create()
    qr.vista_id = pg.inventario_ptr_id
    qr.save()
    return qr


class QrLoginTests(TestCase):
    def test_login_ok_con_0pi(self):
        user, pg = _crea_pilota_con_0pi(valore_0pi=1)
        qr = _crea_qr_per_personaggio(pg)
        client = APIClient()
        res = client.post("/api/pilot/auth/qr-login/", {"qr_id": qr.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        data = res.json()
        self.assertIn("token", data)
        self.assertEqual(data["pilota"]["id"], pg.pk)

    def test_login_negato_senza_0pi(self):
        user, pg = _crea_pilota_con_0pi(valore_0pi=0)
        qr = _crea_qr_per_personaggio(pg)
        client = APIClient()
        res = client.post("/api/pilot/auth/qr-login/", {"qr_id": qr.id}, format="json")
        self.assertEqual(res.status_code, 403)

    def test_login_qr_inesistente(self):
        client = APIClient()
        res = client.post("/api/pilot/auth/qr-login/", {"qr_id": "ZZZ"}, format="json")
        self.assertEqual(res.status_code, 404)


class SessioneEndToEndTests(TestCase):
    def setUp(self):
        self.user, self.pg = _crea_pilota_con_0pi(valore_0pi=1)
        self.qr = _crea_qr_per_personaggio(self.pg)
        self.token = PilotConsoleToken.objects.create(
            pilota=self.pg, token=PilotConsoleToken.genera_token()
        )
        self.client_api = APIClient()
        self.client_api.credentials(HTTP_AUTHORIZATION=f"PilotToken {self.token.token}")

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        self.partenza = Prefettura.objects.create(era=era, nome="P1")
        self.arrivo = Prefettura.objects.create(era=era, nome="P2")

        SequenzaVolo.objects.create(
            tipo=SEQUENZA_DECOLLO, codici=["A12"], attiva=True
        )
        EventoNave.objects.create(
            nome="Brecca", descrizione="Sigilla.",
            codice_soluzione_esatta="B23",
            durata_base_secondi=20,
            peso_random=10,
        )

    def test_state_iniziale(self):
        res = self.client_api.get("/api/pilot/session/state/")
        self.assertEqual(res.status_code, 200, res.content)

    def test_state_espone_sessione_terminata_per_schermata_finale(self):
        sessione = SessioneVolo.objects.create(
            pilota=self.pg,
            prefettura_partenza=self.partenza,
            prefettura_arrivo=self.arrivo,
            stato=SESSIONE_STATO_CRASHED,
            defcon=6,
            durata_pianificata_secondi=600,
            crash_reason="defcon_overflow",
            ended_at=timezone.now(),
        )
        res = self.client_api.get("/api/pilot/session/state/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertIsNotNone(body.get("sessione"))
        self.assertEqual(body["sessione"]["id"], str(sessione.pk))
        self.assertEqual(body["sessione"]["stato"], SESSIONE_STATO_CRASHED)
        self.assertEqual(body["sessione"]["crash_reason"], "defcon_overflow")

    def test_reset_dopo_crash_torna_idle(self):
        SessioneVolo.objects.create(
            pilota=self.pg,
            prefettura_partenza=self.partenza,
            prefettura_arrivo=self.arrivo,
            stato=SESSIONE_STATO_CRASHED,
            defcon=6,
            durata_pianificata_secondi=600,
            crash_reason="catastrophic_event",
            ended_at=timezone.now(),
        )
        res = self.client_api.post("/api/pilot/session/reset/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["sessione"]["stato"], SESSIONE_STATO_IDLE)

        res_state = self.client_api.get("/api/pilot/session/state/")
        self.assertEqual(res_state.status_code, 200, res_state.content)
        self.assertEqual(res_state.json()["sessione"]["stato"], SESSIONE_STATO_IDLE)

    def test_logout_dopo_crash_prossimo_state_idle(self):
        SessioneVolo.objects.create(
            pilota=self.pg,
            prefettura_partenza=self.partenza,
            prefettura_arrivo=self.arrivo,
            stato=SESSIONE_STATO_CRASHED,
            defcon=6,
            durata_pianificata_secondi=600,
            crash_reason="catastrophic_event",
            ended_at=timezone.now(),
        )
        res = self.client_api.post("/api/pilot/auth/logout/", {}, format="json")
        self.assertEqual(res.status_code, 200, res.content)

        nuovo_token = PilotConsoleToken.objects.create(
            pilota=self.pg, token=PilotConsoleToken.genera_token()
        )
        client2 = APIClient()
        client2.credentials(HTTP_AUTHORIZATION=f"PilotToken {nuovo_token.token}")
        res_state = client2.get("/api/pilot/session/state/")
        self.assertEqual(res_state.status_code, 200, res_state.content)
        self.assertEqual(res_state.json()["sessione"]["stato"], SESSIONE_STATO_IDLE)

    def test_start_passa_a_decollo(self):
        res = self.client_api.post(
            "/api/pilot/session/start/",
            {"prefettura_partenza_id": self.partenza.pk, "prefettura_arrivo_id": self.arrivo.pk},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["sessione"]["stato"], SESSIONE_STATO_DECOLLO)

    def test_command_esegue_sequenza_decollo(self):
        self.client_api.post(
            "/api/pilot/session/start/",
            {"prefettura_partenza_id": self.partenza.pk, "prefettura_arrivo_id": self.arrivo.pk},
            format="json",
        )
        res = self.client_api.post(
            "/api/pilot/session/command/", {"codice": "A12"}, format="json"
        )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["sessione"]["stato"], SESSIONE_STATO_VOLO)


@override_settings(PILOT_CONSOLE_ENABLED=True)
class TicketLoginFlowTests(TestCase):
    def setUp(self):
        self.user, self.pg = _crea_pilota_con_0pi(nome="PilotaTicket", valore_0pi=2)
        self.console_client = APIClient()
        self.phone_client = APIClient()
        self.phone_client.force_authenticate(user=self.user)

    def test_ticket_login_inverso_ok(self):
        create = self.console_client.post("/api/pilot/auth/console-ticket/", {}, format="json")
        self.assertEqual(create.status_code, 201, create.content)
        payload = create.json()
        ticket_id = payload["ticket_id"]
        codice = payload["codice"]

        claim = self.phone_client.get(
            f"/api/pilot/auth/console-ticket/{ticket_id}/claim/?c={codice}"
        )
        self.assertEqual(claim.status_code, 200, claim.content)

        status_res = self.console_client.get(
            f"/api/pilot/auth/console-ticket/{ticket_id}/status/?c={codice}"
        )
        self.assertEqual(status_res.status_code, 200, status_res.content)
        body = status_res.json()
        self.assertEqual(body["status"], "authorized")
        self.assertIn("token", body)


class StaffSottosistemaAssociaQrTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_pilot", password="x", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.sottos = SottosistemaNave.objects.create(codice="Q", nome="Propulsione")
        self.qr = QrCode.objects.create()

    def test_associa_qr_senza_vista_crea_manifesto(self):
        url = f"/api/pilot/staff/sottosistemi/{self.sottos.id}/associa-qr/"
        res = self.client.post(url, {"qr_id": self.qr.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.sottos.refresh_from_db()
        self.assertIsNotNone(self.sottos.a_vista_id)
        self.qr.refresh_from_db()
        self.assertEqual(self.qr.vista_id, self.sottos.a_vista_id)
        self.assertTrue(
            Manifesto.objects.filter(pk=self.sottos.a_vista_id).exists()
        )

    def test_associa_qr_già_legato_a_vista(self):
        m = Manifesto.objects.create(nome="M1", testo="")
        self.qr.vista = m
        self.qr.save()
        url = f"/api/pilot/staff/sottosistemi/{self.sottos.id}/associa-qr/"
        res = self.client.post(url, {"qr_id": self.qr.id}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.sottos.refresh_from_db()
        self.assertEqual(self.sottos.a_vista_id, m.pk)

    def test_vista_occupata_da_altro_sottosistema(self):
        m = Manifesto.objects.create(nome="M2", testo="")
        self.qr.vista = m
        self.qr.save()
        altro = SottosistemaNave.objects.create(codice="Z", nome="Altro")
        altro.a_vista = m
        altro.save()
        url = f"/api/pilot/staff/sottosistemi/{self.sottos.id}/associa-qr/"
        res = self.client.post(url, {"qr_id": self.qr.id}, format="json")
        self.assertEqual(res.status_code, 400, res.content)
        self.sottos.refresh_from_db()
        self.assertIsNone(self.sottos.a_vista_id)


class StaffSessioneLiveTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_live", password="x", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        self.pilota_user, self.pilota = _crea_pilota_con_0pi(nome="PilotaLive", valore_0pi=1)
        self.sottos = SottosistemaNave.objects.create(
            codice="V", nome="LiveTest", attivo=True
        )
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            distanza_percorsa=100.0,
            decollo_completato_at=timezone.now(),
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione,
            sottosistema=self.sottos,
            online=True,
            livello_attuale=3,
            livello_target=3,
        )

    def test_sessione_live_get(self):
        res = self.client.get("/api/pilot/staff/sessione-live/")
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertTrue(body["decollo_effettuato"])
        self.assertEqual(body["sessione"]["stato"], SESSIONE_STATO_VOLO)
        self.assertGreaterEqual(len(body["sottosistemi"]), 1)

    def test_staff_guasta_e_ripara(self):
        res = self.client.post(
            "/api/pilot/staff/sessione-live/sottosistema/",
            {"sottosistema_id": str(self.sottos.pk), "azione": "guasto"},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        stato = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sottos
        )
        self.assertFalse(stato.online)

        res2 = self.client.post(
            "/api/pilot/staff/sessione-live/sottosistema/",
            {"sottosistema_id": str(self.sottos.pk), "azione": "ripara"},
            format="json",
        )
        self.assertEqual(res2.status_code, 200, res2.content)
        stato.refresh_from_db()
        self.assertTrue(stato.online)
        self.assertEqual(stato.livello_attuale, 3)


class StaffSerbatoioCarburanteTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_fuel", password="x", is_staff=True
        )
        self.client = APIClient()
        self.client.force_authenticate(user=self.staff)
        _, self.pilota = _crea_pilota_con_0pi(nome="PilotaFuel", valore_0pi=1)
        self.serbatoio = SottosistemaNave.objects.create(
            codice="U",
            nome="Serbatoio Test",
            tipo="serbatoio",
            capacita_carburante=50000.0,
            attivo=True,
        )
        self.altro = SottosistemaNave.objects.create(
            codice="Z", nome="Non serbatoio", tipo="standard", attivo=True
        )
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_IDLE,
            carburante_attuale=1200.0,
            carburante_massimo=1000.0,
        )

    def test_get_carburante_sessione(self):
        url = f"/api/pilot/staff/sottosistemi/{self.serbatoio.pk}/carburante-sessione/"
        res = self.client.get(url)
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertTrue(body["sessione_attiva"])
        self.assertEqual(body["carburante_attuale"], 1200.0)
        self.assertEqual(body["carburante_massimo"], 50000.0)

    def test_post_imposta_carburante(self):
        url = f"/api/pilot/staff/sottosistemi/{self.serbatoio.pk}/carburante-sessione/"
        res = self.client.post(url, {"carburante_attuale": 42000}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.sessione.refresh_from_db()
        self.assertEqual(self.sessione.carburante_attuale, 42000.0)
        self.assertEqual(self.sessione.carburante_massimo, 50000.0)

    def test_post_riempi(self):
        url = f"/api/pilot/staff/sottosistemi/{self.serbatoio.pk}/carburante-sessione/"
        res = self.client.post(url, {"riempi": True}, format="json")
        self.assertEqual(res.status_code, 200, res.content)
        self.sessione.refresh_from_db()
        self.assertEqual(self.sessione.carburante_attuale, 50000.0)

    def test_rifiuta_non_serbatoio(self):
        url = f"/api/pilot/staff/sottosistemi/{self.altro.pk}/carburante-sessione/"
        res = self.client.post(url, {"riempi": True}, format="json")
        self.assertEqual(res.status_code, 400, res.content)

