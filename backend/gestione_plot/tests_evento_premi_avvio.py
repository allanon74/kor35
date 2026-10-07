"""Il premio presenza vale per l'avvio ufficiale, non per sempre sullo stesso evento."""

from datetime import timedelta
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from gestione_plot.evento_premi import (
    applica_premio_presenza_personaggio,
    descrizione_premio_evento,
    report_ricompense_evento,
)
from gestione_plot.models import Evento, EventoPremioPersonaggio
from personaggi.models import (
    Campagna,
    CreditoMovimento,
    Personaggio,
    PuntiCaratteristicaMovimento,
    TipologiaPersonaggio,
)


class PremioAvvioCorrenteTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(slug="premio-avvio", nome="Premio avvio", attiva=True)
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Giocante premio avvio", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="Carloh",
            campagna=self.campagna,
            tipologia=self.tipologia,
            prestigio=1,
        )
        self.now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Verso i Sette Alberi",
            data_inizio=self.now - timedelta(hours=2),
            data_fine=self.now + timedelta(days=1),
            started_at=self.now,
            pc_guadagnati=2,
            crediti_base_inizio_evento=Decimal("1500.00"),
            prestigio_base_inizio_evento=150,
        )
        self.evento.partecipanti.add(self.pg)

    def test_secondo_accredito_stesso_avvio_e_idempotente(self):
        self.assertTrue(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.assertFalse(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 151)
        self.assertEqual(
            CreditoMovimento.objects.filter(personaggio=self.pg, evento=self.evento).count(),
            1,
        )
        self.assertEqual(
            PuntiCaratteristicaMovimento.objects.filter(
                personaggio=self.pg,
                descrizione=descrizione_premio_evento(self.evento),
            ).count(),
            1,
        )

    def test_riga_di_un_avvio_precedente_non_blocca_il_nuovo(self):
        passato = self.now - timedelta(days=90)
        row = EventoPremioPersonaggio.objects.create(
            evento=self.evento,
            personaggio=self.pg,
            avvio_at=passato,
        )
        EventoPremioPersonaggio.objects.filter(pk=row.pk).update(created_at=passato)
        PuntiCaratteristicaMovimento.objects.create(
            personaggio=self.pg,
            importo=1,
            descrizione="Inizio evento «Test su nuove realtà»",
            data=passato,
        )

        self.assertTrue(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.pg.refresh_from_db()
        row.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 151)
        self.assertEqual(row.avvio_at, self.evento.started_at)
        self.assertEqual(
            CreditoMovimento.objects.filter(personaggio=self.pg, descrizione=descrizione_premio_evento(self.evento)).count(),
            1,
        )
        self.assertFalse(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.pg.refresh_from_db()
        self.assertEqual(self.pg.prestigio, 151)

    def test_riga_legacy_dello_stesso_avvio_non_paga_due_volte(self):
        row = EventoPremioPersonaggio.objects.create(evento=self.evento, personaggio=self.pg)
        self.assertIsNone(row.avvio_at)
        self.assertFalse(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.assertEqual(self.pg.prestigio, 1)
        self.assertFalse(
            CreditoMovimento.objects.filter(personaggio=self.pg, evento=self.evento).exists()
        )

    def test_ledger_gia_scritto_non_paga_due_volte(self):
        passato = self.now - timedelta(days=90)
        EventoPremioPersonaggio.objects.create(
            evento=self.evento,
            personaggio=self.pg,
            avvio_at=passato,
        )
        PuntiCaratteristicaMovimento.objects.create(
            personaggio=self.pg,
            importo=2,
            descrizione=descrizione_premio_evento(self.evento),
            data=self.now,
        )
        self.assertFalse(applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now))
        self.assertEqual(
            PuntiCaratteristicaMovimento.objects.filter(personaggio=self.pg).count(),
            1,
        )

    def test_report_distingue_avvio_precedente(self):
        passato = self.now - timedelta(days=90)
        row = EventoPremioPersonaggio.objects.create(
            evento=self.evento,
            personaggio=self.pg,
            avvio_at=passato,
        )
        EventoPremioPersonaggio.objects.filter(pk=row.pk).update(created_at=passato)
        report = report_ricompense_evento(self.evento, ts=self.now)
        riga = report["ricompense"][0]
        self.assertFalse(riga["premio_gia_assegnato"])
        self.assertTrue(riga["premio_avvio_precedente"])

        applica_premio_presenza_personaggio(self.evento, self.pg, when=self.now)
        report = report_ricompense_evento(self.evento, ts=self.now)
        riga = report["ricompense"][0]
        self.assertTrue(riga["premio_gia_assegnato"])
        self.assertFalse(riga["premio_avvio_precedente"])
