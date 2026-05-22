from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import PaginaRegolamento
from kor35.syncing import (
    SYNC_MENU_ONLY_KEY,
    build_model_sync_records,
    serialize_pagina_regolamento_menu_only,
    touch_sync_updated_at,
    try_apply_pagina_regolamento_structure_when_skipped,
)


class WikiSyncTests(TestCase):
    def test_ancestor_export_is_menu_only(self):
        parent = PaginaRegolamento.objects.create(
            titolo="Parent",
            slug="parent-wiki",
            contenuto="<p>segreto parent</p>",
        )
        old = timezone.now() - timedelta(days=2)
        PaginaRegolamento.objects.filter(pk=parent.pk).update(updated_at=old)

        child = PaginaRegolamento.objects.create(
            titolo="Child",
            slug="child-wiki",
            parent=parent,
            contenuto="<p>child</p>",
        )
        child.contenuto = "<p>child updated</p>"
        child.save()

        rows = build_model_sync_records(
            PaginaRegolamento,
            "gestione_plot.paginaregolamento",
            since=timezone.now() - timedelta(seconds=5),
        )
        by_slug = {r["slug"]: r for r in rows}
        self.assertIn("child-wiki", by_slug)
        self.assertIn("parent-wiki", by_slug)
        self.assertTrue(by_slug["parent-wiki"].get(SYNC_MENU_ONLY_KEY))
        self.assertNotIn("contenuto", by_slug["parent-wiki"])
        self.assertNotIn("contenuto", serialize_pagina_regolamento_menu_only(parent))

    def test_structure_patch_does_not_lower_updated_at(self):
        page = PaginaRegolamento.objects.create(
            titolo="Wiki LWW",
            slug="wiki-lww",
            contenuto="<p>locale</p>",
        )
        local_ts = page.updated_at
        stale_remote = local_ts - timedelta(hours=2)
        row = {
            "parent": None,
            "ordine": 99,
            "updated_at": stale_remote.isoformat(),
        }
        result = try_apply_pagina_regolamento_structure_when_skipped(page, row)
        self.assertEqual(result, "applied")
        page.refresh_from_db()
        self.assertEqual(page.ordine, 99)
        self.assertGreaterEqual(page.updated_at, local_ts)
        self.assertIn("<p>locale</p>", page.contenuto)

    def test_touch_sync_updated_at_advances_timestamp(self):
        page = PaginaRegolamento.objects.create(titolo="Touch", slug="wiki-touch")
        before = page.updated_at
        touch_sync_updated_at(PaginaRegolamento, page.pk)
        page.refresh_from_db()
        self.assertGreaterEqual(page.updated_at, before)
