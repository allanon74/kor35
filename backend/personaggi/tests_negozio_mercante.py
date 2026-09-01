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

    def test_acquisto_mutazione_senza_requisiti_forgiatura(self):
        """Istanza da vetrina: aura/mattoni da artigiano non bloccano il montaggio."""
        from personaggi.economia_crediti import CONTO_CORRENTE
        from personaggi.models import (
            CARATTERISTICA,
            Infusione,
            InfusioneCaratteristica,
            Oggetto,
            Punteggio,
            SCELTA_RISULTATO_AUMENTO,
        )
        from personaggi.negozio_mercante_service import acquista_voce

        inf = Infusione.objects.create(
            nome="Mutazione pesante vetrina",
            aura_richiesta=self.aura,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD1",
            campagna=self.campagna,
        )
        car = Punteggio.objects.create(
            nome="Forza negozio mut", tipo=CARATTERISTICA, sigla="FNM"
        )
        InfusioneCaratteristica.objects.create(
            infusione=inf, caratteristica=car, valore=5
        )
        self.assertGreaterEqual(inf.livello, 5)
        self._fondi()
        voce = self._voce(inf, prezzo=90)
        result = acquista_voce(
            self.negozio, self.pg, voce.id, slot_corpo="HD1", conto=CONTO_CORRENTE
        )
        self.assertEqual(result["status"], "success")
        og = Oggetto.objects.get(pk=result["oggetto_id"])
        self.assertEqual(og.inventario_corrente.pk, self.pg.pk)
        self.assertTrue(og.is_equipaggiato)

    def test_acquisto_innesto_senza_ate_fallisce(self):
        from personaggi.economia_crediti import saldo_corrente
        from personaggi.models import (
            AURA,
            Infusione,
            Oggetto,
            Punteggio,
            SCELTA_RISULTATO_AUMENTO,
        )
        from personaggi.negozio_mercante_service import acquista_voce

        ate, _created = Punteggio.objects.get_or_create(
            sigla="ATE",
            defaults={
                "nome": "Aura Tecnologica",
                "tipo": AURA,
                "colore": "#334455",
            },
        )
        inf = Infusione.objects.create(
            nome="Innesto vetrina",
            aura_richiesta=ate,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD1",
            campagna=self.campagna,
        )
        self._fondi()
        voce = self._voce(inf, prezzo=90)
        prima = saldo_corrente(self.pg)
        with self.assertRaises(ValidationError) as ctx:
            acquista_voce(self.negozio, self.pg, voce.id, slot_corpo="HD1")
        self.assertIn("Aura Tecnologica", " ".join(ctx.exception.messages))
        self.assertEqual(saldo_corrente(self.pg), prima)
        self.assertEqual(
            Oggetto.objects.filter(infusione_generatrice=inf).count(), 0
        )

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

    def _assegna_ate(self, pg, valore=1):
        from personaggi.models import (
            AURA,
            CARATTERISTICA,
            Abilita,
            PersonaggioAbilita,
            Punteggio,
            abilita_punteggio,
        )

        ate, _created = Punteggio.objects.get_or_create(
            sigla="ATE",
            defaults={
                "nome": "Aura Tecnologica",
                "tipo": AURA,
                "colore": "#334455",
            },
        )
        car = Punteggio.objects.create(
            nome="Car ATE negozio", tipo=CARATTERISTICA, sigla="ATN"
        )
        ab = Abilita.objects.create(
            nome="Tratto ATE negozio",
            caratteristica=car,
            costo_pc=0,
            costo_crediti=0,
        )
        abilita_punteggio.objects.create(abilita=ab, punteggio=ate, valore=valore)
        PersonaggioAbilita.objects.create(personaggio=pg, abilita=ab)
        if hasattr(pg, "_punteggi_base_cache"):
            del pg._punteggi_base_cache
        return ate

    def _caratt(self, sigla, nome):
        from personaggi.models import CARATTERISTICA, Punteggio

        return Punteggio.objects.create(nome=nome, tipo=CARATTERISTICA, sigla=sigla)

    def test_acquisto_innesto_con_ate_ok(self):
        from personaggi.economia_crediti import CONTO_CORRENTE
        from personaggi.models import Infusione, Oggetto, SCELTA_RISULTATO_AUMENTO
        from personaggi.negozio_mercante_service import acquista_voce

        ate = self._assegna_ate(self.pg, 1)
        inf = Infusione.objects.create(
            nome="Innesto con ATE",
            aura_richiesta=ate,
            tipo_risultato=SCELTA_RISULTATO_AUMENTO,
            slot_corpo_permessi="HD1",
            campagna=self.campagna,
        )
        self._fondi()
        voce = self._voce(inf, prezzo=90)
        result = acquista_voce(
            self.negozio, self.pg, voce.id, slot_corpo="HD1", conto=CONTO_CORRENTE
        )
        self.assertEqual(result["status"], "success")
        og = Oggetto.objects.get(pk=result["oggetto_id"])
        self.assertEqual(og.tipo_oggetto, "INN")
        self.assertTrue(og.is_equipaggiato)

    def test_acquisto_innesto_oggetto_senza_infusione_richiede_ate(self):
        from personaggi.economia_crediti import saldo_corrente
        from personaggi.models import Oggetto, TIPO_OGGETTO_INNESTO
        from personaggi.negozio_mercante_models import NegozioMercanteVoce, VOCE_OGGETTO
        from personaggi.negozio_mercante_service import acquista_voce

        self.negozio.refresh_from_db()
        og = Oggetto.objects.create(nome="Innesto usato", tipo_oggetto=TIPO_OGGETTO_INNESTO)
        og.sposta_in_inventario(self.negozio.inventario)
        voce = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_OGGETTO,
            oggetto=og,
            prezzo_crediti=50,
            attivo=True,
        )
        self._fondi()
        prima = saldo_corrente(self.pg)
        with self.assertRaises(ValidationError) as ctx:
            acquista_voce(self.negozio, self.pg, voce.id, slot_corpo="HD1")
        self.assertIn("Aura Tecnologica", " ".join(ctx.exception.messages))
        self.assertEqual(saldo_corrente(self.pg), prima)

    def test_acquisto_materia_mod_oggetto_base_senza_requisiti(self):
        from personaggi.economia_crediti import CONTO_CORRENTE
        from personaggi.models import (
            Oggetto,
            OggettoBase,
            TIPO_OGGETTO_FISICO,
            TIPO_OGGETTO_MATERIA,
            TIPO_OGGETTO_MOD,
        )
        from personaggi.negozio_mercante_models import (
            NegozioMercanteVoce,
            VOCE_OGGETTO,
            VOCE_OGGETTO_BASE,
        )
        from personaggi.negozio_mercante_service import acquista_voce

        self._fondi()
        self.negozio.refresh_from_db()
        ob = OggettoBase.objects.create(nome="Coltello base", tipo_oggetto=TIPO_OGGETTO_FISICO)
        voce_ob = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_OGGETTO_BASE,
            oggetto_base=ob,
            prezzo_crediti=10,
            attivo=True,
        )
        r_ob = acquista_voce(self.negozio, self.pg, voce_ob.id, conto=CONTO_CORRENTE)
        self.assertEqual(r_ob["status"], "success")

        mat = Oggetto.objects.create(nome="Materia vetrina", tipo_oggetto=TIPO_OGGETTO_MATERIA)
        mat.sposta_in_inventario(self.negozio.inventario)
        voce_mat = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_OGGETTO,
            oggetto=mat,
            prezzo_crediti=10,
            attivo=True,
        )
        r_mat = acquista_voce(self.negozio, self.pg, voce_mat.id, conto=CONTO_CORRENTE)
        self.assertEqual(r_mat["status"], "success")
        mat.refresh_from_db()
        self.assertEqual(mat.inventario_corrente.pk, self.pg.pk)

        mod = Oggetto.objects.create(nome="Mod vetrina", tipo_oggetto=TIPO_OGGETTO_MOD)
        mod.sposta_in_inventario(self.negozio.inventario)
        voce_mod = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_OGGETTO,
            oggetto=mod,
            prezzo_crediti=10,
            attivo=True,
        )
        r_mod = acquista_voce(self.negozio, self.pg, voce_mod.id, conto=CONTO_CORRENTE)
        self.assertEqual(r_mod["status"], "success")

    def test_acquisto_ricetta_infusione_tessitura_cerimoniale_richiede_valida(self):
        from personaggi.economia_crediti import CONTO_CORRENTE, saldo_corrente
        from personaggi.models import (
            Cerimoniale,
            CerimonialeCaratteristica,
            Infusione,
            InfusioneCaratteristica,
            Tessitura,
            TessituraCaratteristica,
        )
        from personaggi.negozio_mercante_models import (
            NegozioMercanteVoce,
            VOCE_CERIMONIALE,
            VOCE_TESSITURA,
        )
        from personaggi.negozio_mercante_service import acquista_voce, build_listino

        car = self._caratt("NRQ", "Req negozio tecnica")
        inf = Infusione.objects.create(
            nome="Ricetta pesante",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        InfusioneCaratteristica.objects.create(infusione=inf, caratteristica=car, valore=4)
        tess = Tessitura.objects.create(
            nome="Tessitura pesante",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        TessituraCaratteristica.objects.create(tessitura=tess, caratteristica=car, valore=4)
        cer = Cerimoniale.objects.create(
            nome="Cerimoniale pesante",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        CerimonialeCaratteristica.objects.create(
            cerimoniale=cer, caratteristica=car, valore=4
        )

        self._fondi()
        prima = saldo_corrente(self.pg)
        voce_inf = self._voce(inf, prezzo=40, consegna_istanza=False)
        with self.assertRaises(ValidationError) as ctx_i:
            acquista_voce(self.negozio, self.pg, voce_inf.id, conto=CONTO_CORRENTE)
        self.assertIn("Aura", " ".join(ctx_i.exception.messages))

        voce_tes = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_TESSITURA,
            tessitura=tess,
            prezzo_crediti=40,
            attivo=True,
        )
        with self.assertRaises(ValidationError) as ctx_t:
            acquista_voce(self.negozio, self.pg, voce_tes.id, conto=CONTO_CORRENTE)
        self.assertIn("Aura", " ".join(ctx_t.exception.messages))

        voce_cer = NegozioMercanteVoce.objects.create(
            negozio=self.negozio,
            tipo_voce=VOCE_CERIMONIALE,
            cerimoniale=cer,
            prezzo_crediti=40,
            attivo=True,
        )
        with self.assertRaises(ValidationError) as ctx_c:
            acquista_voce(self.negozio, self.pg, voce_cer.id, conto=CONTO_CORRENTE)
        self.assertIn("Aura", " ".join(ctx_c.exception.messages))
        self.assertEqual(saldo_corrente(self.pg), prima)

        data = build_listino(self.negozio, self.pg)
        by_nome = {v["nome"]: v for v in data["voci"]}
        self.assertFalse(by_nome["Ricetta pesante"]["acquistabile"])
        self.assertFalse(by_nome["Tessitura pesante"]["acquistabile"])
        self.assertFalse(by_nome["Cerimoniale pesante"]["acquistabile"])

    def test_acquisto_istanza_materia_da_infusione_senza_requisiti(self):
        from personaggi.economia_crediti import CONTO_CORRENTE
        from personaggi.models import Infusione, InfusioneCaratteristica, Oggetto
        from personaggi.negozio_mercante_service import acquista_voce, build_listino

        car = self._caratt("NMT", "Mattone materia")
        InfusioneCaratteristica.objects.create(
            infusione=self.inf_pot, caratteristica=car, valore=5
        )
        self.assertGreaterEqual(self.inf_pot.livello, 5)
        self._fondi()
        voce = self._voce(self.inf_pot, prezzo=50, consegna_istanza=True)
        data = build_listino(self.negozio, self.pg)
        voce_l = next(v for v in data["voci"] if v["id"] == str(voce.id))
        self.assertTrue(voce_l["acquistabile"])
        self.assertFalse(voce_l.get("richiede_montaggio"))
        result = acquista_voce(self.negozio, self.pg, voce.id, conto=CONTO_CORRENTE)
        self.assertEqual(result["status"], "success")
        self.assertTrue(
            Oggetto.objects.filter(infusione_generatrice=self.inf_pot).exists()
        )
        self.assertFalse(self.pg.infusioni_possedute.filter(pk=self.inf_pot.pk).exists())

    def test_listino_mutazione_istanza_ignorare_requisiti_tecnica(self):
        from personaggi.models import InfusioneCaratteristica
        from personaggi.negozio_mercante_service import build_listino

        car = self._caratt("NMU", "Mattone mutazione")
        InfusioneCaratteristica.objects.create(
            infusione=self.inf_aum, caratteristica=car, valore=5
        )
        voce = self._voce(self.inf_aum, prezzo=90)
        data = build_listino(self.negozio, self.pg)
        voce_l = next(v for v in data["voci"] if v["id"] == str(voce.id))
        self.assertTrue(voce_l["acquistabile"])
        self.assertTrue(voce_l["richiede_montaggio"])
        self.assertFalse(voce_l.get("richiede_ate"))

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
