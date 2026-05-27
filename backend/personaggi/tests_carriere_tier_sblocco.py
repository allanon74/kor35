"""Test tier sblocco carriere/KORP e filtro abilità acquistabili."""

from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.carriere_tier_sblocco import (
    personaggio_puo_acquistare_abilita_tier,
    tiers_selezionabili_per_sblocco_carriera,
)
from personaggi.models import (
    TIER_1,
    TIER_3,
    Abilita,
    Campagna,
    Carriera,
    CarrieraTierSblocco,
    CARATTERISTICA,
    Personaggio,
    PersonaggioCarrieraMembership,
    Punteggio,
    Tier,
    TipologiaPersonaggio,
    TipoCarriera,
    abilita_tier,
)

User = get_user_model()


class CarriereTierSbloccoTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-tier-test",
            nome="Kor35 Tier Test",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Tier Test")
        cls.tipo_korp, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})
        cls.tipo_prof, _ = TipoCarriera.objects.get_or_create(
            codice="professione", defaults={"nome": "Professione"}
        )

        cls.tier_pool = Tier.objects.create(nome="Pool T1 Test", descrizione="", tipo=TIER_1)
        cls.carriera = Carriera.objects.create(
            nome="Carriera Test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_prof,
        )
        CarrieraTierSblocco.objects.create(carriera=cls.carriera, tier=cls.tier_pool)

        cls.caratt = Punteggio.objects.create(
            nome="CAR_T",
            sigla="CRT",
            tipo=CARATTERISTICA,
            colore="#000000",
        )

        cls.user = User.objects.create_user(username="tier_pg", password="x")
        cls.personaggio = Personaggio.objects.create(
            nome="PG Tier",
            proprietario=cls.user,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )

        cls.abilita_gated = Abilita.objects.create(
            nome="Ab Gated",
            descrizione="",
            caratteristica=cls.caratt,
            campagna=cls.campagna,
        )
        abilita_tier.objects.create(abilita=cls.abilita_gated, tabella=cls.tier_pool)

        cls.abilita_libera = Abilita.objects.create(
            nome="Ab Libera",
            descrizione="",
            caratteristica=cls.caratt,
            campagna=cls.campagna,
        )

    def test_tiers_selezionabili_esclude_carriere(self):
        ids = set(tiers_selezionabili_per_sblocco_carriera().values_list("pk", flat=True))
        self.assertIn(self.tier_pool.id, ids)
        self.assertNotIn(self.carriera.id, ids)

    def test_abilita_gated_senza_membership(self):
        self.assertFalse(personaggio_puo_acquistare_abilita_tier(self.personaggio, self.abilita_gated))

    def test_abilita_gated_con_membership(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.personaggio,
            carriera=self.carriera,
            tipo_carriera=self.tipo_prof,
        )
        self.assertTrue(personaggio_puo_acquistare_abilita_tier(self.personaggio, self.abilita_gated))

    def test_abilita_senza_tier_gated_restano_libere(self):
        self.assertTrue(personaggio_puo_acquistare_abilita_tier(self.personaggio, self.abilita_libera))
