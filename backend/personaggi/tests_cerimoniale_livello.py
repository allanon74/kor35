"""Regressione: livello cerimoniale = floor(mattoni / 5)."""
from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.models import (
    Cerimoniale,
    CerimonialeCaratteristica,
    PropostaTecnica,
    PropostaTecnicaCaratteristica,
    Punteggio,
    Personaggio,
    Campagna,
    TipologiaPersonaggio,
    AURA,
    CARATTERISTICA,
    TIPO_PROPOSTA_CERIMONIALE,
    STATO_PROPOSTA_BOZZA,
    livello_cerimoniale_da_mattoni,
    MATTONI_PER_LIVELLO_CERIMONIALE,
)

User = get_user_model()


class LivelloCerimonialeDaMattoniTests(TestCase):
    def test_helper_floor_div_5(self):
        self.assertEqual(MATTONI_PER_LIVELLO_CERIMONIALE, 5)
        self.assertEqual(livello_cerimoniale_da_mattoni(0), 0)
        self.assertEqual(livello_cerimoniale_da_mattoni(4), 0)
        self.assertEqual(livello_cerimoniale_da_mattoni(5), 1)
        self.assertEqual(livello_cerimoniale_da_mattoni(9), 1)
        self.assertEqual(livello_cerimoniale_da_mattoni(10), 2)
        self.assertEqual(livello_cerimoniale_da_mattoni(14), 2)
        self.assertEqual(livello_cerimoniale_da_mattoni(15), 3)

    def test_cerimoniale_livello_e_sync_liv(self):
        Campagna.objects.create(
            slug='camp-cer-sync',
            nome='Camp CER Sync',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        aura = Punteggio.objects.create(nome='Aura Test CER', sigla='ATC', tipo=AURA)
        ca1 = Punteggio.objects.create(nome='Caratt A', sigla='CAA', tipo=CARATTERISTICA)
        ca2 = Punteggio.objects.create(nome='Caratt B', sigla='CAB', tipo=CARATTERISTICA)

        cer = Cerimoniale.objects.create(nome='Rito Test', aura_richiesta=aura, liv=99)
        CerimonialeCaratteristica.objects.create(cerimoniale=cer, caratteristica=ca1, valore=7)
        CerimonialeCaratteristica.objects.create(cerimoniale=cer, caratteristica=ca2, valore=4)

        cer.refresh_from_db()
        self.assertEqual(cer.totale_mattoni(), 11)
        self.assertEqual(cer.livello, 2)
        self.assertEqual(cer.liv, 2)

    def test_proposta_cerimoniale_livello_da_mattoni(self):
        campagna = Campagna.objects.create(
            slug='camp-test-cer-liv',
            nome='Camp Test CER',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        tipologia = TipologiaPersonaggio.objects.create(nome='Standard CER Liv')
        user = User.objects.create_user(username='cer_liv_user', password='x')
        aura = Punteggio.objects.create(nome='Aura Prop CER', sigla='APC', tipo=AURA)
        ca = Punteggio.objects.create(nome='Caratt Prop', sigla='CAP', tipo=CARATTERISTICA)
        pg = Personaggio.objects.create(
            nome='PG Prop',
            proprietario=user,
            campagna=campagna,
            tipologia=tipologia,
        )

        prop = PropostaTecnica.objects.create(
            personaggio=pg,
            tipo=TIPO_PROPOSTA_CERIMONIALE,
            stato=STATO_PROPOSTA_BOZZA,
            nome='Proposta CER',
            descrizione='x',
            aura=aura,
            livello_proposto=99,
        )
        PropostaTecnicaCaratteristica.objects.create(proposta=prop, caratteristica=ca, valore=12)

        prop.refresh_from_db()
        self.assertEqual(prop.livello, 2)
        self.assertEqual(prop.livello_proposto, 2)
