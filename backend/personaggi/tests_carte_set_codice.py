from django.test import TestCase

from personaggi.carte_collezionabili_models import CartaCollezionabile, EspansioneCarte
from personaggi.carte_set_codice import (
    build_carta_codice,
    suggest_carta_codice_for_espansione,
)
from personaggi.models import Campagna


class CarteSetCodiceTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(nome="Test", slug="test-codice")

    def test_build_carta_codice_uses_set_slug_and_three_digits(self):
        self.assertEqual(build_carta_codice("sette-elegie", 1), "sette-elegie-001")
        self.assertEqual(build_carta_codice("sette-elegie", 42), "sette-elegie-042")

    def test_suggest_next_number_in_expansion(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Sette Elegie",
            slug="sette-elegie",
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="sette-elegie-003",
            nome="Prima",
            tipo="PG",
            energia="MAR",
            rarita="COM",
            ordine_set=3,
        )
        ordine, codice = suggest_carta_codice_for_espansione(self.campagna, esp)
        self.assertEqual(ordine, 4)
        self.assertEqual(codice, "sette-elegie-004")

    def test_suggest_ignores_unrelated_codice_prefix(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Alpha",
            slug="alpha",
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="legacy-OLD-001",
            nome="Legacy",
            tipo="PG",
            energia="MAR",
            rarita="COM",
        )
        ordine, codice = suggest_carta_codice_for_espansione(self.campagna, esp)
        self.assertEqual(ordine, 1)
        self.assertEqual(codice, "alpha-001")
