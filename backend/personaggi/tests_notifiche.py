from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import CalendarioFeedToken, Evento, StaffCompito, StaffCompitoAssegnazione
from personaggi.models import (
    CAMPAGNA_ROLE_HELPER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    Campagna,
    CampagnaUtente,
    NotificaPreferenze,
)
from personaggi.notify import get_or_create_preferenze, notify_user
from personaggi.telegram_bot import process_telegram_updates

User = get_user_model()


class NotificaPreferenzeApiTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="notif_player", password="x", email="player@example.com"
        )
        self.campagna = Campagna.objects.create(slug="notif-cal", nome="Notif Cal", attiva=True)
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user, ruolo=CAMPAGNA_ROLE_PLAYER, attivo=True
        )

    def test_get_defaults(self):
        self.client.force_authenticate(self.user)
        resp = self.client.get("/api/personaggi/api/notifiche/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        canali = resp.data["canali"]
        self.assertTrue(canali["webpush"]["messaggi"])
        self.assertFalse(canali["telegram"]["messaggi"])
        self.assertFalse(canali["email"]["messaggi"])
        self.assertEqual(resp.data["email"]["address"], "player@example.com")
        self.assertFalse(resp.data["calendario"]["include_compiti"])
        self.assertIn("calendario.ics?token=", resp.data["calendario"]["path"])

    def test_patch_canale(self):
        self.client.force_authenticate(self.user)
        resp = self.client.patch(
            "/api/personaggi/api/notifiche/",
            {"canali": {"telegram": {"messaggi": True}}},
            format="json",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["canali"]["telegram"]["messaggi"])
        self.assertFalse(resp.data["canali"]["telegram"]["compiti"])
        self.assertTrue(resp.data["canali"]["webpush"]["messaggi"])

    @override_settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_BOT_USERNAME="kor35bot")
    def test_telegram_link_url(self):
        self.client.force_authenticate(self.user)
        resp = self.client.post("/api/personaggi/api/notifiche/telegram/link/", {}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertIn("https://t.me/kor35bot?start=", resp.data["start_url"])
        prefs = NotificaPreferenze.objects.get(user=self.user)
        self.assertEqual(prefs.telegram_link_code, resp.data["code"])


class NotifyDispatcherTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="disp_user", password="x", email="disp@example.com"
        )

    @patch("personaggi.notify._send_email", return_value=1)
    @patch("personaggi.notify._send_telegram", return_value=1)
    @patch("personaggi.notify._send_webpush", return_value=1)
    def test_default_solo_webpush(self, mock_wp, mock_tg, mock_email):
        n = notify_user(self.user, category="messaggi", head="H", body="B")
        self.assertEqual(n, 1)
        mock_wp.assert_called_once()
        mock_tg.assert_not_called()
        mock_email.assert_not_called()

    @patch("personaggi.notify._send_email", return_value=1)
    @patch("personaggi.notify._send_telegram", return_value=1)
    @patch("personaggi.notify._send_webpush", return_value=1)
    def test_telegram_richiede_chat_e_toggle(self, mock_wp, mock_tg, mock_email):
        prefs = get_or_create_preferenze(self.user)
        prefs.set_canale("telegram", "messaggi", True)
        prefs.save()
        notify_user(self.user, category="messaggi", head="H", body="B")
        mock_tg.assert_not_called()

        prefs.telegram_chat_id = "12345"
        prefs.save(update_fields=["telegram_chat_id", "updated_at"])
        notify_user(self.user, category="messaggi", head="H", body="B")
        mock_tg.assert_called_once()

    @patch("personaggi.notify._send_email", return_value=1)
    @patch("personaggi.notify._send_telegram", return_value=1)
    @patch("personaggi.notify._send_webpush", return_value=1)
    def test_email_toggle(self, mock_wp, mock_tg, mock_email):
        prefs = get_or_create_preferenze(self.user)
        prefs.set_canale("email", "in_game", True)
        prefs.save()
        notify_user(self.user, category="in_game", head="H", body="B")
        mock_email.assert_called_once()
        notify_user(self.user, category="messaggi", head="H", body="B")
        self.assertEqual(mock_email.call_count, 1)


class TelegramLinkHookTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="tg_user", password="x")

    @override_settings(TELEGRAM_BOT_TOKEN="tok", TELEGRAM_BOT_USERNAME="kor35bot")
    @patch("personaggi.telegram_bot._api")
    def test_start_collega_chat(self, mock_api):
        prefs = get_or_create_preferenze(self.user)
        prefs.telegram_link_code = "deadbeef"
        prefs.telegram_link_expires = timezone.now() + timedelta(minutes=10)
        prefs.save()

        def _api(method, payload=None, http_get=False):
            if method == "getUpdates":
                return {
                    "ok": True,
                    "result": [
                        {
                            "update_id": 7,
                            "message": {
                                "text": "/start deadbeef",
                                "chat": {"id": 4242},
                                "from": {"username": "larper"},
                            },
                        }
                    ],
                }
            return {"ok": True}

        mock_api.side_effect = _api
        stats = process_telegram_updates()
        self.assertEqual(stats["linked"], 1)
        prefs.refresh_from_db()
        self.assertEqual(prefs.telegram_chat_id, "4242")
        self.assertEqual(prefs.telegram_username, "larper")
        self.assertEqual(prefs.telegram_link_code, "")


class CalendarioIcsTuttiTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="ics-all", nome="ICS All", attiva=True)
        self.player = User.objects.create_user(username="ics_player", password="x")
        self.helper = User.objects.create_user(username="ics_helper", password="x")
        self.master = User.objects.create_user(username="ics_master", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.player, ruolo=CAMPAGNA_ROLE_PLAYER, attivo=True
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.helper, ruolo=CAMPAGNA_ROLE_HELPER, attivo=True
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.master, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        self.evento = Evento.objects.create(
            titolo="Sessione bosco",
            data_inizio=timezone.now() + timedelta(days=10),
            data_fine=timezone.now() + timedelta(days=12),
            luogo="Foresta",
            sinossi="Due giorni live.",
        )
        compito = StaffCompito.objects.create(
            campagna=self.campagna,
            titolo="Stampare volantini",
            descrizione="A3",
            scadenza=timezone.now() + timedelta(hours=8),
            preavviso_minuti=60,
            creato_da=self.master,
        )
        StaffCompitoAssegnazione.objects.create(compito=compito, user=self.helper)

    def test_player_solo_eventi(self):
        self.client.force_authenticate(self.player)
        token_resp = self.client.get("/api/personaggi/api/calendario/feed-token/")
        self.assertEqual(token_resp.status_code, status.HTTP_200_OK)
        self.assertFalse(token_resp.data["include_compiti"])
        ics = self.client.get(f"/api/plot/api/calendario.ics?token={token_resp.data['token']}")
        self.assertEqual(ics.status_code, 200)
        body = ics.content.decode("utf-8")
        self.assertIn("Sessione bosco", body)
        self.assertNotIn("Stampare volantini", body)

    def test_helper_eventi_e_compiti(self):
        token_row = CalendarioFeedToken.objects.create(user=self.helper)
        ics = self.client.get(f"/api/plot/api/calendario.ics?token={token_row.token}")
        self.assertEqual(ics.status_code, 200)
        body = ics.content.decode("utf-8")
        self.assertIn("Sessione bosco", body)
        self.assertIn("Stampare volantini", body)
        self.assertIn("BEGIN:VALARM", body)

    def test_alias_compiti_ics_ancora_valido(self):
        token_row = CalendarioFeedToken.objects.create(user=self.helper)
        ics = self.client.get(f"/api/plot/api/calendario-compiti.ics?token={token_row.token}")
        self.assertEqual(ics.status_code, 200)
        self.assertIn("Stampare volantini", ics.content.decode("utf-8"))
