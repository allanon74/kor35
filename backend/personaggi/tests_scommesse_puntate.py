"""Test scommesse: vincite sul deposito; ritiro per-puntata deprecato."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.economia_crediti import saldo_corrente, saldo_deposito
from personaggi.models import Personaggio
from personaggi.scommesse_models import (
    CalendarioScommesse,
    PuntataScommessa,
    SportScommesse,
)
from personaggi.scommesse_service import (
    calcola_ritiro_contanti_da_riserva,
    riscuoti_vincita,
    ritira_da_riserva,
)


class ScommesseRiservaTests(TestCase):
    def setUp(self):
        self.sport = SportScommesse.objects.create(nome="Calcio test", tipo_risultato="calcio")
        self.calendario = CalendarioScommesse.objects.create(
            sport=self.sport,
            titolo="Giornata 1",
            data_apertura=timezone.now(),
            data_risoluzione=timezone.now(),
            liquidato=True,
        )
        self.personaggio = Personaggio.objects.create(nome="Giocatore test")
        self.evento = Evento.objects.create(
            titolo="Evento test",
            data_inizio=timezone.now() - timezone.timedelta(hours=1),
            data_fine=timezone.now() + timezone.timedelta(hours=5),
            started_at=timezone.now() - timezone.timedelta(minutes=30),
        )
        self.evento.partecipanti.add(self.personaggio)

    def test_riscuoti_versa_intera_vincita_in_deposito(self):
        puntata = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("2.50"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("25.00"),
            liquidata_at=timezone.now(),
        )
        dep_prima = saldo_deposito(self.personaggio)
        corr_prima = saldo_corrente(self.personaggio)
        riscuoti_vincita(self.personaggio, puntata.id)
        self.personaggio.refresh_from_db()
        puntata.refresh_from_db()
        self.assertTrue(puntata.vincita_riscossa)
        self.assertEqual(puntata.vincita_versata_riserva, Decimal("25.00"))
        self.assertEqual(puntata.vincita_ritirata, Decimal("0.00"))
        self.assertEqual(saldo_deposito(self.personaggio), dep_prima + Decimal("25.00"))
        self.assertEqual(saldo_corrente(self.personaggio), corr_prima)
        # Campo legacy riserva resta a 0
        self.assertEqual(Decimal(str(self.personaggio.riserva or 0)), Decimal("0.00"))

    def test_ritira_da_riserva_deprecato(self):
        puntata = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("2.50"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("25.00"),
            liquidata_at=timezone.now(),
            vincita_riscossa=True,
            vincita_versata_riserva=Decimal("25.00"),
        )
        with self.assertRaises(ValidationError) as ctx:
            ritira_da_riserva(self.personaggio, puntata.id)
        self.assertIn("non è più disponibile", str(ctx.exception))

    def test_calcola_ritiro_contanti_legacy_helper(self):
        """Helper soglia ancora calcola (audit), ma ritiro effettivo è deprecato."""
        puntata = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("100.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("8.00"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("800.00"),
            liquidata_at=timezone.now(),
            vincita_riscossa=True,
            vincita_versata_riserva=Decimal("800.00"),
        )
        ritiro, residuo = calcola_ritiro_contanti_da_riserva(self.personaggio, puntata)
        self.assertEqual(ritiro, Decimal("500.00"))
        self.assertEqual(residuo, Decimal("300.00"))

    def test_cap_ritiro_per_calendario(self):
        PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("30.00"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("300.00"),
            liquidata_at=timezone.now(),
            vincita_riscossa=True,
            vincita_versata_riserva=Decimal("300.00"),
            vincita_ritirata=Decimal("300.00"),
        )
        puntata2 = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("40.00"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("400.00"),
            liquidata_at=timezone.now(),
            vincita_riscossa=True,
            vincita_versata_riserva=Decimal("400.00"),
        )
        ritiro, residuo = calcola_ritiro_contanti_da_riserva(self.personaggio, puntata2)
        self.assertEqual(ritiro, Decimal("200.00"))
        self.assertEqual(residuo, Decimal("200.00"))
