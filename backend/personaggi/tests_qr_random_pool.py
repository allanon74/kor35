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
    RandomQrPoolClaim,
    RandomQrPoolEffect,
    RandomQrPoolMembership,
    SerieAssegnazione,
    SerieCollezione,
    SerieImmagine,
    SerieQr,
    StatoTrappolaPersonaggio,
    Trappola,
)
from personaggi import qr_random_pool


def _tiny_jpeg_bytes():
    from io import BytesIO

    from PIL import Image

    buf = BytesIO()
    Image.new("RGB", (8, 8), (200, 40, 40)).save(buf, format="JPEG", quality=80)
    return buf.getvalue()


def _serie_immagine(serie, filename):
    from django.core.files.uploadedfile import SimpleUploadedFile

    return SerieImmagine.objects.create(
        serie=serie,
        immagine=SimpleUploadedFile(filename, _tiny_jpeg_bytes(), content_type="image/jpeg"),
        nome_file_originale=filename,
    )


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
        self.assertTrue(
            RandomQrPoolClaim.objects.filter(personaggio=self.pg, qr_code=self.qr).exists()
        )

    def test_pool_anti_farm_un_claim_per_qr(self):
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
            r1 = client.get(
                f"/api/personaggi/api/qrcode/{self.qr.id}/",
                {"personaggio_id": self.pg.id},
            )
            r2 = client.get(
                f"/api/personaggi/api/qrcode/{self.qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "pool_testo")
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "pool_errore")
        self.assertTrue(r2.data["dati"].get("gia_usato"))
        self.assertEqual(
            RandomQrPoolClaim.objects.filter(personaggio=self.pg, qr_code=self.qr).count(),
            1,
        )

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

    def test_trappola_e_serieqr_usano_uuid_pk(self):
        """Regressione .cursorrules §1: niente AutoField da A_vista MTI."""
        import uuid as uuid_mod

        trap = Trappola.objects.create(nome="U", testo="")
        serie = SerieCollezione.objects.create(nome="S", totale=1)
        sqr = SerieQr.objects.create(nome="SQ", serie=serie)
        self.assertIsInstance(trap.pk, uuid_mod.UUID)
        self.assertIsInstance(sqr.pk, uuid_mod.UUID)
        self.assertTrue(hasattr(trap, "sync_id"))
        self.assertTrue(hasattr(sqr, "sync_id"))

    def test_trappola_con_timer(self):
        qr = QrCode.objects.create()
        Trappola.objects.create(
            nome="Fossa", testo="<p>Sei caduto</p>", durata_secondi=90, qr_code=qr
        )
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
        qr = QrCode.objects.create()
        Trappola.objects.create(
            nome="Cartello", testo="Attenzione", durata_secondi=None, qr_code=qr
        )
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "trappola")
        self.assertFalse(r.data["dati"]["timer_attivo"])
        self.assertFalse(StatoTrappolaPersonaggio.objects.filter(personaggio=self.pg).exists())

    def test_serie_indici_unici_e_esaurimento(self):
        """Ogni QR fisico assegna al massimo un pezzo (anti-farm)."""
        serie = SerieCollezione.objects.create(nome="Pecora", totale=2)
        qr1 = QrCode.objects.create()
        qr2 = QrCode.objects.create()
        qr3 = QrCode.objects.create()
        SerieQr.objects.create(nome="Serie Pecora 1", serie=serie, qr_code=qr1)
        SerieQr.objects.create(nome="Serie Pecora 2", serie=serie, qr_code=qr2)
        SerieQr.objects.create(nome="Serie Pecora 3", serie=serie, qr_code=qr3)

        r1 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr1.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r1.data["tipo_modello"], "serie")
        idx1 = r1.data["dati"]["indice"]
        self.assertIn(idx1, (1, 2))
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 1)

        # Stesso QR + stesso PG: idempotente, non crea pezzi nuovi
        r1b = self.client.get(
            f"/api/personaggi/api/qrcode/{qr1.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r1b.status_code, 200)
        self.assertEqual(r1b.data["tipo_modello"], "serie")
        self.assertTrue(r1b.data["dati"].get("gia_riscattato"))
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 1)

        pg2 = Personaggio.objects.create(nome="PG2", proprietario=self.user)
        # Stesso QR + altro PG: bloccato (anti-farm)
        r1_other = self.client.get(
            f"/api/personaggi/api/qrcode/{qr1.id}/",
            {"personaggio_id": pg2.id},
        )
        self.assertEqual(r1_other.status_code, 400)
        self.assertIn("già stato riscosso", r1_other.data.get("error", "").lower())

        r2 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr2.id}/",
            {"personaggio_id": pg2.id},
        )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "serie")
        idx2 = r2.data["dati"]["indice"]
        self.assertNotEqual(idx1, idx2)
        self.assertEqual(SerieAssegnazione.objects.filter(serie=serie).count(), 2)

        pg3 = Personaggio.objects.create(nome="PG3", proprietario=self.user)
        r3 = self.client.get(
            f"/api/personaggi/api/qrcode/{qr3.id}/",
            {"personaggio_id": pg3.id},
        )
        self.assertEqual(r3.status_code, 200)
        self.assertEqual(r3.data["tipo_modello"], "serie_esaurita")

    def test_serie_immagini_alfabetiche_quando_pari_al_totale(self):
        serie = SerieCollezione.objects.create(nome="Carte", totale=3)
        img_b = _serie_immagine(serie, "b_beta.jpg")
        img_a = _serie_immagine(serie, "a_alfa.jpg")
        img_c = _serie_immagine(serie, "c_gamma.jpg")

        # Con count == totale: indice i → i-esima in ordine alfabetico
        self.assertEqual(
            qr_random_pool.scegli_immagine_serie(serie=serie, indice=1, totale=3).pk,
            img_a.pk,
        )
        self.assertEqual(
            qr_random_pool.scegli_immagine_serie(serie=serie, indice=2, totale=3).pk,
            img_b.pk,
        )
        self.assertEqual(
            qr_random_pool.scegli_immagine_serie(serie=serie, indice=3, totale=3).pk,
            img_c.pk,
        )

        qr = QrCode.objects.create()
        SerieQr.objects.create(nome="QR Carte", serie=serie, qr_code=qr)
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "serie")
        self.assertTrue(r.data["dati"].get("immagine_url"))
        ass = SerieAssegnazione.objects.get(serie=serie, personaggio=self.pg)
        expected = {1: img_a.pk, 2: img_b.pk, 3: img_c.pk}[ass.indice]
        self.assertEqual(ass.immagine_id, expected)

    def test_serie_immagini_random_con_ripetizioni_se_meno_del_totale(self):
        serie = SerieCollezione.objects.create(nome="Seed", totale=4)
        only = _serie_immagine(serie, "unica.jpg")
        with patch("personaggi.qr_random_pool.random.choice", side_effect=lambda seq: seq[0]):
            chosen = qr_random_pool.scegli_immagine_serie(serie=serie, indice=3, totale=4)
        self.assertEqual(chosen.pk, only.pk)

        # Con una sola immagine e totale > 1, applica_serie deve comunque assegnarla
        qr = QrCode.objects.create()
        SerieQr.objects.create(nome="QR Seed", serie=serie, qr_code=qr)
        r = self.client.get(
            f"/api/personaggi/api/qrcode/{qr.id}/",
            {"personaggio_id": self.pg.id},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "serie")
        self.assertTrue(r.data["dati"].get("immagine_url"))
        ass = SerieAssegnazione.objects.get(serie=serie, personaggio=self.pg)
        self.assertEqual(ass.immagine_id, only.pk)


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


class ManifestoCondizionaleEPoolLootTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="conduser", password="pass")
        self.pg = Personaggio.objects.create(nome="PG Cond", proprietario=self.user)
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def test_manifesto_testo_condizionato_and(self):
        m = Manifesto.objects.create(
            nome="Segreto",
            testo="<p>Base</p>",
            testo_condizionato="<p>Segreto INT</p>",
            condizioni_testo={
                "operator": "AND",
                "requisiti": [{"tipo": "statistica", "sigla": "INT", "min": 3}],
            },
            requisiti_lettura=[],
        )
        qr = QrCode.objects.create(vista=m)

        with patch.object(Personaggio, "get_valore_statistica", return_value=1):
            r = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["dati"]["puo_leggere"])
        self.assertIn("Base", r.data["dati"]["testo"])
        self.assertFalse(r.data["dati"]["mostra_testo_condizionato"])

        with patch.object(Personaggio, "get_valore_statistica", return_value=5):
            r2 = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertTrue(r2.data["dati"]["mostra_testo_condizionato"])
        self.assertIn("Segreto INT", r2.data["dati"]["testo_condizionato"])

    def test_manifesto_condizioni_or(self):
        m = Manifesto.objects.create(
            nome="OR",
            testo="base",
            testo_condizionato="extra",
            condizioni_testo={
                "operator": "OR",
                "requisiti": [
                    {"tipo": "statistica", "sigla": "INT", "min": 99},
                    {"tipo": "statistica", "sigla": "CCO", "min": 1},
                ],
            },
        )
        from personaggi.qr_logic import risolvi_payload_manifesto

        def fake_stat(sigla):
            return 2 if sigla == "CCO" else 0

        with patch.object(self.pg, "get_valore_statistica", side_effect=fake_stat):
            payload = risolvi_payload_manifesto(m, self.pg)
        self.assertTrue(payload["mostra_testo_condizionato"])

    def test_pool_effetto_manifesto(self):
        pool = RandomQrPool.objects.create(nome="Pool Man", attivo=True)
        qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=pool, qr_code=qr)
        m = Manifesto.objects.create(
            nome="Dal pool",
            testo="<p>Pool base</p>",
            testo_condizionato="<p>Pool segreto</p>",
            condizioni_testo={
                "operator": "AND",
                "requisiti": [{"tipo": "statistica", "sigla": "INT", "min": 1}],
            },
        )
        eff = RandomQrPoolEffect.objects.create(
            pool=pool,
            tipo=RandomQrPoolEffect.TIPO_MANIFESTO,
            frequenza=1,
            manifesto=m,
        )
        with patch("personaggi.qr_random_pool.scegli_effetto", return_value=eff):
            with patch.object(Personaggio, "get_valore_statistica", return_value=5):
                r = self.client.get(
                    f"/api/personaggi/api/qrcode/{qr.id}/",
                    {"personaggio_id": self.pg.id},
                )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "manifesto")
        self.assertTrue(r.data["dati"]["mostra_testo_condizionato"])

    def test_pool_effetto_oggetto_base(self):
        from personaggi.models import Oggetto, OggettoBase, TIPO_OGGETTO_FISICO

        pool = RandomQrPool.objects.create(nome="Pool Loot", attivo=True)
        qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=pool, qr_code=qr)
        template = OggettoBase.objects.create(
            nome="Coltello pool",
            tipo_oggetto=TIPO_OGGETTO_FISICO,
            costo=0,
        )
        eff = RandomQrPoolEffect.objects.create(
            pool=pool,
            tipo=RandomQrPoolEffect.TIPO_OGGETTO_BASE,
            frequenza=1,
            oggetto_base=template,
        )
        with patch("personaggi.qr_random_pool.scegli_effetto", return_value=eff):
            r = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "pool_loot")
        oggetto = Oggetto.objects.get(pk=r.data["dati"]["oggetto_id"])
        self.assertEqual(oggetto.nome, "Coltello pool")
        self.assertEqual(oggetto.inventario_corrente.pk, self.pg.pk)

    def test_pool_effetto_tessitura(self):
        from personaggi.models import AURA, Punteggio, Tessitura

        aura, _ = Punteggio.objects.get_or_create(
            nome="Aura pool test",
            defaults={"tipo": AURA, "sigla": "APT"},
        )
        if aura.tipo != AURA:
            aura.tipo = AURA
            aura.save(update_fields=["tipo"])

        pool = RandomQrPool.objects.create(nome="Pool Tec", attivo=True)
        qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=pool, qr_code=qr)
        t = Tessitura.objects.create(nome="Tessitura pool", testo="", aura_richiesta=aura)
        eff = RandomQrPoolEffect.objects.create(
            pool=pool,
            tipo=RandomQrPoolEffect.TIPO_TESSITURA,
            frequenza=1,
            tessitura=t,
        )
        with patch("personaggi.qr_random_pool.scegli_effetto", return_value=eff):
            r = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["tipo_modello"], "pool_loot")
        self.assertTrue(self.pg.tessiture_possedute.filter(pk=t.pk).exists())
        # Seconda scansione: anti-farm claim (non un secondo roll)
        with patch("personaggi.qr_random_pool.scegli_effetto", return_value=eff):
            r2 = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.data["tipo_modello"], "pool_errore")
        self.assertTrue(r2.data["dati"].get("gia_usato"))

    def test_pool_effetto_materia_da_infusione(self):
        from personaggi.models import AURA, Infusione, Oggetto, Punteggio, TIPO_OGGETTO_MATERIA

        aura, _ = Punteggio.objects.get_or_create(
            nome="Aura materia pool",
            defaults={"tipo": AURA, "sigla": "AMP"},
        )
        if getattr(aura, "sigla", None) != "AMP":
            # sigla già presa: usa quella esistente purché non ATE (diventerebbe Mod)
            pass
        if aura.tipo != AURA:
            aura.tipo = AURA
            aura.save(update_fields=["tipo"])

        pool = RandomQrPool.objects.create(nome="Pool Mat", attivo=True)
        qr = QrCode.objects.create()
        RandomQrPoolMembership.objects.create(pool=pool, qr_code=qr)
        inf = Infusione.objects.create(
            nome="Matrice pool",
            testo="",
            aura_richiesta=aura,
            tipo_risultato="POT",
        )
        eff = RandomQrPoolEffect.objects.create(
            pool=pool,
            tipo=RandomQrPoolEffect.TIPO_DA_INFUSIONE,
            frequenza=1,
            infusione=inf,
        )
        with patch("personaggi.qr_random_pool.scegli_effetto", return_value=eff):
            r = self.client.get(
                f"/api/personaggi/api/qrcode/{qr.id}/",
                {"personaggio_id": self.pg.id},
            )
        self.assertEqual(r.status_code, 200, getattr(r, "data", r.content))
        self.assertEqual(r.data["tipo_modello"], "pool_loot")
        oggetto = Oggetto.objects.get(pk=r.data["dati"]["oggetto_id"])
        self.assertEqual(oggetto.infusione_generatrice_id, inf.pk)
        self.assertEqual(oggetto.inventario_corrente.pk, self.pg.pk)
        # ATE → Mod, altrimenti Materia (per POT)
        if (aura.sigla or "").upper() == "ATE":
            self.assertEqual(oggetto.tipo_oggetto, "MOD")
        else:
            self.assertEqual(oggetto.tipo_oggetto, TIPO_OGGETTO_MATERIA)
