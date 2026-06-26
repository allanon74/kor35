"""Carica collegata a più carriere e espansione appartenenze."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    Campagna,
    CampagnaUtente,
    Carica,
    Carriera,
    Personaggio,
    PersonaggioCarrieraMembership,
    TipoCarriera,
)


class CaricaCarriereM2mTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="carica_m2m", password="x")
        self.campagna = Campagna.objects.create(slug="carica-m2m", nome="Carica M2M", attiva=True)
        CampagnaUtente.objects.create(
            campagna=self.campagna,
            user=self.user,
            ruolo=CAMPAGNA_ROLE_MASTER,
            attivo=True,
        )
        self.tipo_korp, _ = TipoCarriera.objects.get_or_create(
            codice="korp",
            defaults={"nome": "KORP", "ordine": 0},
        )
        self.tipo_prof, _ = TipoCarriera.objects.get_or_create(
            codice="professione",
            defaults={"nome": "Professione", "ordine": 1},
        )

        self.korp_a = Carriera.objects.create(
            nome="KORP Alpha",
            tipo="T3",
            tipo_carriera=self.tipo_korp,
        )
        self.korp_b = Carriera.objects.create(
            nome="KORP Beta",
            tipo="T3",
            tipo_carriera=self.tipo_korp,
        )
        self.carica = Carica.objects.create(nome="Tenente")
        self.carica.carriere.set([self.korp_a, self.korp_b])

        self.personaggio = Personaggio.objects.create(nome="PG Test")

        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
        self.membership_url = "/api/personaggi/api/staff/personaggi-carriere-membership/"
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_carica_applies_to_multiple_carriere(self):
        self.assertTrue(self.carica.applies_to_carriera(self.korp_a.pk))
        self.assertTrue(self.carica.applies_to_carriera(self.korp_b.pk))

    def test_membership_rejects_carica_wrong_carriera(self):
        other = Carriera.objects.create(nome="KORP Gamma", tipo="T3", tipo_carriera=self.tipo_korp)
        m = PersonaggioCarrieraMembership(
            personaggio=self.personaggio,
            carriera=other,
            tipo_carriera=self.tipo_korp,
            carica=self.carica,
        )
        with self.assertRaises(Exception):
            m.full_clean()

    def test_create_membership_expands_all_carriere(self):
        resp = self.client.post(
            self.membership_url,
            {
                "personaggio": self.personaggio.pk,
                "tipo_carriera": str(self.tipo_korp.pk),
                "carica": self.carica.pk,
                "espandi_tutte_carriere_carica": True,
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(resp.data["count"], 2)
        self.assertEqual(
            PersonaggioCarrieraMembership.objects.filter(
                personaggio=self.personaggio,
                carica=self.carica,
                data_a__isnull=True,
            ).count(),
            2,
        )
        carriere_ids = set(
            PersonaggioCarrieraMembership.objects.filter(
                personaggio=self.personaggio,
                carica=self.carica,
            ).values_list("carriera_id", flat=True)
        )
        self.assertEqual(carriere_ids, {self.korp_a.pk, self.korp_b.pk})
