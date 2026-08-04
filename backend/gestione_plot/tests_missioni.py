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
        self.esclusiva = kwargs.get("esclusiva", False)
        self.korp_id = kwargs.get("korp_id")


class MissioniRewardCalcTests(SimpleTestCase):
    def test_primo_piena_ricompensa(self):
        cr, pr = calcola_ricompensa_base(_FakeMissione(), is_primo=True)
        self.assertEqual(cr, Decimal("100.00"))
        self.assertEqual(pr, 10)

    def test_solo_primo_azzera_successivi(self):
        cr, pr = calcola_ricompensa_base(_FakeMissione(premio_solo_primo=True), is_primo=False)
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


class MissioniRiepilogoLogicTests(SimpleTestCase):
    """Verifica classificazione non-korp: generiche + altre KORP non esclusive."""

    def test_classificazione_non_korp(self):
        # Pure unit: replica la regola senza DB
        missioni = [
            _FakeMissione(korp_id=1, esclusiva=False, reward_crediti=Decimal("10")),
            _FakeMissione(korp_id=2, esclusiva=False, reward_crediti=Decimal("20")),
            _FakeMissione(korp_id=2, esclusiva=True, reward_crediti=Decimal("50")),
            _FakeMissione(korp_id=None, esclusiva=False, reward_crediti=Decimal("5")),
        ]
        korp_id = 1
        di = [m for m in missioni if m.korp_id == korp_id]
        non = [m for m in missioni if m.korp_id != korp_id and not m.esclusiva]
        self.assertEqual(len(di), 1)
        self.assertEqual(sum(m.reward_crediti for m in non), Decimal("25"))  # 20 + 5, non 50 esclusiva
