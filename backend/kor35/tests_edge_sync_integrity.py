import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from kor35.edge_sync import EdgeSyncView
from kor35.syncing import serialize_for_sync
from personaggi.models import MinigiocoQrConfig, Punteggio, QrCode, Tessitura
from pilotaggio.models import SottosistemaNave


class EdgeSyncScalarUniqueMergeTests(TestCase):
    """Codici monografici di test: non usare A/B (spesso già presenti nel DB dev)."""

    def test_merge_by_unique_codice_aligns_sync_id(self):
        SottosistemaNave.objects.filter(codice="1").delete()
        master_sync_id = uuid.uuid4()
        edge_sync_id = uuid.uuid4()
        SottosistemaNave.objects.create(
            codice="1",
            nome="Sottosistema master",
            sync_id=master_sync_id,
        )

        view = EdgeSyncView()
        update_data = {
            "codice": "1",
            "nome": "Sottosistema edge",
            "descrizione": "",
            "attivo": True,
        }
        merged = view._merge_by_unique_together_key(
            SottosistemaNave, edge_sync_id, update_data, None
        )
        self.assertTrue(merged)

        obj = SottosistemaNave.objects.get(codice="1")
        self.assertEqual(str(obj.sync_id), str(edge_sync_id))
        self.assertEqual(obj.nome, "Sottosistema edge")

    def test_find_existing_after_merge_by_codice(self):
        SottosistemaNave.objects.filter(codice="2").delete()
        master_sync_id = uuid.uuid4()
        SottosistemaNave.objects.create(
            codice="2",
            nome="Locale",
            sync_id=master_sync_id,
        )
        view = EdgeSyncView()
        row = {"codice": "2", "nome": "Remoto"}
        update_data = {"codice": "2", "nome": "Remoto"}
        obj = view._find_existing_after_merge(SottosistemaNave, row, update_data)
        self.assertIsNotNone(obj)
        self.assertEqual(obj.codice, "2")


class EdgeSyncMinigiocoQrConfigMergeTests(TestCase):
    """OneToOne qr_code: config staff locale con sync_id diverso dal master."""

    def test_merge_minigioco_qr_config_by_qr_code_aligns_sync_id(self):
        qr = QrCode.objects.create(testo="QR minigioco sync test")
        local_sync_id = uuid.uuid4()
        master_sync_id = uuid.uuid4()
        MinigiocoQrConfig.objects.create(
            qr_code=qr,
            sync_id=local_sync_id,
            attivo=False,
            tipi_abilitati=["simon"],
        )

        view = EdgeSyncView()
        update_data = {
            "qr_code": qr,
            "attivo": True,
            "tipi_abilitati": ["memory", "simon"],
            "difficolta": 3,
            "difficolta_min": 1,
            "tipo": "sliding_puzzle",
            "requisiti_attivazione": [],
            "esclusioni_minigioco": [],
            "regole_difficolta": [],
            "messaggio_pre": "",
            "messaggio_vittoria": "",
            "timer_scadenza_azione": "reset_minigioco",
            "usa_biblioteca_se_vuota": True,
        }
        remote_updated = timezone.now()
        merged = view._merge_minigioco_qr_config_by_qr_code(
            MinigiocoQrConfig, master_sync_id, update_data, remote_updated
        )
        self.assertTrue(merged)

        cfg = MinigiocoQrConfig.objects.get(qr_code=qr)
        self.assertEqual(str(cfg.sync_id), str(master_sync_id))
        self.assertTrue(cfg.attivo)
        self.assertEqual(cfg.tipi_abilitati, ["memory", "simon"])

    def test_try_apply_one_merges_when_local_config_has_different_sync_id(self):
        qr = QrCode.objects.create(testo="QR minigioco apply test")
        local_sync_id = uuid.uuid4()
        master_sync_id = uuid.uuid4()
        MinigiocoQrConfig.objects.create(
            qr_code=qr,
            sync_id=local_sync_id,
            attivo=False,
        )

        remote_updated = timezone.now()
        row = {
            "sync_id": str(master_sync_id),
            "qr_code": str(qr.sync_id),
            "attivo": True,
            "tipi_abilitati": ["pipe_connect"],
            "difficolta": 2,
            "difficolta_min": 1,
            "tipo": "sliding_puzzle",
            "requisiti_attivazione": [],
            "esclusioni_minigioco": [],
            "regole_difficolta": [],
            "messaggio_pre": "Pronto?",
            "messaggio_vittoria": "Fatto!",
            "timer_scadenza_azione": "reset_minigioco",
            "usa_biblioteca_se_vuota": True,
            "updated_at": remote_updated.isoformat(),
        }

        view = EdgeSyncView()
        result = view._try_apply_one(MinigiocoQrConfig, row)
        self.assertEqual(result, "applied")

        cfg = MinigiocoQrConfig.objects.get(qr_code=qr)
        self.assertEqual(str(cfg.sync_id), str(master_sync_id))
        self.assertTrue(cfg.attivo)
        self.assertEqual(cfg.messaggio_pre, "Pronto?")


class EdgeSyncQrCodeNaturalPkTests(TestCase):
    """QrCode.id (codice stampato) deve viaggiare nel payload sync."""

    def test_serialize_includes_qrcode_id(self):
        qr = QrCode.objects.create(testo="export id test")
        row = serialize_for_sync(qr)
        self.assertEqual(row.get("id"), qr.id)

    def test_apply_creates_qrcode_with_master_id(self):
        master_sync_id = uuid.uuid4()
        master_id = "FIXEDqrID0001"
        remote_updated = timezone.now()
        row = {
            "sync_id": str(master_sync_id),
            "id": master_id,
            "testo": "Da master",
            "inventario_presente": False,
            "inventario_colore_codice": "",
            "inventario_colore_sfondo": "",
            "stl_creato": False,
            "qr_stampato": False,
            "vista": None,
            "updated_at": remote_updated.isoformat(),
        }
        view = EdgeSyncView()
        result = view._try_apply_one(QrCode, row)
        self.assertEqual(result, "applied")
        qr = QrCode.objects.get(sync_id=master_sync_id)
        self.assertEqual(qr.id, master_id)
        self.assertEqual(qr.testo, "Da master")

    def test_apply_merges_local_qrcode_by_id_when_sync_id_differs(self):
        master_sync_id = uuid.uuid4()
        local_sync_id = uuid.uuid4()
        master_id = "MERGEqrID00002"
        QrCode.objects.create(id=master_id, sync_id=local_sync_id, testo="Locale")

        remote_updated = timezone.now()
        row = {
            "sync_id": str(master_sync_id),
            "id": master_id,
            "testo": "Da master",
            "inventario_presente": False,
            "inventario_colore_codice": "",
            "inventario_colore_sfondo": "",
            "stl_creato": False,
            "qr_stampato": True,
            "vista": None,
            "updated_at": remote_updated.isoformat(),
        }
        view = EdgeSyncView()
        result = view._try_apply_one(QrCode, row)
        self.assertEqual(result, "applied")

        qr = QrCode.objects.get(id=master_id)
        self.assertEqual(str(qr.sync_id), str(master_sync_id))
        self.assertEqual(qr.testo, "Da master")
        self.assertTrue(qr.qr_stampato)

    def test_realigns_qrcode_pk_when_sync_id_matches_but_id_wrong(self):
        master_sync_id = uuid.uuid4()
        mirror_qr = QrCode.objects.create(sync_id=master_sync_id, testo="Mirror auto id")
        wrong_id = mirror_qr.id
        physical_id = "REALIGNqr0001"
        remote_updated = timezone.now()
        row = {
            "sync_id": str(master_sync_id),
            "id": physical_id,
            "testo": "Da master",
            "inventario_presente": False,
            "inventario_colore_codice": "",
            "inventario_colore_sfondo": "",
            "stl_creato": False,
            "qr_stampato": False,
            "vista": None,
            "updated_at": remote_updated.isoformat(),
        }
        view = EdgeSyncView()
        result = view._try_apply_one(QrCode, row)
        self.assertEqual(result, "applied")
        self.assertFalse(QrCode.objects.filter(pk=wrong_id).exists())
        qr = QrCode.objects.get(sync_id=master_sync_id)
        self.assertEqual(qr.id, physical_id)
        self.assertEqual(qr.testo, "Da master")


class EdgeSyncMtiChildLwwTests(TestCase):
    """Campi MTI figlio (es. Tessitura) non devono essere sovrascritti da payload più vecchi."""

    def setUp(self):
        self.aura = Punteggio.objects.create(nome="Aura MTI sync", sigla="AMT", tipo="AU")

    def test_stale_edge_payload_does_not_revert_tessitura_runtime_fields(self):
        tess = Tessitura.objects.create(
            nome="Potenziare Arma sync test",
            aura_richiesta=self.aura,
            usa_effetto_temporaneo=True,
            durata_effetto_secondi=120,
            oggetto_runtime_config={"nome": "Runtime", "slot_key": "melee", "modificatori": []},
        )
        now = timezone.now()
        Tessitura.objects.filter(pk=tess.pk).update(updated_at=now)
        tess.refresh_from_db()

        stale_row = serialize_for_sync(tess)
        stale_row["usa_effetto_temporaneo"] = False
        stale_row["durata_effetto_secondi"] = 0
        stale_row["oggetto_runtime_config"] = None
        stale_row["updated_at"] = (now - timedelta(hours=2)).isoformat()

        view = EdgeSyncView()
        result = view._try_apply_one(Tessitura, stale_row)
        self.assertIn(result, ("skipped", "applied"))

        tess.refresh_from_db()
        self.assertTrue(tess.usa_effetto_temporaneo)
        self.assertEqual(tess.durata_effetto_secondi, 120)
        self.assertEqual(
            tess.oggetto_runtime_config,
            {"nome": "Runtime", "slot_key": "melee", "modificatori": []},
        )
