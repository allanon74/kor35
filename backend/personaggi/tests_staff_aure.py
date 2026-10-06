"""CRUD staff catalogo Aure (dashboard)."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import AURA, Aura, Statistica
from personaggi.serializers import AuraStaffSerializer, StatisticaStaffSerializer


class StatisticaStaffCampiTests(APITestCase):
    def test_serializer_non_include_campi_aura(self):
        fields = set(StatisticaStaffSerializer.Meta.fields)
        self.assertIn("tipo_modificatore", fields)
        self.assertIn("is_costo", fields)
        for forbidden in (
            "produce_aumenti",
            "produce_potenziamenti",
            "stat_costo_creazione_tessitura",
            "aure_infusione_consentite",
            "permette_infusioni",
            "is_soprannaturale",
        ):
            self.assertNotIn(forbidden, fields)


class AuraStaffViewSetTests(APITestCase):
    def setUp(self):
        Aura.objects.filter(sigla__in=["ZA1", "ZA2", "0A9"]).delete()
        Statistica.objects.filter(sigla="ZC1").delete()
        self.staff = User.objects.create_user(
            username="staff-aura-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-aura-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/aure/"
        self.stat_costo = Statistica.objects.create(
            nome="Costo test aura",
            sigla="ZC1",
            parametro="ZC1",
            is_costo=True,
        )

    def test_create_aura_con_flag_e_costo(self):
        r = self.client.post(
            self.url,
            {
                "nome": "Aura test staff",
                "sigla": "ZA1",
                "is_soprannaturale": True,
                "permette_tessiture": True,
                "produce_potenziamenti": True,
                "nome_tipo_potenziamento": "Mod",
                "stat_costo_creazione_tessitura": self.stat_costo.id,
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["tipo"], AURA)
        self.assertTrue(r.data["is_soprannaturale"])
        self.assertTrue(r.data["permette_tessiture"])
        self.assertEqual(r.data["nome_tipo_potenziamento"], "Mod")
        self.assertEqual(r.data["stat_costo_creazione_tessitura"], self.stat_costo.id)
        aura = Aura.objects.get(pk=r.data["id"])
        self.assertEqual(aura.tipo, AURA)
        self.assertEqual(aura.stat_costo_creazione_tessitura_id, self.stat_costo.id)

    def test_infusione_consentita_m2m(self):
        altre = Aura.objects.create(nome="Aura infusa", sigla="ZA2")
        r = self.client.post(
            self.url,
            {
                "nome": "Aura host",
                "sigla": "ZA1",
                "aure_infusione_consentite": [altre.id],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["aure_infusione_consentite"], [altre.id])

    def test_lista_solo_tipo_au(self):
        Aura.objects.create(nome="Aura lista", sigla="ZA1")
        Statistica.objects.create(nome="Non aura", sigla="ZS9", parametro="ZS9")
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        sigle = {row["sigla"] for row in r.data}
        self.assertIn("ZA1", sigle)
        self.assertNotIn("ZS9", sigle)

    def test_serializer_ha_campi_produzione(self):
        fields = set(AuraStaffSerializer.Meta.fields)
        for required in (
            "produce_aumenti",
            "stat_costo_creazione_tessitura",
            "aure_infusione_consentite",
            "permette_cerimoniali",
            "stat_durata_consumabili",
        ):
            self.assertIn(required, fields)

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
