"""Test console scientifica — Fase 2: coerenza, matrice, interventi."""
from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from pilotaggio.engine import valuta_evento_tick
from pilotaggio.models import (
    EVENTO_ESITO_PENDING,
    EventoAttivoSessione,
    EventoNave,
    PilotRuntimeConfig,
    SESSIONE_STATO_VOLO,
    ScientificoStatoNave,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)
from pilotaggio.scientifica_engine import (
    esegui_intervento_scientifico,
    imposta_fase_matrice,
    reset_stato_scientifica_volo,
    tick_coerenza_scientifica,
)
from pilotaggio.componenti_stiva import staff_modifica_stiva


class ScientificaInterventiTests(TestCase):
    def setUp(self):
        call_command("seed_componenti_nave", verbosity=0)
        from personaggi.models import Personaggio

        self.pg = Personaggio.objects.create(nome="Sci Fase2")
        cfg = PilotRuntimeConfig.get_solo()
        cfg.scientifica_console_abilitata = True
        cfg.scientifica_interventi_abilitati = True
        cfg.scientifica_coerenza_cap = 24
        cfg.scientifica_livello_min_esotici = 1
        cfg.save()

        self.sessione = SessioneVolo.objects.create(
            pilota=self.pg,
            stato=SESSIONE_STATO_VOLO,
            defcon=3,
            started_at=timezone.now(),
        )
        for codice, nome in (("R", "Nucleo Temporale"), ("S", "Nucleo Dimensionale"), ("T", "Correttore Paradossi")):
            ss, _ = SottosistemaNave.objects.update_or_create(
                codice=codice,
                defaults={"nome": nome, "gruppo": "Sistemi Esotici", "attivo": True},
            )
            StatoSottosistemaSessione.objects.create(
                sessione=self.sessione,
                sottosistema=ss,
                online=True,
                livello_attuale=3,
                livello_target=3,
            )

        self.evento = EventoNave.objects.create(
            nome="Anomalia test",
            regole_json={
                "ca": {
                    "groups": [
                        {
                            "logic": "all",
                            "conditions": [{"sottosistema": "R", "op": "<=", "value": 0}],
                        }
                    ],
                },
                "st": {
                    "groups": [
                        {
                            "logic": "all",
                            "conditions": [{"sottosistema": "R", "op": ">=", "value": 9}],
                        }
                    ],
                },
                "sp": {
                    "groups": [
                        {
                            "logic": "all",
                            "conditions": [{"sottosistema": "R", "op": ">=", "value": 2}],
                        }
                    ],
                },
            },
        )
        self.istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=self.evento,
            deadline_at=timezone.now(),
            ticks_rimanenti=2,
            esito=EVENTO_ESITO_PENDING,
            valutazioni_eseguite=1,
            prossima_valutazione_at=timezone.now(),
        )

    def _set_coerenza(self, val: int, *, carica: int = 100):
        stato = ScientificoStatoNave.get_solo()
        stato.coerenza_accumulata = val
        stato.carica_intervento = carica
        stato.save(update_fields=["coerenza_accumulata", "carica_intervento", "updated_at"])

    def test_tick_coerenza_con_esotici_online(self):
        reset_stato_scientifica_volo()
        delta = tick_coerenza_scientifica(self.sessione)
        self.assertGreaterEqual(delta, 1)
        stato = ScientificoStatoNave.get_solo()
        self.assertGreater(stato.coerenza_accumulata, 0)
        self.assertGreater(stato.carica_intervento, 0)

    def test_piu_energia_piu_coerenza_per_tick(self):
        reset_stato_scientifica_volo()
        tick_coerenza_scientifica(self.sessione)
        stato_bassa = ScientificoStatoNave.get_solo()
        coerenza_l3 = int(stato_bassa.coerenza_accumulata or 0)

        reset_stato_scientifica_volo()
        StatoSottosistemaSessione.objects.filter(sessione=self.sessione).update(
            livello_attuale=6, livello_target=6
        )
        tick_coerenza_scientifica(self.sessione)
        stato_alta = ScientificoStatoNave.get_solo()
        self.assertGreater(int(stato_alta.coerenza_accumulata or 0), coerenza_l3)
        self.assertGreater(int(stato_alta.carica_intervento or 0), int(stato_bassa.carica_intervento or 0))

    def test_imposta_fase_matrice(self):
        reset_stato_scientifica_volo()
        payload = imposta_fase_matrice(codice="R", fase=2)
        self.assertEqual(payload["matrice"]["nuclei"][0]["fase"], 2)
        stato = ScientificoStatoNave.get_solo()
        self.assertEqual(stato.fase_r, 2)

    def _mattone_stiva(self, delta: int = 3):
        from personaggi.models import Mattone
        from pilotaggio.componenti_nave_constants import AURA_COMPONENTI_SIGLA

        mattone = Mattone.objects.filter(aura__sigla=AURA_COMPONENTI_SIGLA).first()
        staff_modifica_stiva(mattone_id=str(mattone.pk), delta=delta)
        return str(mattone.pk)

    def test_dilatazione_aumenta_ticks(self):
        self._set_coerenza(20)
        mid = self._mattone_stiva(5)
        payload = esegui_intervento_scientifico(
            tipo="dilatazione",
            componenti_scelti=[{"mattone_id": mid, "quantita": 1}],
        )
        self.istanza.refresh_from_db()
        self.assertEqual(self.istanza.ticks_rimanenti, 3)
        self.assertIn("intervento_eseguito", payload)

    def test_gabbia_sopprime_ca(self):
        self._set_coerenza(20)
        mid = self._mattone_stiva(5)
        esegui_intervento_scientifico(
            tipo="gabbia",
            componenti_scelti=[{"mattone_id": mid, "quantita": 2}],
        )
        self.istanza.refresh_from_db()
        self.assertTrue(self.istanza.ca_soppressa_scientifica)

        StatoSottosistemaSessione.objects.filter(
            sessione=self.sessione, sottosistema__codice="R"
        ).update(online=True, livello_attuale=0)
        esito, _ = valuta_evento_tick(self.sessione, self.istanza)
        self.assertEqual(esito, "ca_soppressa")
        self.istanza.refresh_from_db()
        self.assertFalse(self.istanza.ca_soppressa_scientifica)

    def test_eco_parziale_non_decrementa_tick(self):
        self._set_coerenza(10, carica=100)
        esegui_intervento_scientifico(tipo="eco", componenti_scelti=[])
        self.istanza.refresh_from_db()
        self.assertTrue(self.istanza.eco_parziale_attiva)
        ticks_before = self.istanza.ticks_rimanenti

        esito, _ = valuta_evento_tick(self.sessione, self.istanza)
        self.assertEqual(esito, "sp_eco")
        self.istanza.refresh_from_db()
        self.assertEqual(self.istanza.ticks_rimanenti, ticks_before)

    def test_correzione_paradosso_defcon(self):
        self._set_coerenza(20)
        mid = self._mattone_stiva(2)
        defcon_pre = int(self.sessione.defcon or 0)
        esegui_intervento_scientifico(
            tipo="correzione",
            componenti_scelti=[{"mattone_id": mid, "quantita": 1}],
        )
        self.sessione.refresh_from_db()
        self.assertEqual(int(self.sessione.defcon), defcon_pre - 1)
