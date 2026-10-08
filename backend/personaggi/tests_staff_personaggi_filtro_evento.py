"""Filtro «Iscritti all'evento» dell'hub staff personaggi."""

from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import Evento
from personaggi.models import Personaggio, TipologiaPersonaggio

User = get_user_model()

LIST_URL = "/api/personaggi/api/staff/personaggi/"
OPZIONI_URL = "/api/personaggi/api/staff/personaggi/eventi-opzioni/"


class StaffPersonaggiFiltroEventoTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username="staff_filtro_evento", password="x", is_staff=True, is_superuser=True
        )
        self.client.force_authenticate(user=self.staff)

        self.tipo = TipologiaPersonaggio.objects.create(nome="PG filtro evento", giocante=True)
        self.iscritto = Personaggio.objects.create(nome="Aiace Iscritto", tipologia=self.tipo)
        self.altro = Personaggio.objects.create(nome="Bruto Assente", tipologia=self.tipo)

        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento filtro",
            data_inizio=now,
            data_fine=now + timezone.timedelta(hours=8),
        )
        self.evento.partecipanti.add(self.iscritto)
        self.evento_vuoto = Evento.objects.create(
            titolo="Evento senza iscritti",
            data_inizio=now - timezone.timedelta(days=30),
            data_fine=now - timezone.timedelta(days=29),
        )

    def _nomi(self, response):
        body = response.json()
        rows = body.get("results") if isinstance(body, dict) else body
        return [row["nome"] for row in rows or []]

    def test_senza_filtro_evento_torna_tutti(self):
        res = self.client.get(LIST_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        nomi = self._nomi(res)
        self.assertIn("Aiace Iscritto", nomi)
        self.assertIn("Bruto Assente", nomi)

    def test_filtro_evento_torna_solo_iscritti(self):
        res = self.client.get(LIST_URL, {"evento": self.evento.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(self._nomi(res), ["Aiace Iscritto"])

    def test_filtro_evento_senza_iscritti_torna_vuoto(self):
        res = self.client.get(LIST_URL, {"evento": self.evento_vuoto.id})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(self._nomi(res), [])

    def test_filtro_evento_non_numerico_non_rompe(self):
        res = self.client.get(LIST_URL, {"evento": "non-un-id"})
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        self.assertEqual(self._nomi(res), [])

    def test_filtro_evento_si_combina_con_stato_morto(self):
        self.evento.partecipanti.add(self.altro)
        self.altro.data_morte = timezone.now()
        self.altro.save(update_fields=["data_morte", "updated_at"])

        res = self.client.get(LIST_URL, {"evento": self.evento.id, "morto": "vivo"})
        self.assertEqual(self._nomi(res), ["Aiace Iscritto"])

        res_morti = self.client.get(LIST_URL, {"evento": self.evento.id, "morto": "morto"})
        self.assertEqual(self._nomi(res_morti), ["Bruto Assente"])

    def test_eventi_opzioni_espone_titolo_e_conteggio_iscritti(self):
        res = self.client.get(OPZIONI_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK, res.content)
        rows = {row["titolo"]: row for row in res.json()}
        self.assertIn("Evento filtro", rows)
        self.assertEqual(rows["Evento filtro"]["iscritti"], 1)
        self.assertEqual(rows["Evento senza iscritti"]["iscritti"], 0)
        self.assertIn("data_inizio", rows["Evento filtro"])
