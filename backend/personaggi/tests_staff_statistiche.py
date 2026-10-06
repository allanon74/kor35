"""CRUD staff catalogo Statistiche (dashboard)."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import Statistica


class StatisticaStaffViewSetTests(APITestCase):
    def setUp(self):
        Statistica.objects.filter(sigla__in=["ZS1", "ZS2", "0Z9"]).delete()
        self.staff = User.objects.create_user(
            username="staff-stat-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-stat-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/statistiche/"

    def test_create_copia_sigla_in_parametro_se_omesso(self):
        r = self.client.post(
            self.url,
            {"nome": "Uso specchio test staff", "sigla": "ZS1"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["sigla"], "ZS1")
        self.assertEqual(r.data["parametro"], "ZS1")
        st = Statistica.objects.get(pk=r.data["id"])
        self.assertEqual(st.parametro, "ZS1")
        self.assertEqual(st.tipo, "ST")

    def test_destroy_blocca_sigle_sistema_0(self):
        st = Statistica.objects.create(nome="Componente nave test", sigla="0Z9")
        r = self.client.delete(f"{self.url}{st.id}/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertTrue(Statistica.objects.filter(pk=st.pk).exists())

    def test_destroy_statistica_normale(self):
        st = Statistica.objects.create(nome="Stat cancellabile", sigla="ZS2", parametro="ZS2")
        r = self.client.delete(f"{self.url}{st.id}/")
        self.assertEqual(r.status_code, status.HTTP_204_NO_CONTENT, r.data)
        self.assertFalse(Statistica.objects.filter(pk=st.pk).exists())

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
