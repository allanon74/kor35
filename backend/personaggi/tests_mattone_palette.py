"""Nomi mattoni: palette primaria oppure aura di infusione, etichetta con sigla."""

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    MATTONE,
    Aura,
    Campagna,
    Caratteristica,
    Infusione,
    InfusioneCaratteristica,
    Mattone,
    Punteggio,
    aura_fonte_mattoni_per_infusione,
    etichetta_mattone,
)
from personaggi.serializers import InfusioneStaffListSerializer, _serialize_componenti_con_nome_mattone


class PaletteMattoniTests(TestCase):
    def setUp(self):
        Punteggio.objects.filter(sigla__in=["ZT9", "ZI9", "ZM9", "ZD9", "ZA9", "ZC9", "ZF9"]).delete()
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={"nome": "Kor35", "is_default": True, "is_base": True, "attiva": True},
        )
        self.tecnologica = Aura.objects.create(nome="Aura Tecnologica test", sigla="ZT9", tipo=AURA)
        self.tecnologica.aure_infusione_consentite.add(self.tecnologica)
        self.magica = Aura.objects.create(nome="Aura Magica test", sigla="ZM9", tipo=AURA)
        self.trasmutatore = Aura.objects.create(nome="Trasmutatore test", sigla="ZA9", tipo=AURA)
        self.trasmutatore.aure_infusione_consentite.add(self.magica)
        self.destrezza = Caratteristica.objects.create(
            nome="Destrezza test", sigla="ZD9", tipo=CARATTERISTICA
        )
        self.mattone_tec = Mattone.objects.create(
            nome="Circuito",
            sigla="ZC9",
            tipo=MATTONE,
            aura=self.tecnologica,
            caratteristica_associata=self.destrezza,
        )
        self.mattone_mag = Mattone.objects.create(
            nome="Fuoco",
            sigla="ZF9",
            tipo=MATTONE,
            aura=self.magica,
            caratteristica_associata=self.destrezza,
        )

    def test_etichetta_con_sigla(self):
        self.assertEqual(etichetta_mattone(self.mattone_mag), "Fuoco (ZD9)")

    def test_tecnologica_mostra_i_propri_mattoni_anche_con_secondaria(self):
        infusione = Infusione.objects.create(
            nome="Mod circuito",
            testo="x",
            aura_richiesta=self.tecnologica,
            aura_infusione=self.magica,
            campagna=self.campagna,
        )
        InfusioneCaratteristica.objects.create(
            infusione=infusione, caratteristica=self.destrezza, valore=2
        )
        self.assertEqual(aura_fonte_mattoni_per_infusione(infusione).pk, self.tecnologica.pk)
        righe = _serialize_componenti_con_nome_mattone(infusione)
        self.assertEqual(righe[0]["mattone_nome"], "Circuito (ZD9)")

    def test_trasmutatore_mostra_i_mattoni_dell_aura_secondaria(self):
        infusione = Infusione.objects.create(
            nome="Materia fuoco",
            testo="x",
            aura_richiesta=self.trasmutatore,
            aura_infusione=self.magica,
            campagna=self.campagna,
        )
        InfusioneCaratteristica.objects.create(
            infusione=infusione, caratteristica=self.destrezza, valore=1
        )
        self.assertEqual(aura_fonte_mattoni_per_infusione(infusione).pk, self.magica.pk)
        righe = _serialize_componenti_con_nome_mattone(infusione)
        self.assertEqual(righe[0]["mattone_nome"], "Fuoco (ZD9)")
        self.assertEqual(righe[0]["caratteristica"]["id"], self.destrezza.id)


class InfusioneStaffListMattoniTests(APITestCase):
    def setUp(self):
        Punteggio.objects.filter(sigla__in=["ZT9", "ZM9", "ZA9", "ZD9", "ZC9", "ZF9"]).delete()
        self.staff = User.objects.create_user(username="staff-mat-pal", password="x", is_staff=True)
        self.client.force_authenticate(user=self.staff)
        self.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={"nome": "Kor35", "is_default": True, "is_base": True, "attiva": True},
        )
        self.magica = Aura.objects.create(nome="Aura Magica lista", sigla="ZM9", tipo=AURA)
        self.trasmutatore = Aura.objects.create(nome="Trasmutatore lista", sigla="ZA9", tipo=AURA)
        self.trasmutatore.aure_infusione_consentite.add(self.magica)
        self.destrezza = Caratteristica.objects.create(
            nome="Destrezza lista", sigla="ZD9", tipo=CARATTERISTICA
        )
        Mattone.objects.create(
            nome="Fuoco",
            sigla="ZF9",
            tipo=MATTONE,
            aura=self.magica,
            caratteristica_associata=self.destrezza,
        )
        self.infusione = Infusione.objects.create(
            nome="Lista fuoco",
            testo="x",
            aura_richiesta=self.trasmutatore,
            aura_infusione=self.magica,
            campagna=self.campagna,
        )
        InfusioneCaratteristica.objects.create(
            infusione=self.infusione, caratteristica=self.destrezza, valore=3
        )

    def test_lista_staff_include_etichetta_mattone(self):
        data = InfusioneStaffListSerializer(self.infusione).data
        self.assertEqual(data["componenti"][0]["nome"], "Fuoco (ZD9)")
        self.assertEqual(data["componenti"][0]["valore"], 3)
        response = self.client.get(
            "/api/personaggi/api/staff/infusioni/",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(response.status_code, 200, response.data)
        trovata = next(row for row in response.data if row["id"] == self.infusione.id)
        self.assertEqual(trovata["componenti"][0]["nome"], "Fuoco (ZD9)")
