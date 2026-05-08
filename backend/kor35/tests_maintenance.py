from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from gestione_plot.models import ConfigurazioneSito


class MaintenanceModeMiddlewareTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.config = ConfigurazioneSito.get_config()
        self.config.maintenance_mode = True
        self.config.maintenance_public_message = "Manutenzione di test"
        self.config.save(update_fields=["maintenance_mode", "maintenance_public_message"])

        user_model = get_user_model()
        self.superuser = user_model.objects.create_superuser(
            username="super",
            email="super@example.com",
            password="x",
        )
        self.staff_user = user_model.objects.create_user(
            username="staff",
            email="staff@example.com",
            password="x",
            is_staff=True,
        )

    def test_blocked_api_returns_503_with_message(self):
        response = self.client.get("/api/social/posts/")
        self.assertEqual(response.status_code, 503)
        payload = response.json()
        self.assertTrue(payload["maintenance_mode"])
        self.assertEqual(payload["maintenance_message"], "Manutenzione di test")

    def test_admin_non_superuser_forbidden(self):
        self.client.force_login(self.staff_user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 403)

    def test_admin_superuser_allowed(self):
        self.client.force_login(self.superuser)
        response = self.client.get("/admin/")
        self.assertNotEqual(response.status_code, 403)
