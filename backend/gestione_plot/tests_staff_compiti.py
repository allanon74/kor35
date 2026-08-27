from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.compiti_ics import build_compiti_ics
from gestione_plot.compiti_push import dispatch_compiti_scadenze
from gestione_plot.models import CalendarioFeedToken, StaffCompito, StaffCompitoAssegnazione
from personaggi.models import (
    CAMPAGNA_ROLE_HELPER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
)

User = get_user_model()


class StaffCompitiApiTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="compiti-cal", nome="Compiti Cal", attiva=True)
        self.master = User.objects.create_user(username="master_cal", password="x")
        self.staffer = User.objects.create_user(username="staff_cal", password="x")
        self.helper = User.objects.create_user(username="helper_cal", password="x")
        self.player = User.objects.create_user(username="player_cal", password="x")

        for user, ruolo in (
            (self.master, CAMPAGNA_ROLE_MASTER),
            (self.staffer, CAMPAGNA_ROLE_STAFFER),
            (self.helper, CAMPAGNA_ROLE_HELPER),
            (self.player, CAMPAGNA_ROLE_PLAYER),
        ):
            CampagnaUtente.objects.create(campagna=self.campagna, user=user, ruolo=ruolo, attivo=True)

        self.scadenza = timezone.now() + timedelta(hours=2)
        self.compito = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Stampare volantini",
            descrizione="A3, 200 copie",
            scadenza=self.scadenza,
            preavviso_minuti=60,
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=self.compito, user=self.helper)
        StaffCompitoAssegnazione.objects.create(compito=self.compito, user=self.staffer)

    def _auth(self, user, method, url, data=None):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(
            url,
            data,
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_master_crea_compito(self):
        scadenza = (timezone.now() + timedelta(days=1)).isoformat()
        resp = self._auth(
            self.master,
            "post",
            "/api/plot/api/calendario-compiti/",
            {
                "titolo": "Post Instagram",
                "descrizione": "Reel evento",
                "scadenza": scadenza,
                "preavviso_minuti": 1440,
                "assegnatari": [self.helper.id],
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED, resp.data)
        self.assertEqual(resp.data["titolo"], "Post Instagram")
        self.assertEqual(len(resp.data["assegnazioni"]), 1)
        self.assertEqual(resp.data["assegnazioni"][0]["user"], self.helper.id)

    def test_staffer_non_puo_creare(self):
        resp = self._auth(
            self.staffer,
            "post",
            "/api/plot/api/calendario-compiti/",
            {
                "titolo": "Vietato",
                "scadenza": (timezone.now() + timedelta(days=1)).isoformat(),
            },
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_non_accede_dashboard_layout(self):
        resp = self._auth(self.helper, "get", "/api/plot/api/staff/dashboard-layout/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_vede_solo_propri(self):
        altro = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Solo master",
            scadenza=self.scadenza,
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=altro, user=self.master)

        resp = self._auth(self.helper, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        titoli = {row["titolo"] for row in resp.data}
        self.assertIn("Stampare volantini", titoli)
        self.assertNotIn("Solo master", titoli)

    def test_player_non_vede_compiti(self):
        resp = self._auth(self.player, "get", "/api/plot/api/calendario-compiti/miei/")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_helper_completa(self):
        resp = self._auth(self.helper, "post", f"/api/plot/api/calendario-compiti/{self.compito.id}/completa/", {})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        mine = resp.data["mia_assegnazione"]
        self.assertIsNotNone(mine["completato_at"])

    def test_ics_feed_con_token(self):
        token_row = CalendarioFeedToken.objects.create(user=self.helper)
        resp = self.client.get(f"/api/plot/api/calendario-compiti.ics?token={token_row.token}")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/calendar", resp["Content-Type"])
        body = resp.content.decode("utf-8")
        self.assertIn("BEGIN:VCALENDAR", body)
        self.assertIn("Stampare volantini", body)
        self.assertIn("BEGIN:VALARM", body)

    def test_ics_token_mancante(self):
        resp = self.client.get("/api/plot/api/calendario-compiti.ics")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_build_ics_helper(self):
        rows = list(self.compito.assegnazioni.select_related("compito"))
        ics = build_compiti_ics(rows)
        self.assertIn("VEVENT", ics)

    @patch("gestione_plot.compiti_push.notify_compito_user", return_value=1)
    def test_dispatch_preavviso_e_scadenza(self, mock_notify):
        past = timezone.now() - timedelta(minutes=5)
        self.compito.scadenza = past
        self.compito.preavviso_minuti = 60
        self.compito.save()

        stats = dispatch_compiti_scadenze(now=timezone.now())
        self.assertGreaterEqual(stats["dispatched"], 1)
        self.assertTrue(mock_notify.called)

        helper_row = StaffCompitoAssegnazione.objects.get(compito=self.compito, user=self.helper)
        self.assertTrue(helper_row.push_preavviso_inviata)
        self.assertTrue(helper_row.push_scadenza_inviata)

        mock_notify.reset_mock()
        stats2 = dispatch_compiti_scadenze(now=timezone.now())
        self.assertEqual(stats2["dispatched"], 0)
        self.assertFalse(mock_notify.called)

    def test_helper_feed_token(self):
        resp = self._auth(self.helper, "get", "/api/plot/api/calendario-compiti/feed-token/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("token", resp.data)
        self.assertTrue(str(resp.data["path"]).endswith(str(resp.data["token"])))
        self.assertTrue(resp.data["include_compiti"])
        self.assertIn("calendario.ics", resp.data["path"])
