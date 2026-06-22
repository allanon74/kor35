from decimal import Decimal

from django.test import SimpleTestCase

from gestione_plot.evento_coordinate import (
    build_navigatore_links,
    evento_ha_info_logistiche,
    normalize_evento_coordinates,
    parse_coordinates_from_text,
)


class EventoCoordinateTests(SimpleTestCase):
    def test_parse_pair_virgola(self):
        lat, lng = parse_coordinates_from_text("45.123456, 7.654321")
        self.assertEqual(lat, Decimal("45.123456"))
        self.assertEqual(lng, Decimal("7.654321"))

    def test_parse_google_maps_url(self):
        lat, lng = parse_coordinates_from_text(
            "https://www.google.com/maps/@45.5,7.5,15z"
        )
        self.assertEqual(lat, Decimal("45.500000"))
        self.assertEqual(lng, Decimal("7.500000"))

    def test_normalize_entrambi_vuoti(self):
        lat, lng = normalize_evento_coordinates(None, "")
        self.assertIsNone(lat)
        self.assertIsNone(lng)

    def test_normalize_solo_un_campo_errore(self):
        with self.assertRaises(ValueError):
            normalize_evento_coordinates("45.0", None)

    def test_ha_info_logistiche_testo_o_coordinate(self):
        self.assertTrue(evento_ha_info_logistiche("<p>Parcheggio lato nord</p>", None, None))
        self.assertTrue(evento_ha_info_logistiche("", "45.0", "7.0"))
        self.assertFalse(evento_ha_info_logistiche("<p></p>", None, None))
        self.assertFalse(evento_ha_info_logistiche("", "45.0", None))

    def test_link_navigatore(self):
        links = build_navigatore_links(Decimal("45.1"), Decimal("7.2"))
        self.assertIn("geo:45.1,7.2", links["geo"])
        self.assertIn("google.com/maps", links["google_maps"])
