import uuid

from django.test import TestCase

from kor35.edge_sync import EdgeSyncView
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
