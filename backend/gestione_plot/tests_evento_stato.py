"""Avvio/chiusura evento: protezione contro il doppio click «Inizia» → «Termina».

Il pulsante staff cambia etichetta nella stessa posizione: senza protezione un
secondo click chiude l'evento appena avviato e i giocatori perdono la tab Tasks.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.test import APITestCase

from gestione_plot.models import Evento, EventoPremioPersonaggio
from gestione_plot.views import EVENTO_TERMINA_GUARD_SECONDS
from personaggi.models import (
    Campagna,
    Personaggio,
    PuntiCaratteristicaMovimento,
    TipologiaPersonaggio,
)

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


class EventoIniziaPremiGiaAssegnatiTests(APITestCase):
    """Riavvio evento: lo staff scegle se riattribuire il premio di presenza."""

    def setUp(self):
        self.master = User.objects.create_superuser("master_premi", "p@test.local", "x")
        self.campagna = Campagna.objects.create(slug="premi-evento", nome="Premi evento", attiva=True)
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante premi", giocante=True)
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento premi",
            data_inizio=now - timedelta(hours=1),
            data_fine=now + timedelta(days=1),
            pc_guadagnati=2,
        )
        self.pg = Personaggio.objects.create(
            nome="PG premi",
            proprietario=self.master,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.evento.partecipanti.add(self.pg)
        self.client.force_authenticate(user=self.master)

    def _inizia(self, **payload):
        return self.client.post(
            f"/api/plot/api/eventi/{self.evento.id}/inizia/",
            payload,
            format="json",
        )

    def _chiudi(self):
        self.evento.refresh_from_db()
        self.evento.ended_at = timezone.now()
        self.evento.save(update_fields=["ended_at", "updated_at"])

    def _movimenti_pc(self):
        return PuntiCaratteristicaMovimento.objects.filter(personaggio=self.pg).count()

    def test_primo_avvio_assegna_senza_chiedere(self):
        resp = self._inizia()
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["premi_applicati"], 1)
        self.assertEqual(resp.data["premi_saltati"], 0)
        self.assertEqual(self._movimenti_pc(), 1)

    def test_riavvio_chiede_conferma(self):
        self._inizia()
        self._chiudi()
        resp = self._inizia()
        self.assertEqual(resp.status_code, 409, resp.data)
        self.assertEqual(resp.data["code"], "premi_gia_assegnati")
        self.assertEqual(resp.data["gia_premiati_count"], 1)
        self.assertEqual(resp.data["partecipanti_count"], 1)
        self.assertEqual(resp.data["gia_premiati"][0]["nome"], "PG premi")
        self.evento.refresh_from_db()
        self.assertIsNotNone(self.evento.ended_at)

    def test_riavvio_con_riassegna_paga_di_nuovo(self):
        self._inizia()
        self._chiudi()
        resp = self._inizia(riassegna_premi=True)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["premi_applicati"], 1)
        self.assertEqual(resp.data["premi_saltati"], 0)
        self.assertEqual(self._movimenti_pc(), 2)

    def test_riavvio_senza_riassegna_salta_chi_ha_gia_avuto(self):
        self._inizia()
        self._chiudi()
        resp = self._inizia(riassegna_premi=False)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["premi_applicati"], 0)
        self.assertEqual(resp.data["premi_saltati"], 1)
        self.assertEqual(self._movimenti_pc(), 1)
        # Il premio risulta coperto dall'avvio corrente: «Accredita mancanti» non lo ripaga.
        self.evento.refresh_from_db()
        row = EventoPremioPersonaggio.objects.get(evento=self.evento, personaggio=self.pg)
        self.assertEqual(row.avvio_at, self.evento.started_at)

    def test_riavvio_senza_riassegna_paga_i_nuovi_iscritti(self):
        self._inizia()
        self._chiudi()
        nuovo = Personaggio.objects.create(
            nome="PG nuovo",
            proprietario=self.master,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.evento.partecipanti.add(nuovo)
        resp = self._inizia(riassegna_premi=False)
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertEqual(resp.data["premi_applicati"], 1)
        self.assertEqual(resp.data["premi_saltati"], 1)
        self.assertEqual(
            PuntiCaratteristicaMovimento.objects.filter(personaggio=nuovo).count(), 1
        )
