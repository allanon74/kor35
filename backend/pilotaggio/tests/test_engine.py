"""
Test motore pilotaggio: validazione codici, DEFCON, sottosistemi e sequenze.

Eseguire con:
    docker exec -t kor35_devhome_backend python manage.py test pilotaggio
"""
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from unittest.mock import patch

from pilotaggio.engine import (
    CRUISE_VELOCITY_PER_TICK,
    calcola_distanza_target,
    codice_valido_3char,
    durata_viaggio_secondi,
    genera_evento_se_dovuto,
    prepara_sessione_nuovo_volo,
    intervallo_tick_effettivo_sessione,
    intervallo_tick_sessione,
    matcha_pattern,
    processa_codice,
    scadenza_critica_da_evento,
    secondi_durata_totale_evento,
    secondi_tick_durante_evento,
    tick_sessione,
    ticks_durata_evento_catalogo,
)
from pilotaggio.models import (
    ComandoCriticoGlobale,
    DEFCON_MAX,
    EVENTO_ESITO_FALLITO,
    EVENTO_ESITO_PARZIALE,
    EVENTO_ESITO_PENDING,
    EVENTO_ESITO_RISOLTO,
    EVENTO_ESITO_TIMEOUT,
    EventoAttivoSessione,
    EventoNave,
    SESSIONE_STATO_ATTERRAGGIO,
    SESSIONE_STATO_ARRIVATA,
    SESSIONE_STATO_CRASHED,
    SESSIONE_STATO_DECOLLO,
    SESSIONE_STATO_IDLE,
    SESSIONE_STATO_VOLO,
    SEQUENZA_ATTERRAGGIO,
    SEQUENZA_DECOLLO,
    SequenzaVolo,
    SessioneVolo,
    SottosistemaNave,
    StatoAllertaPilot,
    StatoSottosistemaSessione,
)


def _crea_pilota():
    """Crea un Personaggio minimo per i test (l'engine non lo usa direttamente)."""
    from personaggi.models import Personaggio

    pg = Personaggio.objects.create(nome="Test Pilota")
    return pg


def _attiva_crociera(sessione: SessioneVolo) -> None:
    """Simula decollo effettivo (motore acceso almeno una volta)."""
    sessione.decollo_completato_at = timezone.now()
    sessione.save(update_fields=["decollo_completato_at", "updated_at"])


def _evento_pronto_per_test(istanza: EventoAttivoSessione) -> None:
    """Supera il periodo di reazione (22s DEFCON 0) per test che chiamano valuta_evento_tick."""
    past = timezone.now() - timedelta(seconds=1)
    created_past = timezone.now() - timedelta(seconds=60)
    EventoAttivoSessione.objects.filter(pk=istanza.pk).update(
        created_at=created_past,
        reazione_fino_at=past,
        prossima_valutazione_at=past,
    )
    istanza.refresh_from_db()


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


class DistanzaTargetTests(TestCase):
    def _prefetture(self):
        from personaggi.models import Era, Prefettura, Regione

        era = Era.objects.create(nome="E1", abbreviazione="E1")
        reg1 = Regione.objects.create(nome="R1")
        reg2 = Regione.objects.create(nome="R2")
        p1 = Prefettura.objects.create(era=era, nome="P1", regione=reg1)
        p2 = Prefettura.objects.create(era=era, nome="P2", regione=reg1)
        p3 = Prefettura.objects.create(era=era, nome="P3", regione=reg2)
        return p1, p2, p3

    def _expected_distanza(self, durata_sec: int) -> int:
        num_tick = durata_sec / 5.0
        return max(1, int(round(num_tick * CRUISE_VELOCITY_PER_TICK)))

    def test_stessa_prefettura(self):
        p1, _, _ = self._prefetture()
        dist, dur = calcola_distanza_target(p1, p1, defcon_iniziale=0)
        self.assertEqual(dur, 600)
        self.assertEqual(dist, self._expected_distanza(600))

    def test_stessa_regione(self):
        p1, p2, _ = self._prefetture()
        dist, dur = calcola_distanza_target(p1, p2, defcon_iniziale=0)
        self.assertEqual(dur, 1800)
        self.assertEqual(dist, self._expected_distanza(1800))

    def test_regioni_diverse(self):
        p1, _, p3 = self._prefetture()
        dist, dur = calcola_distanza_target(p1, p3, defcon_iniziale=0)
        self.assertEqual(dur, 3600)
        self.assertEqual(dist, self._expected_distanza(3600))

    def test_malus_defcon_allunga_distanza(self):
        p1, _, _ = self._prefetture()
        dist0, _ = calcola_distanza_target(p1, p1, defcon_iniziale=0)
        dist3, dur3 = calcola_distanza_target(p1, p1, defcon_iniziale=3)
        self.assertEqual(dur3, 960)
        self.assertGreater(dist3, dist0)
        self.assertEqual(dist3, self._expected_distanza(960))


class CountdownTests(TestCase):
    def test_tick_durante_evento_scala_con_defcon(self):
        self.assertGreater(secondi_tick_durante_evento(0), secondi_tick_durante_evento(4))

    def test_tick_durante_evento_minimo_uno(self):
        self.assertGreaterEqual(secondi_tick_durante_evento(99), 1)

    def test_ticks_catalogo_a_b(self):
        with patch("pilotaggio.engine.random.randint", return_value=6):
            self.assertEqual(ticks_durata_evento_catalogo("4-8"), 6)
        self.assertEqual(ticks_durata_evento_catalogo("5"), 5)

    def test_secondi_totali_evento(self):
        self.assertEqual(secondi_durata_totale_evento(4, 0), 4 * secondi_tick_durante_evento(0))


class EventoDurataUnificataTests(TestCase):
    def test_genera_evento_ticks_coerenti_con_countdown(self):
        from unittest.mock import patch

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            distanza_percorsa=10.0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            tick_secondi=5,
        )
        evento = EventoNave.objects.create(
            nome="Durata sync",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_tick="4",
            attivo=True,
        )
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            istanza = genera_evento_se_dovuto(sessione)
        self.assertIsNotNone(istanza)
        ticks = ticks_durata_evento_catalogo(evento.durata_tick)
        durata = secondi_durata_totale_evento(ticks, sessione.defcon)
        self.assertEqual(istanza.ticks_rimanenti, ticks)
        delta = (istanza.deadline_at - istanza.created_at).total_seconds()
        self.assertAlmostEqual(delta, durata, delta=1.0)
        self.assertFalse(istanza.precipita_a_scadenza)


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
        sottos, _ = SottosistemaNave.objects.get_or_create(
            codice="Z",
            defaults={"nome": "Test off", "attivo": True},
        )
        s = SessioneVolo.objects.create(
            pilota=self.pilota, stato=SESSIONE_STATO_ATTERRAGGIO,
            durata_pianificata_secondi=600,
        )
        StatoSottosistemaSessione.objects.create(
            sessione=s,
            sottosistema=sottos,
            online=True,
            livello_attuale=5,
            livello_target=5,
        )
        processa_codice(s, "X11")
        processa_codice(s, "Y22")
        s.refresh_from_db()
        self.assertEqual(s.stato, SESSIONE_STATO_ARRIVATA)
        stato = StatoSottosistemaSessione.objects.get(sessione=s, sottosistema=sottos)
        self.assertFalse(stato.online)
        self.assertEqual(stato.livello_attuale, 0)
        self.assertEqual(stato.livello_target, 0)


class ComandoCriticoGlobaleTests(TestCase):
    """Pattern staff globali: precipizio immediato senza dipendere dall'evento."""

    def setUp(self):
        self.pilota = _crea_pilota()
        ComandoCriticoGlobale.objects.create(
            pattern="QQ7", nome="Test critico", attivo=True
        )

    def test_precipizio_senza_evento_attivo(self):
        s = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        ris = processa_codice(s, "QQ7")
        self.assertEqual(ris.esito, "precipizio")
        s.refresh_from_db()
        self.assertEqual(s.stato, SESSIONE_STATO_CRASHED)
        self.assertGreater(s.defcon, DEFCON_MAX)

    def test_pattern_disattivo_non_precipita(self):
        ComandoCriticoGlobale.objects.update(attivo=False)
        s = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        ris = processa_codice(s, "QQ7")
        self.assertEqual(ris.esito, "no_evento")
        s.refresh_from_db()
        self.assertNotEqual(s.stato, SESSIONE_STATO_CRASHED)


class GenerazioneEventiTests(TestCase):
    def test_defcon0_puo_generare_evento(self):
        """A DEFCON 0 la probabilità per tick deve essere > 0 (non deadlock silenzioso)."""
        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            distanza_percorsa=0.0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        EventoNave.objects.create(
            nome="Test spawn",
            descrizione="Evento di test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            attivo=True,
        )
        row = StatoAllertaPilot.objects.filter(livello=0).first()
        self.assertIsNotNone(row)
        self.assertGreater(float(row.probabilita_evento_per_tick or 0.0), 0.0)

        with patch("pilotaggio.engine.random.random", return_value=0.0):
            istanza = genera_evento_se_dovuto(sessione)
        self.assertIsNone(istanza)

        _attiva_crociera(sessione)
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            istanza = genera_evento_se_dovuto(sessione)
        self.assertIsNotNone(istanza)
        self.assertEqual(istanza.esito, EVENTO_ESITO_PENDING)

    def test_nessun_evento_prima_decollo(self):
        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            distanza_percorsa=0.0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        EventoNave.objects.create(
            nome="Pre decollo",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            attivo=True,
        )
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            self.assertIsNone(genera_evento_se_dovuto(sessione))
        sessione.distanza_percorsa = 500.0
        sessione.save(update_fields=["distanza_percorsa", "updated_at"])
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            self.assertIsNone(genera_evento_se_dovuto(sessione))
        _attiva_crociera(sessione)
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            self.assertIsNotNone(genera_evento_se_dovuto(sessione))


class PreDecolloEventoTests(TestCase):
    def test_prepara_sessione_chiude_eventi_pending(self):
        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_IDLE,
            distanza_percorsa=500.0,
            durata_pianificata_secondi=600,
        )
        evento = EventoNave.objects.create(
            nome="Vecchio",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
        )
        pending = EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=60),
            ticks_rimanenti=3,
        )
        prepara_sessione_nuovo_volo(sessione)
        pending.refresh_from_db()
        sessione.refresh_from_db()
        self.assertEqual(pending.esito, EVENTO_ESITO_TIMEOUT)
        self.assertEqual(sessione.distanza_percorsa, 0.0)
        self.assertIsNone(sessione.next_event_at)
        self.assertIsNone(sessione.decollo_completato_at)

    def test_tick_non_genera_né_valuta_evento_prima_decollo(self):
        from unittest.mock import patch

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            distanza_percorsa=0.0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        evento = EventoNave.objects.create(
            nome="Residual",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            attivo=True,
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "A", "op": "=", "value": 0}],
                    }
                },
                "ca_effetto": {"tipo": "precipizio"},
            },
        )
        EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=60),
            ticks_rimanenti=3,
            precipita_a_scadenza=True,
        )
        EventoNave.objects.create(
            nome="Spawn",
            descrizione="Test",
            codice_soluzione_esatta="B12",
            durata_base_secondi=20,
            attivo=True,
        )
        with patch("pilotaggio.engine.random.random", return_value=0.0):
            tick_sessione(sessione)
        sessione.refresh_from_db()
        self.assertEqual(sessione.stato, SESSIONE_STATO_VOLO)
        self.assertEqual(
            EventoAttivoSessione.objects.filter(
                sessione=sessione, esito=EVENTO_ESITO_PENDING
            ).count(),
            1,
        )
        self.assertIsNone(genera_evento_se_dovuto(sessione))


class TimeoutEventoTests(TestCase):
    def test_evento_scaduto_aumenta_defcon(self):
        pilota = _crea_pilota()
        s = SessioneVolo.objects.create(
            pilota=pilota, stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            decollo_completato_at=timezone.now(),
        )
        ev = EventoNave.objects.create(
            nome="X", descrizione="X", codice_soluzione_esatta="A12",
            durata_base_secondi=10,
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=s, evento=ev,
            deadline_at=timezone.now() - timedelta(seconds=5),
        )
        _evento_pronto_per_test(istanza)
        tick_sessione(s)
        s.refresh_from_db()
        self.assertEqual(s.defcon, 1)


class CaEffettoGuastoTests(TestCase):
    def setUp(self):
        self.pilota = _crea_pilota()
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        self.sotto_a, _ = SottosistemaNave.objects.get_or_create(
            codice="A",
            defaults={"nome": "Manovra A", "gruppo": "Test", "ordine": 1},
        )
        self.sotto_b, _ = SottosistemaNave.objects.get_or_create(
            codice="B",
            defaults={"nome": "Sistema B", "gruppo": "Test", "ordine": 2},
        )
        self.sotto_c, _ = SottosistemaNave.objects.get_or_create(
            codice="C",
            defaults={"nome": "Sistema C", "gruppo": "Test", "ordine": 3},
        )
        for sdef in (self.sotto_a, self.sotto_b, self.sotto_c):
            StatoSottosistemaSessione.objects.get_or_create(
                sessione=self.sessione,
                sottosistema=sdef,
                defaults={"online": True},
            )

    def _istanza_ca(self, ca_effetto: dict) -> EventoAttivoSessione:
        evento = EventoNave.objects.create(
            nome="CA test",
            descrizione="Test CA",
            codice_soluzione_esatta="Z99",
            regole_json={
                "version": 3,
                "ca": {"expression": {"op": "and", "items": [{"sottosistema": "A", "op": ">", "value": 0}]}},
                "ca_effetto": ca_effetto,
            },
        )
        return EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=evento,
            deadline_at=timezone.now() + timedelta(seconds=30),
        )

    def test_ca_guasto_singolo_legacy(self):
        from pilotaggio.engine import _applica_esito_ca_da_regole

        istanza = self._istanza_ca(
            {"tipo": "guasto_sottosistema", "sottosistema_id": str(self.sotto_a.pk)}
        )
        esito, _ = _applica_esito_ca_da_regole(
            self.sessione, istanza, istanza.evento.regole_json
        )
        self.assertEqual(esito, "ca_guasto")
        stato = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_a
        )
        self.assertFalse(stato.online)
        self.sessione.refresh_from_db()
        self.assertNotEqual(self.sessione.stato, SESSIONE_STATO_CRASHED)

    def test_ca_guasto_tutti_selezionati(self):
        from pilotaggio.engine import _applica_esito_ca_da_regole

        istanza = self._istanza_ca(
            {
                "tipo": "guasto_sottosistemi",
                "modalita": "tutti",
                "sottosistema_ids": [str(self.sotto_a.pk), str(self.sotto_b.pk)],
            }
        )
        esito, _ = _applica_esito_ca_da_regole(
            self.sessione, istanza, istanza.evento.regole_json
        )
        self.assertEqual(esito, "ca_guasto")
        for sdef in (self.sotto_a, self.sotto_b):
            stato = StatoSottosistemaSessione.objects.get(
                sessione=self.sessione, sottosistema=sdef
            )
            self.assertFalse(stato.online)
        stato_c = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_c
        )
        self.assertTrue(stato_c.online)

    def test_ca_guasto_random_da_elenco(self):
        from unittest.mock import patch

        from pilotaggio.engine import _applica_esito_ca_da_regole

        stato_b = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_b
        )
        stato_c = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_c
        )
        istanza = self._istanza_ca(
            {
                "tipo": "guasto_sottosistemi",
                "modalita": "random",
                "quantita": 1,
                "sottosistema_ids": [str(self.sotto_b.pk), str(self.sotto_c.pk)],
            }
        )
        with patch(
            "pilotaggio.engine.random.sample",
            return_value=[stato_c],
        ):
            esito, _ = _applica_esito_ca_da_regole(
                self.sessione, istanza, istanza.evento.regole_json
            )
        self.assertEqual(esito, "ca_guasto")
        stato_b.refresh_from_db()
        stato_c.refresh_from_db()
        self.assertTrue(stato_b.online)
        self.assertFalse(stato_c.online)

    def test_ca_guasto_random_senza_elenco(self):
        from unittest.mock import patch

        from pilotaggio.engine import _applica_esito_ca_da_regole

        stato_a = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_a
        )
        istanza = self._istanza_ca(
            {"tipo": "guasto_sottosistemi", "modalita": "random", "quantita": 2}
        )
        with patch(
            "pilotaggio.engine.random.sample",
            side_effect=lambda pool, k: pool[:k],
        ):
            esito, _ = _applica_esito_ca_da_regole(
                self.sessione, istanza, istanza.evento.regole_json
            )
        self.assertEqual(esito, "ca_guasto")
        offline = StatoSottosistemaSessione.objects.filter(
            sessione=self.sessione, online=False
        ).count()
        self.assertEqual(offline, 2)
        stato_a.refresh_from_db()
        self.assertFalse(stato_a.online)

    def test_ca_guasto_uuid_stale_fallback_da_regola_ca(self):
        from pilotaggio.engine import _applica_esito_ca_da_regole

        istanza = self._istanza_ca(
            {
                "tipo": "guasto_sottosistema",
                "sottosistema_id": "cb6d7dd7-8ed7-4857-b859-daba2d58e439",
            }
        )
        esito, _ = _applica_esito_ca_da_regole(
            self.sessione, istanza, istanza.evento.regole_json
        )
        self.assertEqual(esito, "ca_guasto")
        stato = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_a
        )
        self.assertFalse(stato.online)
        self.sessione.refresh_from_db()
        self.assertNotEqual(self.sessione.stato, SESSIONE_STATO_CRASHED)

    def test_durata_tick_meno_n_scadenza_applica_ca_effetto(self):
        from pilotaggio.engine import valuta_evento_tick

        stato_b = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_b
        )
        evento = EventoNave.objects.create(
            nome="Scadenza critica",
            descrizione="Test",
            codice_soluzione_esatta="Z99",
            durata_tick="2",
            scadenza_critica=True,
            regole_json={
                "version": 3,
                "ca_effetto": {
                    "tipo": "guasto_sottosistemi",
                    "modalita": "tutti",
                    "sottosistema_ids": [str(self.sotto_b.pk)],
                },
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=evento,
            deadline_at=timezone.now() + timedelta(seconds=30),
            ticks_rimanenti=1,
            persiste_fino_st=True,
            precipita_a_scadenza=True,
            valutazioni_eseguite=1,
        )
        _evento_pronto_per_test(istanza)
        esito, _ = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "ca_guasto")
        istanza.refresh_from_db()
        self.assertEqual(istanza.esito, "guasto_ca")
        stato_b.refresh_from_db()
        self.assertFalse(stato_b.online)
        self.sessione.refresh_from_db()
        self.assertNotEqual(self.sessione.stato, SESSIONE_STATO_CRASHED)

    def test_ca_attiva_dal_secondo_tick(self):
        from pilotaggio.engine import valuta_evento_tick

        evento = EventoNave.objects.create(
            nome="CA immediata",
            descrizione="Test",
            codice_soluzione_esatta="Z99",
            durata_tick="4",
            scadenza_critica=True,
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "A", "op": "=", "value": 0}],
                    }
                },
                "ca_effetto": {"tipo": "precipizio"},
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=evento,
            deadline_at=timezone.now() + timedelta(seconds=80),
            ticks_rimanenti=4,
            precipita_a_scadenza=True,
        )
        _evento_pronto_per_test(istanza)
        esito, _ = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "ko")
        self.sessione.refresh_from_db()
        self.assertEqual(self.sessione.stato, SESSIONE_STATO_VOLO)

        _evento_pronto_per_test(istanza)
        esito, _ = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "ca")
        self.sessione.refresh_from_db()
        self.assertEqual(self.sessione.stato, SESSIONE_STATO_CRASHED)

    def test_st_risolve_sp_prosegue(self):
        from pilotaggio.engine import valuta_evento_tick

        evento = EventoNave.objects.create(
            nome="ST vs SP",
            descrizione="Test",
            codice_soluzione_esatta="Z99",
            durata_tick="3",
            regole_json={
                "version": 3,
                "st": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "A", "op": ">", "value": 5}],
                    }
                },
                "sp": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "A", "op": ">", "value": 2}],
                    }
                },
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=evento,
            deadline_at=timezone.now() + timedelta(seconds=60),
            ticks_rimanenti=3,
        )
        stato_a = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_a
        )
        stato_a.livello_attuale = 3
        stato_a.livello_target = 3
        stato_a.save()

        _evento_pronto_per_test(istanza)
        esito, defcon = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "sp")
        self.assertEqual(defcon, 0)
        istanza.refresh_from_db()
        self.assertEqual(istanza.esito, EVENTO_ESITO_PENDING)
        self.assertEqual(istanza.ticks_rimanenti, 2)

        stato_a.livello_attuale = 6
        stato_a.livello_target = 6
        stato_a.save()
        self.sessione.defcon = 2
        self.sessione.save()
        _evento_pronto_per_test(istanza)
        esito, defcon = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "st")
        self.assertEqual(defcon, 1)
        istanza.refresh_from_db()
        self.assertEqual(istanza.esito, EVENTO_ESITO_RISOLTO)


class TickIntervalEventoTests(TestCase):
    def test_intervallo_passa_a_tempo_risoluzione_defcon(self):
        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            tick_secondi=5,
        )
        row = StatoAllertaPilot.objects.filter(livello=0).first()
        self.assertIsNotNone(row)
        tris = int(row.tempo_risoluzione_secondi or 22)
        evento = EventoNave.objects.create(
            nome="Tick test",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
        )
        EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=60),
            ticks_rimanenti=3,
            prossima_valutazione_at=timezone.now() + timedelta(seconds=tris),
        )
        self.assertEqual(intervallo_tick_effettivo_sessione(sessione), float(tris))
        self.assertEqual(intervallo_tick_sessione(sessione), 5.0)

    def test_prima_valutazione_evento_non_prima_intervallo_defcon(self):
        from pilotaggio.engine import (
            _schedula_prossima_valutazione_evento,
            secondi_fino_prossimo_tick,
            tick_sessione_se_dovuto,
        )

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            decollo_completato_at=timezone.now(),
        )
        row = StatoAllertaPilot.objects.filter(livello=0).first()
        tris = int(row.tempo_risoluzione_secondi or 22)
        evento = EventoNave.objects.create(
            nome="Delay test",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            attivo=True,
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "Z", "op": "=", "value": 99}],
                    }
                },
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=120),
            ticks_rimanenti=3,
        )
        _schedula_prossima_valutazione_evento(istanza, sessione)
        istanza.refresh_from_db()
        sessione.ultimo_tick_motore_at = timezone.now()
        sessione.save(update_fields=["ultimo_tick_motore_at", "updated_at"])

        self.assertGreater(secondi_fino_prossimo_tick(sessione), tris - 2)
        self.assertIsNone(tick_sessione_se_dovuto(sessione))

        past = timezone.now() - timedelta(seconds=tris + 3)
        EventoAttivoSessione.objects.filter(pk=istanza.pk).update(
            created_at=past,
            reazione_fino_at=timezone.now() - timedelta(seconds=1),
            prossima_valutazione_at=timezone.now() - timedelta(seconds=1),
            valutazioni_eseguite=0,
        )
        istanza.refresh_from_db()
        tick_sessione_se_dovuto(sessione, force=False)
        istanza.refresh_from_db()
        self.assertEqual(istanza.ticks_rimanenti, 2)

    def test_evento_comparso_non_valuta_prima_tempo_defcon(self):
        from pilotaggio.engine import (
            secondi_fino_prossimo_tick,
            tick_sessione_se_dovuto,
        )

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            decollo_completato_at=timezone.now(),
        )
        row = StatoAllertaPilot.objects.filter(livello=0).first()
        tris = int(row.tempo_risoluzione_secondi or 22)
        evento = EventoNave.objects.create(
            nome="Timer reazione",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_base_secondi=20,
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "and",
                        "items": [{"sottosistema": "E", "op": "=", "value": 0}],
                    }
                },
                "ca_effetto": {"tipo": "precipizio"},
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=120),
            ticks_rimanenti=3,
            prossima_valutazione_at=timezone.now() + timedelta(seconds=tris),
            intervallo_reazione_secondi=tris,
        )
        self.assertGreater(secondi_fino_prossimo_tick(sessione), tris - 2)
        for _ in range(10):
            self.assertIsNone(tick_sessione_se_dovuto(sessione))
            sessione.refresh_from_db()
            self.assertEqual(sessione.defcon, 0)
        istanza.refresh_from_db()
        self.assertEqual(istanza.valutazioni_eseguite, 0)
        self.assertEqual(istanza.esito, EVENTO_ESITO_PENDING)

    def test_asteroide_reazione_22s_non_accorciata_se_defcon_sale(self):
        from pilotaggio.engine import (
            _programma_prossimo_check_evento,
            secondi_fino_prossimo_tick,
            tick_sessione,
            tick_sessione_se_dovuto,
        )

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            decollo_completato_at=timezone.now(),
        )
        row = StatoAllertaPilot.objects.filter(livello=0).first()
        tris = int(row.tempo_risoluzione_secondi or 22)
        evento = EventoNave.objects.create(
            nome="Asteroide test",
            descrizione="Test",
            codice_soluzione_esatta="A12",
            durata_tick="2",
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "or",
                        "items": [
                            {"sottosistema": "E", "op": "=", "value": 0},
                            {"sottosistema": "D", "op": "<", "value": 3},
                        ],
                    }
                },
                "ca_effetto": {"tipo": "precipizio"},
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            esito=EVENTO_ESITO_PENDING,
            deadline_at=timezone.now() + timedelta(seconds=120),
            ticks_rimanenti=2,
        )
        _programma_prossimo_check_evento(istanza, sessione)
        istanza.refresh_from_db()
        for code, lvl in [("E", 0), ("D", 5)]:
            sub, _ = SottosistemaNave.objects.get_or_create(
                codice=code, defaults={"nome": code, "gruppo": "T", "ordine": 1}
            )
            StatoSottosistemaSessione.objects.update_or_create(
                sessione=sessione,
                sottosistema=sub,
                defaults={
                    "online": True,
                    "livello_attuale": lvl,
                    "livello_target": lvl,
                },
            )

        sessione.defcon = 5
        sessione.save(update_fields=["defcon", "updated_at"])
        self.assertGreater(secondi_fino_prossimo_tick(sessione), tris - 2)
        for _ in range(5):
            tick_sessione(sessione)
            istanza.refresh_from_db()
            sessione.refresh_from_db()
            self.assertEqual(istanza.esito, EVENTO_ESITO_PENDING)
            self.assertEqual(sessione.defcon, 5)
        self.assertIsNone(tick_sessione_se_dovuto(sessione))

    def test_poll_e_pilot_tick_5s_non_alzano_defcon_prima_22s(self):
        """Simula console (poll) + worker pilot_tick ogni 5s: niente valutazione anticipata."""
        from pilotaggio.engine import (
            genera_evento_se_dovuto,
            tick_sessione,
            tick_sessione_se_dovuto,
        )

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            decollo_completato_at=timezone.now(),
            distanza_percorsa=50.0,
            next_event_at=timezone.now(),
        )
        evento = EventoNave.objects.filter(nome="Ammutinamento").first()
        if evento is None:
            evento = EventoNave.objects.create(
                nome="Ammutinamento test",
                descrizione="Test",
                codice_soluzione_esatta="A12",
                durata_tick="7",
                attivo=True,
                regole_json={
                    "version": 3,
                    "ca": {
                        "expression": {
                            "op": ">",
                            "value": 2,
                            "sottosistema": "S",
                        }
                    },
                    "ca_effetto": {"tipo": "precipizio"},
                },
            )
        with patch("pilotaggio.engine._scegli_evento_random", return_value=evento):
            with patch("pilotaggio.engine.random.random", return_value=0.0):
                istanza = genera_evento_se_dovuto(sessione)
        self.assertIsNotNone(istanza)
        sessione.refresh_from_db()
        defcon0 = sessione.defcon
        tris = int(
            StatoAllertaPilot.objects.filter(livello=0)
            .values_list("tempo_risoluzione_secondi", flat=True)
            .first()
            or 22
        )
        self.assertGreaterEqual(
            (istanza.prossima_valutazione_at - istanza.created_at).total_seconds(),
            tris - 1,
        )
        # 6 cicli: poll console + pilot_tick (entrambi chiamano tick_sessione_se_dovuto)
        for _ in range(6):
            tick_sessione_se_dovuto(sessione)  # poll ~3s
            tick_sessione(sessione)  # pilot_tick legacy senza throttle (non deve valutare)
            sessione.refresh_from_db()
            istanza.refresh_from_db()
            self.assertEqual(sessione.defcon, defcon0)
            self.assertEqual(istanza.valutazioni_eseguite, 0)
            self.assertEqual(istanza.esito, EVENTO_ESITO_PENDING)
            self.assertNotEqual(sessione.stato, SESSIONE_STATO_CRASHED)

    def test_primo_check_ca_non_precipita_meteore_like(self):
        from pilotaggio.engine import valuta_evento_tick

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=0,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        evento = EventoNave.objects.create(
            nome="CA a riposo",
            descrizione="Test",
            codice_soluzione_esatta="Z99",
            durata_tick="4",
            scadenza_critica=True,
            regole_json={
                "version": 3,
                "ca": {
                    "expression": {
                        "op": "or",
                        "items": [
                            {"sottosistema": "A", "op": "=", "value": 0},
                            {"sottosistema": "E", "op": "=", "value": 0},
                        ],
                    }
                },
                "ca_effetto": {"tipo": "precipizio"},
            },
        )
        istanza = EventoAttivoSessione.objects.create(
            sessione=sessione,
            evento=evento,
            deadline_at=timezone.now() + timedelta(seconds=120),
            ticks_rimanenti=4,
            precipita_a_scadenza=True,
            prossima_valutazione_at=timezone.now() - timedelta(seconds=1),
        )
        past = timezone.now() - timedelta(seconds=25)
        EventoAttivoSessione.objects.filter(pk=istanza.pk).update(created_at=past)
        istanza.refresh_from_db()
        esito, _ = valuta_evento_tick(sessione, istanza)
        sessione.refresh_from_db()
        self.assertNotEqual(sessione.stato, SESSIONE_STATO_CRASHED)
        self.assertIn(esito, {"ko", "sp", "st", "timeout", "ca_grace"})


class TickThrottleTests(TestCase):
    def test_poll_rapido_non_avanza_piu_tick(self):
        from pilotaggio.engine import (
            intervallo_tick_effettivo_sessione,
            tick_sessione_se_dovuto,
        )

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
            tick_secondi=20,
            ultimo_tick_motore_at=timezone.now(),
        )
        self.assertIsNone(tick_sessione_se_dovuto(sessione))
        sessione.refresh_from_db()
        intervallo = intervallo_tick_effettivo_sessione(sessione)
        last_before = timezone.now() - timedelta(seconds=intervallo + 1)
        sessione.ultimo_tick_motore_at = last_before
        sessione.save(update_fields=["ultimo_tick_motore_at"])
        tick_sessione_se_dovuto(sessione)
        sessione.refresh_from_db()
        self.assertGreater(sessione.ultimo_tick_motore_at, last_before)
        self.assertIsNone(tick_sessione_se_dovuto(sessione))


class StatoSessioneNaveSyncTests(TestCase):
    """La sessione attiva non deve essere sovrascritta da nave persistente stale."""

    def test_comando_console_non_revertito_da_nave_stale(self):
        import string

        from pilotaggio.engine import get_o_crea_stato_sottosistema

        used = set(SottosistemaNave.objects.values_list("codice", flat=True))
        codice = next(c for c in string.ascii_uppercase if c not in used)

        pilota = _crea_pilota()
        sessione = SessioneVolo.objects.create(
            pilota=pilota,
            stato=SESSIONE_STATO_VOLO,
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        sottos = SottosistemaNave.objects.create(codice=codice, nome="Reattore test sync")
        stato = get_o_crea_stato_sottosistema(sessione, sottos)
        stato.livello_target = 7
        stato.livello_attuale = 7
        stato.online = True
        stato.save()

        from pilotaggio.models import StatoSottosistemaNave

        nave = StatoSottosistemaNave.objects.get(sottosistema=sottos)
        StatoSottosistemaNave.objects.filter(pk=nave.pk).update(
            livello_target=0,
            livello_attuale=0,
            online=False,
            updated_at=timezone.now() + timedelta(seconds=5),
        )

        got = get_o_crea_stato_sottosistema(sessione, sottos)
        self.assertEqual(got.livello_target, 7)
        self.assertTrue(got.online)

        nave.refresh_from_db()
        self.assertEqual(nave.livello_target, 7)
        self.assertTrue(nave.online)
