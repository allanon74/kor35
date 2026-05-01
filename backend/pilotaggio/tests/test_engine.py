"""
Test motore pilotaggio: validazione codici, DEFCON, sottosistemi e sequenze.

Eseguire con:
    docker exec -t kor35_devhome_backend python manage.py test pilotaggio
"""
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from pilotaggio.engine import (
    codice_valido_3char,
    durata_viaggio_secondi,
    matcha_pattern,
    processa_codice,
    secondi_evento_per_defcon,
    tick_sessione,
)
from pilotaggio.models import (
    DEFCON_MAX,
    EVENTO_ESITO_FALLITO,
    EVENTO_ESITO_PARZIALE,
    EVENTO_ESITO_PENDING,
    EVENTO_ESITO_RISOLTO,
    EventoAttivoSessione,
    EventoNave,
    SESSIONE_STATO_ATTERRAGGIO,
    SESSIONE_STATO_ARRIVATA,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_DECOLLO,
    SESSIONE_STATO_VOLO,
    SEQUENZA_ATTERRAGGIO,
    SEQUENZA_DECOLLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)


def _crea_pilota():
    """Crea un Personaggio minimo per i test (l'engine non lo usa direttamente)."""
    from personaggi.models import Personaggio

    pg = Personaggio.objects.create(nome="Test Pilota")
    return pg


class FormatoCodiceTests(TestCase):
    def test_codice_3char_validi(self):
        for c in ["A12", "B05", "Z99", "1A0", "MX7"]:
            self.assertTrue(codice_valido_3char(c), c)

    def test_codice_3char_invalidi(self):
        for c in ["", "AB", "ABCD", "AB!", "AAA", "12A", "1AA"]:
            self.assertFalse(codice_valido_3char(c), c)

    def test_pattern_jolly(self):
        self.assertTrue(matcha_pattern("A_3", "A23"))
        self.assertTrue(matcha_pattern("a_3", "A23"))
        self.assertFalse(matcha_pattern("A_3", "B23"))
        self.assertFalse(matcha_pattern("A_3", "A2"))


class DurataViaggioTests(TestCase):
    def test_stessa_prefettura(self):
        from personaggi.models import Era, Prefettura

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        pref = Prefettura.objects.create(era=era, nome="P1")
        self.assertEqual(durata_viaggio_secondi(pref, pref, 0), 600)

    def test_stessa_regione(self):
        from personaggi.models import Era, Prefettura, Regione

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        reg = Regione.objects.create(nome="R1")
        p1 = Prefettura.objects.create(era=era, nome="P1", regione=reg)
        p2 = Prefettura.objects.create(era=era, nome="P2", regione=reg)
        self.assertEqual(durata_viaggio_secondi(p1, p2, 0), 1800)

    def test_regioni_diverse(self):
        from personaggi.models import Era, Prefettura, Regione

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        r1 = Regione.objects.create(nome="R1")
        r2 = Regione.objects.create(nome="R2")
        p1 = Prefettura.objects.create(era=era, nome="P1", regione=r1)
        p2 = Prefettura.objects.create(era=era, nome="P2", regione=r2)
        self.assertEqual(durata_viaggio_secondi(p1, p2, 0), 3600)

    def test_malus_defcon(self):
        from personaggi.models import Era, Prefettura

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        pref = Prefettura.objects.create(era=era, nome="P1")
        # DEFCON 3 -> +60% sul base 600 = 960
        self.assertEqual(durata_viaggio_secondi(pref, pref, 3), 960)


class CountdownTests(TestCase):
    def test_countdown_si_riduce_con_defcon(self):
        base = 30
        self.assertGreater(secondi_evento_per_defcon(base, 0), secondi_evento_per_defcon(base, 4))

    def test_countdown_floor_minimo(self):
        self.assertGreaterEqual(secondi_evento_per_defcon(30, 99), 3)


class MatchPatternParzialeTests(TestCase):
    def test_range_ml_4_9(self):
        self.assertTrue(matcha_pattern("ML(4-9)", "ML4"))
        self.assertTrue(matcha_pattern("ML(4-9)", "ML9"))
        self.assertFalse(matcha_pattern("ML(4-9)", "ML3"))
        self.assertFalse(matcha_pattern("ML(4-9)", "MK5"))

    def test_range_bounds_invertiti(self):
        self.assertTrue(matcha_pattern("ML(9-4)", "ML5"))

    def test_range_con_jolly(self):
        self.assertTrue(matcha_pattern("_L(4-9)", "AL8"))
        self.assertFalse(matcha_pattern("_L(4-9)", "XL3"))

    def test_legacy_underscore(self):
        self.assertTrue(matcha_pattern("A_2", "A52"))


class CodiceProcessingTests(TestCase):
    def setUp(self):
        self.pilota = _crea_pilota()
        self.evento_a = EventoNave.objects.create(
            nome="Brecca scafo",
            descrizione="Sigilla la perdita.",
            codice_soluzione_esatta="A12",
            codici_soluzione_parziale=["A_2"],
            durata_base_secondi=20,
            peso_random=10,
        )
        self.session = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        self.attivo = EventoAttivoSessione.objects.create(
            sessione=self.session,
            evento=self.evento_a,
            deadline_at=timezone.now() + timedelta(seconds=20),
        )

    def test_codice_esatto_risolve_evento_e_riduce_defcon(self):
        self.session.defcon = 2
        self.session.save()
        ris = processa_codice(self.session, "A12")
        self.attivo.refresh_from_db()
        self.assertEqual(ris.esito, EVENTO_ESITO_RISOLTO)
        self.assertEqual(self.attivo.esito, EVENTO_ESITO_RISOLTO)
        self.session.refresh_from_db()
        self.assertEqual(self.session.defcon, 1)

    def test_codice_parziale_lascia_defcon(self):
        ris = processa_codice(self.session, "A52")
        self.assertEqual(ris.esito, EVENTO_ESITO_PARZIALE)
        self.session.refresh_from_db()
        self.assertEqual(self.session.defcon, 0)

    def test_codice_parziale_intervallo_cifra(self):
        self.evento_a.codice_soluzione_esatta = "ZZ9"
        self.evento_a.codici_soluzione_parziale = ["ML(4-9)"]
        self.evento_a.save()
        ris = processa_codice(self.session, "ML6")
        self.assertEqual(ris.esito, EVENTO_ESITO_PARZIALE)

    def test_codice_precipizio_crash_immediato(self):
        self.evento_a.codice_soluzione_esatta = "AB1"
        self.evento_a.codici_soluzione_parziale = []
        self.evento_a.codici_precipizio = ["XX9"]
        self.evento_a.save()
        self.session.defcon = 2
        self.session.save()
        ris = processa_codice(self.session, "XX9")
        self.assertEqual(ris.esito, "precipizio")
        self.session.refresh_from_db()
        self.assertEqual(self.session.stato, SESSIONE_STATO_CRASHED)
        self.assertEqual(self.session.defcon, DEFCON_MAX + 1)

    def test_codice_dannoso_aumenta_defcon(self):
        ris = processa_codice(self.session, "X99")
        self.assertEqual(ris.esito, EVENTO_ESITO_FALLITO)
        self.session.refresh_from_db()
        self.assertEqual(self.session.defcon, 1)

    def test_formato_invalido_aumenta_defcon(self):
        ris = processa_codice(self.session, "XX")
        self.assertEqual(ris.esito, "invalido")
        self.session.refresh_from_db()
        self.assertEqual(self.session.defcon, 1)

    def test_crash_oltre_defcon_max(self):
        self.session.defcon = DEFCON_MAX
        self.session.save()
        ris = processa_codice(self.session, "Z99")
        self.session.refresh_from_db()
        self.assertEqual(self.session.stato, SESSIONE_STATO_CRASHED)
        self.assertGreater(self.session.defcon, DEFCON_MAX)


class SottosistemaGuastoTests(TestCase):
    def setUp(self):
        self.pilota = _crea_pilota()
        self.sottos = SottosistemaNave.objects.create(
            codice="A", nome="Motori", durata_ripristino_secondi=60
        )
        self.evento = EventoNave.objects.create(
            nome="Surriscaldamento",
            descrizione="...",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            peso_random=10,
        )
        self.session = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        EventoAttivoSessione.objects.create(
            sessione=self.session,
            evento=self.evento,
            deadline_at=timezone.now() + timedelta(seconds=20),
        )
        StatoSottosistemaSessione.objects.create(
            sessione=self.session,
            sottosistema=self.sottos,
            online=False,
            guasto_at=timezone.now(),
        )

    def test_codice_su_sottosistema_offline_fallisce(self):
        ris = processa_codice(self.session, "A12")
        self.assertEqual(ris.esito, "sottosistema_offline")
        self.session.refresh_from_db()
        self.assertEqual(self.session.defcon, 1)

    def test_recovery_dopo_scadenza(self):
        stato = StatoSottosistemaSessione.objects.get(sessione=self.session)
        stato.recovery_at = timezone.now() - timedelta(seconds=1)
        stato.save()
        tick_sessione(self.session)
        stato.refresh_from_db()
        self.assertTrue(stato.online)


class SequenzeVoloTests(TestCase):
    def setUp(self):
        self.pilota = _crea_pilota()
        SequenzaVolo.objects.create(
            tipo=SEQUENZA_DECOLLO, codici=["A12", "B34"], attiva=True
        )
        SequenzaVolo.objects.create(
            tipo=SEQUENZA_ATTERRAGGIO, codici=["X11", "Y22"], attiva=True
        )

    def test_sequenza_decollo_completa_passa_a_volo(self):
        s = SessioneVolo.objects.create(
            pilota=self.pilota, stato=SESSIONE_STATO_DECOLLO,
            durata_pianificata_secondi=600,
        )
        processa_codice(s, "A12")
        processa_codice(s, "B34")
        s.refresh_from_db()
        self.assertEqual(s.stato, SESSIONE_STATO_VOLO)

    def test_sequenza_decollo_errata_resetta_e_aumenta_defcon(self):
        s = SessioneVolo.objects.create(
            pilota=self.pilota, stato=SESSIONE_STATO_DECOLLO,
            durata_pianificata_secondi=600,
        )
        processa_codice(s, "A12")
        processa_codice(s, "Z99")
        s.refresh_from_db()
        self.assertEqual(s.decollo_idx, 0)
        self.assertEqual(s.defcon, 1)

    def test_sequenza_atterraggio_completa_porta_ad_arrivata(self):
        s = SessioneVolo.objects.create(
            pilota=self.pilota, stato=SESSIONE_STATO_ATTERRAGGIO,
            durata_pianificata_secondi=600,
        )
        processa_codice(s, "X11")
        processa_codice(s, "Y22")
        s.refresh_from_db()
        self.assertEqual(s.stato, SESSIONE_STATO_ARRIVATA)


class TimeoutEventoTests(TestCase):
    def test_evento_scaduto_aumenta_defcon(self):
        pilota = _crea_pilota()
        s = SessioneVolo.objects.create(
            pilota=pilota, stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        ev = EventoNave.objects.create(
            nome="X", descrizione="X", codice_soluzione_esatta="A12",
            durata_base_secondi=10,
        )
        EventoAttivoSessione.objects.create(
            sessione=s, evento=ev,
            deadline_at=timezone.now() - timedelta(seconds=5),
        )
        tick_sessione(s)
        s.refresh_from_db()
        self.assertEqual(s.defcon, 1)
