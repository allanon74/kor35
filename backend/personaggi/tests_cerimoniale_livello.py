"""Regressione: cerimoniali con livello manuale, mattoni generici e costi su totale minimi."""
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
    livello_suggerito_cerimoniale,
    MATTONI_PER_LIVELLO_CERIMONIALE,
)

User = get_user_model()


class CerimonialeMattoniGenericiTests(TestCase):
    def test_helper_floor_div_5(self):
        self.assertEqual(MATTONI_PER_LIVELLO_CERIMONIALE, 5)
        self.assertEqual(livello_suggerito_cerimoniale(0), 0)
        self.assertEqual(livello_suggerito_cerimoniale(4), 0)
        self.assertEqual(livello_suggerito_cerimoniale(5), 1)
        self.assertEqual(livello_suggerito_cerimoniale(11), 2)
        self.assertEqual(livello_suggerito_cerimoniale(15), 3)

    def test_livello_manuale_e_suggerito_con_generici(self):
        Campagna.objects.create(
            slug='camp-cer-gen',
            nome='Camp CER Gen',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        aura = Punteggio.objects.create(nome='Aura Magica', sigla='AMG', tipo=AURA)
        fulmine = Punteggio.objects.create(nome='Fulmine', sigla='FUL', tipo=CARATTERISTICA)
        fuoco = Punteggio.objects.create(nome='Fuoco', sigla='FUO', tipo=CARATTERISTICA)
        vento = Punteggio.objects.create(nome='Vento', sigla='VEN', tipo=CARATTERISTICA)

        cer = Cerimoniale.objects.create(
            nome='Rito Elementale',
            aura_richiesta=aura,
            liv=3,  # scelto a mano dal Master
            mattoni_generici=4,
        )
        CerimonialeCaratteristica.objects.create(cerimoniale=cer, caratteristica=fulmine, valore=2)
        CerimonialeCaratteristica.objects.create(cerimoniale=cer, caratteristica=fuoco, valore=1)
        CerimonialeCaratteristica.objects.create(cerimoniale=cer, caratteristica=vento, valore=4)

        cer.refresh_from_db()
        # 2+1+4 specifici + 4 generici = 11 → suggerito 2; liv resta 3
        self.assertEqual(cer.totale_mattoni_specifici(), 7)
        self.assertEqual(cer.totale_mattoni_minimi(), 11)
        self.assertEqual(cer.livello_suggerito, 2)
        self.assertEqual(cer.livello, 3)
        self.assertEqual(cer.liv, 3)
        # costo acquisto = totale minimi * fallback 100
        self.assertEqual(cer.costo_crediti, 1100)

    def test_proposta_cerimoniale_livello_manuale(self):
        campagna = Campagna.objects.create(
            slug='camp-prop-cer-gen',
            nome='Camp Prop CER',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        tipologia = TipologiaPersonaggio.objects.create(nome='Standard CER Gen')
        user = User.objects.create_user(username='cer_gen_user', password='x')
        aura = Punteggio.objects.create(nome='Aura Prop Gen', sigla='APG', tipo=AURA)
        ca = Punteggio.objects.create(nome='Caratt Gen', sigla='CGN', tipo=CARATTERISTICA)
        pg = Personaggio.objects.create(
            nome='PG Prop Gen',
            proprietario=user,
            campagna=campagna,
            tipologia=tipologia,
        )

        prop = PropostaTecnica.objects.create(
            personaggio=pg,
            tipo=TIPO_PROPOSTA_CERIMONIALE,
            stato=STATO_PROPOSTA_BOZZA,
            nome='Proposta CER Gen',
            descrizione='x',
            aura=aura,
            livello_proposto=4,
            mattoni_generici=4,
        )
        PropostaTecnicaCaratteristica.objects.create(proposta=prop, caratteristica=ca, valore=7)

        prop.refresh_from_db()
        self.assertEqual(prop.totale_mattoni_minimi(), 11)
        self.assertEqual(prop.livello_suggerito, 2)
        self.assertEqual(prop.livello, 4)  # manuale
        self.assertEqual(prop.livello_proposto, 4)
