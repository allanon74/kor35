"""Test sync pagine Wiki staff da docs/wiki/staff/."""

from django.test import TestCase

from gestione_plot.models import PaginaRegolamento
from gestione_plot.wiki_staff_ops import sync_wiki_staff_ops


class WikiStaffOpsSyncTests(TestCase):
    def test_sync_creates_staff_section_and_pages(self):
        results = sync_wiki_staff_ops(force=True)
        slugs = {r["slug"] for r in results}
        self.assertIn("staff-operativita-tecnica", slugs)
        self.assertIn("staff-make-comandi", slugs)
        self.assertIn("staff-mirror-pi", slugs)

        parent = PaginaRegolamento.objects.get(slug="staff-operativita-tecnica")
        self.assertTrue(parent.visibile_solo_staff)
        self.assertIsNone(parent.parent)

        make_page = PaginaRegolamento.objects.get(slug="staff-make-comandi")
        self.assertEqual(make_page.parent_id, parent.id)
        self.assertTrue(make_page.visibile_solo_staff)
        self.assertIn("make mirror-pi-check", make_page.contenuto)

        mirror_page = PaginaRegolamento.objects.get(slug="staff-mirror-pi")
        self.assertEqual(mirror_page.parent_id, parent.id)
        self.assertIn("192.168.100.1", mirror_page.contenuto)

    def test_sync_without_force_skips_existing(self):
        sync_wiki_staff_ops(force=True)
        make_page = PaginaRegolamento.objects.get(slug="staff-make-comandi")
        make_page.contenuto = "<p>modifica manuale</p>"
        make_page.save(update_fields=["contenuto", "updated_at"])

        sync_wiki_staff_ops(force=False)
        make_page.refresh_from_db()
        self.assertIn("modifica manuale", make_page.contenuto)
