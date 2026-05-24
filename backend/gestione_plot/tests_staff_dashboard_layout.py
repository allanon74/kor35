from django.core.exceptions import ValidationError
from django.test import SimpleTestCase

from gestione_plot.staff_dashboard_layout import (
    default_staff_dashboard_layout,
    effective_staff_dashboard_layout,
    validate_staff_dashboard_layout,
)


class StaffDashboardLayoutTests(SimpleTestCase):
    def test_default_layout_valido(self):
        layout = default_staff_dashboard_layout()
        validated = validate_staff_dashboard_layout(layout)
        self.assertEqual(validated["version"], 1)
        self.assertGreater(len(validated["groups"]), 0)

    def test_tool_duplicato_in_gruppi_rifiutato(self):
        layout = default_staff_dashboard_layout()
        layout["groups"][0]["tool_ids"] = layout["groups"][1]["tool_ids"][:1]
        with self.assertRaises(ValidationError):
            validate_staff_dashboard_layout(layout)

    def test_layout_corrotto_fallback(self):
        effective = effective_staff_dashboard_layout({"version": 99})
        self.assertEqual(effective["version"], 1)

    def test_tool_labels_e_palette(self):
        layout = default_staff_dashboard_layout()
        layout["tool_labels"] = {"plot": "Plot operativo"}
        layout["groups"][0]["palette"] = "indigo"
        validated = validate_staff_dashboard_layout(layout)
        self.assertEqual(validated["tool_labels"]["plot"], "Plot operativo")
        self.assertEqual(validated["groups"][0]["palette"], "indigo")

    def test_palette_non_valida(self):
        layout = default_staff_dashboard_layout()
        layout["groups"][0]["palette"] = "rainbow"
        with self.assertRaises(ValidationError):
            validate_staff_dashboard_layout(layout)

    def test_scommesse_tool_nel_default(self):
        from gestione_plot.staff_dashboard_layout import KNOWN_STAFF_TOOL_IDS

        self.assertIn("scommesse", KNOWN_STAFF_TOOL_IDS)
        layout = default_staff_dashboard_layout()
        evento_tools = layout["groups"][0]["tool_ids"]
        self.assertIn("scommesse", evento_tools)
        validate_staff_dashboard_layout(layout)
