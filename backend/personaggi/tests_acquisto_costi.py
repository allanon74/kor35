"""
Test anti-exploit: rimborso revoca = costo pagato, non prezzo di listino corrente.
Listino acquisto tecniche: valore effettivo della stat aura (non solo valore_base_predefinito).
"""
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase
from django.utils import timezone

from personaggi.acquisto_costi import (
    calcola_costo_creazione_proposta,
    calcola_costo_invio_proposta,
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
        self.car = Punteggio.objects.create(nome="Int Test", sigla="INT", tipo=CARATTERISTICA)
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


class InfusioneSerializerRealizzazioneTest(SimpleTestCase):
    def test_espone_costo_e_tempo_del_personaggio_una_sola_volta(self):
        from personaggi.serializers import InfusioneSerializer

        infusione = SimpleNamespace(pk=7)
        personaggio = object()
        serializer = InfusioneSerializer(context={"personaggio": personaggio})

        with patch(
            "personaggi.services.GestioneCraftingService.calcola_costi_tempi",
            return_value=(240, 90),
        ) as mock_calcolo:
            self.assertEqual(serializer.get_costo_realizzazione(infusione), 240)
            self.assertEqual(serializer.get_tempo_realizzazione_secondi(infusione), 90)
            mock_calcolo.assert_called_once_with(personaggio, infusione)

    def test_senza_personaggio_non_calcola(self):
        from personaggi.serializers import InfusioneSerializer

        infusione = SimpleNamespace(pk=8)
        serializer = InfusioneSerializer(context={})

        with patch(
            "personaggi.services.GestioneCraftingService.calcola_costi_tempi",
        ) as mock_calcolo:
            self.assertIsNone(serializer.get_costo_realizzazione(infusione))
            self.assertIsNone(serializer.get_tempo_realizzazione_secondi(infusione))
            mock_calcolo.assert_not_called()


class CostiCerimonialeDaStatisticaAuraTest(TestCase):
    """
    Invio, creazione e acquisto di un cerimoniale usano la statistica
    indicata sull'aura (valore di scheda), non 100 crediti a mattone.
    """

    def setUp(self):
        from personaggi.models import (
            Cerimoniale,
            CerimonialeCaratteristica,
            PropostaTecnica,
            PropostaTecnicaCaratteristica,
            TIPO_PROPOSTA_CERIMONIALE,
        )

        self.user = User.objects.create_user(username="pg_cer_costi", password="x")
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Std cer costi",
            crediti_iniziali=Decimal("1000"),
            caratteristiche_iniziali=20,
        )
        self.campagna = Campagna.objects.create(nome="Camp cer costi", slug="camp-cer-costi")
        self.personaggio = Personaggio.objects.create(
            nome="EdwinTest",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.stat_invio = Statistica.objects.create(
            nome="costo invio cerimoniale",
            sigla="CIC",
            parametro="invio_cer",
            tipo="ST",
            is_costo=True,
            valore_base_predefinito=100,
        )
        self.stat_creazione = Statistica.objects.create(
            nome="costo creazione cerimoniale",
            sigla="CCC",
            parametro="creaz_cer",
            tipo="ST",
            is_costo=True,
            valore_base_predefinito=100,
        )
        self.stat_acquisto = Statistica.objects.create(
            nome="costo acquisto cerimoniale",
            sigla="CAC",
            parametro="acq_cer",
            tipo="ST",
            is_costo=True,
            valore_base_predefinito=100,
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.personaggio, statistica=self.stat_invio, valore_base=2
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.personaggio, statistica=self.stat_creazione, valore_base=8
        )
        PersonaggioStatisticaBase.objects.create(
            personaggio=self.personaggio, statistica=self.stat_acquisto, valore_base=10
        )
        self.aura = Punteggio.objects.create(
            nome="Aura Arcana Test",
            sigla="AAR",
            tipo=AURA,
            permette_cerimoniali=True,
            stat_costo_invio_proposta_cerimoniale=self.stat_invio,
            stat_costo_creazione_cerimoniale=self.stat_creazione,
            stat_costo_acquisto_cerimoniale=self.stat_acquisto,
        )
        self.car = Punteggio.objects.create(nome="Forza Test", sigla="FOR", tipo=CARATTERISTICA)
        self.proposta = PropostaTecnica.objects.create(
            personaggio=self.personaggio,
            tipo=TIPO_PROPOSTA_CERIMONIALE,
            nome="Marchio di guerra",
            descrizione="x",
            aura=self.aura,
            livello_proposto=2,
            mattoni_generici=3,
        )
        PropostaTecnicaCaratteristica.objects.create(
            proposta=self.proposta, caratteristica=self.car, valore=2
        )
        self.cerimoniale = Cerimoniale.objects.create(
            nome="Marchio pubblicato",
            aura_richiesta=self.aura,
            campagna=self.campagna,
            liv=2,
            mattoni_generici=3,
        )
        CerimonialeCaratteristica.objects.create(
            cerimoniale=self.cerimoniale, caratteristica=self.car, valore=2
        )

    def test_invio_e_creazione_e_acquisto_non_usano_cento_a_mattone(self):
        self.assertEqual(self.proposta.totale_mattoni_minimi(), 5)
        # 5 × valore di scheda, non 5 × 100
        self.assertEqual(calcola_costo_invio_proposta(self.personaggio, self.proposta), 10)
        pieno, effettivo = calcola_costo_creazione_proposta(self.personaggio, self.proposta)
        self.assertEqual(pieno, 40)
        self.assertEqual(effettivo, 40)
        self.assertEqual(self.cerimoniale.costo_crediti, 500)
        self.assertEqual(
            calcola_costo_pieno_tecnica_acquisto(self.personaggio, self.cerimoniale),
            50,
        )

    def test_rinvio_addebita_solo_la_differenza(self):
        from personaggi.models import STATO_PROPOSTA_BOZZA, STATO_PROPOSTA_IN_VALUTAZIONE

        self.personaggio.modifica_crediti(Decimal("100"), "Fondo test")
        self.client.force_login(self.user)
        self.proposta.mattoni_generici = 0
        self.proposta.save(update_fields=["mattoni_generici", "updated_at"])
        saldo_iniziale = Personaggio.objects.get(pk=self.personaggio.pk).crediti

        with patch.object(Personaggio, "get_valore_aura_effettivo", return_value=5), \
             patch.object(Personaggio, "max_livello_creazione", return_value=5), \
             patch.object(Personaggio, "get_valore_statistica", side_effect=lambda sigla: {
                 "CIC": 2, "CCO": 9, "RCT": 0,
             }.get(sigla, 0)):
            primo = self.client.post(
                f"/api/personaggi/api/proposte/{self.proposta.pk}/invia_proposta/",
            )
        self.assertEqual(primo.status_code, 200, primo.content)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_IN_VALUTAZIONE)
        self.assertEqual(self.proposta.costo_invio_pagato, 4)
        self.assertEqual(Personaggio.objects.get(pk=self.personaggio.pk).crediti, saldo_iniziale - 4)

        self.proposta.stato = STATO_PROPOSTA_BOZZA
        self.proposta.mattoni_generici = 3
        self.proposta.save(update_fields=["stato", "mattoni_generici", "updated_at"])

        with patch.object(Personaggio, "get_valore_aura_effettivo", return_value=5), \
             patch.object(Personaggio, "max_livello_creazione", return_value=5), \
             patch.object(Personaggio, "get_valore_statistica", side_effect=lambda sigla: {
                 "CIC": 2, "CCO": 9, "RCT": 0,
             }.get(sigla, 0)):
            secondo = self.client.post(
                f"/api/personaggi/api/proposte/{self.proposta.pk}/invia_proposta/",
            )
        self.assertEqual(secondo.status_code, 200, secondo.content)
        self.proposta.refresh_from_db()
        self.personaggio.refresh_from_db()
        self.assertEqual(self.proposta.costo_invio_pagato, 10)
        self.assertEqual(Personaggio.objects.get(pk=self.personaggio.pk).crediti, saldo_iniziale - 10)
