from decimal import Decimal
from unittest.mock import patch

from django.test import SimpleTestCase

from gestione_plot.missioni_service import applica_fattore_korp, calcola_ricompensa_base


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
        self.allineamento = kwargs.get("allineamento", "GRIGIA")


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


class MissioniFattoreKorpTests(SimpleTestCase):
    def _missione(self, *, korp_id, fattore):
        m = _FakeMissione(korp_id=korp_id)
        m.korp = type("Korp", (), {"fattore_task": fattore})()
        return m

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=True)
    def test_sovrapagata_solo_fattore_maggiore_di_uno(self, _mock):
        m = self._missione(korp_id=1, fattore=Decimal("2.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("20.00"))
        self.assertEqual(pr, 8)
        self.assertTrue(is_bonus)
        self.assertEqual(fat, Decimal("2.00"))

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=True)
    def test_stessa_korp_fattore_uno_non_evidenzia(self, _mock):
        m = self._missione(korp_id=1, fattore=Decimal("1.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertEqual(pr, 4)
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))

    @patch("gestione_plot.missioni_service.personaggio_ha_korp", return_value=False)
    def test_altra_korp_nessun_bonus(self, _mock):
        m = self._missione(korp_id=2, fattore=Decimal("3.00"))
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))

    def test_task_generica_nessun_bonus(self):
        m = _FakeMissione(korp_id=None)
        cr, pr, is_bonus, fat = applica_fattore_korp(m, object(), Decimal("10"), 4)
        self.assertEqual(cr, Decimal("10.00"))
        self.assertFalse(is_bonus)
        self.assertEqual(fat, Decimal("1.00"))
