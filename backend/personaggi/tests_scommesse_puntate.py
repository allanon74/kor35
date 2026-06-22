"""Test riscossione vincite scommesse."""
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from personaggi.models import Personaggio
from personaggi.scommesse_models import (
    CalendarioScommesse,
    PuntataScommessa,
    SportScommesse,
)
from personaggi.scommesse_service import riscuoti_vincita


class ScommesseRiscossioneTests(TestCase):
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

    def test_riscuoti_vincita_accredita_crediti(self):
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
        crediti_prima = self.personaggio.crediti
        riscuoti_vincita(self.personaggio, puntata.id)
        self.personaggio.refresh_from_db()
        puntata.refresh_from_db()
        self.assertTrue(puntata.vincita_riscossa)
        self.assertIsNotNone(puntata.riscossa_at)
        self.assertEqual(self.personaggio.crediti, crediti_prima + 25)

    def test_riscuoti_vincita_gia_riscossa_fallisce(self):
        puntata = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=self.calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("2.00"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("20.00"),
            liquidata_at=timezone.now(),
            vincita_riscossa=True,
            riscossa_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            riscuoti_vincita(self.personaggio, puntata.id)

    def test_riscuoti_vincita_prima_pubblicazione_fallisce(self):
        futuro = timezone.now() + timezone.timedelta(hours=2)
        calendario = CalendarioScommesse.objects.create(
            sport=self.sport,
            titolo="Giornata futura",
            data_apertura=timezone.now(),
            data_risoluzione=futuro,
            liquidato=False,
        )
        puntata = PuntataScommessa.objects.create(
            personaggio=self.personaggio,
            calendario=calendario,
            importo=Decimal("10.00"),
            tipo=PuntataScommessa.TIPO_SINGOLA,
            quota_totale=Decimal("2.00"),
            stato=PuntataScommessa.STATO_WON,
            vincita=Decimal("20.00"),
            liquidata_at=timezone.now(),
        )
        with self.assertRaises(ValidationError):
            riscuoti_vincita(self.personaggio, puntata.id)
