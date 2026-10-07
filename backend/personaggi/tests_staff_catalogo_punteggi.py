"""CRUD staff catalogo CA / Mattoni / Modelli aura / Punteggi residui."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    CARATTERISTICA,
    ELEMENTO,
    MATTONE,
    Aura,
    Caratteristica,
    CaratteristicaModificatore,
    Mattone,
    ModelloAura,
    Punteggio,
    Statistica,
)
from personaggi.serializers import (
    PUNTEGGI_TIPI_RESIDUI,
    PunteggioResiduoStaffSerializer,
)


class CatalogoPunteggiStaffMixin:
    def _cleanup_sigle(self, *sigle):
        Punteggio.objects.filter(sigla__in=sigle).delete()


class CaratteristicaStaffViewSetTests(CatalogoPunteggiStaffMixin, APITestCase):
    def setUp(self):
        self._cleanup_sigle("QC1", "QS1", "0Q9")
        self.staff = User.objects.create_user(
            username="staff-ca-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-ca-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/caratteristiche/"
        self.stat = Statistica.objects.create(
            nome="Stat CA test", sigla="QS1", parametro="QS1"
        )

    def test_create_con_modificatore(self):
        r = self.client.post(
            self.url,
            {
                "nome": "Robustezza test",
                "sigla": "QC1",
                "modificatori": [
                    {
                        "statistica_modificata": self.stat.id,
                        "modificatore": "1.50",
                        "ogni_x_punti": 2,
                    }
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["tipo"], CARATTERISTICA)
        self.assertEqual(len(r.data["modificatori"]), 1)
        self.assertEqual(r.data["modificatori"][0]["statistica_modificata"], self.stat.id)
        ca = Caratteristica.objects.get(pk=r.data["id"])
        self.assertEqual(ca.tipo, CARATTERISTICA)
        self.assertEqual(ca.modificatori_dati.count(), 1)

    def test_update_modificatori_non_rompe_unique(self):
        ca = Caratteristica.objects.create(nome="CA upd", sigla="QC1", tipo=CARATTERISTICA)
        CaratteristicaModificatore.objects.create(
            caratteristica=ca,
            statistica_modificata=self.stat,
            modificatore=1,
            ogni_x_punti=1,
        )
        r = self.client.patch(
            f"{self.url}{ca.id}/",
            {
                "modificatori": [
                    {
                        "statistica_modificata": self.stat.id,
                        "modificatore": 2,
                        "ogni_x_punti": 3,
                    }
                ]
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        row = ca.modificatori_dati.get()
        self.assertEqual(row.modificatore, 2)
        self.assertEqual(row.ogni_x_punti, 3)

    def test_lista_solo_tipo_ca(self):
        Caratteristica.objects.create(nome="CA lista", sigla="QC1", tipo=CARATTERISTICA)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        sigle = {row["sigla"] for row in r.data}
        self.assertIn("QC1", sigle)
        self.assertNotIn("QS1", sigle)

    def test_destroy_blocca_sigle_sistema_0(self):
        ca = Caratteristica.objects.create(nome="Colore nave", sigla="0Q9", tipo=CARATTERISTICA)
        r = self.client.delete(f"{self.url}{ca.id}/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertTrue(Caratteristica.objects.filter(pk=ca.pk).exists())

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class MattoneStaffViewSetTests(CatalogoPunteggiStaffMixin, APITestCase):
    def setUp(self):
        self._cleanup_sigle("QA1", "QC1", "QS1", "QM1")
        self.staff = User.objects.create_user(
            username="staff-ma-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-ma-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/mattoni/"
        self.aura = Aura.objects.create(nome="Aura mattone", sigla="QA1")
        self.ca = Caratteristica.objects.create(
            nome="CA mattone", sigla="QC1", tipo=CARATTERISTICA
        )
        self.stat = Statistica.objects.create(
            nome="Stat mattone", sigla="QS1", parametro="QS1"
        )

    def test_create_mattone_con_stat(self):
        r = self.client.post(
            self.url,
            {
                "nome": "Mattone test",
                "sigla": "QM1",
                "aura": self.aura.id,
                "caratteristica_associata": self.ca.id,
                "statistiche_mod": [
                    {"statistica": self.stat.id, "valore": 2, "tipo_modificatore": "ADD"}
                ],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["tipo"], MATTONE)
        self.assertEqual(r.data["aura_nome"], "Aura mattone")
        self.assertEqual(len(r.data["statistiche_mod"]), 1)
        mattone = Mattone.objects.get(pk=r.data["id"])
        self.assertTrue(mattone.is_mattone)
        self.assertEqual(mattone.mattonestatistica_set.get().valore, 2)

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class ModelloAuraStaffViewSetTests(CatalogoPunteggiStaffMixin, APITestCase):
    def setUp(self):
        self._cleanup_sigle("QA1", "QC1", "QM1")
        self.staff = User.objects.create_user(
            username="staff-mo-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-mo-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/modelli-aura/"
        self.aura = Aura.objects.create(nome="Aura modello", sigla="QA1")
        self.ca = Caratteristica.objects.create(
            nome="CA modello", sigla="QC1", tipo=CARATTERISTICA
        )
        self.mattone = Mattone.objects.create(
            nome="Mattone modello",
            sigla="QM1",
            tipo=MATTONE,
            aura=self.aura,
            caratteristica_associata=self.ca,
        )

    def test_create_con_m2m_e_requisiti(self):
        r = self.client.post(
            self.url,
            {
                "nome": "Modello test",
                "aura": self.aura.id,
                "mattoni_proibiti": [self.mattone.id],
                "usa_condizione_doppia": True,
                "requisiti_doppia": [{"requisito": self.ca.id, "valore": 4}],
            },
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["aura_nome"], "Aura modello")
        self.assertEqual(r.data["mattoni_proibiti"], [self.mattone.id])
        self.assertEqual(len(r.data["requisiti_doppia"]), 1)
        self.assertEqual(r.data["requisiti_doppia"][0]["requisito"], self.ca.id)
        modello = ModelloAura.objects.get(pk=r.data["id"])
        self.assertEqual(modello.mattoni_proibiti.get().pk, self.mattone.pk)
        self.assertEqual(modello.req_doppia_rel.get().valore, 4)

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)


class PunteggioResiduoStaffViewSetTests(CatalogoPunteggiStaffMixin, APITestCase):
    def setUp(self):
        self._cleanup_sigle("QE1", "QK1", "QS9", "QA9", "QC9", "QM9", "0Q8", "QA1", "QC1")
        self.staff = User.objects.create_user(
            username="staff-pr-ed", password="x", is_staff=True, is_superuser=True
        )
        self.player = User.objects.create_user(username="player-pr-ed", password="x")
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/punteggi/"

    def test_create_elemento(self):
        r = self.client.post(
            self.url,
            {"nome": "Fuoco test", "sigla": "QE1", "tipo": ELEMENTO},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_201_CREATED, r.data)
        self.assertEqual(r.data["tipo"], ELEMENTO)
        self.assertEqual(Punteggio.objects.get(pk=r.data["id"]).tipo, ELEMENTO)

    def test_rifiuta_tipo_con_maschera_dedicata(self):
        r = self.client.post(
            self.url,
            {"nome": "Non qui", "sigla": "QS9", "tipo": "ST"},
            format="json",
        )
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)

    def test_lista_esclude_st_au_ca_e_mattoni(self):
        el = Punteggio.objects.create(nome="El residuo", sigla="QE1", tipo=ELEMENTO)
        Statistica.objects.create(nome="Stat nascosta", sigla="QS9", parametro="QS9")
        Aura.objects.create(nome="Aura nascosta", sigla="QA9")
        Caratteristica.objects.create(nome="CA nascosta", sigla="QC9", tipo=CARATTERISTICA)
        aura = Aura.objects.create(nome="Aura per mattone", sigla="QA1")
        ca = Caratteristica.objects.create(nome="CA per mattone", sigla="QC1", tipo=CARATTERISTICA)
        Mattone.objects.create(
            nome="Mattone nascosto",
            sigla="QM9",
            tipo=MATTONE,
            aura=aura,
            caratteristica_associata=ca,
        )
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        sigle = {row["sigla"] for row in r.data}
        self.assertIn(el.sigla, sigle)
        self.assertNotIn("QS9", sigle)
        self.assertNotIn("QA9", sigle)
        self.assertNotIn("QC9", sigle)
        self.assertNotIn("QM9", sigle)

    def test_destroy_blocca_sigle_sistema_0(self):
        p = Punteggio.objects.create(nome="Sistema", sigla="0Q8", tipo=ELEMENTO)
        r = self.client.delete(f"{self.url}{p.id}/")
        self.assertEqual(r.status_code, status.HTTP_400_BAD_REQUEST, r.data)
        self.assertTrue(Punteggio.objects.filter(pk=p.pk).exists())

    def test_tipi_residui_serializer(self):
        self.assertEqual(
            set(PUNTEGGI_TIPI_RESIDUI),
            {"EL", "CO", "CU", "VI", "AR", "AT", "CS", "ND", "KA"},
        )
        fields = set(PunteggioResiduoStaffSerializer.Meta.fields)
        self.assertEqual(
            fields, {"id", "nome", "sigla", "tipo", "ordine", "colore", "descrizione"}
        )

    def test_giocatore_non_staff_forbidden(self):
        self.client.force_authenticate(user=self.player)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
