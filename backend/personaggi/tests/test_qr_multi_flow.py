"""
Test minimi per flussi QR: manifesto con requisiti, inventario doppia scansione.
"""
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from personaggi.models import (
    Manifesto,
    Inventario,
    Nodo,
    Era,
    QrCode,
    Personaggio,
    QrInventarioScanSession,
    INVENTARIO_QR_ATTESA_SECONDI,
)


class QrManifestoInventarioTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="qruser", password="pass")
        self.client.force_authenticate(self.user)
        self.pg = Personaggio.objects.create(
            nome="PG QR",
            proprietario=self.user,
        )

    def test_manifesto_accesso_libero(self):
        m = Manifesto.objects.create(nome="M1", testo="<p>Ciao</p>", requisiti_lettura=[])
        qr = QrCode.objects.create(vista=m)
        r = self.client.get(f"/api/personaggi/api/qrcode/{qr.id}/", {"personaggio_id": self.pg.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "manifesto")
        self.assertTrue(r.data["dati"].get("puo_leggere", True))
        self.assertIsNotNone(r.data["dati"].get("testo"))

    def test_inventario_doppia_scansione(self):
        inv = Inventario.objects.create(nome="Inv QR", testo="")
        qr = QrCode.objects.create(vista=inv)
        r1 = self.client.get(f"/api/personaggi/api/qrcode/{qr.id}/", {"personaggio_id": self.pg.id})
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "inventario_attesa_conferma")

        with patch("django.utils.timezone.now", return_value=timezone.now() + timedelta(seconds=INVENTARIO_QR_ATTESA_SECONDI + 1)):
            r2 = self.client.get(f"/api/personaggi/api/qrcode/{qr.id}/", {"personaggio_id": self.pg.id})
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "inventario")
        self.assertTrue(r2.data["dati"].get("inventario_qr_confermato"))

        self.assertEqual(QrInventarioScanSession.objects.filter(confermato_at__isnull=False).count(), 1)

    def test_nodo_scan_imposta_cooldown_e_reward(self):
        era = Era.objects.create(nome="Eroi", abbreviazione="eroi")
        self.pg.era = era
        self.pg.save(update_fields=["era"])
        nodo = Nodo.objects.create(nome="Nodo 1", testo="", tipo_nodo="MIN")
        qr = QrCode.objects.create(vista=nodo)

        r = self.client.get(f"/api/personaggi/api/qrcode/{qr.id}/", {"personaggio_id": self.pg.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "nodo")
        self.assertIsNotNone(r.data["dati"].get("cooldown_until"))
