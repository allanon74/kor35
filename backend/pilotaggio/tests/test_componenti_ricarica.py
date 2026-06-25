"""Test ricarica componenti batteria/serbatoio."""
from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from pilotaggio.componenti_ricarica import (
    build_requisiti_ricarica_payload,
    valida_selezione_ricarica,
)
from pilotaggio.models import PilotRuntimeConfig, SottosistemaNave
from pilotaggio.componenti_stiva import staff_modifica_stiva
from personaggi.models import Mattone


class ComponentiRicaricaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_componenti_nave", verbosity=0)
        cls.m0 = Mattone.objects.filter(aura__sigla="0CP", indice_componente=0).first()
        cls.m1 = Mattone.objects.filter(aura__sigla="0CP", indice_componente=1).first()

    def setUp(self):
        cfg = PilotRuntimeConfig.get_solo()
        cfg.riparazione_componenti_abilitata = True
        cfg.save()
        self.batteria, _ = SottosistemaNave.objects.update_or_create(
            codice="T",
            defaults={"nome": "Test Batteria", "attivo": True, "tipo": "batteria"},
        )
        self.batteria.richiede_componenti_ricarica = True
        self.batteria.requisiti_ricarica_json = [
            {
                "tipo": "specifico",
                "mattone_id": str(self.m0.pk),
                "quantita": 1,
                "ricarica": 25,
            }
        ]
        self.batteria.save()
        staff_modifica_stiva(mattone_id=str(self.m0.pk), delta=5)

    def test_build_payload_ricarica(self):
        payload = build_requisiti_ricarica_payload(self.batteria)
        self.assertTrue(payload["richiede_componenti"])
        self.assertEqual(payload["tipo_ricarica"], "batteria")
        self.assertEqual(payload["ricarica_totale_configurata"], 25)
        self.assertEqual(len(payload["vincoli"]), 1)

    def test_valida_selezione_ricarica(self):
        ok, err, alloc, importo = valida_selezione_ricarica(
            self.batteria,
            [{"mattone_id": str(self.m0.pk), "quantita": 1}],
        )
        self.assertTrue(ok, err)
        self.assertEqual(importo, 25)
        self.assertEqual(len(alloc), 1)
