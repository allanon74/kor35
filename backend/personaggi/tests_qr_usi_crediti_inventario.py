"""
Test QR: usi limitati/illimitati, credito deposito, regole inventario QR.
"""
from datetime import date, timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import (
    AURA,
    ConsumabileInInventario,
    Inventario,
    Oggetto,
    OggettoBase,
    OggettoInInventario,
    Personaggio,
    Punteggio,
    QrCode,
    QrCreditoDeposito,
    Tessitura,
    TIPO_OGGETTO_FISICO,
)
from personaggi.economia_crediti import saldo_deposito


class QrUsiAcquisizioneTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="usi_user", password="pass")
        self.client.force_authenticate(self.user)
        self.pg = Personaggio.objects.create(nome="PG Usi", proprietario=self.user)
        self.user2 = User.objects.create_user(username="usi_user2", password="pass")
        self.pg2 = Personaggio.objects.create(nome="PG Usi 2", proprietario=self.user2)
        self.aura = Punteggio.objects.create(nome="Aura Test Usi", sigla="ATU", tipo=AURA)

    def _tessitura_qr(self, *, usi_max):
        t = Tessitura.objects.create(
            nome="Tess Usi", testo="x", formula="test", aura_richiesta=self.aura
        )
        qr = QrCode.objects.create(vista=t, usi_max=usi_max, usi_consumati=0)
        return t, qr

    def test_usi_max_1_svuota_dopo_acquisizione(self):
        t, qr = self._tessitura_qr(usi_max=1)
        r = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        qr.refresh_from_db()
        self.assertIsNone(qr.vista_id)
        self.assertEqual(qr.usi_consumati, 1)
        self.assertTrue(self.pg.tessiture_possedute.filter(pk=t.pk).exists())

    def test_usi_illimitati_non_svuota(self):
        t, qr = self._tessitura_qr(usi_max=None)
        r1 = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(r1.status_code, 200, r1.data)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, t.pk)
        self.assertEqual(qr.usi_consumati, 1)

        self.client.force_authenticate(self.user2)
        r2 = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": qr.id, "personaggio_id": self.pg2.id},
            format="json",
        )
        self.assertEqual(r2.status_code, 200, r2.data)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, t.pk)
        self.assertEqual(qr.usi_consumati, 2)
        self.assertTrue(self.pg2.tessiture_possedute.filter(pk=t.pk).exists())

    def test_oggetto_multi_uso_clona(self):
        obj = Oggetto.objects.create(nome="Loot", tipo_oggetto=TIPO_OGGETTO_FISICO)
        qr = QrCode.objects.create(vista=obj, usi_max=2, usi_consumati=0)
        r = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": qr.id, "personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, obj.pk)
        self.assertEqual(qr.usi_consumati, 1)
        # Clone nell'inventario PG, template ancora sul QR
        self.assertIsNone(obj.inventario_corrente)
        self.assertEqual(self.pg.get_oggetti().filter(nome="Loot").count(), 1)

        self.client.force_authenticate(self.user2)
        r2 = self.client.post(
            "/api/personaggi/api/transazioni/acquisisci/",
            {"qrcode_id": qr.id, "personaggio_id": self.pg2.id},
            format="json",
        )
        self.assertEqual(r2.status_code, 200, r2.data)
        qr.refresh_from_db()
        self.assertIsNone(qr.vista_id)
        self.assertEqual(obj.inventario_corrente, self.pg2.inventario_ptr)


class QrCreditoDepositoTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="cred_user", password="pass")
        self.client.force_authenticate(self.user)
        self.pg = Personaggio.objects.create(nome="PG Cred", proprietario=self.user)

    def test_credito_fisso_e_usi(self):
        qr = QrCode.objects.create(usi_max=1, usi_consumati=0)
        cfg = QrCreditoDeposito.objects.create(
            nome="Borsa",
            importo_min=Decimal("10.00"),
            importo_max=Decimal("10.00"),
            qr_code=qr,
        )
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(r.data["tipo_modello"], "credito_deposito")
        self.assertEqual(Decimal(r.data["dati"]["importo"]), Decimal("10.00"))
        self.assertEqual(saldo_deposito(self.pg), Decimal("10.00"))
        cfg.refresh_from_db()
        self.assertIsNone(cfg.qr_code_id)

    def test_credito_illimitato(self):
        qr = QrCode.objects.create(usi_max=None, usi_consumati=0)
        QrCreditoDeposito.objects.create(
            nome="Fontana",
            importo_min=Decimal("1.00"),
            importo_max=Decimal("1.00"),
            qr_code=qr,
        )
        for _ in range(3):
            r = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
            self.assertEqual(r.status_code, 200, r.data)
        self.assertEqual(saldo_deposito(self.pg), Decimal("3.00"))
        qr.refresh_from_db()
        self.assertEqual(qr.usi_consumati, 3)
        self.assertTrue(QrCreditoDeposito.objects.filter(qr_code=qr).exists())


class InventarioQrVisibilitaTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(username="inv_user", password="pass")
        self.client.force_authenticate(self.user)
        self.pg = Personaggio.objects.create(nome="PG Inv", proprietario=self.user)
        self.ams = Punteggio.objects.create(nome="Aura Mondana", sigla="AMS", tipo=AURA)
        self.aura_obj = Punteggio.objects.create(nome="Aureola", sigla="AUR", tipo=AURA)
        self.inv = Inventario.objects.create(
            nome="Cassa", testo="", crediti_deposito_contenuti=Decimal("25.00")
        )
        self.qr = QrCode.objects.create(vista=self.inv)

    def _conferma_inventario(self):
        from personaggi.models import INVENTARIO_QR_ATTESA_SECONDI, QrInventarioScanSession
        from django.utils import timezone

        r1 = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "inventario_attesa_conferma")
        sess = QrInventarioScanSession.objects.filter(qr_code=self.qr).first()
        sess.first_scan_at = timezone.now() - timedelta(seconds=INVENTARIO_QR_ATTESA_SECONDI + 1)
        sess.save(update_fields=["first_scan_at", "updated_at"])
        r2 = self.client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r2.status_code, 200, r2.data)
        self.assertEqual(r2.data["tipo_modello"], "inventario")
        return r2

    def test_oggetto_base_sempre_visibile_e_prendibile(self):
        tpl = OggettoBase.objects.create(nome="Coltello", tipo_oggetto=TIPO_OGGETTO_FISICO, costo=1)
        og = Oggetto.objects.create(
            nome="Coltello",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            oggetto_base_generatore=tpl,
        )
        OggettoInInventario.objects.create(oggetto=og, inventario=self.inv)
        r = self._conferma_inventario()
        ids = [o["id"] for o in r.data["dati"]["oggetti"]]
        self.assertIn(og.id, ids)
        row = next(o for o in r.data["dati"]["oggetti"] if o["id"] == og.id)
        self.assertTrue(row["puo_prendere"])

        with patch("personaggi.transazioni_evento.gioco_live_consentito", return_value=True):
            take = self.client.post(
                "/api/personaggi/api/inventario-qr/prendi/",
                {
                    "personaggio_id": self.pg.id,
                    "inventario_id": self.inv.id,
                    "tipo": "oggetto",
                    "oggetto_id": og.id,
                },
                format="json",
            )
        self.assertEqual(take.status_code, 200, take.data)
        og.refresh_from_db()
        self.assertEqual(og.inventario_corrente, self.pg.inventario_ptr)

    def test_craftato_nascosto_senza_ams(self):
        og = Oggetto.objects.create(
            nome="Reliquia",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            aura=self.aura_obj,
        )
        OggettoInInventario.objects.create(oggetto=og, inventario=self.inv)
        r = self._conferma_inventario()
        ids = [o["id"] for o in r.data["dati"]["oggetti"]]
        self.assertNotIn(og.id, ids)

    def test_prendi_crediti_e_consumabile(self):
        cons = ConsumabileInInventario.objects.create(
            inventario=self.inv,
            nome="Pozione",
            descrizione="cura",
            utilizzi_rimanenti=2,
            data_scadenza=date.today() + timedelta(days=10),
        )
        self._conferma_inventario()
        with patch("personaggi.transazioni_evento.gioco_live_consentito", return_value=True):
            r_cred = self.client.post(
                "/api/personaggi/api/inventario-qr/prendi/",
                {
                    "personaggio_id": self.pg.id,
                    "inventario_id": self.inv.id,
                    "tipo": "crediti",
                },
                format="json",
            )
            self.assertEqual(r_cred.status_code, 200, r_cred.data)
            self.assertEqual(saldo_deposito(self.pg), Decimal("25.00"))
            self.inv.refresh_from_db()
            self.assertEqual(self.inv.crediti_deposito_contenuti, Decimal("0"))

            r_cons = self.client.post(
                "/api/personaggi/api/inventario-qr/prendi/",
                {
                    "personaggio_id": self.pg.id,
                    "inventario_id": self.inv.id,
                    "tipo": "consumabile",
                    "consumabile_id": str(cons.id),
                },
                format="json",
            )
        self.assertEqual(r_cons.status_code, 200, r_cons.data)
        self.assertFalse(ConsumabileInInventario.objects.filter(pk=cons.pk).exists())
        self.assertTrue(self.pg.consumabili.filter(nome="Pozione").exists())


class AssociaQrUsiMaxTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_superuser(username="staff", password="pass", email="s@t.it")
        self.client.force_authenticate(self.user)
        self.aura = Punteggio.objects.create(nome="Aura Staff", sigla="AST", tipo=AURA)

    def test_associa_con_usi_max_null_illimitato(self):
        t = Tessitura.objects.create(nome="T", testo="", formula="x", aura_richiesta=self.aura)
        qr = QrCode.objects.create()
        r = self.client.post(
            f"/api/personaggi/api/a-vista/{t.pk}/associa-qr/",
            {"qr_id": qr.id, "usi_max": None},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        qr.refresh_from_db()
        self.assertEqual(qr.vista_id, t.pk)
        self.assertIsNone(qr.usi_max)
        self.assertEqual(qr.usi_consumati, 0)

    def test_associa_con_usi_max_3(self):
        t = Tessitura.objects.create(nome="T2", testo="", formula="x", aura_richiesta=self.aura)
        qr = QrCode.objects.create()
        r = self.client.post(
            f"/api/personaggi/api/a-vista/{t.pk}/associa-qr/",
            {"qr_id": qr.id, "usi_max": 3},
            format="json",
        )
        self.assertEqual(r.status_code, 200, r.data)
        qr.refresh_from_db()
        self.assertEqual(qr.usi_max, 3)
