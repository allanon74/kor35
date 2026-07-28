from django.test import TestCase

from personaggi.carte_collezionabili_models import CartaCollezionabile, EspansioneCarte
from personaggi.carte_set_codice import (
    build_carta_codice,
    renumber_carte_in_espansione,
    set_code_prefix,
    suggest_carta_codice_for_espansione,
    suggest_sigla_from_nome,
)
from personaggi.models import Campagna


class CarteSetCodiceTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(nome="Test", slug="test-codice")

    def test_suggest_sigla_kor_the_beginning(self):
        self.assertEqual(suggest_sigla_from_nome("KOR: the beginning"), "KBE")

    def test_build_carta_codice_uses_sigla_and_three_digits(self):
        self.assertEqual(build_carta_codice("KBE", 1), "KBE-001")
        self.assertEqual(build_carta_codice("kbe", 42), "KBE-042")

    def test_set_code_prefix_prefers_sigla(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="KOR: the beginning",
            slug="kor-the-beginning",
            sigla="KBE",
        )
        self.assertEqual(set_code_prefix(esp), "KBE")

    def test_suggest_next_number_in_expansion(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Sette Elegie",
            slug="sette-elegie",
            sigla="ELE",
        )
        CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="ELE-003",
            nome="Prima",
            tipo="PG",
            energia="MAR",
            rarita="COM",
            ordine_set=3,
        )
        ordine, codice = suggest_carta_codice_for_espansione(self.campagna, esp)
        self.assertEqual(ordine, 4)
        self.assertEqual(codice, "ELE-004")

    def test_suggest_ignores_unrelated_codice_prefix(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Alpha",
            slug="alpha",
            sigla="ALP",
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
        self.assertEqual(codice, "ALP-001")

    def test_renumber_sorts_by_energia_then_nome_with_sigla(self):
        esp = EspansioneCarte.objects.create(
            campagna=self.campagna,
            nome="Demo Set",
            slug="demo",
            sigla="DEM",
        )
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
        self.assertEqual(summary["sigla"], "DEM")

        ordered = list(
            CartaCollezionabile.objects.filter(espansione=esp).order_by("ordine_set", "nome")
        )
        self.assertEqual(
            [(c.codice, c.nome, c.energia, c.ordine_set) for c in ordered],
            [
                ("DEM-001", "Alpha", "MAR", 1),
                ("DEM-002", "Bravo", "MAR", 2),
                ("DEM-003", "Charlie", "TEC", 3),
                ("DEM-004", "Zebra Magica", "MAG", 4),
            ],
        )
