from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.test import APIClient

from .formula_builder import build_stats_by_selection


class FormulaBuilderLogicTests(TestCase):
    def test_build_stats_by_selection_resets_controlled_params(self):
        current = {"prefisso_puro": 1, "dardo": 1, "custom_param": 5}
        selections = {
            "formula_prefix": ["prefisso_diretto"],
            "formula_target": "tocco",
        }

        merged = build_stats_by_selection(current, selections)

        self.assertEqual(merged["prefisso_puro"], 0)
        self.assertEqual(merged["prefisso_diretto"], 1)
        self.assertEqual(merged["dardo"], 0)
        self.assertEqual(merged["tocco"], 1)
        self.assertEqual(merged["custom_param"], 5)


class FormulaBuilderApiTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            username="staff_formula_builder",
            password="test-pass-123",
            is_staff=True,
            is_superuser=True,
        )
        self.client.force_authenticate(user=self.user)

    def test_schema_endpoint_returns_sections(self):
        res = self.client.get("/api/personaggi/api/staff/formula-builder/schema/")
        self.assertEqual(res.status_code, 200)
        self.assertIn("sections", res.data)
        self.assertTrue(any(section.get("id") == "formula_status" for section in res.data["sections"]))

    def test_preview_endpoint_renders_status_with_duration(self):
        payload = {
            "formula": "{formula_status}",
            "stats_by_param": {"durata": 15},
            "selections": {"formula_status": "paralisi"},
            "custom_text": "testo libero",
        }
        res = self.client.post("/api/personaggi/api/staff/formula-builder/preview/", payload, format="json")
        self.assertEqual(res.status_code, 200)
        rendered = res.data.get("formula_rendered", "")
        self.assertIn("Paralisi 15 secondi!", rendered)
        self.assertTrue(rendered.endswith("testo libero"))
