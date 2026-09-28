"""Motore contratti: slot, firma, esclusività, effetti e modulo spento."""
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
import uuid

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import RequestFactory, SimpleTestCase, TestCase
from django.utils import timezone

from gestione_plot.models import Evento
from personaggi.contratti_effetti import calcola_post_tetto, render_testo_contratto
from personaggi.contratti_models import STATO_ANNULLATO, STATO_IN_ATTESA, STATO_STIPULATO
from personaggi.contratti_service import (
    annulla_proposta,
    costo_con_sconto_contratto,
    crea_preset,
    crea_proposta,
    firma_contratto,
    on_evento_terminato,
    riepilogo_ruoli,
    on_task_reclamata,
    risposta_qr_contratto,
    slot_liberi,
    slot_totali,
    slot_usati,
    tab_visibile,
)
from personaggi.economia_crediti import CONTO_CORRENTE, saldo_conto
from personaggi.models import (
    TIER_3,
    Campagna,
    Carica,
    Carriera,
    Personaggio,
    PersonaggioCarrieraMembership,
    Statistica,
    TipologiaPersonaggio,
    TipoCarriera,
)
from social.models import SocialPost

User = get_user_model()


class CalcolaPostTettoTests(SimpleTestCase):
    def test_esempi_tetto_tre_per_trenta(self):
        casi = {
            0: (Decimal("0.00"), Decimal("90.00"), Decimal("90.00"), Decimal("-90.00")),
            2: (Decimal("60.00"), Decimal("30.00"), Decimal("90.00"), Decimal("30.00")),
            3: (Decimal("90.00"), Decimal("0.00"), Decimal("90.00"), Decimal("90.00")),
            5: (Decimal("90.00"), Decimal("0.00"), Decimal("90.00"), Decimal("90.00")),
        }
        for n_post, atteso in casi.items():
            piano = calcola_post_tetto(n_post, 3, 30)
            self.assertEqual(
                (piano["creato_ciascuno"], piano["indennizzo"], piano["netto_cliente"], piano["netto_proponente"]),
                atteso,
                n_post,
            )


class RenderTestoContrattoTests(SimpleTestCase):
    def test_sostituisce_parametri_e_non_confonde_il_blocco(self):
        testo = (
            "{{proponente}} ({{korp}}) propone a {{cliente}} fino al {{scadenza}}.\n"
            "Bonus {{param:pct_cliente}}% e {{ param: pct_proponente }}%.\n"
            "{{parametri}}"
        )
        reso = render_testo_contratto(
            testo,
            proponente="Ada",
            cliente="il sottoscrittore",
            korp="Vigilanza",
            scadenza="01/01/2027 18:00",
            parametri={"pct_cliente": 10, "pct_proponente": 20},
            etichette={"pct_cliente": "Percentuale cliente", "pct_proponente": "Percentuale proponente"},
        )
        self.assertIn("Ada (Vigilanza) propone a il sottoscrittore fino al 01/01/2027 18:00.", reso)
        self.assertIn("Bonus 10% e 20%.", reso)
        self.assertIn("- Percentuale cliente: 10", reso)
        self.assertNotIn("{{param:", reso)


class ContrattiMotoreTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-contratti",
            nome="Kor35 Contratti",
            is_default=True,
            is_base=True,
            attiva=True,
            moduli_accesso={"contratti": "OPEN"},
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Contratti")
        cls.tipo_korp, _ = TipoCarriera.objects.get_or_create(codice="korp", defaults={"nome": "KORP"})
        cls.korp = Carriera.objects.create(
            nome="Vigilanza Test",
            descrizione="",
            tipo=TIER_3,
            tipo_carriera=cls.tipo_korp,
            sottoscrive_contratti=True,
            slot_contratto_base=3,
        )
        cls.carica = Carica.objects.create(nome="Capitano Test", bonus_slot_contratto=1)
        cls.carica.carriere.add(cls.korp)
        cls.user_a = User.objects.create_user(username="contratti_prop", password="x")
        cls.user_b = User.objects.create_user(username="contratti_cli", password="x")
        cls.proponente = Personaggio.objects.create(
            nome="Proponente",
            proprietario=cls.user_a,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )
        cls.cliente = Personaggio.objects.create(
            nome="Cliente",
            proprietario=cls.user_b,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )
        PersonaggioCarrieraMembership.objects.create(
            personaggio=cls.proponente,
            carriera=cls.korp,
            tipo_carriera=cls.tipo_korp,
            carica=cls.carica,
        )

    def setUp(self):
        self.korp.refresh_from_db()
        self.carica.refresh_from_db()
        self.campagna.refresh_from_db()

    def _proposta(self, preset, parametri=None, proponente=None):
        modello = crea_preset(self.campagna, self.korp, preset)
        return crea_proposta(proponente or self.proponente, modello, parametri or {}, [])

    def test_slot_base_carica_sct_e_pavimento(self):
        self.assertEqual(slot_totali(self.proponente), 4)
        with patch.object(Personaggio, "get_valore_statistica", return_value=1):
            self.assertEqual(slot_totali(self.proponente), 5)
        self.korp.sottoscrive_contratti = False
        self.korp.save(update_fields=["sottoscrive_contratti", "updated_at"])
        self.assertEqual(slot_totali(self.proponente), 0)
        self.korp.sottoscrive_contratti = True
        self.korp.slot_contratto_base = 1
        self.korp.save(update_fields=["sottoscrive_contratti", "slot_contratto_base", "updated_at"])
        self.carica.bonus_slot_contratto = -5
        self.carica.save(update_fields=["bonus_slot_contratto", "updated_at"])
        self.assertEqual(slot_totali(self.proponente), 0)

    def test_firma_rifiuto_annullo_e_un_cliente_per_modello(self):
        modello = crea_preset(self.campagna, self.korp, "talento")
        prima = crea_proposta(self.proponente, modello, {}, [])
        seconda = crea_proposta(self.proponente, modello, {}, [])
        self.assertEqual(prima.stato, STATO_IN_ATTESA)
        with self.assertRaises(ValidationError):
            firma_contratto(prima, self.proponente)
        firma_contratto(prima, self.cliente)
        prima.refresh_from_db()
        self.assertEqual(prima.stato, STATO_STIPULATO)
        self.assertEqual(riepilogo_ruoli(self.cliente), {"attivi_cliente": 1, "attivi_offerente": 0})
        self.assertEqual(riepilogo_ruoli(self.proponente), {"attivi_cliente": 0, "attivi_offerente": 1})
        self.assertEqual(slot_usati(self.cliente), 0)
        with self.assertRaises(ValidationError):
            firma_contratto(seconda, self.cliente)
        annulla_proposta(seconda, self.proponente)
        seconda.refresh_from_db()
        self.assertEqual(seconda.stato, STATO_ANNULLATO)

    def test_slot_liberi_solo_proponente_e_altro_modello_firmabile(self):
        PersonaggioCarrieraMembership.objects.create(
            personaggio=self.cliente,
            carriera=self.korp,
            tipo_carriera=self.tipo_korp,
        )
        self.assertEqual(slot_totali(self.cliente), 3)
        self.assertEqual(slot_liberi(self.cliente), 3)
        talento = crea_preset(self.campagna, self.korp, "talento")
        firma_contratto(crea_proposta(self.proponente, talento, {}, []), self.cliente)
        self.assertEqual(slot_usati(self.cliente), 0)
        self.assertEqual(slot_liberi(self.cliente), 3)
        self.assertEqual(slot_usati(self.proponente), 1)
        self.assertEqual(slot_liberi(self.proponente), slot_totali(self.proponente) - 1)
        altro_talento = crea_preset(self.campagna, self.korp, "talento")
        self.assertEqual(altro_talento.chiave_esclusivita, talento.chiave_esclusivita)
        firma_contratto(crea_proposta(self.proponente, altro_talento, {}, []), self.cliente)
        self.assertEqual(riepilogo_ruoli(self.cliente)["attivi_cliente"], 2)
        self.assertEqual(slot_usati(self.cliente), 0)

    def test_firma_blocca_se_il_prezzo_non_e_coperto(self):
        proposta = self._proposta("protettore")
        with self.assertRaises(ValidationError):
            firma_contratto(proposta, self.cliente)
        proposta.refresh_from_db()
        self.assertEqual(proposta.stato, STATO_IN_ATTESA)
        self.cliente.modifica_crediti(Decimal("200"), "fondo firma", conto=CONTO_CORRENTE)
        firma_contratto(proposta, self.cliente)
        proposta.refresh_from_db()
        self.assertEqual(proposta.stato, STATO_STIPULATO)
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), Decimal("0.00"))
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("200.00"))

    def test_talento_sul_credito_della_task_del_cliente(self):
        firma_contratto(self._proposta("talento"), self.cliente)
        on_task_reclamata(SimpleNamespace(pk=uuid.uuid4(), personaggio=self.cliente, reward_crediti=Decimal("100")))
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), Decimal("10.00"))
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("20.00"))
        prima_cliente = saldo_conto(self.cliente, CONTO_CORRENTE)
        on_task_reclamata(SimpleNamespace(pk=uuid.uuid4(), personaggio=self.proponente, reward_crediti=Decimal("100")))
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), prima_cliente)

    def test_sconto_sul_pieno_e_bonus_proponente(self):
        firma_contratto(self._proposta("creatore"), self.cliente)
        pagamento = costo_con_sconto_contratto(
            self.cliente, "forgiatura", 600, 600, "forgiatura-test", eroga=True
        )
        self.assertEqual(pagamento, Decimal("540.00"))
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("60.00"))
        di_nuovo = costo_con_sconto_contratto(
            self.cliente, "forgiatura", 600, 600, "forgiatura-test", eroga=True
        )
        self.assertEqual(di_nuovo, Decimal("540.00"))
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("60.00"))

    def test_pubblicitario_zero_post_lascia_debito(self):
        proposta = self._proposta("pubblicitario", {"tema": "birreria"})
        firma_contratto(proposta, self.cliente)
        self.proponente.modifica_crediti(Decimal("30"), "cassa", conto=CONTO_CORRENTE)
        ora = timezone.now()
        evento = Evento.objects.create(
            titolo="Evento zero post",
            data_inizio=ora - timedelta(hours=2),
            data_fine=ora + timedelta(days=1),
        )
        evento.partecipanti.add(self.proponente, self.cliente)
        on_evento_terminato(evento)
        on_evento_terminato(evento)
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("0.00"))
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), Decimal("30.00"))
        ademp = proposta.adempimenti.get()
        self.assertEqual(ademp.stato, "DEBITO")
        self.assertEqual(ademp.dovuto, Decimal("90.00"))
        self.assertEqual(ademp.versato, Decimal("30.00"))

    def test_pubblicitario_due_post_netto_come_esempio(self):
        proposta = self._proposta("pubblicitario", {"tema": "locandina"})
        firma_contratto(proposta, self.cliente)
        ora = timezone.now()
        evento = Evento.objects.create(
            titolo="Evento due post",
            data_inizio=ora - timedelta(hours=2),
            data_fine=ora + timedelta(days=1),
        )
        evento.partecipanti.add(self.proponente, self.cliente)
        for titolo in ("Uno", "Due"):
            post = SocialPost.objects.create(autore=self.proponente, titolo=titolo, testo="testo", evento=evento)
            from personaggi.contratti_service import associa_post

            associa_post(proposta, self.proponente, post)
        on_evento_terminato(evento)
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), Decimal("90.00"))
        self.assertEqual(saldo_conto(self.proponente, CONTO_CORRENTE), Decimal("30.00"))

    def test_modulo_spento_nasconde_la_tab_e_non_paga(self):
        firma_contratto(self._proposta("talento"), self.cliente)
        self.campagna.moduli_accesso = {"contratti": "OFF"}
        self.campagna.save(update_fields=["moduli_accesso", "updated_at"])
        self.proponente.campagna = self.campagna
        self.cliente.campagna = self.campagna
        self.assertFalse(tab_visibile(self.proponente, self.user_a))
        on_task_reclamata(SimpleNamespace(pk=uuid.uuid4(), personaggio=self.cliente, reward_crediti=Decimal("100")))
        self.assertEqual(saldo_conto(self.cliente, CONTO_CORRENTE), Decimal("0.00"))

    def test_statistica_sct_creata_dalla_migrazione(self):
        stat = Statistica.objects.filter(sigla__iexact="SCT").first()
        self.assertIsNotNone(stat)
        self.assertEqual(stat.parametro, "SCT")
        self.assertEqual(stat.tipo, "ST")

    def test_qr_risponde_contratto(self):
        proposta = self._proposta("talento")
        request = RequestFactory().get("/", {"personaggio_id": str(self.cliente.pk)})
        request.user = self.user_b
        risposta = risposta_qr_contratto(proposta.qr_code, request)
        self.assertEqual(risposta.data["tipo_modello"], "contratto")
        self.assertTrue(risposta.data["dati"]["puo_firmare"])
