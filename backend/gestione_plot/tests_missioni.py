from decimal import Decimal

from django.test import SimpleTestCase

from gestione_plot.missioni_service import calcola_ricompensa_base


class _FakeMissione:
    def __init__(self, **kwargs):
        self.reward_crediti = kwargs.get("reward_crediti", Decimal("100"))
        self.reward_prestigio = kwargs.get("reward_prestigio", 10)
        self.premio_solo_primo = kwargs.get("premio_solo_primo", False)
        self.malus_non_primo_crediti = kwargs.get("malus_non_primo_crediti", Decimal("0"))
        self.malus_non_primo_prestigio = kwargs.get("malus_non_primo_prestigio", 0)
        self.bonus_successive_crediti = kwargs.get("bonus_successive_crediti", Decimal("0"))
        self.bonus_successive_prestigio = kwargs.get("bonus_successive_prestigio", 0)


class MissioniRewardCalcTests(SimpleTestCase):
    def test_primo_piena_ricompensa(self):
        m = _FakeMissione()
        cr, pr = calcola_ricompensa_base(m, is_primo=True)
        self.assertEqual(cr, Decimal("100.00"))
        self.assertEqual(pr, 10)

    def test_solo_primo_azzera_successivi(self):
        m = _FakeMissione(premio_solo_primo=True)
        cr, pr = calcola_ricompensa_base(m, is_primo=False)
        self.assertEqual(cr, Decimal("0.00"))
        self.assertEqual(pr, 0)

    def test_malus_e_bonus_successivi(self):
        m = _FakeMissione(
            malus_non_primo_crediti=Decimal("20"),
            malus_non_primo_prestigio=3,
            bonus_successive_crediti=Decimal("5"),
            bonus_successive_prestigio=1,
        )
        cr, pr = calcola_ricompensa_base(m, is_primo=False)
        self.assertEqual(cr, Decimal("85.00"))
        self.assertEqual(pr, 8)
