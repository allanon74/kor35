from django.test import TestCase

from personaggi.carte_collezionabili_models import CartaCollezionabile, EspansioneCarte
from personaggi.carte_set_codice import (
    build_carta_codice,
    renumber_carte_in_espansione,
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

    def test_renumber_sorts_by_energia_then_nome(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Demo",
            slug="demo",
        )
        # Inserite fuori ordine: MAG Z, MAR B, MAR A, TEC C
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="x-9",
            nome="Zebra Magica",
            tipo="PG",
            energia="MAG",
            rarita="COM",
            ordine_set=9,
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="x-8",
            nome="Bravo",
            tipo="PG",
            energia="MAR",
            rarita="COM",
            ordine_set=8,
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="x-7",
            nome="Alpha",
            tipo="PG",
            energia="MAR",
            rarita="COM",
            ordine_set=7,
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="x-6",
            nome="Charlie",
            tipo="PG",
            energia="TEC",
            rarita="COM",
            ordine_set=6,
        )

        summary = renumber_carte_in_espansione(self.campagna, esp)
        self.assertEqual(summary["updated"], 4)

        ordered = list(
            CartaCollezionabile.objects.filter(espansione=esp).order_by("ordine_set", "nome")
        )
        self.assertEqual(
            [(c.codice, c.nome, c.energia, c.ordine_set) for c in ordered],
            [
                ("demo-001", "Alpha", "MAR", 1),
                ("demo-002", "Bravo", "MAR", 2),
                ("demo-003", "Charlie", "TEC", 3),
                ("demo-004", "Zebra Magica", "MAG", 4),
            ],
        )
