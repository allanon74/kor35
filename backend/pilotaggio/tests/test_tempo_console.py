"""Secondi di countdown calcolati sull'orologio del nodo, non del browser."""
from datetime import datetime, timedelta, timezone
from unittest import TestCase

from pilotaggio.tempo_console import secondi_fino_a


class SecondiFinoATests(TestCase):
    def test_durata_evento_non_dipende_dallo_scarto_del_kiosk(self):
        ora = datetime(2026, 10, 8, 9, 10, tzinfo=timezone.utc)
        # 5 tick × 22s a DEFCON 0.
        deadline = ora + timedelta(seconds=110)
        self.assertEqual(secondi_fino_a(deadline, ora), 110)

    def test_scaduto_vale_zero_e_mancante_vale_none(self):
        ora = datetime(2026, 10, 8, 9, 10, tzinfo=timezone.utc)
        self.assertEqual(secondi_fino_a(ora - timedelta(seconds=3), ora), 0)
        self.assertIsNone(secondi_fino_a(None, ora))

    def test_ceil_sul_frazione_di_secondo(self):
        ora = datetime(2026, 10, 8, 9, 10, tzinfo=timezone.utc)
        self.assertEqual(secondi_fino_a(ora + timedelta(milliseconds=200), ora), 1)
