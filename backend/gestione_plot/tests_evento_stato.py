"""Avvio/chiusura evento: protezione contro il doppio click «Inizia» → «Termina».

Il pulsante staff cambia etichetta nella stessa posizione: senza protezione un
secondo click chiude l'evento appena avviato e i giocatori perdono la tab Tasks.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from gestione_plot.models import Evento
from gestione_plot.views import EVENTO_TERMINA_GUARD_SECONDS

User = get_user_model()


class EventoIniziaTerminaTests(APITestCase):
    def setUp(self):
        self.master = User.objects.create_superuser("master_evento_stato", "m@test.local", "x")
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento stato",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(days=1),
        )
        self.client.force_authenticate(user=self.master)

    def _inizia(self):
        return self.client.post(f"/api/plot/api/eventi/{self.evento.id}/inizia/", {}, format="json")

    def _termina(self, **payload):
        return self.client.post(
            f"/api/plot/api/eventi/{self.evento.id}/termina/",
            payload,
            format="json",
        )

    def test_inizia_mette_evento_in_corso(self):
        resp = self._inizia()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.evento.refresh_from_db()
        self.assertIsNotNone(self.evento.started_at)
        self.assertIsNone(self.evento.ended_at)

    def test_doppio_click_non_chiude_evento_appena_avviato(self):
        self._inizia()
        resp = self._termina()
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data["code"], "evento_appena_avviato")
        self.evento.refresh_from_db()
        self.assertIsNone(self.evento.ended_at)

    def test_termina_con_force_chiude_subito(self):
        self._inizia()
        resp = self._termina(force=True)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.evento.refresh_from_db()
        self.assertIsNotNone(self.evento.ended_at)

    def test_termina_senza_force_oltre_la_finestra(self):
        self._inizia()
        self.evento.refresh_from_db()
        self.evento.started_at = timezone.now() - timedelta(
            seconds=EVENTO_TERMINA_GUARD_SECONDS + 5
        )
        self.evento.save(update_fields=["started_at", "updated_at"])
        resp = self._termina()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.evento.refresh_from_db()
        self.assertIsNotNone(self.evento.ended_at)

    def test_termina_evento_non_in_corso(self):
        resp = self._termina(force=True)
        self.assertEqual(resp.status_code, 400, resp.data)
