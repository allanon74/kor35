from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import Evento, EventoVocePortare
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
)

User = get_user_model()


class EventoVocePortareApiTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="voci-portare", nome="Voci Portare", attiva=True)
        self.master = User.objects.create_user(username="master_vp", password="x")
        self.staffer_a = User.objects.create_user(username="staff_a", password="x")
        self.staffer_b = User.objects.create_user(username="staff_b", password="x")

        for user, ruolo in (
            (self.master, CAMPAGNA_ROLE_MASTER),
            (self.staffer_a, CAMPAGNA_ROLE_STAFFER),
            (self.staffer_b, CAMPAGNA_ROLE_STAFFER),
        ):
            CampagnaUtente.objects.create(campagna=self.campagna, user=user, ruolo=ruolo, attivo=True)

        now = timezone.now()
        self.evento = Evento.objects.create(titolo="Evento test", data_inizio=now, data_fine=now)
        self.evento.staff_assegnato.set([self.master, self.staffer_a, self.staffer_b])

        self.voce_a = EventoVocePortare.objects.create(
            evento=self.evento,
            descrizione="Tavolo pieghevole",
            portatore=self.staffer_a,
        )
        self.voce_unassigned = EventoVocePortare.objects.create(
            evento=self.evento,
            descrizione="Cavo HDMI",
        )

    def _auth(self, user, method, url, data=None):
        self.client.force_authenticate(user=user)
        return getattr(self.client, method)(
            url,
            data,
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_evento_serializer_include_voci_portare(self):
        resp = self._auth(self.staffer_a, "get", "/api/plot/api/eventi/")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        evento = next(row for row in resp.data if row["id"] == self.evento.id)
        self.assertEqual(len(evento["voci_portare"]), 2)

    def test_master_crea_voce_senza_portatore(self):
        resp = self._auth(
            self.master,
            "post",
            "/api/plot/api/voci-portare/",
            {"evento": self.evento.id, "descrizione": "Gazebo"},
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertIsNone(resp.data.get("portatore"))

    def test_staffer_non_puo_creare(self):
        resp = self._auth(
            self.staffer_a,
            "post",
            "/api/plot/api/voci-portare/",
            {"evento": self.evento.id, "descrizione": "Vietato"},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staffer_toggle_propria_voce(self):
        resp = self._auth(
            self.staffer_a,
            "patch",
            f"/api/plot/api/voci-portare/{self.voce_a.id}/",
            {"a_posto": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.voce_a.refresh_from_db()
        self.assertTrue(self.voce_a.a_posto)

    def test_staffer_non_toggle_voce_altrui(self):
        resp = self._auth(
            self.staffer_b,
            "patch",
            f"/api/plot/api/voci-portare/{self.voce_a.id}/",
            {"a_posto": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_staffer_toggle_voce_non_assegnata(self):
        resp = self._auth(
            self.staffer_b,
            "patch",
            f"/api/plot/api/voci-portare/{self.voce_unassigned.id}/",
            {"a_posto": True},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)

    def test_portatore_deve_essere_staff_evento(self):
        outsider = User.objects.create_user(username="outsider", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=outsider, ruolo=CAMPAGNA_ROLE_STAFFER, attivo=True
        )
        resp = self._auth(
            self.master,
            "post",
            "/api/plot/api/voci-portare/",
            {"evento": self.evento.id, "descrizione": "X", "portatore": outsider.id},
        )
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_filtro_per_evento(self):
        resp = self._auth(
            self.staffer_a,
            "get",
            f"/api/plot/api/voci-portare/?evento={self.evento.id}",
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 2)
