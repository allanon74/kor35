"""Console comunicazioni: allarme, dipartimento, grazia CA."""
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone
from rest_framework.test import APIClient

from django.test import TestCase

from pilotaggio.allarme_equipaggio import ALLARME_EQUIPAGGIO_AMBRA, ALLARME_EQUIPAGGIO_ROSSO
from personaggi.models import (
    Carriera,
    PersonaggioCarrieraMembership,
    TipoCarriera,
)
from pilotaggio.comunicazioni import applica_grazia_colore, integra_elenco_guasti, render_messaggio
from pilotaggio.engine import valuta_evento_tick
from pilotaggio.models import (
    EVENTO_ESITO_PENDING,
    EventoAttivoSessione,
    EventoNave,
    PilotConsoleToken,
    PilotRuntimeConfig,
    ProtocolloComunicazione,
    SESSIONE_STATO_VOLO,
    SessioneVolo,
    SottosistemaNave,
    StatoSottosistemaSessione,
)
from pilotaggio.tests.test_engine import _evento_pronto_per_test
from pilotaggio.tests.test_views import _crea_pilota_con_0pi


class ComunicazioniAllarmeTests(TestCase):
    def setUp(self):
        self.user, self.pilota = _crea_pilota_con_0pi(nome="Radio", valore_0pi=1)
        self.sessione = SessioneVolo.objects.create(
            pilota=self.pilota,
            stato=SESSIONE_STATO_VOLO,
            defcon=1,
            decollo_completato_at=timezone.now(),
            durata_pianificata_secondi=600,
            started_at=timezone.now(),
        )
        self.token = PilotConsoleToken.objects.create(
            pilota=self.pilota, token=PilotConsoleToken.genera_token()
        )
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"PilotToken {self.token.token}")
        cfg = PilotRuntimeConfig.get_solo()
        cfg.comunicazioni_console_abilitata = True
        cfg.save(update_fields=["comunicazioni_console_abilitata", "updated_at"])
        tipo, _ = TipoCarriera.objects.get_or_create(
            codice="korp", defaults={"nome": "KORP"}
        )
        korp = Carriera.objects.create(
            nome="Ingegneria", tipo="T3", tipo_carriera=tipo
        )
        self.korp = korp
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pilota,
            carriera=korp,
            tipo_carriera=tipo,
        )
        self.sotto = SottosistemaNave.objects.create(codice="P", nome="Propulsore")
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione, sottosistema=self.sotto, online=False
        )
        self.evento = EventoNave.objects.create(
            nome="Falla",
            descrizione="Perdita.",
            codice_soluzione_esatta="A12",
            allarme_richiesto=ALLARME_EQUIPAGGIO_AMBRA,
        )
        self.istanza = EventoAttivoSessione.objects.create(
            sessione=self.sessione,
            evento=self.evento,
            deadline_at=timezone.now() + timedelta(minutes=5),
            esito=EVENTO_ESITO_PENDING,
            valutazioni_eseguite=0,
            reazione_fino_at=timezone.now() + timedelta(seconds=30),
            prossima_valutazione_at=timezone.now() + timedelta(seconds=30),
        )
        ProtocolloComunicazione.objects.create(
            colore=ALLARME_EQUIPAGGIO_AMBRA,
            korp=self.korp,
            testo="Riparare {sottosistema} durante {evento}.",
            testo_audio="Tecnici su {sottosistema}.",
        )

    def test_messaggio_sostituisce_sottosistema(self):
        testo = render_messaggio("Guasto: {sottosistema}", self.sessione, "Falla")
        self.assertIn("Propulsore", testo)

    def test_dichiara_ambra_avvisa_e_arma_grazia(self):
        with patch("personaggi.notify.notify_users", return_value=1) as notify:
            res = self.client.post(
                "/api/pilot/session/allarme-equipaggio/",
                {"allarme": ALLARME_EQUIPAGGIO_AMBRA},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["allarme_equipaggio"], ALLARME_EQUIPAGGIO_AMBRA)
        self.assertIn("Propulsore", body["announcement"])
        self.assertIn("Propulsore", body["messaggio_dipartimento"])
        self.assertEqual(body["dipartimento"], "Ingegneria")
        self.assertEqual(body["inviati"], 1)
        self.assertTrue(body["grazia_ca"])
        notify.assert_called_once()
        self.istanza.refresh_from_db()
        self.assertTrue(self.istanza.ca_soppressa_comunicazioni)
        self.sessione.refresh_from_db()
        self.assertIn("Propulsore", self.sessione.allarme_annuncio)

    def test_ambra_nomina_i_guasti_anche_senza_segnaposto(self):
        ProtocolloComunicazione.objects.filter(colore=ALLARME_EQUIPAGGIO_AMBRA).update(
            testo="Squadra tecnica in sala macchine.",
            testo_audio="Allarme Ambra.",
        )
        SottosistemaNave.objects.create(codice="S", nome="Scudi")
        scudi = SottosistemaNave.objects.get(codice="S")
        StatoSottosistemaSessione.objects.create(
            sessione=self.sessione, sottosistema=scudi, online=False
        )
        with patch("personaggi.notify.notify_users", return_value=1) as notify:
            res = self.client.post(
                "/api/pilot/session/allarme-equipaggio/",
                {"allarme": ALLARME_EQUIPAGGIO_AMBRA},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        for nome in ("Propulsore", "Scudi"):
            self.assertIn(nome, body["messaggio_dipartimento"])
            self.assertIn(nome, body["announcement"])
        self.assertIn("Sottosistemi guasti:", body["messaggio_dipartimento"])
        notify.assert_called_once()
        _args, kwargs = notify.call_args
        self.assertIn("Propulsore", kwargs["body"])
        self.assertIn("Scudi", kwargs["body"])

    def test_elenco_gia_presente_non_si_duplica(self):
        testo = integra_elenco_guasti("Riparare Propulsore.", "Propulsore")
        self.assertEqual(testo, "Riparare Propulsore.")

    def test_colore_sbagliato_non_arma_grazia(self):
        self.assertFalse(applica_grazia_colore(self.sessione, ALLARME_EQUIPAGGIO_ROSSO))
        self.istanza.refresh_from_db()
        self.assertFalse(self.istanza.ca_soppressa_comunicazioni)

    def test_dopo_reazione_niente_grazia(self):
        self.istanza.reazione_fino_at = timezone.now() - timedelta(seconds=1)
        self.istanza.save(update_fields=["reazione_fino_at", "updated_at"])
        self.assertFalse(applica_grazia_colore(self.sessione, ALLARME_EQUIPAGGIO_AMBRA))

    def test_console_spenta_non_invia_il_dipartimento(self):
        cfg = PilotRuntimeConfig.get_solo()
        cfg.comunicazioni_console_abilitata = False
        cfg.save(update_fields=["comunicazioni_console_abilitata", "updated_at"])
        with patch("personaggi.notify.notify_users", return_value=1) as notify:
            res = self.client.post(
                "/api/pilot/session/allarme-equipaggio/",
                {"allarme": ALLARME_EQUIPAGGIO_AMBRA},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertNotIn("messaggio_dipartimento", res.json())
        notify.assert_not_called()

    def test_grazia_salta_il_primo_controllo_ca(self):
        self.istanza.ca_soppressa_comunicazioni = True
        self.istanza.valutazioni_eseguite = 1
        self.istanza.save(
            update_fields=["ca_soppressa_comunicazioni", "valutazioni_eseguite", "updated_at"]
        )
        _evento_pronto_per_test(self.istanza)
        with patch("pilotaggio.engine._eval_outcome_regole", return_value=True):
            esito, _defcon = valuta_evento_tick(self.sessione, self.istanza)
        self.assertEqual(esito, "ca_soppressa_comunicazioni")
        self.istanza.refresh_from_db()
        self.assertFalse(self.istanza.ca_soppressa_comunicazioni)
