"""Homepage wiki e calendario: niente eventi di prova, date provvisorie nascoste."""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import CalendarioFeedToken, Evento

User = get_user_model()


class EventiPubbliciVisibilitaTests(APITestCase):
    def setUp(self):
        now = timezone.now()
        self.pubblico = Evento.objects.create(
            titolo="Live bosco",
            data_inizio=now + timedelta(days=20),
            data_fine=now + timedelta(days=22),
            luogo="Bosco",
        )
        self.test_master = Evento.objects.create(
            titolo="Prova PayPal master",
            data_inizio=now + timedelta(days=5),
            data_fine=now + timedelta(days=6),
            iscrizione_test_attiva=True,
            logistiche_pubbliche="<p>segreto sandbox</p>",
        )
        self.tbd = Evento.objects.create(
            titolo="Prossimo live",
            data_inizio=now + timedelta(days=40),
            data_fine=now + timedelta(days=42),
            data_da_definire=True,
            luogo="Da confermare",
            logistiche_pubbliche="<p>Tenda principale</p>",
        )
        self.user = User.objects.create_user("cal_player_pub", "cal-pub@test.local", "x")
        self.master = User.objects.create_superuser("master_pub_ev", "master-pub@test.local", "x")

    def _rows(self, data):
        if isinstance(data, list):
            return data
        return data.get("results") or []

    def test_homepage_nasconde_eventi_test_e_date_provvisorie(self):
        resp = self.client.get("/api/plot/api/public/eventi/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        rows = self._rows(resp.data)
        titoli = [row["titolo"] for row in rows]
        self.assertIn("Live bosco", titoli)
        self.assertIn("Prossimo live", titoli)
        self.assertNotIn("Prova PayPal master", titoli)

        live = next(row for row in rows if row["titolo"] == "Live bosco")
        self.assertTrue(live["data_inizio"])
        self.assertFalse(live["data_da_definire"])
        self.assertTrue(live["e_prossimo"])

        tbd = next(row for row in rows if row["titolo"] == "Prossimo live")
        self.assertTrue(tbd["data_da_definire"])
        self.assertIsNone(tbd["data_inizio"])
        self.assertIsNone(tbd["data_fine"])
        self.assertTrue(tbd["e_prossimo"])
        self.assertNotIn(self.tbd.data_inizio.date().isoformat(), str(tbd))

    def test_dettaglio_test_assente_e_date_tbd_nascoste(self):
        missing = self.client.get(f"/api/plot/api/public/eventi/{self.test_master.id}/")
        self.assertEqual(missing.status_code, status.HTTP_404_NOT_FOUND)

        detail = self.client.get(f"/api/plot/api/public/eventi/{self.tbd.id}/")
        self.assertEqual(detail.status_code, status.HTTP_200_OK, detail.data)
        self.assertIsNone(detail.data["data_inizio"])
        self.assertIsNone(detail.data["data_fine"])
        self.assertIn("Tenda principale", detail.data["logistiche_pubbliche"])

    def test_staff_vede_ancora_le_date_provvisorie(self):
        self.client.force_authenticate(self.master)
        resp = self.client.get(f"/api/plot/api/eventi/{self.tbd.id}/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.assertTrue(resp.data["data_da_definire"])
        self.assertTrue(resp.data["data_inizio"])
        self.assertTrue(resp.data["data_fine"])

    def test_calendario_esclude_test_e_date_da_definire(self):
        token = CalendarioFeedToken.objects.create(user=self.user)
        ics = self.client.get(f"/api/plot/api/calendario.ics?token={token.token}")
        self.assertEqual(ics.status_code, status.HTTP_200_OK)
        body = ics.content.decode("utf-8")
        self.assertIn("Live bosco", body)
        self.assertNotIn("Prova PayPal master", body)
        self.assertNotIn("Prossimo live", body)
