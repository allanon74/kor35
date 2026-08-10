"""Test pool QR randomico, trappola e serie."""
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import (
    Manifesto,
    MinigiocoQrConfig,
    Personaggio,
    QrCode,
    RandomQrPool,
    RandomQrPoolEffect,
    RandomQrPoolMembership,
    SerieAssegnazione,
    SerieCollezione,
    SerieQr,
    StatoTrappolaPersonaggio,
    Trappola,
)
from personaggi import qr_random_pool


class RandomQrPoolLogicTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pooluser", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Pool", proprietario=self.user)
        self.pool = RandomQrPool.objects.create(nome="Pool Test", attivo=True)
        self.qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=self.pool, qr_code=self.qr)

    def test_scegli_effetto_pesato(self):
        e1 = RandomQrPoolEffect.objects.create(
            pool=self.pool, tipo=RandomQrPoolEffect.TIPO_TESTO, frequenza=100, titolo="A", testo="a"
        )
        e2 = RandomQrPoolEffect.objects.create(
            pool=self.pool, tipo=RandomQrPoolEffect.TIPO_TESTO, frequenza=1, titolo="B", testo="b"
        )

        class FakeRng:
            def choices(self, population, weights=None, k=1):
                self.last_population = list(population)
                self.last_weights = list(weights or [])
                # restituisce sempre l'effetto con frequenza 100
                for row, w in zip(self.last_population, self.last_weights):
                    if w == 100:
                        return [row]
                return [self.last_population[0]]

        rng = FakeRng()
        chosen = qr_random_pool.scegli_effetto(self.pool, rng=rng)
        self.assertEqual(chosen.pk, e1.pk)
        by_id = {row.pk: w for row, w in zip(rng.last_population, rng.last_weights)}
        self.assertEqual(by_id[e1.pk], 100)
        self.assertEqual(by_id[e2.pk], 1)

    def test_membership_unica(self):
        qr2 = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=self.pool, qr_code=qr2)
        with self.assertRaises(Exception):
            RandomQrPoolMembership.objects.create(pool=self.pool, qr_code=self.qr)

    def test_scan_pool_testo(self):
        RandomQrPoolEffect.objects.create(
            pool=self.pool,
            tipo=RandomQrPoolEffect.TIPO_TESTO,
            frequenza=1,
            titolo="Messaggio",
            testo="<p>Ciao</p>",
        )
        client = APIClient()
        client.force_authenticate(self.user)
        with patch("personaggi.qr_random_pool.scegli_effetto") as mock_choose:
            mock_choose.return_value = self.pool.effetti.first()
            r = client.get(
                f"/api/personaggi/api/qrcode/{self.qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "pool_testo")
        self.assertIn("Ciao", r.data["dati"]["testo"])

    def test_pool_has_priority_over_vista(self):
        m = Manifesto.objects.create(nome="M", testo="manifesto", requisiti_lettura=[])
        self.qr.vista = m
        self.qr.save(update_fields=["vista", "updated_at"])
        RandomQrPoolEffect.objects.create(
            pool=self.pool,
            tipo=RandomQrPoolEffect.TIPO_TESTO,
            frequenza=1,
            titolo="Pool",
            testo="dal pool",
        )
        client = APIClient()
        client.force_authenticate(self.user)
        with patch("personaggi.qr_random_pool.scegli_effetto") as mock_choose:
            mock_choose.return_value = self.pool.effetti.first()
            r = client.get(
                f"/api/personaggi/api/qrcode/{self.qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "pool_testo")


class TrappolaSerieTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="trapuser", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Trap", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_trappola_con_timer(self):
        trap = Trappola.objects.create(nome="Fossa", testo="<p>Sei caduto</p>", durata_secondi=90)
        qr = QrCode.objects.create(vista=trap)
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "trappola")
        self.assertTrue(r.data["dati"]["timer_attivo"])
        self.assertTrue(
            StatoTrappolaPersonaggio.objects.filter(personaggio=self.pg, nome="Fossa").exists()
        )

    def test_trappola_senza_timer(self):
        trap = Trappola.objects.create(nome="Cartello", testo="Attenzione", durata_secondi=None)
        qr = QrCode.objects.create(vista=trap)
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "trappola")
        self.assertFalse(r.data["dati"]["timer_attivo"])
        self.assertFalse(StatoTrappolaPersonaggio.objects.filter(personaggio=self.pg).exists())

    def test_serie_indici_unici_e_esaurimento(self):
        serie = SerieCollezione.objects.create(nome="Pecora", totale=2)
        sqr = SerieQr.objects.create(nome="Serie Pecora", serie=serie)
        qr = QrCode.objects.create(vista=sqr)

        r1 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "serie")
        idx1 = r1.data["dati"]["indice"]
        self.assertIn(idx1, (1, 2))
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 1)

        pg2 = Personaggio.objects.create(nome="PG2", proprietario=self.user)
        r2 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": pg2.id},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "serie")
        idx2 = r2.data["dati"]["indice"]
        self.assertNotEqual(idx1, idx2)
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 2)

        pg3 = Personaggio.objects.create(nome="PG3", proprietario=self.user)
        r3 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": pg3.id},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.data["tipo_modello"], "serie_esaurita")


class PoolMinigiocoOverrideTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="miniusr", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Mini", proprietario=self.user)
        self.pool = RandomQrPool.objects.create(
            nome="Pool Mini",
            attivo=True,
            minigioco_sezione_attiva=True,
            minigioco_attivo=True,
            minigioco_messaggio_pre="Gioca dal pool",
        )
        self.qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=self.pool, qr_code=self.qr)
        RandomQrPoolEffect.objects.create(
            pool=self.pool,
            tipo=RandomQrPoolEffect.TIPO_TESTO,
            frequenza=1,
            titolo="X",
            testo="y",
        )

    def test_minigioco_pool_gate(self):
        client = APIClient()
        client.force_authenticate(self.user)
        r = client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "minigioco_richiesto")
        self.assertIn("Gioca dal pool", r.data.get("messaggio") or "")

    def test_override_per_qr_vince(self):
        MinigiocoQrConfig.objects.create(
            qr_code=self.qr,
            sezione_attiva=True,
            attivo=True,
            messaggio_pre="Override QR",
            tipi_abilitati=["simon"],
        )
        client = APIClient()
        client.force_authenticate(self.user)
        r = client.get(
            f"/api/personaggi/api/qrcode/{self.qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "minigioco_richiesto")
        self.assertIn("Override", r.data.get("messaggio") or "")
