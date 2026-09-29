"""Inventario serie: eventi, duplicati, trasferimento, reset staff."""
from datetime import timedelta

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from gestione_plot.models import Evento
from personaggi.models import (
    Personaggio,
    QrCode,
    SerieAssegnazione,
    SerieCollezione,
    SerieQr,
)
from personaggi import qr_random_pool


class SerieInventarioApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="serieinv", password="pass")
        self.user2 = User.objects.create_user(username="serieinv2", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Serie", proprietario=self.user)
        self.pg2 = Personaggio.objects.create(nome="PG Dest", proprietario=self.user2)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def _serie_con_qr(self, *, totale=2, ammetti_duplicati=False):
        serie = SerieCollezione.objects.create(
            nome="Pecora",
            totale=totale,
            ammetti_duplicati=ammetti_duplicati,
        )
        qr = QrCode.objects.create()
        SerieQr.objects.create(nome="QR Pecora", serie=serie, qr_code=qr)
        return serie, qr

    def test_scan_mette_in_inventario_serie_non_zaino(self):
        serie, qr = self._serie_con_qr()
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "serie")
        self.assertTrue(r.data["dati"].get("in_inventario_serie"))
        ass = SerieAssegnazione.objects.get(serie=serie)
        self.assertEqual(ass.personaggio_id, self.pg.id)
        # Non nello zaino generico
        if ass.oggetto_id:
            self.assertIsNone(ass.oggetto.inventario_corrente)

        inv = self.client.get(
            "/api/personaggi/api/serie-inventario/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(inv.status_code, 200)
        self.assertEqual(len(inv.data["serie"]), 1)
        self.assertEqual(inv.data["serie"][0]["pezzi"][0]["indice"], ass.indice)

    def test_trasferimento_tra_pg(self):
        serie, qr = self._serie_con_qr()
        self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        ass = SerieAssegnazione.objects.get(serie=serie)
        r = self.client.post(
            f"/api/personaggi/api/serie-inventario/{ass.pk}/trasferisci/",
            {
                "personaggio_id": self.pg.id,
                "destinatario_personaggio_id": self.pg2.id,
            },
            format="json",
        )
        self.assertEqual(r.status_code, 200)
        ass.refresh_from_db()
        self.assertEqual(ass.personaggio_id, self.pg2.id)

        inv1 = self.client.get(
            "/api/personaggi/api/serie-inventario/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(inv1.data["serie"], [])

        client2 = APIClient()
        client2.force_authenticate(self.user2)
        inv2 = client2.get(
            "/api/personaggi/api/serie-inventario/",
            {"personaggio_id": self.pg2.id},
        )
        self.assertEqual(len(inv2.data["serie"][0]["pezzi"]), 1)

    def test_evento_chiuso_nasconde_inventario(self):
        serie, qr = self._serie_con_qr()
        ev = Evento.objects.create(
            titolo="Evento serie",
            data_inizio=timezone.now(),
            data_fine=timezone.now() + timedelta(days=1),
        )
        serie.eventi.add(ev)
        self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        inv_open = self.client.get(
            "/api/personaggi/api/serie-inventario/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(len(inv_open.data["serie"]), 1)

        ev.ended_at = timezone.now()
        ev.save(update_fields=["ended_at"])
        inv_closed = self.client.get(
            "/api/personaggi/api/serie-inventario/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(inv_closed.data["serie"], [])

    def test_ammetti_duplicati_stesso_qr_due_pg(self):
        serie, qr = self._serie_con_qr(totale=1, ammetti_duplicati=True)
        r1 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "serie")

        client2 = APIClient()
        client2.force_authenticate(self.user2)
        # pg2 owned by user2 — need pg under user2
        pg_b = Personaggio.objects.create(nome="PG B", proprietario=self.user2)
        r2 = client2.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": pg_b.id},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "serie")
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 2)
        # stesso indice possibile
        indici = list(
            SerieAssegnazione.objects.filter(serie=serie).values_list("indice", flat=True)
        )
        self.assertEqual(indici, [1, 1])


class SerieResetStaffTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="seriestaff", password="pass", email="s@test.it"
        )
        self.pg = Personaggio.objects.create(nome="PG", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_stato_e_reset(self):
        serie = SerieCollezione.objects.create(nome="ResetMe", totale=2)
        qr1 = QrCode.objects.create()
        qr2 = QrCode.objects.create()
        SerieQr.objects.create(nome="A", serie=serie, qr_code=qr1)
        SerieQr.objects.create(nome="B", serie=serie, qr_code=qr2)
        self.client.get(
            f"/api/personaggi/api/qrcode/{qr1.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.client.get(
            f"/api/personaggi/api/qrcode/{qr2.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 2)

        stato = self.client.get(
            f"/api/personaggi/api/staff/serie-collezioni/{serie.pk}/stato/"
        )
        self.assertEqual(stato.status_code, 200)
        self.assertEqual(stato.data["pezzi_assegnati"], 2)
        self.assertEqual(len(stato.data["per_personaggio"]), 1)

        bad = self.client.post(
            f"/api/personaggi/api/staff/serie-collezioni/{serie.pk}/reset/",
            {},
            format="json",
        )
        self.assertEqual(bad.status_code, 400)

        ok = self.client.post(
            f"/api/personaggi/api/staff/serie-collezioni/{serie.pk}/reset/",
            {"conferma": True},
            format="json",
        )
        self.assertEqual(ok.status_code, 200)
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 0)
        # Dopo reset si può riconsegnare
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr1.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "serie")
        self.assertFalse(r.data["dati"].get("gia_riscattato"))


class SerieDuplicatiLogicTests(TestCase):
    def test_senza_duplicati_indice_unico(self):
        user = User.objects.create_user(username="u", password="x")
        pg = Personaggio.objects.create(nome="P", proprietario=user)
        serie = SerieCollezione.objects.create(nome="S", totale=1, ammetti_duplicati=False)
        payload, err, override = qr_random_pool.applica_serie(personaggio=pg, serie=serie)
        self.assertIsNone(err)
        self.assertIsNone(override)
        payload2, err2, override2 = qr_random_pool.applica_serie(personaggio=pg, serie=serie)
        self.assertIsNone(err2)
        self.assertEqual(override2, "serie_esaurita")
        self.assertIsNotNone(payload2)
