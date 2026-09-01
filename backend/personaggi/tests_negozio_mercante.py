"""Test negozi mercante: anteprima vendita e associazione QR staff."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from rest_framework.test import APIClient

from personaggi.models import Campagna, Oggetto, OggettoInInventario, Personaggio, QrCode
from personaggi.negozio_mercante_models import NegozioMercante
from personaggi.negozio_mercante_service import preview_vendita_oggetto


class NegozioMercanteServiceTests(TestCase):
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
        cls.user = User.objects.create_user(username="negozio_pg", password="test")
        cls.pg = Personaggio.objects.create(nome="Venditore", proprietario=cls.user, campagna=cls.campagna)
        cls.negozio = NegozioMercante.objects.create(
            nome="Mercante test",
            campagna=cls.campagna,
            saldo_crediti=Decimal("5000"),
            regole_apertura={"modalita": "sempre_aperto"},
        )
        cls.oggetto = Oggetto.objects.create(nome="Pugnale", costo_acquisto=100)
        OggettoInInventario.objects.create(oggetto=cls.oggetto, inventario=cls.pg)

    def test_preview_vendita_fascia_offerta(self):
        data = preview_vendita_oggetto(self.negozio, self.pg, self.oggetto.id)
        self.assertEqual(data["nome"], "Pugnale")
        self.assertGreaterEqual(data["offerta_max"], data["offerta_min"])
        self.assertTrue(data["cassa_sufficiente"])


class NegozioMercanteAssociaQrApiTests(TestCase):
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
        cls.staff = User.objects.create_superuser(
            username="staff_negozio",
            password="test",
            email="staff@test.local",
        )
        cls.negozio = NegozioMercante.objects.create(nome="Bottega QR", campagna=cls.campagna)
        cls.qr = QrCode.objects.create(testo="NEGOZIO-TEST-QR")

    def test_associa_e_scollega_qr(self):
        client = APIClient()
        client.force_authenticate(user=self.staff)
        url = f"/api/personaggi/api/staff/negozi-mercante/{self.negozio.id}/associa-qr/"
        res = client.post(url, {"qr_id": self.qr.id}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res.status_code, 200)
        self.negozio.refresh_from_db()
        self.assertEqual(self.negozio.qr_code_id, self.qr.id)

        res2 = client.post(url, {"qr_id": None}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res2.status_code, 200)
        self.negozio.refresh_from_db()
        self.assertIsNone(self.negozio.qr_code_id)

    def test_associa_qr_imposta_vista_portale(self):
        from personaggi.models import NegozioMercantePortale

        client = APIClient()
        client.force_authenticate(user=self.staff)
        url = f"/api/personaggi/api/staff/negozi-mercante/{self.negozio.id}/associa-qr/"
        res = client.post(url, {"qr_id": self.qr.id}, format="json", HTTP_X_CAMPAGNA="kor35")
        self.assertEqual(res.status_code, 200)
        self.negozio.refresh_from_db()
        self.qr.refresh_from_db()
        portale = NegozioMercantePortale.objects.get(negozio=self.negozio)
        self.assertEqual(self.qr.vista_id, portale.pk)
        self.assertEqual(self.negozio.qr_code_id, self.qr.id)


class NegozioMercanteAcquistoAumentoTests(TestCase):
    """Acquisto infusioni-istanza, valuta duale e montaggio innesto/mutazione."""

    @classmethod
    def setUpTestData(cls):
        from personaggi.campagna_moduli import MODULO_ACCESSO_OPEN, MODULO_CONTO_DEPOSITO, apply_moduli_accesso
        from personaggi.models import (
            AURA,
            Infusione,
            Punteggio,
            SCELTA_RISULTATO_AUMENTO,
            SCELTA_RISULTATO_POTENZIAMENTO,
            TIPO_OGGETTO_MUTAZIONE,
        )

        cls.campagna, _ = Campagna.objects.get_or_create(
            slug="kor35",
            defaults={
                "nome": "KOR35",
                "is_default": True,
                "is_base": True,
                "attiva": True,
            },
        )
        apply_moduli_accesso(cls.campagna, {MODULO_CONTO_DEPOSITO: MODULO_ACCESSO_OPEN})
        cls.user = User.objects.create_user(username="negozio_buyer", password="test")
        cls.altro_user = User.objects.create_user(username="negozio_paziente", password="test")
        cls.pg = Personaggio.objects.create(
            nome="Acquirente", proprietario=cls.user, campagna=cls.campagna
        )
        cls.paziente = Personaggio.objects.create(
            nome="Paziente", proprietario=cls.altro_user, campagna=cls.campagna
        )
        cls.aura = Punteggio.objects.create(
            nome="Aura negozio mut", tipo=AURA, sigla="NMA", colore="#334455"
        )
        cls.inf_aum = Infusione.objects.create(
            nome="Mutazione vetrina",
            aura_richiesta=cls.aura,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD1,HD2",
            campagna=cls.campagna,
        )
        cls.inf_pot = Infusione.objects.create(
            nome="Ricetta vetrina",
            aura_richiesta=cls.aura,
            tipo_risultato=SCELTA_RISULTATO_POTENZIAMENTO,
            campagna=cls.campagna,
        )
        cls.negozio = NegozioMercante.objects.create(
            nome="Clinica test",
            campagna=cls.campagna,
            saldo_crediti=Decimal("0"),
            regole_apertura={"modalita": "sempre_aperto"},
        )
        cls.TIPO_OGGETTO_MUTAZIONE = TIPO_OGGETTO_MUTAZIONE

    def _fondi(self, pg=None, corrente="400", deposito="200"):
        from personaggi.economia_crediti import CONTO_CORRENTE, CONTO_DEPOSITO, modifica_crediti

        target = pg or self.pg
        modifica_crediti(target, Decimal(corrente), "fondi corrente test", conto=CONTO_CORRENTE)
        modifica_crediti(target, Decimal(deposito), "fondi deposito test", conto=CONTO_DEPOSITO)

    def _voce(self, infusione, *, prezzo=90, consegna_istanza=False):
        from personaggi.negozio_mercante_models import NegozioMercanteVoce, VOCE_INFUSIONE

        return NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_INFUSIONE,
            infusione=infusione,
            prezzo_crediti=prezzo,
            consegna_istanza=consegna_istanza,
            attivo=True,
        )

    def test_listino_espone_prezzi_duali_e_montaggio(self):
        from personaggi.negozio_mercante_service import build_listino

        self._voce(self.inf_aum, prezzo=90)
        data = build_listino(self.negozio, self.pg)
        self.assertTrue(data["economia"]["modulo_attivo"])
        voce = data["voci"][0]
        self.assertTrue(voce["richiede_montaggio"])
        self.assertTrue(voce["consegna_istanza"])
        self.assertEqual(voce["prezzo_corrente"], "90.00")
        self.assertEqual(voce["prezzo_deposito"], "100.00")
        self.assertIn("HD1", [s["code"] for s in voce["slot_disponibili"]])

    def test_acquisto_mutazione_monta_su_acquirente(self):
        from personaggi.economia_crediti import CONTO_CORRENTE, saldo_corrente
        from personaggi.models import Oggetto
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_corrente(self.pg)
        result = acquista_voce(
            self.negozio, self.pg, voce.id, slot_corpo="HD1", conto=CONTO_CORRENTE
        )
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["slot_corpo"], "HD1")
        og = Oggetto.objects.get(pk=result["oggetto_id"])
        self.assertEqual(og.tipo_oggetto, self.TIPO_OGGETTO_MUTAZIONE)
        self.assertEqual(og.slot_corpo, "HD1")
        self.assertTrue(og.is_equipaggiato)
        self.assertEqual(og.inventario_corrente.pk, self.pg.pk)
        self.assertEqual(saldo_corrente(self.pg), prima - Decimal("90.00"))
        self.assertFalse(self.pg.infusioni_possedute.filter(pk=self.inf_aum.pk).exists())

    def test_acquisto_senza_slot_non_addebita(self):
        from personaggi.economia_crediti import saldo_corrente
        from personaggi.models import Oggetto
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_corrente(self.pg)
        with self.assertRaises(ValidationError):
            acquista_voce(self.negozio, self.pg, voce.id)
        self.assertEqual(saldo_corrente(self.pg), prima)
        self.assertFalse(
            Oggetto.objects.filter(infusione_generatrice=self.inf_aum).exists()
        )

    def test_acquisto_slot_occupato_annulla(self):
        from personaggi.economia_crediti import saldo_corrente
        from personaggi.models import Oggetto, TIPO_OGGETTO_MUTAZIONE
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        occupante = Oggetto.objects.create(
            nome="Occupante HD1",
            tipo_oggetto=TIPO_OGGETTO_MUTAZIONE,
            slot_corpo="HD1",
            is_equipaggiato=True,
        )
        occupante.sposta_in_inventario(self.pg)
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_corrente(self.pg)
        with self.assertRaises(ValidationError) as ctx:
            acquista_voce(self.negozio, self.pg, voce.id, slot_corpo="HD1")
        self.assertIn("annullato", " ".join(ctx.exception.messages).lower())
        self.assertEqual(saldo_corrente(self.pg), prima)
        self.assertEqual(
            Oggetto.objects.filter(infusione_generatrice=self.inf_aum).count(), 0
        )

    def test_acquisto_monta_su_terzi(self):
        from personaggi.economia_crediti import CONTO_CORRENTE, saldo_corrente
        from personaggi.models import Oggetto
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_corrente(self.pg)
        result = acquista_voce(
            self.negozio,
            self.pg,
            voce.id,
            slot_corpo="HD2",
            conto=CONTO_CORRENTE,
            destinatario_id=self.paziente.id,
        )
        og = Oggetto.objects.get(pk=result["oggetto_id"])
        self.assertEqual(og.inventario_corrente.pk, self.paziente.pk)
        self.assertEqual(og.slot_corpo, "HD2")
        self.assertTrue(og.is_equipaggiato)
        self.assertEqual(result["montato_su"], self.paziente.id)
        self.assertEqual(saldo_corrente(self.pg), prima - Decimal("90.00"))

    def test_acquisto_terzi_slot_occupato_annulla(self):
        from personaggi.economia_crediti import saldo_corrente
        from personaggi.models import Oggetto, TIPO_OGGETTO_MUTAZIONE
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        occupante = Oggetto.objects.create(
            nome="Occupante paziente",
            tipo_oggetto=TIPO_OGGETTO_MUTAZIONE,
            slot_corpo="HD1",
            is_equipaggiato=True,
        )
        occupante.sposta_in_inventario(self.paziente)
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_corrente(self.pg)
        with self.assertRaises(ValidationError):
            acquista_voce(
                self.negozio,
                self.pg,
                voce.id,
                slot_corpo="HD1",
                destinatario_id=self.paziente.id,
            )
        self.assertEqual(saldo_corrente(self.pg), prima)
        self.assertEqual(
            Oggetto.objects.filter(infusione_generatrice=self.inf_aum).count(), 0
        )

    def test_acquisto_con_deposito(self):
        from personaggi.economia_crediti import CONTO_DEPOSITO, saldo_deposito
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        voce = self._voce(self.inf_aum, prezzo=90)
        prima = saldo_deposito(self.pg)
        result = acquista_voce(
            self.negozio, self.pg, voce.id, slot_corpo="HD1", conto=CONTO_DEPOSITO
        )
        self.assertEqual(result["conto"], CONTO_DEPOSITO)
        self.assertEqual(Decimal(result["prezzo_pagato"]), Decimal("100.00"))
        self.assertEqual(saldo_deposito(self.pg), prima - Decimal("100.00"))

    def test_infusione_pot_resta_ricetta(self):
        from personaggi.economia_crediti import CONTO_CORRENTE
        from personaggi.models import Oggetto
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        voce = self._voce(self.inf_pot, prezzo=50, consegna_istanza=False)
        acquista_voce(self.negozio, self.pg, voce.id, conto=CONTO_CORRENTE)
        self.assertTrue(self.pg.infusioni_possedute.filter(pk=self.inf_pot.pk).exists())
        self.assertFalse(
            Oggetto.objects.filter(infusione_generatrice=self.inf_pot).exists()
        )

    def test_api_acquisto_mutazione(self):
        from personaggi.economia_crediti import CONTO_CORRENTE

        self._fondi()
        voce = self._voce(self.inf_aum, prezzo=90)
        client = APIClient()
        client.force_authenticate(user=self.user)
        url = f"/api/personaggi/api/negozi-mercante/{self.negozio.id}/acquista/"
        res = client.post(
            url,
            {
                "char_id": self.pg.id,
                "voce_id": str(voce.id),
                "slot_corpo": "HD1",
                "conto": CONTO_CORRENTE,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 200, res.data)
        self.assertEqual(res.data["slot_corpo"], "HD1")
