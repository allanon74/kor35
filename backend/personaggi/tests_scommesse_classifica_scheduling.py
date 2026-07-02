"""Test classifiche e programmazione torneo scommesse."""
from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.scommesse_classifica import calcola_classifica_sport
from personaggi.scommesse_logic import (
    STRATEGIA_ACCOPPIAMENTO_ROUND_ROBIN,
    accoppia_squadre_round_robin,
    num_giornate_round_robin,
)
from personaggi.scommesse_models import (
    CalendarioScommesse,
    IncontroScommesse,
    ProgrammazioneTorneoScommesse,
    SportScommesse,
    SquadraScommesse,
)
from personaggi.scommesse_scheduling import (
    calcola_date_calendario,
    genera_calendario_per_evento,
    prossima_finestra_cadenza,
    sincronizza_programmazione,
)


class ScommesseClassificaTests(TestCase):
    def setUp(self):
        self.sport = SportScommesse.objects.create(nome="Lega test", tipo_risultato="calcio")
        self.a = SquadraScommesse.objects.create(sport=self.sport, nome="Alpha", potenza=50)
        self.b = SquadraScommesse.objects.create(sport=self.sport, nome="Beta", potenza=50)
        self.cal = CalendarioScommesse.objects.create(
            sport=self.sport,
            titolo="G1",
            data_apertura=timezone.now() - timezone.timedelta(days=7),
            data_risoluzione=timezone.now() - timezone.timedelta(days=1),
            liquidato=True,
            giornata_numero=1,
        )
        IncontroScommesse.objects.create(
            calendario=self.cal,
            squadra_casa=self.a,
            squadra_trasferta=self.b,
            ordine=0,
            potenza_casa_effettiva=Decimal("50"),
            potenza_trasferta_effettiva=Decimal("50"),
            quota_casa=Decimal("2.00"),
            quota_pareggio=Decimal("3.50"),
            quota_trasferta=Decimal("2.00"),
            esito="1",
            gol_casa=2,
            gol_trasferta=1,
        )

    def test_classifica_punti_vittoria(self):
        data = calcola_classifica_sport(self.sport.id)
        self.assertEqual(data["giornate_liquidate"], 1)
        alpha = next(r for r in data["classifica"] if r["nome"] == "Alpha")
        beta = next(r for r in data["classifica"] if r["nome"] == "Beta")
        self.assertEqual(alpha["punti"], 3)
        self.assertEqual(alpha["vinte"], 1)
        self.assertEqual(beta["punti"], 0)
        self.assertEqual(alpha["posizione"], 1)


class ScommesseSchedulingTests(TestCase):
    def setUp(self):
        self.sport = SportScommesse.objects.create(nome="Campionato", tipo_risultato="calcio")
        for nome in ("Uno", "Due", "Tre", "Quattro"):
            SquadraScommesse.objects.create(sport=self.sport, nome=nome, potenza=50)
        self.prog = ProgrammazioneTorneoScommesse.objects.create(
            sport=self.sport,
            attiva=False,
            auto_genera=True,
            intervallo_giorni=14,
            sfasamento_giorni=0,
            giorni_apertura=12,
            strategia_accoppiamento=STRATEGIA_ACCOPPIAMENTO_ROUND_ROBIN,
            data_ancora_cadenza=timezone.now() - timezone.timedelta(days=20),
        )

    def _evento_futuro(self, titolo="Evento futuro", giorni=14):
        return Evento.objects.create(
            titolo=titolo,
            data_inizio=timezone.now() + timezone.timedelta(days=giorni),
            data_fine=timezone.now() + timezone.timedelta(days=giorni + 1),
        )

    def test_round_robin_quattro_squadre_tre_giornate(self):
        self.assertEqual(num_giornate_round_robin(4), 3)
        squadre = list(self.sport.squadre.order_by("nome"))
        g0 = accoppia_squadre_round_robin(squadre, 0, "seed")
        g1 = accoppia_squadre_round_robin(squadre, 1, "seed")
        self.assertEqual(len(g0), 2)
        self.assertEqual(len(g1), 2)

    def test_genera_calendario_per_evento_manuale(self):
        evento = self._evento_futuro()
        cal = genera_calendario_per_evento(self.prog, evento)
        self.assertEqual(cal.giornata_numero, 1)
        self.assertEqual(cal.evento_id, evento.id)
        self.assertEqual(cal.incontri.count(), 2)
        self.prog.refresh_from_db()
        self.assertEqual(self.prog.giornata_corrente, 1)

    def test_date_calendario_prima_evento(self):
        evento = self._evento_futuro()
        apertura, risoluzione = calcola_date_calendario(evento, self.prog)
        self.assertLess(apertura, risoluzione)
        self.assertLess(risoluzione, evento.data_inizio)

    def test_sincronizza_cadenza_crea_giornata(self):
        self.prog.attiva = True
        self.prog.save(update_fields=["attiva", "updated_at"])
        creati = sincronizza_programmazione(self.prog, max_crea=1)
        self.assertEqual(len(creati), 1)
        cal = creati[0]
        self.assertIsNone(cal.evento_id)
        self.assertEqual(cal.giornata_numero, 1)
        self.assertEqual(cal.incontri.count(), 2)

    def test_sincronizza_cadenza_non_duplica(self):
        self.prog.attiva = True
        self.prog.save(update_fields=["attiva", "updated_at"])
        first = sincronizza_programmazione(self.prog, max_crea=1)
        self.assertEqual(len(first), 1)
        self.prog.refresh_from_db()
        sincronizza_programmazione(self.prog, max_crea=1)
        self.assertEqual(
            CalendarioScommesse.objects.filter(
                sport=self.sport, evento__isnull=True, giornata_numero=1,
            ).count(),
            1,
        )

    def test_sfasamento_sposta_prima_finestra(self):
        prog2 = ProgrammazioneTorneoScommesse.objects.create(
            sport=SportScommesse.objects.create(nome="Altro sport", tipo_risultato="calcio"),
            attiva=False,
            sfasamento_giorni=5,
            data_ancora_cadenza=self.prog.data_ancora_cadenza,
        )
        a0, r0 = prossima_finestra_cadenza(self.prog)
        a5, r5 = prossima_finestra_cadenza(prog2)
        self.assertEqual((r5 - r0).days, 5)

    def test_evento_non_genera_automaticamente(self):
        self.prog.attiva = True
        self.prog.save(update_fields=["attiva", "updated_at"])
        n_before = CalendarioScommesse.objects.filter(sport=self.sport).count()
        self._evento_futuro(titolo="Evento signal", giorni=21)
        self.assertEqual(CalendarioScommesse.objects.filter(sport=self.sport).count(), n_before)
