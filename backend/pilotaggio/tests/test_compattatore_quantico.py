"""Test algoritmo e operazione Compattatore Quantico."""
from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase

from pilotaggio.compattatore_engine import operazione_compattatore_quantico
from pilotaggio.compattatore_quantico import (
    _calcola_indice_componente,
    _calcola_quantita_componenti,
    _digest_nome,
    genera_componenti_da_nome,
    normalizza_nome_quantico,
)
from pilotaggio.models import CompattatoreStatoNave, PilotRuntimeConfig, SottosistemaNave, StatoSottosistemaNave


class CompattatoreQuanticoAlgorithmTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_componenti_nave", verbosity=0)

    def test_normalizza_nome(self):
        self.assertEqual(normalizza_nome_quantico("Spada-Ancestrale 7"), "SPADAANCESTRALE7")

    def test_genera_da_1_a_5_deterministico(self):
        a = genera_componenti_da_nome("Reattore Omega")
        b = genera_componenti_da_nome("Reattore Omega")
        self.assertEqual(a, b)
        self.assertGreaterEqual(a["numero_unit"], 1)
        self.assertLessEqual(a["numero_unit"], 5)
        self.assertEqual(len(a["unita"]), a["numero_unit"])
        for u in a["unita"]:
            self.assertNotIn("lettera_fonte", u)

    def test_stessa_stringa_esatta_stesso_risultato(self):
        nome = "Modulo-Delta 42"
        self.assertEqual(
            genera_componenti_da_nome(nome),
            genera_componenti_da_nome(nome),
        )
        norm = normalizza_nome_quantico(nome)
        digest = _digest_nome(norm)
        qty = _calcola_quantita_componenti(norm, digest)
        self.assertEqual(qty, genera_componenti_da_nome(nome)["numero_unit"])
        for i in range(qty):
            indice = _calcola_indice_componente(norm, digest, i)
            self.assertEqual(indice, genera_componenti_da_nome(nome)["unita"][i]["indice_componente"])

    def test_modifica_una_lettera_cambia_esito(self):
        base = genera_componenti_da_nome("Cristallo Alfa")
        altro = genera_componenti_da_nome("Cristallo Alfb")
        self.assertNotEqual(base, altro)


class CompattatoreQuanticoOperationTests(TestCase):
    def setUp(self):
        call_command("seed_componenti_nave", verbosity=0)
        cfg = PilotRuntimeConfig.get_solo()
        cfg.compattatore_console_abilitata = True
        cfg.compattatore_quantico_abilitato = False
        cfg.save()

        self.ss, _ = SottosistemaNave.objects.update_or_create(
            codice="Z",
            defaults={"nome": "Compattatore", "attivo": True, "tipo": "compattatore"},
        )
        stato, _ = StatoSottosistemaNave.objects.get_or_create(
            sottosistema=self.ss,
            defaults={"livello_attuale": 3, "livello_target": 3, "online": True},
        )
        stato.livello_attuale = 3
        stato.online = True
        stato.save()

        comp = CompattatoreStatoNave.get_solo()
        comp.energia_accumulata = 9.0
        comp.save()

    def test_disabilitato_senza_flag(self):
        with self.assertRaises(ValueError) as ctx:
            operazione_compattatore_quantico(nome_oggetto="Cristallo instabile")
        self.assertIn("disabilitato", str(ctx.exception).lower())

    def test_testo_ok_con_flag(self):
        cfg = PilotRuntimeConfig.get_solo()
        cfg.compattatore_quantico_abilitato = True
        cfg.save()
        payload = operazione_compattatore_quantico(nome_oggetto="Modulo Delta")
        self.assertIn("quantico", payload)
        self.assertEqual(payload["quantico"]["nome_input"], "Modulo Delta")
        self.assertGreater(payload["quantico"]["numero_unit"], 0)
