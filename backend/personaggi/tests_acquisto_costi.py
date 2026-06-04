"""
Test anti-exploit: rimborso revoca = costo pagato, non prezzo di listino corrente.
"""
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from personaggi.acquisto_costi import calcola_costo_tecnica_acquisto, rimborso_crediti_da_pivot
from personaggi.models import (
    Campagna,
    Personaggio,
    PersonaggioTessitura,
    Punteggio,
    Tessitura,
    TipologiaPersonaggio,
    AURA,
)


class RimborsoCostoPagatoTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="pg_costi", password="x")
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="Std costi test",
            crediti_iniziali=Decimal("10000"),
            caratteristiche_iniziali=20,
        )
        self.campagna = Campagna.objects.create(nome="Camp costi", slug="camp-costi")
        self.personaggio = Personaggio.objects.create(
            nome="Eroe",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.aura = Punteggio.objects.create(nome="Aura Costi", sigla="ACO", tipo=AURA)
        self.tessitura = Tessitura.objects.create(
            nome="Tess Test",
            testo="x",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )

    def test_rimborso_usa_costo_pagato_sul_pivot(self):
        pivot = PersonaggioTessitura.objects.create(
            personaggio=self.personaggio,
            tessitura=self.tessitura,
            costo_crediti_pagato=Decimal("500"),
            data_acquisizione=timezone.now(),
        )
        refund = rimborso_crediti_da_pivot(
            pivot, item=self.tessitura, acquired_at=pivot.data_acquisizione
        )
        self.assertEqual(refund, Decimal("500"))

    def test_acquisto_tecnica_applica_sconto_rct(self):
        with patch.object(Personaggio, "get_valore_statistica", return_value=50):
            with patch.object(
                type(self.tessitura),
                "costo_crediti",
                property(lambda self: 1000),
            ):
                costo = calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(costo, 500)

    def test_rimborso_restituisce_pagato_anche_se_sconto_attuale_sparito(self):
        """Dopo rimozione comprensione il listino torna pieno; il pivot resta a 500."""
        with patch.object(Personaggio, "get_valore_statistica", return_value=0):
            with patch.object(
                type(self.tessitura),
                "costo_crediti",
                property(lambda self: 1000),
            ):
                listino = calcola_costo_tecnica_acquisto(self.personaggio, self.tessitura)
        self.assertEqual(listino, 1000)

        pivot = PersonaggioTessitura.objects.create(
            personaggio=self.personaggio,
            tessitura=self.tessitura,
            costo_crediti_pagato=Decimal("500"),
            data_acquisizione=timezone.now(),
        )
        refund = rimborso_crediti_da_pivot(
            pivot, item=self.tessitura, acquired_at=pivot.data_acquisizione
        )
        self.assertEqual(refund, Decimal("500"))
        self.assertNotEqual(refund, Decimal("1000"))
