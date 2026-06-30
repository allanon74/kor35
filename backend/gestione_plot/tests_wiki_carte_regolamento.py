"""Test sync e visibilità Wiki regolamento carte."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import PaginaRegolamento
from gestione_plot.wiki_carte_regolamento import get_wiki_carte_regolamento_info, sync_wiki_carte_regolamento
from personaggi.carte_collezionabili_models import CARTE_ACCESSO_OFF, CARTE_ACCESSO_OPEN, ConfigurazioneCarteCollezionabili
from personaggi.carte_wiki_access import CARTE_WIKI_KEYWORDS_STAFF_SLUG, CARTE_WIKI_REGOLAMENTO_SLUG
from personaggi.models import CAMPAGNA_ROLE_MASTER, Campagna, CampagnaUtente


class WikiCarteRegolamentoSyncTests(TestCase):
    def test_sync_creates_section_and_page(self):
        results = sync_wiki_carte_regolamento(force=True)
        slugs = {r["slug"] for r in results}
        self.assertIn("gioco-carte", slugs)
        self.assertIn("carte-collezionabili-regolamento", slugs)
        self.assertIn("carte-keywords-staff", slugs)

        parent = PaginaRegolamento.objects.get(slug="gioco-carte")
        self.assertFalse(parent.visibile_solo_staff)
        self.assertTrue(parent.public)

        page = PaginaRegolamento.objects.get(slug="carte-collezionabili-regolamento")
        self.assertEqual(page.parent_id, parent.id)
        self.assertIn("Cronache delle Sette Elegie", page.contenuto)

        staff_kw = PaginaRegolamento.objects.get(slug="carte-keywords-staff")
        self.assertEqual(staff_kw.parent_id, parent.id)
        self.assertTrue(staff_kw.visibile_solo_staff)
        self.assertIn("Mutazione", staff_kw.contenuto)

    def test_get_info_ok(self):
        info = get_wiki_carte_regolamento_info()
        self.assertTrue(info["manifest_ok"])
        self.assertEqual(info["section"]["slug"], "gioco-carte")


class WikiCarteRegolamentoVisibilityTests(APITestCase):
    menu_url = "/api/plot/api/wiki/menu/"
    page_url = f"/api/plot/api/wiki/pagina/{CARTE_WIKI_REGOLAMENTO_SLUG}/"
    staff_kw_url = f"/api/plot/api/wiki/pagina/{CARTE_WIKI_KEYWORDS_STAFF_SLUG}/"

    def setUp(self):
        User = get_user_model()
        self.campagna = Campagna.objects.create(slug="wiki-carte-vis", nome="Wiki Carte", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OFF,
            abilitata=False,
        )
        self.player = User.objects.create_user(username="carte_player", password="x")
        self.master = User.objects.create_user(username="carte_master", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.master, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )
        sync_wiki_carte_regolamento(force=True)

    def test_player_off_mode_hides_carte_wiki(self):
        resp = self.client.get(self.menu_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        slugs = {p["slug"] for p in resp.data}
        self.assertNotIn(CARTE_WIKI_REGOLAMENTO_SLUG, slugs)
        self.assertNotIn("gioco-carte", slugs)

        page_resp = self.client.get(self.page_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(page_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_master_off_mode_sees_carte_wiki(self):
        self.client.force_authenticate(user=self.master)
        resp = self.client.get(self.menu_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        slugs = {p["slug"] for p in resp.data}
        self.assertIn(CARTE_WIKI_REGOLAMENTO_SLUG, slugs)

        page_resp = self.client.get(self.page_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(page_resp.status_code, status.HTTP_200_OK)

        self.assertNotIn(CARTE_WIKI_KEYWORDS_STAFF_SLUG, slugs)
        staff_resp = self.client.get(self.staff_kw_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(staff_resp.status_code, status.HTTP_404_NOT_FOUND)

    def test_master_sees_keywords_staff_page(self):
        from rest_framework.authtoken.models import Token

        token = Token.objects.create(user=self.master)
        auth = f"Token {token.key}"
        resp = self.client.get(
            self.menu_url,
            HTTP_X_CAMPAGNA=self.campagna.slug,
            HTTP_AUTHORIZATION=auth,
        )
        slugs = {p["slug"] for p in resp.data}
        self.assertIn(CARTE_WIKI_KEYWORDS_STAFF_SLUG, slugs)
        page_resp = self.client.get(
            self.staff_kw_url,
            HTTP_X_CAMPAGNA=self.campagna.slug,
            HTTP_AUTHORIZATION=auth,
        )
        self.assertEqual(page_resp.status_code, status.HTTP_200_OK)
        self.assertIn("guida master", page_resp.data.get("titolo", "").lower())

    def test_player_open_mode_sees_carte_wiki(self):
        cfg = ConfigurazioneCarteCollezionabili.objects.get(campagna=self.campagna)
        cfg.accesso_modo = CARTE_ACCESSO_OPEN
        cfg.abilitata = True
        cfg.save()

        self.client.force_authenticate(user=self.player)
        resp = self.client.get(self.menu_url, HTTP_X_CAMPAGNA=self.campagna.slug)
        slugs = {p["slug"] for p in resp.data}
        self.assertIn(CARTE_WIKI_REGOLAMENTO_SLUG, slugs)
        self.assertNotIn(CARTE_WIKI_KEYWORDS_STAFF_SLUG, slugs)


class StaffWikiCarteRegolamentoApiTests(APITestCase):
    url = "/api/personaggi/api/staff/carte/wiki-regolamento/sync/"

    def setUp(self):
        User = get_user_model()
        self.campagna = Campagna.objects.create(slug="wiki-carte-api", nome="Wiki Carte API", attiva=True)
        self.master = User.objects.create_user(username="carte_wiki_master", password="x")
        CampagnaUtente.objects.create(
            campagna=self.campagna, user=self.master, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True
        )

    def test_get_info_master_ok(self):
        self.client.force_authenticate(user=self.master)
        resp = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertIn("manifest_ok", resp.data)

    def test_post_sync_master_ok(self):
        self.client.force_authenticate(user=self.master)
        resp = self.client.post(
            self.url,
            {"force": True},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data.get("ok"))
