"""Test sistema allibratore scommesse."""
from decimal import Decimal
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.models import Personaggio
from personaggi.scommesse_logic import applica_bonus_quota_allibratore
from personaggi.scommesse_models import (
    CalendarioScommesse,
    CodiceScommessa,
    IncontroScommesse,
    PuntataScommessa,
    SportScommesse,
    SquadraScommesse,
)
from personaggi.scommesse_service import _liquida_calendario, piazza_puntata


class ScommesseAllibratoreTests(TestCase):
    def setUp(self):
        self.sport = SportScommesse.objects.create(nome="Calcio test ALL", tipo_risultato="calcio")
        self.squadra_casa = SquadraScommesse.objects.create(sport=self.sport, nome="Casa", potenza=50)
        self.squadra_trasf = SquadraScommesse.objects.create(sport=self.sport, nome="Trasferta", potenza=50)
        self.calendario = CalendarioScommesse.objects.create(
            sport=self.sport,
            titolo="Giornata test",
            data_apertura=timezone.now() - timezone.timedelta(hours=1),
            data_risoluzione=timezone.now() + timezone.timedelta(days=1),
            importo_max_senza_codice=Decimal("15.00"),
        )
        self.incontro = IncontroScommesse.objects.create(
            calendario=self.calendario,
            squadra_casa=self.squadra_casa,
            squadra_trasferta=self.squadra_trasf,
            ordine=0,
            potenza_casa_effettiva=Decimal("50.00"),
            potenza_trasferta_effettiva=Decimal("50.00"),
            quota_casa=Decimal("2.00"),
            quota_pareggio=Decimal("3.50"),
            quota_trasferta=Decimal("2.00"),
            esito="1",
            gol_casa=2,
            gol_trasferta=1,
        )
        self.giocatore = Personaggio.objects.create(nome="Giocatore")
        self.giocatore.modifica_crediti(1000, "Setup test")
        self.allibratore = Personaggio.objects.create(nome="Allibratore")
        self.allibratore.modifica_crediti(1000, "Setup test")
        self.evento = Evento.objects.create(
            titolo="Evento allibratore",
            data_inizio=timezone.now() - timezone.timedelta(hours=1),
            data_fine=timezone.now() + timezone.timedelta(hours=5),
            started_at=timezone.now() - timezone.timedelta(minutes=30),
        )
        self.evento.partecipanti.add(self.allibratore)

    def _selezione_casa(self):
        return [{"incontro_id": self.incontro.id, "esito": "1"}]

    def test_bonus_quota_allibratore_dieci_percento(self):
        quota = applica_bonus_quota_allibratore(Decimal("2.00"))
        self.assertEqual(quota, Decimal("2.20"))

    def test_codice_aumenta_quota_del_dieci_percento(self):
        codice = CodiceScommessa.objects.create(allibratore=self.allibratore, codice="ABC12")
        puntata = piazza_puntata(
            self.giocatore,
            self.calendario.id,
            self._selezione_casa(),
            Decimal("10.00"),
            codice_str=codice.codice,
        )
        self.assertEqual(puntata.quota_totale, Decimal("2.20"))

    def test_allibratore_non_puo_usare_codici(self):
        codice = CodiceScommessa.objects.create(allibratore=self.allibratore, codice="XYZ99")
        with patch.object(Personaggio, "get_valore_statistica", return_value=2):
            with self.assertRaises(ValidationError) as ctx:
                piazza_puntata(
                    self.allibratore,
                    self.calendario.id,
                    self._selezione_casa(),
                    Decimal("10.00"),
                    codice_str=codice.codice,
                )
        self.assertIn("non possono usare codici", str(ctx.exception))

    def test_allibratore_senza_limite_importo(self):
        with patch.object(Personaggio, "get_valore_statistica", return_value=2):
            puntata = piazza_puntata(
                self.allibratore,
                self.calendario.id,
                self._selezione_casa(),
                Decimal("100.00"),
            )
        self.assertEqual(puntata.importo, Decimal("100.00"))
        self.allibratore.refresh_from_db()
        self.assertEqual(self.allibratore.crediti, 900)

    def test_giocatore_senza_codice_rispetta_limite(self):
        with self.assertRaises(ValidationError) as ctx:
            piazza_puntata(
                self.giocatore,
                self.calendario.id,
                self._selezione_casa(),
                Decimal("20.00"),
            )
        self.assertIn("massimo", str(ctx.exception).lower())

    def test_commissione_solo_su_vincita_in_liquidazione(self):
        codice = CodiceScommessa.objects.create(allibratore=self.allibratore, codice="WIN01")
        crediti_all_prima = self.allibratore.crediti

        piazza_puntata(
            self.giocatore,
            self.calendario.id,
            self._selezione_casa(),
            Decimal("10.00"),
            codice_str=codice.codice,
        )
        self.allibratore.refresh_from_db()
        self.assertEqual(self.allibratore.crediti, crediti_all_prima)

        self.calendario.data_risoluzione = timezone.now() - timezone.timedelta(minutes=5)
        self.calendario.save(update_fields=["data_risoluzione", "updated_at"])
        _liquida_calendario(self.calendario)

        puntata = PuntataScommessa.objects.get(codice=codice)
        self.allibratore.refresh_from_db()
        self.assertEqual(puntata.stato, PuntataScommessa.STATO_WON)
        self.assertEqual(puntata.vincita, Decimal("22.00"))
        delta = self.allibratore.crediti - crediti_all_prima
        self.assertEqual(delta, Decimal("1.76"))

    def test_commissione_non_su_puntata_persa(self):
        codice = CodiceScommessa.objects.create(allibratore=self.allibratore, codice="LOSE1")
        crediti_all_prima = self.allibratore.crediti

        piazza_puntata(
            self.giocatore,
            self.calendario.id,
            [{"incontro_id": self.incontro.id, "esito": "2"}],
            Decimal("10.00"),
            codice_str=codice.codice,
        )

        self.calendario.data_risoluzione = timezone.now() - timezone.timedelta(minutes=5)
        self.calendario.save(update_fields=["data_risoluzione", "updated_at"])
        _liquida_calendario(self.calendario)

        self.allibratore.refresh_from_db()
        self.assertEqual(self.allibratore.crediti, crediti_all_prima)
