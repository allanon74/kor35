"""Test generazione codici evento da stato sottosistemi."""
from __future__ import annotations

from django.test import TestCase

from pilotaggio.evento_codici import (
    aggiorna_codici_eventi_da_stato,
    genera_codici_evento_da_stato,
)
from pilotaggio.models import ComandoNave, EventoNave, SottosistemaNave, StatoSottosistemaNave


class EventoCodiciTests(TestCase):
    def setUp(self):
        ComandoNave.objects.get_or_create(codice="L", defaults={"nome": "Lock"})
        self.ss, _ = SottosistemaNave.objects.update_or_create(
            codice="A",
            defaults={"nome": "Test A", "attivo": True},
        )
        nave = StatoSottosistemaNave.objects.get(sottosistema=self.ss)
        nave.livello_attuale = 5
        nave.livello_target = 5
        nave.online = True
        nave.save()

        self.evento = EventoNave.objects.create(
            nome="Evento test",
            descrizione="d",
            codice_soluzione_esatta="XXX",
            regole_json={
                "version": 3,
                "st": {"_conditions": [{"sottosistema": "A", "op": "=", "value": 5}]},
                "sp": {"_conditions": [{"sottosistema": "A", "op": ">", "value": 3}]},
                "ca": {"_conditions": [{"sottosistema": "A", "op": "<", "value": 2}]},
            },
            attivo=True,
        )

    def test_genera_codici_da_stato(self):
        from pilotaggio.evento_codici import build_stati_by_key_da_sessione_o_nave

        stati = build_stati_by_key_da_sessione_o_nave()
        payload = genera_codici_evento_da_stato(self.evento, stati, comando="L")
        self.assertEqual(payload["codice_soluzione_esatta"], "AL5")
        self.assertTrue(payload["codici_soluzione_parziale"])
        self.assertTrue(payload["codici_precipizio"])

    def test_aggiorna_eventi_bulk(self):
        res = aggiorna_codici_eventi_da_stato(solo_attivi=True)
        self.assertGreaterEqual(res["conteggio"], 1)
        self.evento.refresh_from_db()
        self.assertEqual(self.evento.codice_soluzione_esatta, "AL5")
