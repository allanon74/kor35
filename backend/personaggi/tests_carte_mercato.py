"""Test mercato scambio carte."""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from personaggi.carte_collezionabili_models import (
    CARTA_ENERGIA_MARZIALE,
    CARTA_RARITA_COMUNE,
    CARTA_TIPO_PERSONAGGIO,
    CARTE_ACCESSO_OPEN,
    CartaCollezionabile,
    CartaPosseduta,
    ConfigurazioneCarteCollezionabili,
    EspansioneCarte,
    OffertaScambioCarte,
    SCAMBIO_STATO_ACCETTATA,
    SCAMBIO_STATO_APERTA,
    SCAMBIO_STATO_ANNULLATA,
)
from personaggi.carte_mercato_service import (
    accetta_offerta_scambio,
    annulla_offerta_scambio,
    build_mercato_payload,
    crea_offerta_scambio,
)
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio

User = get_user_model()


class CarteMercatoServiceTests(TestCase):
    def setUp(self):
        self.user_a = User.objects.create_user(username="merc_a", password="test")
        self.user_b = User.objects.create_user(username="merc_b", password="test")
        self.campagna = Campagna.objects.create(slug="merc-test", nome="Merc Test", attiva=True)
        ConfigurazioneCarteCollezionabili.objects.create(
            campagna=self.campagna,
            accesso_modo=CARTE_ACCESSO_OPEN,
            mercato_commissione_pct=Decimal("10.00"),
        )
        tipologia = TipologiaPersonaggio.objects.create(nome="Umano", giocante=True)
        self.pg_a = Personaggio.objects.create(
            nome="Alice",
            proprietario=self.user_a,
            campagna=self.campagna,
            tipologia=tipologia,
        )
        self.pg_b = Personaggio.objects.create(
            nome="Bob",
            proprietario=self.user_b,
            campagna=self.campagna,
            tipologia=tipologia,
        )
        self.pg_a.modifica_crediti(Decimal("1000"), "Setup")
        self.pg_b.modifica_crediti(Decimal("500"), "Setup")
        esp = EspansioneCarte.objects.create(campagna=self.campagna, nome="Set", slug="set")
        self.carta_a = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="M-A",
            nome="Carta A",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
        )
        self.carta_b = CartaCollezionabile.objects.create(
            campagna=self.campagna,
            espansione=esp,
            codice="M-B",
            nome="Carta B",
            tipo=CARTA_TIPO_PERSONAGGIO,
            energia=CARTA_ENERGIA_MARZIALE,
            rarita=CARTA_RARITA_COMUNE,
        )
        self.cp_a = CartaPosseduta.objects.create(personaggio=self.pg_a, carta=self.carta_a)
        self.cp_b = CartaPosseduta.objects.create(personaggio=self.pg_b, carta=self.carta_b)

    def test_scambio_carte_tra_pg(self):
        crea_offerta_scambio(
            self.pg_a,
            carta_offerta_id=str(self.cp_a.id),
            richiesta_carta_id=str(self.carta_b.id),
        )
        offerta = OffertaScambioCarte.objects.get(stato=SCAMBIO_STATO_APERTA)
        accetta_offerta_scambio(
            self.pg_b,
            offerta.id,
            carta_contropartita_id=str(self.cp_b.id),
        )
        self.cp_a.refresh_from_db()
        self.cp_b.refresh_from_db()
        offerta.refresh_from_db()
        self.assertEqual(self.cp_a.personaggio_id, self.pg_b.id)
        self.assertEqual(self.cp_b.personaggio_id, self.pg_a.id)
        self.assertEqual(offerta.stato, SCAMBIO_STATO_ACCETTATA)
        self.assertEqual(offerta.accettante_id, self.pg_b.id)

    def test_scambio_solo_crediti(self):
        crea_offerta_scambio(
            self.pg_a,
            carta_offerta_id=str(self.cp_a.id),
            richiesta_crediti="100",
        )
        offerta = OffertaScambioCarte.objects.get()
        crediti_b_prima = self.pg_b.crediti
        crediti_a_prima = self.pg_a.crediti
        accetta_offerta_scambio(self.pg_b, offerta.id)
        self.assertEqual(self.pg_b.crediti, crediti_b_prima - Decimal("100"))
        self.assertEqual(self.pg_a.crediti, crediti_a_prima + Decimal("90"))
        offerta.refresh_from_db()
        self.assertEqual(offerta.commissione_crediti, Decimal("10.00"))

    def test_annulla_offerta(self):
        crea_offerta_scambio(
            self.pg_a,
            carta_offerta_id=str(self.cp_a.id),
            richiesta_crediti="50",
        )
        offerta = OffertaScambioCarte.objects.get()
        annulla_offerta_scambio(self.pg_a, offerta.id)
        offerta.refresh_from_db()
        self.assertEqual(offerta.stato, SCAMBIO_STATO_ANNULLATA)

    def test_mercato_payload_include_offerte(self):
        crea_offerta_scambio(
            self.pg_a,
            carta_offerta_id=str(self.cp_a.id),
            richiesta_crediti="25",
        )
        payload_b = build_mercato_payload(self.pg_b)
        self.assertEqual(len(payload_b["offerte_aperte"]), 1)
        payload_a = build_mercato_payload(self.pg_a)
        self.assertEqual(len(payload_a["mie_offerte"]), 1)

    def test_crea_offerta_senza_richiesta_fallisce(self):
        with self.assertRaises(ValidationError):
            crea_offerta_scambio(self.pg_a, carta_offerta_id=str(self.cp_a.id))
