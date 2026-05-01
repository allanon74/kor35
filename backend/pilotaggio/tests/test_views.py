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
    SottosistemaNave,
    SESSIONE_STATO_DECOLLO,
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
