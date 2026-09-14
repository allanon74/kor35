"""
Test sblocco creazione (T3): max_livello_creazione e gate valida_acquisto_tecnica.
"""

from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Abilita,
    Personaggio,
    PersonaggioAbilita,
    Punteggio,
    Tessitura,
    abilita_punteggio,
)


class MaxLivelloCreazioneTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="craft-unlock-user", password="x")
        self.pg = Personaggio.objects.create(nome="PG Craft Unlock", proprietario=self.user)
        self.ca = Punteggio.objects.create(nome="Car Craft", sigla="CCR", tipo=CARATTERISTICA)
        self.aura_ama = Punteggio.objects.create(
            nome="Aura Magica Craft", sigla="AMA", tipo=AURA, is_generica=False
        )
        self.aura_asa = Punteggio.objects.create(
            nome="Aura Sacra Craft", sigla="ASA", tipo=AURA, is_generica=False
        )
        self.aura_alc = Punteggio.objects.create(
            nome="Aura Alchimia Craft", sigla="ALC", tipo=AURA, is_generica=False
        )
        grant = Abilita.objects.create(
            nome="Grant aura base craft",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
        )
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura_ama, valore=2)
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura_alc, valore=1)
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.ca, valore=5)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)

    def _abilita(self, **kwargs):
        defaults = {
            "nome": "Unlock test",
            "caratteristica": self.ca,
            "costo_pc": 0,
            "costo_crediti": 0,
        }
        defaults.update(kwargs)
        return Abilita.objects.create(**defaults)

    def test_tes_aura_unlock_raises_cap(self):
        ab = self._abilita(
            nome="Mago 1 test",
            sblocca_creazione_livello=5,
            ambito_creazione=Abilita.AMBITO_CREAZIONE_TES_AURA,
            aura_creazione=self.aura_ama,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=ab)
        self.assertEqual(
            self.pg.max_livello_creazione(
                ambito=Abilita.AMBITO_CREAZIONE_TES_AURA, aura=self.aura_ama
            ),
            5,
        )
        self.assertEqual(
            self.pg.max_livello_creazione(
                ambito=Abilita.AMBITO_CREAZIONE_TES_AURA, aura=self.aura_asa
            ),
            0,
        )

    def test_consumabile_unlock(self):
        ab = self._abilita(
            nome="Apotecario 1 test",
            sblocca_creazione_livello=5,
            ambito_creazione=Abilita.AMBITO_CREAZIONE_CONSUMABILE,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=ab)
        self.assertEqual(
            self.pg.max_livello_creazione(ambito=Abilita.AMBITO_CREAZIONE_CONSUMABILE),
            5,
        )

    def test_valida_acquisto_tecnica_usa_unlock(self):
        ab = self._abilita(
            nome="Mago unlock tessitura",
            sblocca_creazione_livello=5,
            ambito_creazione=Abilita.AMBITO_CREAZIONE_TES_AURA,
            aura_creazione=self.aura_ama,
        )
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=ab)
        from personaggi.models import TessituraCaratteristica

        t = Tessitura.objects.create(
            nome="Incantesimo Lv5",
            aura_richiesta=self.aura_ama,
        )
        TessituraCaratteristica.objects.create(
            tessitura=t, caratteristica=self.ca, valore=5
        )
        ok, msg = self.pg.valida_acquisto_tecnica(t)
        self.assertTrue(ok, msg)

    def test_senza_unlock_acquisto_fallisce(self):
        from personaggi.models import TessituraCaratteristica

        t = Tessitura.objects.create(
            nome="Incantesimo Lv5 no unlock",
            aura_richiesta=self.aura_ama,
        )
        TessituraCaratteristica.objects.create(
            tessitura=t, caratteristica=self.ca, valore=5
        )
        ok, _msg = self.pg.valida_acquisto_tecnica(t)
        self.assertFalse(ok)
