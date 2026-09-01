"""CRUD staff infusioni: nested modificatori senza FK parent nel payload."""

from decimal import Decimal

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    Campagna,
    Infusione,
    InfusioneStatistica,
    Punteggio,
    Statistica,
)


class StaffInfusioneModificatoriTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff-inf", password="x", is_staff=True)
        self.client.force_authenticate(user=self.staff)
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "Kor35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        self.aura = Punteggio.objects.create(nome="Aura Inf Staff", sigla="AIS", tipo=AURA)
        self.stat = Statistica.objects.create(
            nome="Forza staff",
            sigla="FST",
            parametro="FST",
            valore_base_predefinito=0,
        )
        self.url = "/api/personaggi/api/staff/infusioni/"
        self.headers = {"HTTP_X_CAMPAGNA": self.campagna.slug}

    def test_create_infusione_con_modificatori_senza_fk_parent(self):
        """Regressione: il dashboard staff non invia `infusione` sui nested (parent non esiste ancora)."""
        payload = {
            "nome": "Infusione nested mods",
            "testo": "desc",
            "aura_richiesta": self.aura.id,
            "modificatori": [
                {
                    "statistica": self.stat.id,
                    "valore": 2,
                    "tipo_modificatore": "ADD",
                    "usa_limitazione_aura": False,
                    "limit_a_aure": [],
                    "usa_limitazione_elemento": False,
                    "limit_a_elementi": [],
                    "usa_condizione_text": False,
                    "condizione_text": "",
                    "solo_oggetto_ospitante": False,
                }
            ],
        }
        r = self.client.post(self.url, payload, format="json", **self.headers)
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        infusione = Infusione.objects.get(pk=r.data["id"])
        mods = list(InfusioneStatistica.objects.filter(infusione=infusione))
        self.assertEqual(len(mods), 1)
        self.assertEqual(mods[0].statistica_id, self.stat.id)
        self.assertEqual(mods[0].valore, Decimal("2.00"))

    def test_update_infusione_aggiunge_modificatore_senza_fk_parent(self):
        infusione = Infusione.objects.create(
            nome="Inf esistente",
            testo="x",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        r = self.client.patch(
            f"{self.url}{infusione.id}/",
            {
                "modificatori": [
                    {"statistica": self.stat.id, "valore": 1, "tipo_modificatore": "ADD"},
                ]
            },
            format="json",
            **self.headers,
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        self.assertTrue(
            InfusioneStatistica.objects.filter(infusione=infusione, statistica=self.stat).exists()
        )
