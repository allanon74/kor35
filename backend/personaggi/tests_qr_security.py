"""Regressione security/LWW sui flussi QR (auth, gate minigioco, bypass null-safe)."""
from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import (
    MinigiocoQrConfig,
    Oggetto,
    Personaggio,
    QrCode,
)
from personaggi import qr_minigioco


class QrCodeDetailAuthTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="qrsec", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Sec", proprietario=self.user)
        self.qr = QrCode.objects.create()
        self.client = APIClient()

    def test_resolver_richiede_autenticazione(self):
        r = self.client.get(f"/api/personaggi/api/qrcode/{self.qr.id}/")
        self.assertIn(r.status_code, (401, 403))

    def test_resolver_autenticato_ok_su_qr_scollegato(self):
        self.client.force_authenticate(self.user)
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "qrcode_scollegato")


class AcquisisciMinigiocoGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="acqgate", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Acq", proprietario=self.user)
        self.oggetto = Oggetto.objects.create(nome="Loot Gate", testo="x")
        self.qr = QrCode.objects.create(vista=self.oggetto)
        MinigiocoQrConfig.objects.create(
            qr_code=self.qr,
            sezione_attiva=True,
            attivo=True,
            tipi_abilitati=[qr_minigioco.MINIGIOCO_TIPO_SIMON],
            difficolta=1,
            modalita_sblocco=MinigiocoQrConfig.SBLOCCO_OGNI_SCANSIONE,
        )
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_acquisisci_bloccato_senza_sessione_minigioco(self):
        r = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": self.qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(r.status_code, 400)
        # DRF ValidationError → dettaglio in non_field_errors o stringa
        blob = str(r.data).lower()
        self.assertIn("minigioco", blob)

    def test_scan_restituisce_minigioco_richiesto(self):
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "minigioco_richiesto")


class SessionBypassNullSafeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="bypass", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Bypass", proprietario=self.user)
        self.qr = QrCode.objects.create()

    def test_session_allows_bypass_null_safe(self):
        self.assertFalse(qr_minigioco.session_allows_bypass(None, self.pg, self.qr))
        self.assertFalse(qr_minigioco.session_allows_bypass("", self.pg, self.qr))
        self.assertFalse(qr_minigioco.session_allows_bypass("not-a-uuid", self.pg, self.qr))
        self.assertFalse(qr_minigioco.session_allows_bypass(self.qr.id, None, self.qr))
        self.assertFalse(qr_minigioco.session_allows_bypass(self.qr.id, self.pg, None))

    def test_messaggio_blocco_gate_minigioco(self):
        self.assertIsNone(qr_minigioco.messaggio_blocco_gate_minigioco(None))
        self.assertIn(
            "Completa",
            qr_minigioco.messaggio_blocco_gate_minigioco(
                {"tipo_modello": "minigioco_richiesto"}
            ),
        )
        self.assertEqual(
            qr_minigioco.messaggio_blocco_gate_minigioco(
                {"tipo_modello": "minigioco_bloccato", "messaggio": "nope"}
            ),
            "nope",
        )
        self.assertEqual(
            qr_minigioco.messaggio_blocco_gate_minigioco({"blocked": True, "error": "x"}),
            "x",
        )
