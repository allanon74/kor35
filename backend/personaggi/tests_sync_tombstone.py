from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import PaginaRegolamento
from kor35.sync_tombstone import (
    TOMBSTONE_PAYLOAD_KEY,
    apply_one_tombstone_row,
    apply_tombstone_rows,
    build_tombstones_outgoing,
    clear_tombstone,
    get_sync_model_registry,
    record_tombstone_for_instance,
    tombstone_blocks_record_apply,
)
from personaggi.models import Carriera, SyncTombstone, Tessitura, Punteggio, TIER_3, TipoCarriera


class SyncTombstoneTests(TestCase):
    def setUp(self):
        self.aura = Punteggio.objects.create(nome="Aura Tomb", sigla="ATB", tipo="AU")

    def test_record_tombstone_on_delete(self):
        tess = Tessitura.objects.create(nome="Da cancellare", aura_richiesta=self.aura)
        sync_id = tess.sync_id
        label = tess._meta.label_lower
        tess.delete()
        self.assertTrue(SyncTombstone.objects.filter(model_label=label, sync_id=sync_id).exists())

    def test_tombstone_blocks_stale_record_apply(self):
        sync_id = uuid4()
        deleted_at = timezone.now()
        SyncTombstone.objects.create(
            model_label="personaggi.tessitura",
            sync_id=sync_id,
            deleted_at=deleted_at,
        )
        stale = deleted_at - timezone.timedelta(hours=1)
        self.assertTrue(
            tombstone_blocks_record_apply("personaggi.tessitura", sync_id, stale)
        )

    def test_apply_tombstone_deletes_local_row(self):
        tess = Tessitura.objects.create(nome="Zombie", aura_richiesta=self.aura)
        sync_id = tess.sync_id
        label = tess._meta.label_lower
        deleted_at = timezone.now()
        registry = get_sync_model_registry(("personaggi",))
        apply_one_tombstone_row(
            registry,
            {
                "model_label": label,
                "sync_id": str(sync_id),
                "deleted_at": deleted_at.isoformat(),
            },
        )
        self.assertFalse(Tessitura.objects.filter(sync_id=sync_id).exists())
        self.assertTrue(SyncTombstone.objects.filter(model_label=label, sync_id=sync_id).exists())

    def test_apply_tombstone_does_not_delete_newer_local(self):
        tess = Tessitura.objects.create(nome="Vince LWW", aura_richiesta=self.aura)
        sync_id = tess.sync_id
        label = tess._meta.label_lower
        old_delete = tess.updated_at - timezone.timedelta(hours=1)
        registry = get_sync_model_registry(("personaggi",))
        apply_one_tombstone_row(
            registry,
            {
                "model_label": label,
                "sync_id": str(sync_id),
                "deleted_at": old_delete.isoformat(),
            },
        )
        self.assertTrue(Tessitura.objects.filter(sync_id=sync_id).exists())

    def test_save_clears_obsolete_tombstone(self):
        sync_id = uuid4()
        label = "personaggi.tessitura"
        SyncTombstone.objects.create(
            model_label=label,
            sync_id=sync_id,
            deleted_at=timezone.now(),
        )
        Tessitura.objects.create(nome="Resurrezione", aura_richiesta=self.aura, sync_id=sync_id)
        self.assertFalse(SyncTombstone.objects.filter(model_label=label, sync_id=sync_id).exists())

    def test_build_tombstones_outgoing_incremental(self):
        sync_id = uuid4()
        now = timezone.now()
        SyncTombstone.objects.create(
            model_label="gestione_plot.paginaregolamento",
            sync_id=sync_id,
            deleted_at=now,
        )
        rows = build_tombstones_outgoing(now + timezone.timedelta(seconds=1))
        self.assertEqual(rows, [])
        rows_all = build_tombstones_outgoing(None)
        self.assertEqual(len(rows_all), 1)
        self.assertEqual(rows_all[0]["sync_id"], str(sync_id))

    def test_post_save_clears_tombstone_via_signal(self):
        page = PaginaRegolamento.objects.create(titolo="Wiki", slug="wiki-tomb-test")
        clear_tombstone(page._meta.label_lower, page.sync_id)
        SyncTombstone.objects.create(
            model_label=page._meta.label_lower,
            sync_id=page.sync_id,
            deleted_at=timezone.now(),
        )
        page.contenuto = "aggiornato"
        page.save()
        self.assertFalse(
            SyncTombstone.objects.filter(
                model_label=page._meta.label_lower, sync_id=page.sync_id
            ).exists()
        )

    def test_tombstone_payload_key_constant(self):
        self.assertEqual(TOMBSTONE_PAYLOAD_KEY, "sync.tombstone")

    def test_apply_tombstone_rows_batch(self):
        tess = Tessitura.objects.create(nome="Batch", aura_richiesta=self.aura)
        registry = get_sync_model_registry(("personaggi",))
        apply_tombstone_rows(
            registry,
            [
                {
                    "model_label": tess._meta.label_lower,
                    "sync_id": str(tess.sync_id),
                    "deleted_at": timezone.now().isoformat(),
                }
            ],
        )
        self.assertFalse(Tessitura.objects.filter(pk=tess.pk).exists())

    def test_apply_tombstone_deferred_when_fk_protect(self):
        tipo = TipoCarriera.objects.create(codice="tomb-fk-test", nome="Tipo FK test")
        Carriera.objects.create(
            nome="Carriera FK test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=tipo,
        )
        registry = get_sync_model_registry(("personaggi",))
        result = apply_one_tombstone_row(
            registry,
            {
                "model_label": tipo._meta.label_lower,
                "sync_id": str(tipo.sync_id),
                "deleted_at": timezone.now().isoformat(),
            },
        )
        self.assertEqual(result, "deferred")
        self.assertTrue(TipoCarriera.objects.filter(pk=tipo.pk).exists())
        self.assertTrue(
            SyncTombstone.objects.filter(
                model_label=tipo._meta.label_lower, sync_id=tipo.sync_id
            ).exists()
        )
