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
    ComandoCriticoGlobale,
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

    def test_durata_tick_meno_n_scadenza_applica_ca_effetto(self):
        from pilotaggio.engine import valuta_evento_tick

        stato_b = StatoSottosistemaSessione.objects.get(
            sessione=self.sessione, sottosistema=self.sotto_b
        )
        evento = EventoNave.objects.create(
            nome="Scadenza -N",
            descrizione="Test",
            codice_soluzione_esatta="Z99",
            durata_tick="-2",
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
        )
        esito, _ = valuta_evento_tick(self.sessione, istanza)
        self.assertEqual(esito, "ca_guasto")
        istanza.refresh_from_db()
        self.assertEqual(istanza.esito, "guasto_ca")
        stato_b.refresh_from_db()
        self.assertFalse(stato_b.online)
        self.sessione.refresh_from_db()
        self.assertNotEqual(self.sessione.stato, SESSIONE_STATO_CRASHED)
