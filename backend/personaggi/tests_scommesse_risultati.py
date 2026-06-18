"""Test generatori risultato scommesse per sport."""
import random
from decimal import Decimal

from django.test import SimpleTestCase

from personaggi.scommesse_logic import (
    ESITO_CASA,
    ESITO_PAREGGIO,
    ESITO_TRASFERTA,
    calcola_probabilita_esito,
    calcola_quote,
    genera_esito_incontro,
)
from personaggi.scommesse_risultati import (
    TIPO_BASKET,
    TIPO_CALCIO,
    TIPO_RUGBY,
    TIPO_TENNIS,
    TIPO_VOLLEY,
    formatta_risultato,
    genera_punteggio_incontro,
    pareggio_consentito,
)


class ScommesseRisultatiSportTests(SimpleTestCase):
    def test_pareggio_solo_calcio_e_rugby(self):
        self.assertTrue(pareggio_consentito(TIPO_CALCIO))
        self.assertTrue(pareggio_consentito(TIPO_RUGBY))
        self.assertFalse(pareggio_consentito(TIPO_VOLLEY))
        self.assertFalse(pareggio_consentito(TIPO_TENNIS))
        self.assertFalse(pareggio_consentito(TIPO_BASKET))

    def test_probabilita_senza_pareggio(self):
        p_casa, p_x, p_trasf = calcola_probabilita_esito(
            Decimal("60"), Decimal("40"), allow_draw=False,
        )
        self.assertEqual(p_x, 0.0)
        self.assertAlmostEqual(p_casa + p_trasf, 1.0)

    def test_genera_esito_volley_mai_pareggio(self):
        for i in range(30):
            res = genera_esito_incontro(Decimal("55"), Decimal("45"), f"volley-{i}", TIPO_VOLLEY)
            self.assertIn(res["esito"], {ESITO_CASA, ESITO_TRASFERTA})
            self.assertEqual(max(res["gol_casa"], res["gol_trasferta"]), 3)
            self.assertIn(min(res["gol_casa"], res["gol_trasferta"]), {0, 1, 2})

    def test_genera_esito_tennis_set(self):
        res = genera_esito_incontro(Decimal("70"), Decimal("30"), "tennis-1", TIPO_TENNIS)
        self.assertIn(res["esito"], {ESITO_CASA, ESITO_TRASFERTA})
        winner, loser = (
            (res["gol_casa"], res["gol_trasferta"])
            if res["esito"] == ESITO_CASA
            else (res["gol_trasferta"], res["gol_casa"])
        )
        self.assertEqual(winner, 2)
        self.assertIn(loser, {0, 1})

    def test_genera_esito_calcio_puo_pareggiare(self):
        esiti = {
            genera_esito_incontro(Decimal("50"), Decimal("50"), f"calcio-{i}", TIPO_CALCIO)["esito"]
            for i in range(40)
        }
        self.assertIn(ESITO_PAREGGIO, esiti)

    def test_quote_senza_pareggio_quota_x_zero(self):
        q = calcola_quote(50, 50, "seed-basket", allow_draw=False)
        self.assertEqual(q["quota_pareggio"], Decimal("0.00"))
        self.assertGreater(q["quota_casa"], Decimal("1.00"))

    def test_punteggio_coerente_con_esito(self):
        rng = random.Random(42)
        for tipo in (TIPO_CALCIO, TIPO_BASKET, TIPO_VOLLEY):
            for esito in (ESITO_CASA, ESITO_TRASFERTA):
                casa, trasf = genera_punteggio_incontro(tipo, esito, rng)
                if esito == ESITO_CASA:
                    self.assertGreater(casa, trasf)
                else:
                    self.assertGreater(trasf, casa)

    def test_formatta_risultato(self):
        self.assertEqual(formatta_risultato(TIPO_VOLLEY, 3, 1), "3-1 set")
        self.assertEqual(formatta_risultato(TIPO_CALCIO, 2, 1), "2-1 gol")
