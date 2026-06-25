"""Test abilità default automatiche per membership carriera/KORP."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from personaggi.carriere_abilita_default import sync_abilita_default_carriere_for_personaggio
from personaggi.models import (
    TIER_3,
    Abilita,
    Campagna,
    Carriera,
    CarrieraAbilita,
    CARATTERISTICA,
    PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
    PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioCarrieraMembership,
    Punteggio,
    TipologiaPersonaggio,
    TipoCarriera,
)

User = get_user_model()


class CarrieraAbilitaDefaultTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-carriera-ab",
            nome="Kor35 Carriera Ab",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Carriera Ab")
        cls.tipo_korp, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})
        cls.carriera_a = Carriera.objects.create(
            nome="KORP A Test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
        )
        cls.carriera_b = Carriera.objects.create(
            nome="KORP B Test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
        )
        cls.caratt = Punteggio.objects.create(
            nome="CAR_CA",
            sigla="CCA",
            tipo=CARATTERISTICA,
            colore="#000000",
        )
        cls.ab_tech = Abilita.objects.create(
            nome="Perk Forgiatura Tech",
            descrizione="",
            caratteristica=cls.caratt,
            campagna=cls.campagna,
        )
        cls.ab_inn = Abilita.objects.create(
            nome="Perk Forgiatura Innata",
            descrizione="",
            caratteristica=cls.caratt,
            campagna=cls.campagna,
        )
        CarrieraAbilita.objects.create(carriera=cls.carriera_a, abilita=cls.ab_tech, is_default=True)
        CarrieraAbilita.objects.create(carriera=cls.carriera_a, abilita=cls.ab_inn, is_default=True)
        CarrieraAbilita.objects.create(carriera=cls.carriera_b, abilita=cls.ab_inn, is_default=True)

        cls.user = User.objects.create_user(username="carriera_ab_pg", password="x")
        cls.personaggio = Personaggio.objects.create(
            nome="PG Carriera Ab",
            proprietario=cls.user,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )

    def test_membership_attiva_assegna_abilita_default(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.personaggio,
            carriera=self.carriera_a,
            tipo_carriera=self.tipo_korp,
        )
        ids = set(
            PersonaggioAbilita.objects.filter(
                personaggio=self.personaggio,
                origine=PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
            ).values_list("abilita_id", flat=True)
        )
        self.assertEqual(ids, {self.ab_tech.id, self.ab_inn.id})

    def test_chiusura_membership_rimuove_perk(self):
        membership = PersonaggioCarrieraMembership.objects.create(
            personaggio=self.personaggio,
            carriera=self.carriera_a,
            tipo_carriera=self.tipo_korp,
        )
        membership.data_a = timezone.now()
        membership.save()
        self.assertFalse(
            PersonaggioAbilita.objects.filter(
                personaggio=self.personaggio,
                origine=PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
            ).exists()
        )

    def test_cambio_korp_aggiorna_perk(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.personaggio,
            carriera=self.carriera_a,
            tipo_carriera=self.tipo_korp,
        )
        old = PersonaggioCarrieraMembership.objects.get(personaggio=self.personaggio, data_a__isnull=True)
        old.data_a = timezone.now()
        old.save()
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.personaggio,
            carriera=self.carriera_b,
            tipo_carriera=self.tipo_korp,
        )
        ids = set(
            PersonaggioAbilita.objects.filter(
                personaggio=self.personaggio,
                origine=PERSONAGGIO_ABILITA_ORIGINE_CARRIERA_DEFAULT,
            ).values_list("abilita_id", flat=True)
        )
        self.assertEqual(ids, {self.ab_inn.id})

    def test_non_duplica_abilita_gia_acquistata(self):
        PersonaggioAbilita.objects.create(
            personaggio=self.personaggio,
            abilita=self.ab_tech,
            origine=PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO,
        )
        sync_abilita_default_carriere_for_personaggio(self.personaggio)
        self.assertEqual(
            PersonaggioAbilita.objects.filter(personaggio=self.personaggio, abilita=self.ab_tech).count(),
            1,
        )
        pivot = PersonaggioAbilita.objects.get(personaggio=self.personaggio, abilita=self.ab_tech)
        self.assertEqual(pivot.origine, PERSONAGGIO_ABILITA_ORIGINE_ACQUISTO)
