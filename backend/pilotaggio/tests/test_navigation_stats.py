"""Test configurazione statistiche navigazione."""
from django.test import TestCase

from pilotaggio.models import PilotRuntimeConfig
from pilotaggio.navigation_stats import (
    build_navigation_stats_payload,
    ingegneria_stat_sigla,
    navigazione_stat_sigla,
    riparazione_stat_sigla,
    sabotaggio_stat_sigla,
    scientifica_stat_sigla,
)


class NavigationStatsConfigTests(TestCase):
    def test_defaults(self):
        cfg = PilotRuntimeConfig.get_solo()
        self.assertEqual(navigazione_stat_sigla(cfg), "0PI")
        self.assertEqual(ingegneria_stat_sigla(cfg), "0IN")
        self.assertEqual(sabotaggio_stat_sigla(cfg), "0SA")
        self.assertEqual(riparazione_stat_sigla(cfg), "0RI")
        self.assertEqual(scientifica_stat_sigla(cfg), "0SC")

    def test_override_runtime(self):
        cfg = PilotRuntimeConfig.get_solo()
        cfg.navigazione_stat_accesso_sigla = "9PI"
        cfg.sabotaggio_stat_sigla = "9SA"
        cfg.save()
        self.assertEqual(navigazione_stat_sigla(), "9PI")
        self.assertEqual(sabotaggio_stat_sigla(), "9SA")

    def test_catalogo_ruoli(self):
        payload = build_navigation_stats_payload()
        self.assertIn("ruoli", payload)
        ids = {r["id"] for r in payload["ruoli"]}
        self.assertIn("navigazione", ids)
        self.assertIn("ingegneria", ids)
        self.assertIn("scientifica", ids)
        self.assertIn("comunicazioni", ids)
        self.assertIn("sabotaggio", ids)
        self.assertIn("riparazione", ids)
        comm = next(r for r in payload["ruoli"] if r["id"] == "comunicazioni")
        self.assertFalse(comm["implementato"])
