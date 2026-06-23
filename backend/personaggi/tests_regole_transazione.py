"""Test regole transazione tra giocatori."""
from decimal import Decimal

from django.test import TestCase

from personaggi.models import (
    REGOLA_TX_CODICE_CREDITI,
    Campagna,
    RegolaTransazioneCategoria,
    Personaggio,
    TipologiaPersonaggio,
)
from personaggi.regole_transazione import (
    ensure_regole_transazione_campagna,
    personaggio_puo_trasferire_categoria,
    valida_proposta_transazione,
)


class RegoleTransazioneTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.filter(slug='kor35').first()
        if not self.campagna:
            self.campagna = Campagna.objects.create(slug='kor35', nome='KOR35', attiva=True, is_default=True)
        ensure_regole_transazione_campagna(self.campagna)
        tipologia = TipologiaPersonaggio.objects.filter(giocante=True).first()
        if not tipologia:
            tipologia = TipologiaPersonaggio.objects.create(nome='PG test', giocante=True)
        self.personaggio = Personaggio.objects.create(
            nome='Tester TX',
            tipologia=tipologia,
            campagna=self.campagna,
        )

    def test_categoria_bloccata(self):
        regola = RegolaTransazioneCategoria.objects.get(
            campagna=self.campagna, codice=REGOLA_TX_CODICE_CREDITI
        )
        regola.vendibile_giocatori = False
        regola.save()
        ok, msg = personaggio_puo_trasferire_categoria(self.personaggio, REGOLA_TX_CODICE_CREDITI)
        self.assertFalse(ok)
        self.assertIn('Crediti', msg)

    def test_valida_proposta_crediti_ok(self):
        ok, msg = valida_proposta_transazione(
            self.personaggio,
            {'crediti_da_dare': Decimal('10'), 'oggetti_da_dare': [], 'consumabili_da_dare': []},
        )
        self.assertTrue(ok, msg)
