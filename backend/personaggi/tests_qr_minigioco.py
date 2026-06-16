"""Test logica minigioco QR."""
from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase

from personaggi.qr_minigioco import (
    generate_game_state,
    generate_sliding_state,
    verify_memory,
    verify_rotate,
    verify_sliding,
    verify_solution,
    scegli_tipo_e_difficolta,
    tipi_pool,
    risolvi_difficolta,
    deve_saltare_minigioco,
    MINIGIOCO_TIPO_MEMORY,
    MINIGIOCO_TIPO_ROTATE,
    MINIGIOCO_TIPO_SLIDING,
)


class _Cfg:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class _Pg:
    def __init__(self, stats=None, auras=None):
        self._stats = stats or {}
        self._auras = auras or {}

    def get_valore_statistica(self, sigla):
        return int(self._stats.get(str(sigla).upper(), 0))

    def get_valore_aura_effettivo(self, punteggio):
        nome = getattr(punteggio, "nome", punteggio)
        return int(self._auras.get(nome, 0))


class QrMinigiocoLogicTests(SimpleTestCase):
    def test_sliding_solved_state(self):
        tiles = list(range(16))
        self.assertTrue(verify_sliding(tiles, 4))

    def test_sliding_shuffle_is_solvable_path(self):
        tiles = generate_sliding_state(3, 42)
        self.assertEqual(len(tiles), 9)
        self.assertNotEqual(tiles, list(range(9)))

    def test_rotate_solved(self):
        self.assertTrue(verify_rotate([0, 0, 0, 0], 2))

    def test_memory_solved(self):
        self.assertTrue(verify_memory([0, 0, 1, 1], [0, 1, 2, 3], 2, 2))

    def test_verify_solution_integration(self):
        state = generate_game_state(MINIGIOCO_TIPO_ROTATE, 2, 7)
        solved = {"rotations": [0] * (state["size"] ** 2)}
        self.assertTrue(verify_solution(MINIGIOCO_TIPO_ROTATE, 2, solved))

    def test_memory_game_state_even_cells(self):
        state = generate_game_state(MINIGIOCO_TIPO_MEMORY, 2, 99)
        self.assertEqual(len(state["cards"]), 12)

    def test_sliding_full_solution(self):
        size = 3
        solved = {"tiles": list(range(size * size))}
        self.assertTrue(verify_solution(MINIGIOCO_TIPO_SLIDING, 2, solved))

    def test_scegli_tipo_e_difficolta_deterministico(self):
        cfg = _Cfg(
            tipi_abilitati=[MINIGIOCO_TIPO_SLIDING, MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE],
            difficolta=4,
            regole_difficolta=[],
        )
        pg = _Pg(stats={"PV": 1})
        t1, d1 = scegli_tipo_e_difficolta(cfg, 12345, personaggio=pg)
        t2, d2 = scegli_tipo_e_difficolta(cfg, 12345, personaggio=pg)
        self.assertEqual((t1, d1), (t2, d2))
        self.assertIn(t1, (MINIGIOCO_TIPO_SLIDING, MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE))
        self.assertEqual(d1, 4)

    def test_tipi_pool_default_tutti(self):
        cfg = _Cfg(tipi_abilitati=[], tipo=MINIGIOCO_TIPO_SLIDING)
        self.assertEqual(len(tipi_pool(cfg)), 1)
        cfg2 = _Cfg(tipi_abilitati=[MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE])
        self.assertEqual(tipi_pool(cfg2), [MINIGIOCO_TIPO_MEMORY, MINIGIOCO_TIPO_ROTATE])

    def test_risolvi_difficolta_default(self):
        cfg = _Cfg(difficolta=4, regole_difficolta=[])
        self.assertEqual(risolvi_difficolta(_Pg(), cfg), 4)

    @patch("personaggi.models.Punteggio.objects.filter")
    def test_risolvi_difficolta_aura(self, mock_punteggio_filter):
        mock_p = MagicMock()
        mock_p.nome = "Magica"
        mock_punteggio_filter.return_value.first.return_value = mock_p
        cfg = _Cfg(
            difficolta=4,
            regole_difficolta=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "punteggio", "nome": "Magica", "min": 1}],
                    "difficolta": 3,
                },
            ],
        )
        self.assertEqual(risolvi_difficolta(_Pg(auras={"Magica": 2}), cfg), 3)
        self.assertEqual(risolvi_difficolta(_Pg(auras={"Magica": 0}), cfg), 4)

    @patch("personaggi.models.Statistica.objects.filter")
    def test_risolvi_difficolta_regole_min(self, mock_stat):
        mock_stat.return_value.first.return_value = None
        cfg = _Cfg(
            difficolta=4,
            regole_difficolta=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 1}],
                    "difficolta": 3,
                },
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 3}],
                    "difficolta": 2,
                },
            ],
        )
        self.assertEqual(risolvi_difficolta(_Pg(stats={"PV": 1}), cfg), 3)
        self.assertEqual(risolvi_difficolta(_Pg(stats={"PV": 5}), cfg), 2)

    @patch("personaggi.models.Statistica.objects.filter")
    def test_deve_saltare_pv_alto(self, mock_stat):
        mock_stat.return_value.first.return_value = None
        cfg = _Cfg(
            esclusioni_minigioco=[
                {
                    "operator": "AND",
                    "requisiti": [{"tipo": "statistica", "sigla": "PV", "min": 6}],
                }
            ]
        )
        self.assertTrue(deve_saltare_minigioco(_Pg(stats={"PV": 6}), cfg))
        self.assertFalse(deve_saltare_minigioco(_Pg(stats={"PV": 5}), cfg))
