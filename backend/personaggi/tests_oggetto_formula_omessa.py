"""
Formula d'attacco degli oggetti: se l'oggetto (o l'infusione che l'ha generato)
ha la formula vuota, nel rendering non deve comparire alcuna riga «Formula:».
"""
from django.contrib.auth.models import User
from django.test import TestCase

from personaggi.models import (
    AURA,
    DEFAULT_ATTACK_FORMULA_TEMPLATE,
    Campagna,
    Infusione,
    Oggetto,
    Personaggio,
    Punteggio,
)
from personaggi.serializers import OggettoSerializer


class OggettoFormulaOmessaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "KOR35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        cls.user = User.objects.create_user(username="formula_pg", password="test")
        cls.pg = Personaggio.objects.create(
            nome="Tecnico", proprietario=cls.user, campagna=cls.campagna
        )
        cls.aura = Punteggio.objects.create(
            nome="Aura formula", tipo=AURA, sigla="AFR", colore="#223344"
        )

    def _infusione(self, *, formula):
        return Infusione.objects.create(
            nome=f"Infusione {formula or 'senza formula'}",
            aura_richiesta=self.aura,
            formula_attacco=formula,
            campagna=self.campagna,
        )

    def _oggetto(self, *, attacco_base, infusione=None):
        return Oggetto.objects.create(
            nome="Materia di prova",
            testo="<p>Descrizione della materia.</p>",
            attacco_base=attacco_base,
            infusione_generatrice=infusione,
            aura=self.aura,
        )

    def test_formula_vuota_sull_oggetto_non_viene_resa(self):
        oggetto = self._oggetto(attacco_base="")
        self.assertEqual(oggetto.formula_attacco_effettiva, "")
        html = self.pg.get_testo_formattato_per_item(oggetto)
        self.assertIn("Descrizione della materia", html)
        self.assertNotIn("Formula:", html)

    def test_infusione_senza_formula_azzera_quella_dell_oggetto(self):
        """Il default del campo sull'istanza non deve generare formule fantasma."""
        infusione = self._infusione(formula="")
        oggetto = self._oggetto(
            attacco_base=DEFAULT_ATTACK_FORMULA_TEMPLATE, infusione=infusione
        )
        self.assertEqual(oggetto.formula_attacco_effettiva, "")
        html = self.pg.get_testo_formattato_per_item(oggetto)
        self.assertNotIn("Formula:", html)
        self.assertNotIn("Formula:", oggetto.TestoFormattato)

    def test_infusione_con_formula_mantiene_la_formula(self):
        infusione = self._infusione(formula="Mischia 1d10")
        oggetto = self._oggetto(attacco_base="Mischia 1d10", infusione=infusione)
        self.assertEqual(oggetto.formula_attacco_effettiva, "Mischia 1d10")
        html = self.pg.get_testo_formattato_per_item(oggetto)
        self.assertIn("Formula:", html)

    def test_oggetto_senza_infusione_mantiene_la_propria_formula(self):
        oggetto = self._oggetto(attacco_base="Mischia 1d10")
        self.assertEqual(oggetto.formula_attacco_effettiva, "Mischia 1d10")
        self.assertIn("Formula:", self.pg.get_testo_formattato_per_item(oggetto))

    def test_serializer_non_espone_attacco_quando_omesso(self):
        infusione = self._infusione(formula="   ")
        oggetto = self._oggetto(
            attacco_base=DEFAULT_ATTACK_FORMULA_TEMPLATE, infusione=infusione
        )
        data = OggettoSerializer(oggetto, context={"personaggio": self.pg}).data
        self.assertIsNone(data["attacco_base_effettivo"])
        self.assertIsNone(data["attacco_formattato"])

    def test_serializer_espone_attacco_quando_presente(self):
        oggetto = self._oggetto(attacco_base="Mischia 1d10")
        data = OggettoSerializer(oggetto, context={"personaggio": self.pg}).data
        self.assertEqual(data["attacco_base_effettivo"], "Mischia 1d10")
        self.assertTrue(data["attacco_formattato"])
