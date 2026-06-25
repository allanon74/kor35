"""Test stiva componenti nave e annichilamento opposti."""
from __future__ import annotations

from django.test import TestCase

from pilotaggio.componenti_nave_constants import TICK_COESISTENZA_OPPOSITI_MAX
from pilotaggio.componenti_riparazione import valida_selezione_componenti
from pilotaggio.componenti_stiva import (
    applica_annichilamento_opposti_stiva,
    build_stiva_payload,
    staff_modifica_stiva,
)
from pilotaggio.models import (
    CoppiaColoriComponente,
    PilotRuntimeConfig,
    SottosistemaNave,
    StivaCoppiaOppositiStato,
)


class ComponentiStivaTests(TestCase):
    def setUp(self):
        from django.core.management import call_command

        call_command("seed_componenti_nave", verbosity=0)
        cfg = PilotRuntimeConfig.get_solo()
        cfg.annichilamento_opposti_abilitato = True
        cfg.riparazione_componenti_abilitata = True
        cfg.save()

        from pilotaggio.componenti_stiva import mattoni_componente_qs

        self.mattoni = list(mattoni_componente_qs())
        self.assertGreaterEqual(len(self.mattoni), 10)

        coppia = CoppiaColoriComponente.objects.first()
        self.assertIsNotNone(coppia)
        self.colore_a_id = coppia.colore_a_id
        self.colore_b_id = coppia.colore_b_id
        self.mattone_a = next(
            m for m in self.mattoni if m.caratteristica_associata_id == self.colore_a_id
        )
        self.mattone_b = next(
            m for m in self.mattoni if m.caratteristica_associata_id == self.colore_b_id
        )

    def test_staff_modifica_stiva(self):
        staff_modifica_stiva(mattone_id=str(self.mattone_a.pk), delta=3)
        payload = build_stiva_payload()
        row = next(r for r in payload["righe"] if r["mattone_id"] == str(self.mattone_a.pk))
        self.assertEqual(row["quantita"], 3)

    def test_annichilamento_dopo_coesistenza(self):
        staff_modifica_stiva(mattone_id=str(self.mattone_a.pk), delta=2)
        staff_modifica_stiva(mattone_id=str(self.mattone_b.pk), delta=2)

        coppia = CoppiaColoriComponente.objects.get(
            colore_a_id=self.colore_a_id, colore_b_id=self.colore_b_id
        )

        for i in range(TICK_COESISTENZA_OPPOSITI_MAX):
            res = applica_annichilamento_opposti_stiva()
            self.assertFalse(res.get("eventi"), msg=f"tick {i+1}")
            stato = StivaCoppiaOppositiStato.objects.get(coppia=coppia)
            self.assertEqual(stato.tick_coesistenza, i + 1)

        res = applica_annichilamento_opposti_stiva()
        self.assertTrue(res.get("eventi"))
        payload = build_stiva_payload()
        tot_a = sum(
            r["quantita"]
            for r in payload["righe"]
            if r["colore_id"] == str(self.colore_a_id)
        )
        tot_b = sum(
            r["quantita"]
            for r in payload["righe"]
            if r["colore_id"] == str(self.colore_b_id)
        )
        self.assertEqual(tot_a, 0)
        self.assertEqual(tot_b, 0)

    def test_valida_selezione_riparazione(self):
        ss, _ = SottosistemaNave.objects.update_or_create(
            codice="Q",
            defaults={
                "nome": "Test componenti",
                "richiede_componenti_riparazione": True,
                "requisiti_riparazione_json": [
                    {"tipo": "specifico", "mattone_id": str(self.mattone_a.pk), "quantita": 1},
                ],
            },
        )
        staff_modifica_stiva(mattone_id=str(self.mattone_a.pk), delta=1)
        ok, err, alloc = valida_selezione_componenti(
            ss,
            [{"mattone_id": str(self.mattone_a.pk), "quantita": 1}],
        )
        self.assertTrue(ok, err)
        self.assertEqual(len(alloc), 1)

        ok2, err2, _ = valida_selezione_componenti(ss, [])
        self.assertFalse(ok2)
        self.assertIn("Seleziona", err2)
