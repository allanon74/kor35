"""Test motore compattatore (compressione/decompressione)."""
from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from pilotaggio.compattatore_engine import (
    build_compattatore_state_payload,
    operazione_compressione,
    operazione_decompressione,
    operazione_risonanza,
)
from pilotaggio.componenti_stiva import mattoni_componente_qs, staff_modifica_stiva
from pilotaggio.models import CompattatoreStatoNave, PilotRuntimeConfig, SottosistemaNave, StatoSottosistemaNave


class CompattatoreEngineTests(TestCase):
    def setUp(self):
        call_command("seed_componenti_nave", verbosity=0)

        cfg = PilotRuntimeConfig.get_solo()
        cfg.compattatore_console_abilitata = True
        cfg.save(update_fields=["compattatore_console_abilitata", "updated_at"])

        self.ss, _ = SottosistemaNave.objects.update_or_create(
            codice="Z",
            defaults={"nome": "Compattatore", "attivo": True, "tipo": "compattatore"},
        )
        stato, _ = StatoSottosistemaNave.objects.get_or_create(
            sottosistema=self.ss,
            defaults={"livello_attuale": 3, "livello_target": 3, "online": True},
        )
        stato.livello_attuale = 3
        stato.livello_target = 3
        stato.online = True
        stato.save()

        mattoni = sorted(mattoni_componente_qs(), key=lambda m: m.indice_componente or 0)
        self.m0 = mattoni[0]
        self.m1 = mattoni[1]

        stato_comp = CompattatoreStatoNave.get_solo()
        stato_comp.energia_accumulata = 9.0
        stato_comp.save(update_fields=["energia_accumulata", "updated_at"])
        staff_modifica_stiva(mattone_id=str(self.m0.pk), delta=4)

    def test_compressione_2_a_1(self):
        operazione_compressione(mattone_id=str(self.m0.pk))
        payload = build_compattatore_state_payload()
        righe = {r["indice_componente"]: r["quantita"] for r in payload["stiva"]["righe"]}
        self.assertEqual(righe.get(0), 2)
        self.assertEqual(righe.get(1), 1)

    def test_decompressione_1_a_2(self):
        staff_modifica_stiva(mattone_id=str(self.m1.pk), delta=1)
        operazione_decompressione(mattone_id=str(self.m1.pk))
        payload = build_compattatore_state_payload()
        righe = {r["indice_componente"]: r["quantita"] for r in payload["stiva"]["righe"]}
        self.assertEqual(righe.get(0), 6)
        self.assertEqual(righe.get(1, 0), 0)

    def test_risonanza_consuma_energia_e_mattone(self):
        rng = __import__("random").Random(42)
        payload = operazione_risonanza(mattone_id=str(self.m0.pk), rng=rng)
        self.assertIn("risonanza", payload)
        self.assertIsNotNone(payload["risonanza"]["slot_a"])
        self.assertIsNotNone(payload["risonanza"]["slot_b"])
        self.assertLess(payload["energia_accumulata"], 9.0)
