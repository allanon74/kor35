from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from .models import Campagna, CampagnaUtente


class CampagnaAdminApiTests(APITestCase):
    def setUp(self):
        self.staff = User.objects.create_user(username="staff", password="x", is_staff=True)
        self.client.force_authenticate(user=self.staff)

        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )

    def test_create_new_default_unsets_previous_default(self):
        response = self.client.post(
            "/api/personaggi/api/staff/campagne/",
            {
                "slug": "campagna-b",
                "nome": "Campagna B",
                "is_default": True,
                "is_base": False,
                "attiva": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.kor35.refresh_from_db()
        self.assertFalse(self.kor35.is_default)

    def test_update_last_default_to_false_is_blocked(self):
        response = self.client.patch(
            f"/api/personaggi/api/staff/campagne/{self.kor35.id}/",
            {"is_default": False},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("is_default", response.data)

    def test_create_new_base_unsets_previous_base(self):
        response = self.client.post(
            "/api/personaggi/api/staff/campagne/",
            {
                "slug": "campagna-c",
                "nome": "Campagna C",
                "is_default": False,
                "is_base": True,
                "attiva": True,
            },
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.kor35.refresh_from_db()
        self.assertFalse(self.kor35.is_base)


class ActiveCampaignValidationTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="player", password="x")
        self.client.force_authenticate(user=self.user)
        self.kor35 = Campagna.objects.create(
            slug="kor35",
            nome="Kor35",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        self.alt = Campagna.objects.create(
            slug="alt-camp",
            nome="Alt Camp",
            is_default=False,
            is_base=False,
            attiva=True,
        )

    def test_validate_non_member_campaign_returns_403(self):
        response = self.client.post(
            "/api/personaggi/api/campagne/active/",
            {"slug": "alt-camp"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_validate_member_campaign_returns_200(self):
        CampagnaUtente.objects.create(
            campagna=self.alt,
            user=self.user,
            ruolo="PLAYER",
            attivo=True,
        )
        response = self.client.post(
            "/api/personaggi/api/campagne/active/",
            {"slug": "alt-camp"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get("slug"), "alt-camp")
