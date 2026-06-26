"""Test sync pagine Wiki staff da docs/wiki/staff/."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import PaginaRegolamento
from gestione_plot.wiki_staff_ops import get_wiki_staff_ops_info, sync_wiki_staff_ops
from personaggi.models import (
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_REDACTOR,
    Campagna,
    CampagnaUtente,
)


class WikiStaffOpsSyncTests(TestCase):
    def test_markdown_tables_convert_to_styled_html(self):
        from gestione_plot.wiki_staff_ops import _markdown_to_html

        md = "| Comando | Descrizione |\n|---------|-------------|\n| `make up` | Avvia |"
        html = _markdown_to_html(md)
        self.assertIn('<div class="wiki-table-scroll"><table data-table-style="grid">', html)
        self.assertIn("<th>Comando</th>", html)
        self.assertIn("<code>make up</code>", html)

    def test_sync_creates_staff_section_and_pages(self):
        results = sync_wiki_staff_ops(force=True)
        slugs = {r["slug"] for r in results}
        self.assertIn("staff-operativita-tecnica", slugs)
        self.assertIn("staff-make-comandi", slugs)
        self.assertIn("staff-pilot-eventi", slugs)
        self.assertIn("staff-mirror-pi", slugs)
        self.assertIn("staff-test-offline-omada", slugs)

        parent = PaginaRegolamento.objects.get(slug="staff-operativita-tecnica")
        self.assertTrue(parent.visibile_solo_staff)
        self.assertIsNone(parent.parent)

        make_page = PaginaRegolamento.objects.get(slug="staff-make-comandi")
        self.assertEqual(make_page.parent_id, parent.id)
        self.assertTrue(make_page.visibile_solo_staff)
        self.assertIn("make mirror-pi-check", make_page.contenuto)
        self.assertIn("sync-certs-to-mirror", make_page.contenuto)
        self.assertIn("mirror-reinstall-units", make_page.contenuto)
        self.assertIn('<table data-table-style="grid">', make_page.contenuto)
        self.assertIn("<th>Comando</th>", make_page.contenuto)

        pilot_page = PaginaRegolamento.objects.get(slug="staff-pilot-eventi")
        self.assertEqual(pilot_page.parent_id, parent.id)
        self.assertTrue(pilot_page.visibile_solo_staff)
        self.assertIn("ST / SP / CA", pilot_page.contenuto)
        self.assertIn("Catalogo eventi", pilot_page.contenuto)

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


class StaffWikiStaffOpsApiTests(APITestCase):
    url = "/api/plot/api/staff/wiki-staff-ops/sync/"

    def setUp(self):
        User = get_user_model()
        self.campagna = Campagna.objects.create(slug="wiki-ops-api", nome="Wiki Ops", attiva=True)
        self.user_redactor = User.objects.create_user(username="wiki_red", password="x")
        self.user_master = User.objects.create_user(username="wiki_master", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user_redactor, ruolo=CAMPAGNA_ROLE_REDACTOR, attivo=True
        )
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.user_master, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )

    def test_get_info_redactor_ok(self):
        self.client.force_authenticate(user=self.user_redactor)
        resp = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("manifest_ok", resp.data)
        self.assertIn("pages", resp.data)

    def test_post_sync_master_ok(self):
        self.client.force_authenticate(user=self.user_master)
        resp = self.client.post(
            self.url,
            {"force": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["ok"])
        self.assertIn("staff-make-comandi", {r["slug"] for r in resp.data["results"]})

    def test_post_sync_redactor_forbidden(self):
        self.client.force_authenticate(user=self.user_redactor)
        resp = self.client.post(
            self.url,
            {"force": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_get_wiki_staff_ops_info_matches_manifest(self):
        info = get_wiki_staff_ops_info()
        self.assertTrue(info["manifest_ok"])
        self.assertEqual(info["section"]["slug"], "staff-operativita-tecnica")
        self.assertGreaterEqual(len(info["pages"]), 4)
