"""Test unitari della formula di sintesi carburante (senza DB)."""
from __future__ import annotations

from django.test import SimpleTestCase

from pilotaggio.compattatore_carburante import (
    CROCIERA_TIPICA_CARBURANTE_PER_TICK,
    calcola_resa_sintesi,
    efficienza_livello,
)


class SintesiCarburanteFormulaTests(SimpleTestCase):
    def test_efficienza_z1_e_z9(self):
        self.assertAlmostEqual(efficienza_livello(1), 0.49, places=2)
        self.assertAlmostEqual(efficienza_livello(9), 1.05, places=2)
        self.assertEqual(efficienza_livello(0), 0.0)

    def test_ingegnere_capace_supera_crociera_per_tick(self):
        """
        Z=9, 3 unità miste indici alti: 1 operazione = 1 tick a Z=9
        deve produrre più della crociera tipica per tick (28.8).
        """
        resa = calcola_resa_sintesi(
            unita=[
                {"indice": 6, "quantita": 1},
                {"indice": 7, "quantita": 1},
                {"indice": 8, "quantita": 1},
            ],
            livello=9,
        )
        self.assertGreater(resa, CROCIERA_TIPICA_CARBURANTE_PER_TICK)

    def test_z1_troppo_lento_per_crociera(self):
        """A Z=1 serve 9 tick per un'operazione: resa/tick sotto crociera tipica."""
        resa = calcola_resa_sintesi(
            unita=[{"indice": 5, "quantita": 3}],
            livello=1,
        )
        self.assertLess(resa / 9.0, CROCIERA_TIPICA_CARBURANTE_PER_TICK)
