"""Test console scientifica — spettrografia e scan profondo."""
from __future__ import annotations

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from pilotaggio.models import (
    EVENTO_ESITO_PENDING,
    EventoAttivoSessione,
    EventoNave,
    PilotRuntimeConfig,
    SESSIONE_STATO_VOLO,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)
from pilotaggio.scientifica_spectro import (
    build_scientifica_state_payload,
    build_spectrografia_evento,
    esegui_scan_profondo,
)
from pilotaggio.componenti_stiva import staff_modifica_stiva


class ScientificaSpectroTests(TestCase):
    def setUp(self):
        call_command("seed_componenti_nave", verbosity=0)
        from personaggi.models import Personaggio

        self.pg = Personaggio.objects.create(nome="Sci Test")
        cfg = PilotRuntimeConfig.get_solo()
        cfg.scientifica_console_abilitata = True
        cfg.scientifica_scan_profondo_abilitato = True
        cfg.scientifica_scan_max_per_volo = 2
        cfg.save()

        self.sessione = SessioneVolo.objects.create(
            pilota=self.pg,
            stato=SESSIONE_STATO_VOLO,
            defcon=2,
            started_at=timezone.now(),
        )
        self.ss_g, _ = SottosistemaNave.objects.update_or_create(
            codice="G",
            defaults={"nome": "Point Defense", "gruppo": "Difesa", "attivo": True},
        )
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione,
            sottosistema=self.ss_g,
            online=True,
            livello_attuale=5,
            livello_target=5,
        )
        self.evento = EventoNave.objects.create(
            nome="Shear test",
            descrizione="Fenomeno di prova",
            regole_json={
                "st": {
                    "groups": [
                        {
                            "logic": "all",
                            "conditions": [
                                {"sottosistema": "G", "op": ">=", "value": 6},
                            ],
                        }
                    ],
                    "_conditions": [{"sottosistema": "G", "op": ">=", "value": 6}],
                },
                "sp": {
                    "groups": [
                        {
                            "logic": "all",
                            "conditions": [
                                {"sottosistema": "G", "op": ">=", "value": 4},
                            ],
                        }
                    ],
                    "_conditions": [{"sottosistema": "G", "op": ">=", "value": 4}],
                },
            },
            attivo=True,
        )
        self.istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=self.evento,
            deadline_at=timezone.now(),
            ticks_rimanenti=4,
            esito=EVENTO_ESITO_PENDING,
            direzione_evento="destra",
        )

    def test_spectrografia_delta_e_firma(self):
        payload = build_spectrografia_evento(self.sessione, self.istanza)
        self.assertEqual(payload["evento_nome"], "Shear test")
        self.assertTrue(payload["firma_spettrale"])
        self.assertTrue(any("G" in d for d in payload["delta_navigazione"]))
        self.assertEqual(payload["stato_soluzione"]["codice"], "sp_ok")

    def test_scan_profondo_consuma_componente(self):
        from personaggi.models import Mattone
        from pilotaggio.componenti_nave_constants import AURA_COMPONENTI_SIGLA

        mattone = Mattone.objects.filter(aura__sigla=AURA_COMPONENTI_SIGLA).first()
        staff_modifica_stiva(mattone_id=str(mattone.pk), delta=2)

        res = esegui_scan_profondo(
            componenti_scelti=[{"mattone_id": str(mattone.pk), "quantita": 1}],
        )
        self.assertIn("scan_eseguito", res)
        self.istanza.refresh_from_db()
        self.sessione.refresh_from_db()
        self.assertTrue(self.istanza.scan_profondo_eseguito)
        self.assertEqual(self.sessione.scans_profondi_count, 1)

    def test_state_payload_senza_evento(self):
        self.istanza.esito = "risolto"
        self.istanza.save(update_fields=["esito", "updated_at"])
        payload = build_scientifica_state_payload()
        self.assertFalse(payload["evento_pending"])
        self.assertIsNone(payload["spettrografia"])
