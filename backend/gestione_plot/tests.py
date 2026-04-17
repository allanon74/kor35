from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.test import APITestCase

from gestione_plot.models import PaginaRegolamento
from personaggi.models import (
    CAMPAGNA_ROLE_HEAD_MASTER,
    CAMPAGNA_ROLE_MASTER,
    CAMPAGNA_ROLE_PLAYER,
    CAMPAGNA_ROLE_REDACTOR,
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
)


class WikiPermissionsMatrixTests(APITestCase):
    def setUp(self):
        User = get_user_model()
        self.campagna = Campagna.objects.create(slug="perm-test", nome="Perm Test", attiva=True)

        self.user_player = User.objects.create_user(username="player", password="x")
        self.user_redactor = User.objects.create_user(username="redactor", password="x")
        self.user_staffer = User.objects.create_user(username="staffer", password="x")
        self.user_master = User.objects.create_user(username="master", password="x")
        self.user_head = User.objects.create_user(username="head", password="x")
        self.user_admin = User.objects.create_user(
            username="admin", password="x", is_superuser=True, is_staff=True
        )

        CampagnaUtente.objects.create(campagna=self.campagna, user=self.user_player, ruolo=CAMPAGNA_ROLE_PLAYER, attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.user_redactor, ruolo=CAMPAGNA_ROLE_REDACTOR, attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.user_staffer, ruolo=CAMPAGNA_ROLE_STAFFER, attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.user_master, ruolo=CAMPAGNA_ROLE_MASTER, attivo=True)
        CampagnaUtente.objects.create(campagna=self.campagna, user=self.user_head, ruolo=CAMPAGNA_ROLE_HEAD_MASTER, attivo=True)

        self.page_public = PaginaRegolamento.objects.create(
            titolo="Public",
            slug="public-page",
            public=True,
            visibile_solo_staff=False,
        )
        self.page_staff = PaginaRegolamento.objects.create(
            titolo="Staff",
            slug="staff-page",
            public=True,
            visibile_solo_staff=True,
        )
        self.page_draft = PaginaRegolamento.objects.create(
            titolo="Draft",
            slug="draft-page",
            public=False,
            visibile_solo_staff=False,
        )

    def _get(self, user, url):
        self.client.force_authenticate(user=user)
        return self.client.get(url, HTTP_X_CAMPAGNA=self.campagna.slug)

    def _patch_page_title(self, user, page, title):
        self.client.force_authenticate(user=user)
        return self.client.patch(
            f"/api/plot/api/staff/pagine-regolamento/{page.id}/",
            {"titolo": title},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_visibility_matrix(self):
        # PLAYER: solo pagine public e non staff.
        menu_player = self._get(self.user_player, "/api/plot/api/wiki/menu/")
        self.assertEqual(menu_player.status_code, status.HTTP_200_OK)
        slugs_player = {row["slug"] for row in menu_player.data}
        self.assertIn(self.page_public.slug, slugs_player)
        self.assertNotIn(self.page_staff.slug, slugs_player)
        self.assertNotIn(self.page_draft.slug, slugs_player)

        page_draft_player = self._get(self.user_player, f"/api/plot/api/wiki/pagina/{self.page_draft.slug}/")
        self.assertEqual(page_draft_player.status_code, status.HTTP_404_NOT_FOUND)

        page_staff_player = self._get(self.user_player, f"/api/plot/api/wiki/pagina/{self.page_staff.slug}/")
        self.assertEqual(page_staff_player.status_code, status.HTTP_404_NOT_FOUND)

        # REDACTOR / STAFFER: vedono draft non staff, ma non staff-only.
        for user in (self.user_redactor, self.user_staffer):
            with self.subTest(user=user.username):
                menu = self._get(user, "/api/plot/api/wiki/menu/")
                self.assertEqual(menu.status_code, status.HTTP_200_OK)
                slugs = {row["slug"] for row in menu.data}
                self.assertIn(self.page_public.slug, slugs)
                self.assertIn(self.page_draft.slug, slugs)
                self.assertNotIn(self.page_staff.slug, slugs)

        # MASTER / HEAD / ADMIN: visione completa.
        for user in (self.user_master, self.user_head, self.user_admin):
            with self.subTest(user=user.username):
                menu = self._get(user, "/api/plot/api/wiki/menu/")
                self.assertEqual(menu.status_code, status.HTTP_200_OK)
                slugs = {row["slug"] for row in menu.data}
                self.assertIn(self.page_public.slug, slugs)
                self.assertIn(self.page_draft.slug, slugs)
                self.assertIn(self.page_staff.slug, slugs)

    def test_edit_matrix_non_staff_pages(self):
        # Non-staff page editable by redactor/staffer/master/head/admin.
        allowed_users = (
            self.user_redactor,
            self.user_staffer,
            self.user_master,
            self.user_head,
            self.user_admin,
        )
        for user in allowed_users:
            with self.subTest(user=user.username):
                resp = self._patch_page_title(user, self.page_draft, f"Draft {user.username}")
                self.assertEqual(resp.status_code, status.HTTP_200_OK)

        # Player sempre bloccato in modifica.
        denied = self._patch_page_title(self.user_player, self.page_draft, "Draft blocked")
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_edit_matrix_staff_only_pages(self):
        # Staff-only editable solo da master/head/admin.
        allowed_users = (self.user_master, self.user_head, self.user_admin)
        for user in allowed_users:
            with self.subTest(user=user.username):
                resp = self._patch_page_title(user, self.page_staff, f"Staff {user.username}")
                self.assertEqual(resp.status_code, status.HTTP_200_OK)

        denied_users = (self.user_player, self.user_redactor, self.user_staffer)
        for user in denied_users:
            with self.subTest(user=user.username):
                resp = self._patch_page_title(user, self.page_staff, "Staff blocked")
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def _create_page(self, user, *, slug, staff_only, public=True):
        self.client.force_authenticate(user=user)
        return self.client.post(
            "/api/plot/api/staff/pagine-regolamento/",
            {
                "titolo": f"Create {slug}",
                "slug": slug,
                "contenuto": "<p>Test</p>",
                "public": public,
                "visibile_solo_staff": staff_only,
                "ordine": 0,
                "parent": None,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def test_create_matrix_non_staff_pages(self):
        # Non-staff page: consentita a redactor/staffer/master/head/admin.
        allowed_users = (
            self.user_redactor,
            self.user_staffer,
            self.user_master,
            self.user_head,
            self.user_admin,
        )
        for user in allowed_users:
            with self.subTest(user=user.username):
                resp = self._create_page(
                    user,
                    slug=f"create-nonstaff-{user.username}",
                    staff_only=False,
                    public=False,
                )
                self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        denied = self._create_page(
            self.user_player,
            slug="create-nonstaff-player",
            staff_only=False,
            public=True,
        )
        self.assertEqual(denied.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_matrix_staff_only_pages(self):
        # Staff-only page: consentita solo a master/head/admin.
        allowed_users = (self.user_master, self.user_head, self.user_admin)
        for user in allowed_users:
            with self.subTest(user=user.username):
                resp = self._create_page(
                    user,
                    slug=f"create-staff-{user.username}",
                    staff_only=True,
                    public=True,
                )
                self.assertEqual(resp.status_code, status.HTTP_201_CREATED)

        denied_users = (self.user_player, self.user_redactor, self.user_staffer)
        for user in denied_users:
            with self.subTest(user=user.username):
                resp = self._create_page(
                    user,
                    slug=f"create-staff-denied-{user.username}",
                    staff_only=True,
                    public=True,
                )
                self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
