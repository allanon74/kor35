"""Test diario di volo (flight_log)."""
from django.test import TestCase
from django.utils import timezone

from personaggi.models import Era, Personaggio, Prefettura

from .flight_log import (
    log_evento_comparso,
    log_precipizio,
    log_volo_iniziato,
    registra_voce_diario,
    riepilogo_sessione_per_pilota,
    spiega_crash,
)
from .models import (
    EVENTO_ESITO_PENDING,
    EventoAttivoSessione,
    EventoNave,
    SessioneVolo,
    VoceDiarioVolo,
)


class FlightLogTests(TestCase):
    def setUp(self):
        self.era = Era.objects.create(nome="E1", abbreviazione="E1")
        self.pilota = Personaggio.objects.create(nome="Pilota Test")
        self.partenza = Prefettura.objects.create(era=self.era, nome="Alpha")
        self.arrivo = Prefettura.objects.create(era=self.era, nome="Beta")
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            prefettura_partenza=self.partenza,
            prefettura_arrivo=self.arrivo,
            stato="volo",
            defcon=2,
        )
        self.evento_nave = EventoNave.objects.create(
            nome="Ammutinamento",
            descrizione="Test",
            peso_random=10,
        )

    def test_spiega_crash_noti(self):
        self.assertIn("DEFCON", spiega_crash("defcon_overflow"))
        self.assertIn("Energia", spiega_crash("end_of_energy"))

    def test_registra_voce_diario(self):
        registra_voce_diario(self.sessione, "info", "Messaggio di prova", defcon_pre=1, defcon_post=2)
        voce = VoceDiarioVolo.objects.get(sessione=self.sessione)
        self.assertEqual(voce.categoria, "info")
        self.assertEqual(voce.defcon_pre, 1)
        self.assertEqual(voce.defcon_post, 2)

    def test_log_volo_iniziato(self):
        log_volo_iniziato(self.sessione, partenza="Alpha", arrivo="Beta")
        self.assertTrue(
            VoceDiarioVolo.objects.filter(sessione=self.sessione, categoria="volo_iniziato").exists()
        )

    def test_log_precipizio(self):
        self.sessione.stato = "crashed"
        self.sessione.crash_reason = "catastrophic_event"
        log_precipizio(self.sessione, "catastrophic_event")
        voce = VoceDiarioVolo.objects.get(sessione=self.sessione, categoria="precipizio")
        self.assertIn("PRECIPIZIO", voce.messaggio)

    def test_log_evento_comparso(self):
        now = timezone.now()
        istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=self.evento_nave,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=now,
            prossima_valutazione_at=now,
            intervallo_reazione_secondi=22,
        )
        log_evento_comparso(self.sessione, istanza)
        voce = VoceDiarioVolo.objects.get(sessione=self.sessione, categoria="evento_comparso")
        self.assertIn("Ammutinamento", voce.messaggio)

    def test_riepilogo_sessione_crashed(self):
        self.sessione.stato = "crashed"
        self.sessione.crash_reason = "end_of_energy"
        self.sessione.ended_at = timezone.now()
        riep = riepilogo_sessione_per_pilota(self.sessione)
        self.assertEqual(riep["stato"], "crashed")
        self.assertEqual(riep["stato_etichetta"], "Precipitata")
        self.assertIn("Energia", riep["crash_spiegazione"])
