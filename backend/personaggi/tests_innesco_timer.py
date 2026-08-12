"""Test innesco timer: attivazione, broadcast destinatari, ripristino active timers."""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import (
    InnescoTimer,
    Personaggio,
    QrCode,
    TipologiaPersonaggio,
)
from personaggi import qr_logic


class InnescoTimerBehaviorTests(TestCase):
    def setUp(self):
        self.tipo = TipologiaPersonaggio.objects.create(nome="Giocante", giocante=True)
        self.user = User.objects.create_user(username="innuser", password="pass")
        self.user2 = User.objects.create_user(username="innuser2", password="pass")
        self.pg = Personaggio.objects.create(
            nome="PG Inn", proprietario=self.user, tipologia=self.tipo
        )
        self.pg2 = Personaggio.objects.create(
            nome="PG Inn 2", proprietario=self.user2, tipologia=self.tipo
        )
        self.innesco = InnescoTimer.objects.create(
            nome="Allarme Globale",
            testo="Boom",
            durata_secondi=90,
            max_cariche=0,
            modalita_target=InnescoTimer.INNESCO_TARGET_GLOBAL,
        )
        self.qr = QrCode.objects.create(vista=self.innesco)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    @patch("personaggi.qr_logic._broadcast_timer_innesco")
    def test_scan_innesco_broadcast_include_tutti_giocanti(self, mock_broadcast):
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "timer_innesco")
        self.assertTrue(r.data["dati"]["scadenza"])
        mock_broadcast.assert_called_once()
        kwargs = mock_broadcast.call_args.kwargs
        self.assertEqual(kwargs["nome"], "Allarme Globale")
        ids = set(kwargs["recipient_personaggio_ids"])
        self.assertIn(self.pg.id, ids)
        self.assertIn(self.pg2.id, ids)

    @patch("personaggi.qr_logic._broadcast_timer_innesco")
    def test_active_timers_ripristina_innesco_per_altro_pg(self, mock_broadcast):
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        self.assertIsNotNone(payload)

        rows_self = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg)
        rows_other = qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2)
        self.assertEqual(len(rows_self), 1)
        self.assertEqual(len(rows_other), 1)
        self.assertEqual(rows_other[0]["nome"], "Allarme Globale")
        self.assertFalse(rows_other[0]["notifica_push"])  # push server-side allo scadere

        client2 = APIClient()
        client2.force_authenticate(self.user2)
        r = client2.get(
            "/api/personaggi/api/timers/active/",
            {"personaggio_id": self.pg2.id},
        )
        self.assertEqual(r.status_code, 200)
        nomi = [row["nome"] for row in r.data]
        self.assertIn("Allarme Globale", nomi)

    def test_active_timers_non_include_scaduti(self):
        payload, err = qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        self.assertIsNone(err)
        from personaggi.models import StatoInnescoTimerPersonaggio

        StatoInnescoTimerPersonaggio.objects.filter(
            personaggio=self.pg, innesco_timer=self.innesco
        ).update(data_fine=timezone.now() - timedelta(seconds=5))
        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=5),
            broadcast_push_inviata=False,
        )
        self.assertEqual(qr_logic.active_innesco_timer_rows_for_personaggio(self.pg2), [])

    @patch("personaggi.timer_expiry_push._send_webpush_to_users")
    def test_dispatch_push_scadenza_a_proprietari(self, mock_send):
        from personaggi.timer_expiry_push import dispatch_expired_innesco_pushes

        mock_send.return_value = 2
        qr_logic.attiva_innesco_timer_per_personaggio(self.pg, self.innesco)
        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=1),
            broadcast_push_inviata=False,
        )
        stats = dispatch_expired_innesco_pushes()
        self.assertEqual(stats["dispatched"], 1)
        mock_send.assert_called_once()
        user_ids = set(mock_send.call_args.args[0])
        self.assertIn(self.user.id, user_ids)
        self.assertIn(self.user2.id, user_ids)
        self.innesco.refresh_from_db()
        self.assertTrue(self.innesco.broadcast_push_inviata)

    def test_dispatch_non_ripete_push(self):
        from personaggi.timer_expiry_push import dispatch_expired_innesco_pushes

        InnescoTimer.objects.filter(pk=self.innesco.pk).update(
            broadcast_data_fine=timezone.now() - timedelta(seconds=1),
            broadcast_push_inviata=True,
        )
        with patch("personaggi.timer_expiry_push._send_webpush_to_users") as mock_send:
            stats = dispatch_expired_innesco_pushes()
            self.assertEqual(stats["dispatched"], 0)
            mock_send.assert_not_called()