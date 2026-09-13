"""
Test anti-exploit: rimborso revoca = costo pagato, non prezzo di listino corrente.
Listino acquisto tecniche: valore effettivo della stat aura (non solo valore_base_predefinito).
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from personaggi.acquisto_costi import (
    calcola_costo_pieno_tecnica_acquisto,
    calcola_costo_tecnica_acquisto,
    rimborso_crediti_da_pivot,
)
from personaggi.services import GestioneCraftingService
from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Campagna,
    Personaggio,
    PersonaggioStatisticaBase,
    PersonaggioTessitura,
    Punteggio,
    Statistica,
    Tessitura,
    TessituraCaratteristica,
    TipologiaPersonaggio,
)


class RimborsoCostoPagatoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pg_costi", password="x")
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Std costi test",
            crediti_iniziali=Decimal("10000"),
            caratteristiche_iniziali=20,
        )
        self.campagna = Campagna.objects.create(nome="Camp costi", slug="camp-costi")
        self.personaggio = Personaggio.objects.create(
            nome="Eroe",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.aura = Punteggio.objects.create(nome="Aura Costi", sigla="ACO", tipo=AURA)
        self.tessitura = Tessitura.objects.create(
            nome="Tess Test",
            testo="x",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )

    def test_rimborso_usa_costo_pagato_sul_pivot(self):
        pivot = PersonaggioTessitura.objects.create(
            personaggio=self.personaggio,
            tessitura=self.tessitura,
            costo_crediti_pagato=Decimal("500"),
            data_acquisizione=timezone.now(),
        )
        refund = rimborso_crediti_da_pivot(
            pivot, item=self.tessitura, acquired_at=pivot.data_acquisizione
        )
        self.assertEqual(refund, Decimal("500"))

    def test_acquisto_tecnica_applica_sconto_rct(self):
        with patch(
            "personaggi.acquisto_costi.calcola_costo_pieno_tecnica_acquisto",
            return_value=1000,
        ):
            with patch.object(Personaggio, "get_valore_statistica", return_value=50):
                costo = calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(costo, 500)

    def test_rimborso_restituisce_pagato_anche_se_sconto_attuale_sparito(self):
        """Dopo rimozione comprensione il listino torna pieno; il pivot resta a 500."""
        with patch(
            "personaggi.acquisto_costi.calcola_costo_pieno_tecnica_acquisto",
            return_value=1000,
        ):
            with patch.object(Personaggio, "get_valore_statistica", return_value=0):
                listino = calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(listino, 1000)

        pivot = PersonaggioTessitura.objects.create(
            personaggio=self.personaggio,
            tessitura=self.tessitura,
            costo_crediti_pagato=Decimal("500"),
            data_acquisizione=timezone.now(),
        )
        refund = rimborso_crediti_da_pivot(
            pivot, item=self.tessitura, acquired_at=pivot.data_acquisizione
        )
        self.assertEqual(refund, Decimal("500"))
        self.assertNotEqual(refund, Decimal("1000"))


class AcquistoTessituraStatAuraEffettivaTest(TestCase):
    """
    Regressione: acquisto deve usare il valore effettivo della stat_costo_acquisto_tessitura
    (come creazione), non il solo valore_base_predefinito del catalogo.

    Scenario prod-like: catalogo stale a 10 CR/livello, scheda PG a 100 → listino 100×livello.
    """

    def setUp(self):
        self.user = User.objects.create_user(username="pg_acq_tes", password="x")
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Std acq tes",
            crediti_iniziali=Decimal("10000"),
            caratteristiche_iniziali=20,
        )
        self.campagna = Campagna.objects.create(nome="Camp acq tes", slug="camp-acq-tes")
        self.personaggio = Personaggio.objects.create(
            nome="DarianTest",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.stat_costo = Statistica.objects.create(
            nome="Costo generico",
            sigla="CGN",
            parametro="costo_gen",
            tipo="ST",
            is_costo=True,
            valore_base_predefinito=10,  # catalogo stale (bug storico)
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.personaggio,
            statistica=self.stat_costo,
            valore_base=100,  # valore effettivo in scheda / PROD
        )
        self.aura = Punteggio.objects.create(
            nome="Aura Magica Test",
            sigla="AMT",
            tipo=AURA,
            stat_costo_acquisto_tessitura=self.stat_costo,
        )
        self.car = Punteggio.objects.create(nome="Int Test", sigla="INTT", tipo=CARATTERISTICA)
        self.tessitura = Tessitura.objects.create(
            nome="Tess Magica Test",
            testo="x",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        TessituraCaratteristica.objects.create(
            tessitura=self.tessitura,
            caratteristica=self.car,
            valore=3,
        )

    def test_listino_usa_valore_scheda_non_catalogo_stale(self):
        # Proprietà catalogo (senza PG) resta sul default statistica
        self.assertEqual(self.tessitura.costo_crediti, 30)  # 3 × 10

        pieno = calcola_costo_pieno_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(pieno, 300)  # 3 × 100

        with patch.object(Personaggio, "get_valore_statistica") as mock_stat:
            # RCT=0, CGN letto via get_valore_statistica_aura → side_effect su sigla
            def _stat(sigla):
                if sigla == "RCT":
                    return 0
                if sigla == "CGN":
                    return 100
                return 0

            mock_stat.side_effect = _stat
            # Evita dipendenza da punteggi_base completo: forziamo il path aura helper
            with patch.object(
                GestioneCraftingService,
                "get_valore_statistica_aura",
                return_value=100,
            ):
                effettivo = calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(effettivo, 300)

    def test_listino_reale_con_scheda_senza_mock(self):
        pieno = calcola_costo_pieno_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(pieno, 300)
        self.assertEqual(
            calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura),
            300,
        )


class CreazionePropostaCostoRctTest(TestCase):
    def setUp(self):
        from personaggi.models import PropostaTecnica, PropostaTecnicaCaratteristica, TIPO_PROPOSTA_TESSITURA

        self.user = User.objects.create_user(username="pg_crea", password="x")
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Std crea test",
            crediti_iniziali=Decimal("10000"),
            caratteristiche_iniziali=20,
        )
        self.campagna = Campagna.objects.create(nome="Camp crea", slug="camp-crea")
        self.personaggio = Personaggio.objects.create(
            nome="Artigiano",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.stat_costo = Statistica.objects.create(nome="Costo Tess", sigla="CTT", parametro="CTT", is_costo=True)
        self.aura = Punteggio.objects.create(
            nome="Aura Crea",
            sigla="ACR",
            tipo=AURA,
            stat_costo_creazione_tessitura=self.stat_costo,
        )
        self.proposta = PropostaTecnica.objects.create(
            personaggio=self.personaggio,
            tipo=TIPO_PROPOSTA_TESSITURA,
            nome="Proposta test",
            descrizione="x",
            aura=self.aura,
        )
        PropostaTecnicaCaratteristica.objects.create(
            proposta=self.proposta,
            caratteristica=Punteggio.objects.create(nome="Matt", sigla="MAT", tipo="CA"),
            valore=2,
        )

    def test_creazione_proposta_applica_sconto_rct(self):
        from personaggi.acquisto_costi import calcola_costo_creazione_proposta

        with patch.object(Personaggio, "get_valore_statistica") as mock_stat:
            mock_stat.side_effect = lambda sigla: 100 if sigla != "RCT" else 50
            pieno, effettivo = calcola_costo_creazione_proposta(self.personaggio, self.proposta)
        self.assertEqual(pieno, 200)
        self.assertEqual(effettivo, 100)


class ForgiaturaCostoCondizionaleAuraTest(TestCase):
    def test_calcola_costi_tempi_applica_modificatore_condizionale_aura(self):
        personaggio = SimpleNamespace()
        personaggio.get_modificatori_extra_da_contesto = lambda _ctx: {
            "costo_forg": {"add": 0, "mol": 0.5}
        }

        stat_cfg = SimpleNamespace(parametro="costo_forg")
        aura = SimpleNamespace(sigla="ATE", stat_costo_forgiatura=stat_cfg)
        infusione = SimpleNamespace(
            aura_richiesta=aura,
            aura_infusione=None,
            tipo_risultato="POT",
            livello=3,
        )

        with patch.object(GestioneCraftingService, "get_valore_statistica_aura") as mock_valori:
            mock_valori.side_effect = [100, 60]  # costo unitario, tempo unitario
            costo, tempo = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)

        self.assertEqual(costo, 150)  # (100 * 0.5) * livello 3
        self.assertEqual(tempo, 180)  # tempo invariato

    def test_calcola_costi_tempi_non_applica_modificatore_condizionale_non_match(self):
        personaggio = SimpleNamespace()
        personaggio.get_modificatori_extra_da_contesto = lambda _ctx: {}

        stat_cfg = SimpleNamespace(parametro="costo_forg")
        aura = SimpleNamespace(sigla="ATE", stat_costo_forgiatura=stat_cfg)
        infusione = SimpleNamespace(
            aura_richiesta=aura,
            aura_infusione=None,
            tipo_risultato="POT",
            livello=3,
        )

        with patch.object(GestioneCraftingService, "get_valore_statistica_aura") as mock_valori:
            mock_valori.side_effect = [100, 60]
            costo, tempo = GestioneCraftingService.calcola_costi_tempi(personaggio, infusione)

        self.assertEqual(costo, 300)
        self.assertEqual(tempo, 180)
