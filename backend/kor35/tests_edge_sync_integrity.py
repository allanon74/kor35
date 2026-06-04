import uuid
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from kor35.edge_sync import EdgeSyncView
from kor35.syncing import serialize_for_sync
from personaggi.models import Punteggio, Tessitura
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
