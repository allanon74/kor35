"""Console comunicazioni: allarme, dipartimento, grazia CA."""
import tempfile
from datetime import timedelta
from unittest.mock import patch

from django.core.files.storage import default_storage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test.utils import override_settings
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
from pilotaggio.serializers import ProtocolloComunicazioneSerializer
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
        self.sotto, _ = SottosistemaNave.objects.get_or_create(
            codice="P", defaults={"nome": "Propulsore"}
        )
        if self.sotto.nome != "Propulsore":
            self.sotto.nome = "Propulsore"
            self.sotto.save(update_fields=["nome", "updated_at"])
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
        scudi, _ = SottosistemaNave.objects.get_or_create(
            codice="S", defaults={"nome": "Scudi"}
        )
        if scudi.nome != "Scudi":
            scudi.nome = "Scudi"
            scudi.save(update_fields=["nome", "updated_at"])
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

    def test_dipartimento_non_korp_riceve_il_messaggio(self):
        tipo, _ = TipoCarriera.objects.get_or_create(
            codice="dipartimento", defaults={"nome": "Dipartimento"}
        )
        medico = Carriera.objects.create(
            nome="Medica", tipo="T3", tipo_carriera=tipo
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.pilota,
            carriera=medico,
            tipo_carriera=tipo,
        )
        ProtocolloComunicazione.objects.create(
            colore="bianco",
            korp=medico,
            testo="Infermeria, intervento.",
        )
        with patch("personaggi.notify.notify_users", return_value=1) as notify:
            res = self.client.post(
                "/api/pilot/session/allarme-equipaggio/",
                {"allarme": "bianco"},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        body = res.json()
        self.assertEqual(body["dipartimento"], "Medica")
        self.assertEqual(body["inviati"], 1)
        notify.assert_called_once()

    def test_professione_non_e_un_destinatario(self):
        tipo, _ = TipoCarriera.objects.get_or_create(
            codice="professione", defaults={"nome": "Professione"}
        )
        mestiere = Carriera.objects.create(
            nome="Cuoco", tipo="T3", tipo_carriera=tipo
        )
        ser = ProtocolloComunicazioneSerializer(data={
            "colore": "blu",
            "korp": str(mestiere.pk),
            "testo": "no",
        })
        self.assertFalse(ser.is_valid())
        self.assertIn("korp", ser.errors)

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

    def test_campione_caricato_finisce_nello_stato_e_si_sostituisce(self):
        media = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media):
            proto = ProtocolloComunicazione.objects.get(colore=ALLARME_EQUIPAGGIO_AMBRA)
            primo = SimpleUploadedFile("sirena.mp3", b"ID3fake", content_type="audio/mpeg")
            ser = ProtocolloComunicazioneSerializer(
                proto, data={"campione": primo}, partial=True
            )
            self.assertTrue(ser.is_valid(), ser.errors)
            ser.save()
            proto.refresh_from_db()
            self.assertTrue(proto.campione.name.endswith("ambra.mp3"))

            with patch("personaggi.notify.notify_users", return_value=1):
                res = self.client.post(
                    "/api/pilot/session/allarme-equipaggio/",
                    {"allarme": ALLARME_EQUIPAGGIO_AMBRA},
                    format="json",
                )
            self.assertEqual(res.status_code, 200, res.content)
            url = res.json()["allarme_campione_url"]
            self.assertIn("/media/pilotaggio/allarmi/ambra.mp3", url)
            self.assertIn("v=", url)

            secondo = SimpleUploadedFile("altro.wav", b"RIFFxxxx", content_type="audio/wav")
            ser = ProtocolloComunicazioneSerializer(
                proto, data={"campione": secondo}, partial=True
            )
            self.assertTrue(ser.is_valid(), ser.errors)
            ser.save()
            proto.refresh_from_db()
            self.assertTrue(proto.campione.name.endswith("ambra.wav"))
            self.assertFalse(default_storage.exists("pilotaggio/allarmi/ambra.mp3"))

            ser = ProtocolloComunicazioneSerializer(
                proto, data={"rimuovi_campione": True}, partial=True
            )
            self.assertTrue(ser.is_valid(), ser.errors)
            ser.save()
            proto.refresh_from_db()
            self.assertFalse(proto.campione)
            self.assertFalse(default_storage.exists("pilotaggio/allarmi/ambra.wav"))

    def test_campione_rifiuta_estensione(self):
        proto = ProtocolloComunicazione.objects.get(colore=ALLARME_EQUIPAGGIO_AMBRA)
        ser = ProtocolloComunicazioneSerializer(
            proto,
            data={"campione": SimpleUploadedFile("nota.txt", b"no", content_type="text/plain")},
            partial=True,
        )
        self.assertFalse(ser.is_valid())

    def test_staff_crea_protocollo_senza_rimuovi_campione(self):
        """
        POST staff senza campione non deve 500: rimuovi_campione non va a Model.create.
        """
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff = User.objects.create_user(
            username="staff_allarmi", password="x", is_staff=True, is_superuser=True
        )
        client = APIClient()
        client.force_authenticate(user=staff)
        res = client.post(
            "/api/pilot/staff/protocolli-comunicazione/",
            {
                "colore": "giallo",
                "testo_audio": "Allarme giallo di prova.",
                "testo": "",
                "attivo": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        body = res.json()
        self.assertEqual(body["colore"], "giallo")
        self.assertEqual(body["campione_url"], "")

    def test_staff_carica_campione_su_protocollo_nuovo(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff = User.objects.create_user(
            username="staff_allarmi2", password="x", is_staff=True, is_superuser=True
        )
        client = APIClient()
        client.force_authenticate(user=staff)
        media = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media):
            res = client.post(
                "/api/pilot/staff/protocolli-comunicazione/",
                {
                    "colore": "rosso",
                    "testo_audio": "Allarme rosso.",
                    "attivo": True,
                },
                format="json",
            )
            self.assertEqual(res.status_code, 201, res.content)
            proto_id = res.json()["id"]
            audio = SimpleUploadedFile(
                "sirena.mp3", b"ID3fake", content_type="audio/mpeg"
            )
            res2 = client.patch(
                f"/api/pilot/staff/protocolli-comunicazione/{proto_id}/",
                {"campione": audio},
                format="multipart",
            )
            self.assertEqual(res2.status_code, 200, res2.content)
            self.assertIn("/media/pilotaggio/allarmi/rosso.mp3", res2.json()["campione_url"])
            proto = ProtocolloComunicazione.objects.get(pk=proto_id)
            self.assertTrue(proto.campione.name.endswith("rosso.mp3"))

    def test_quadro_espone_ordine_layout(self):
        ProtocolloComunicazione.objects.filter(colore=ALLARME_EQUIPAGGIO_AMBRA).update(
            ordine=5
        )
        ProtocolloComunicazione.objects.create(
            colore=ALLARME_EQUIPAGGIO_ROSSO,
            testo_audio="Rosso.",
            ordine=90,
            attivo=True,
        )
        res = self.client.get("/api/pilot/comunicazioni/quadro/")
        self.assertEqual(res.status_code, 200, res.content)
        by_colore = {row["colore"]: row for row in res.json()["protocolli"]}
        self.assertEqual(by_colore[ALLARME_EQUIPAGGIO_AMBRA]["ordine"], 5)
        self.assertEqual(by_colore[ALLARME_EQUIPAGGIO_ROSSO]["ordine"], 90)

    def test_staff_salva_ordine_protocollo(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        staff = User.objects.create_user(
            username="staff_ordine", password="x", is_staff=True, is_superuser=True
        )
        client = APIClient()
        client.force_authenticate(user=staff)
        proto = ProtocolloComunicazione.objects.get(colore=ALLARME_EQUIPAGGIO_AMBRA)
        res = client.patch(
            f"/api/pilot/staff/protocolli-comunicazione/{proto.pk}/",
            {"ordine": 42},
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["ordine"], 42)
        proto.refresh_from_db()
        self.assertEqual(proto.ordine, 42)

    def test_sync_serializza_campione_come_path(self):
        """Config allarmi (incluso path audio) entra nel payload edge sync."""
        from kor35.sync_tombstone import get_sync_model_registry
        from kor35.syncing import serialize_for_sync

        self.assertIn(
            "pilotaggio.protocollocomunicazione",
            get_sync_model_registry(),
        )
        media = tempfile.mkdtemp()
        with override_settings(MEDIA_ROOT=media):
            proto = ProtocolloComunicazione.objects.get(colore=ALLARME_EQUIPAGGIO_AMBRA)
            proto.ordine = 33
            audio = SimpleUploadedFile(
                "sirena.mp3", b"ID3fake", content_type="audio/mpeg"
            )
            ser = ProtocolloComunicazioneSerializer(
                proto, data={"campione": audio, "ordine": 33}, partial=True
            )
            self.assertTrue(ser.is_valid(), ser.errors)
            ser.save()
            proto.refresh_from_db()
            row = serialize_for_sync(proto)
            self.assertEqual(row["ordine"], 33)
            self.assertEqual(row["campione"], "pilotaggio/allarmi/ambra.mp3")
            self.assertTrue(row["sync_id"])
            self.assertTrue(row["updated_at"])

    def test_senza_campione_lo_stato_non_ha_url(self):
        with patch("personaggi.notify.notify_users", return_value=0):
            res = self.client.post(
                "/api/pilot/session/allarme-equipaggio/",
                {"allarme": ALLARME_EQUIPAGGIO_AMBRA},
                format="json",
            )
        self.assertEqual(res.status_code, 200, res.content)
        self.assertEqual(res.json()["allarme_campione_url"], "")

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
