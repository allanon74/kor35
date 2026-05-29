"""Test filtri catalogo Accademia (flag escluso_negozio_ufficiale / non_vendibile)."""
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.accademia_catalogo import (
    abilita_accademia_filter,
    oggetto_base_accademia_qs,
    tecnica_visibile_in_accademia,
    verifica_abilita_accademia,
    verifica_oggetto_base_accademia,
    verifica_tecnica_accademia,
)
from personaggi.models import Abilita, Campagna, CARATTERISTICA, Infusione, OggettoBase, Punteggio, AURA


class AccademiaCatalogoFlagsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="accademia-catalogo-test",
            nome="Test Accademia",
            is_default=False,
            is_base=True,
            attiva=True,
        )
        cls.aura = Punteggio.objects.create(
            nome="Aura Test Accademia",
            tipo=AURA,
            sigla="AAT",
            colore="#112233",
        )
        cls.caratteristica = Punteggio.objects.create(
            nome="Forza Test Accademia",
            tipo=CARATTERISTICA,
            sigla="FAT",
            colore="#445566",
        )

    def test_oggetto_base_accademia_qs_esclude_flag(self):
        visibile = OggettoBase.objects.create(
            nome="Spada",
            costo=10,
            in_vendita=True,
            campagna=self.campagna,
        )
        OggettoBase.objects.create(
            nome="Segreta",
            costo=20,
            in_vendita=True,
            escluso_negozio_ufficiale=True,
            campagna=self.campagna,
        )
        OggettoBase.objects.create(
            nome="Plot",
            costo=30,
            in_vendita=True,
            non_vendibile=True,
            campagna=self.campagna,
        )
        ids = set(oggetto_base_accademia_qs().values_list("id", flat=True))
        self.assertEqual(ids, {visibile.id})

    def test_oggetto_base_save_sync_in_vendita(self):
        ob = OggettoBase.objects.create(
            nome="Sync",
            costo=5,
            in_vendita=True,
            escluso_negozio_ufficiale=True,
            campagna=self.campagna,
        )
        ob.refresh_from_db()
        self.assertFalse(ob.in_vendita)

    def test_verifica_oggetto_base_accademia(self):
        ob = OggettoBase.objects.create(
            nome="Nope",
            costo=1,
            non_vendibile=True,
            campagna=self.campagna,
        )
        with self.assertRaises(ValidationError):
            verifica_oggetto_base_accademia(ob)

    def test_abilita_accademia_filter(self):
        ok = Abilita.objects.create(
            nome="Skill OK",
            caratteristica=self.caratteristica,
            campagna=self.campagna,
        )
        Abilita.objects.create(
            nome="Skill esclusa",
            caratteristica=self.caratteristica,
            escluso_negozio_ufficiale=True,
            campagna=self.campagna,
        )
        ids = set(abilita_accademia_filter().values_list("id", flat=True))
        self.assertEqual(ids, {ok.id})

    def test_tecnica_infusione_flag_sync_non_acquistabile(self):
        inf = Infusione.objects.create(
            nome="Inf segreta",
            aura_richiesta=self.aura,
            escluso_negozio_ufficiale=True,
            campagna=self.campagna,
        )
        inf.refresh_from_db()
        self.assertTrue(inf.non_acquistabile)
        self.assertFalse(tecnica_visibile_in_accademia(inf))
        with self.assertRaises(ValidationError):
            verifica_tecnica_accademia(inf)

    def test_verifica_abilita_esclusa(self):
        ab = Abilita.objects.create(
            nome="Plot skill",
            caratteristica=self.caratteristica,
            non_vendibile=True,
            campagna=self.campagna,
        )
        with self.assertRaises(ValidationError):
            verifica_abilita_accademia(ab)
