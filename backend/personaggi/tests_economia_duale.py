"""Test economia duale: conti corrente/deposito, prezzo, trasferimento."""
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from gestione_plot.models import Evento, EventoTrasferimentoDeposito
from personaggi.campagna_moduli import (
    MODULO_ACCESSO_OPEN,
    MODULO_CONTO_DEPOSITO,
    apply_moduli_accesso,
)
from personaggi.economia_crediti import (
    CONTO_CORRENTE,
    CONTO_DEPOSITO,
    addebita_bene,
    get_economia_config,
    modifica_crediti,
    prezzo_da_deposito,
    saldo_corrente,
    saldo_deposito,
    trasferisci_deposito_a_corrente,
)
from personaggi.models import Campagna, Personaggio, TipologiaPersonaggio


class EconomiaDualeTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="eco_user", password="x")
        self.campagna = Campagna.objects.create(
            slug="eco-test",
            nome="Eco Test",
            attiva=True,
        )
        apply_moduli_accesso(self.campagna, {MODULO_CONTO_DEPOSITO: MODULO_ACCESSO_OPEN})
        self.tipologia = TipologiaPersonaggio.objects.create(
            nome="EcoTipo",
            crediti_iniziali=Decimal("100.00"),
            caratteristiche_iniziali=5,
        )
        self.pg = Personaggio.objects.create(
            nome="Eco PG",
            proprietario=self.user,
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        self.evento = Evento.objects.create(
            titolo="Evento Eco",
            data_inizio=timezone.now() - timezone.timedelta(hours=1),
            data_fine=timezone.now() + timezone.timedelta(hours=5),
            started_at=timezone.now() - timezone.timedelta(minutes=30),
            crediti_base_inizio_evento=Decimal("50.00"),
        )
        self.evento.partecipanti.add(self.pg)

    def test_prezzo_deposito_worth_less(self):
        self.assertEqual(prezzo_da_deposito(100, fattore=Decimal("0.90")), Decimal("111.11"))

    def test_saldi_split(self):
        modifica_crediti(self.pg, Decimal("20"), "bonus corrente", conto=CONTO_CORRENTE)
        modifica_crediti(self.pg, Decimal("30"), "bonus deposito", conto=CONTO_DEPOSITO)
        self.assertEqual(saldo_corrente(self.pg), Decimal("120.00"))
        self.assertEqual(saldo_deposito(self.pg), Decimal("30.00"))
        # modulo ON → crediti = solo corrente
        self.assertEqual(Decimal(str(self.pg.crediti)), Decimal("120.00"))

    def test_addebita_bene_deposito(self):
        modifica_crediti(self.pg, Decimal("200"), "fondi", conto=CONTO_DEPOSITO)
        pagato = addebita_bene(
            self.pg,
            90,
            "acquisto test",
            conto=CONTO_DEPOSITO,
            categoria="negozio",
            campagna=self.campagna,
            user=self.user,
        )
        self.assertEqual(pagato, Decimal("100.00"))  # 90 / 0.90
        self.assertEqual(saldo_deposito(self.pg), Decimal("100.00"))

    def test_trasferimento_una_volta(self):
        modifica_crediti(self.pg, Decimal("200"), "fondi", conto=CONTO_DEPOSITO)
        # stipendio evento = 50, frazione default 1.00 → tetto 50
        trasferisci_deposito_a_corrente(
            self.pg, Decimal("40.00"), self.evento, user=self.user
        )
        self.assertEqual(saldo_deposito(self.pg), Decimal("160.00"))
        self.assertEqual(saldo_corrente(self.pg), Decimal("140.00"))
        self.assertTrue(
            EventoTrasferimentoDeposito.objects.filter(
                evento=self.evento, personaggio=self.pg
            ).exists()
        )
        with self.assertRaises(ValidationError):
            trasferisci_deposito_a_corrente(
                self.pg, Decimal("10.00"), self.evento, user=self.user
            )

    def test_config_default(self):
        cfg = get_economia_config(self.campagna)
        self.assertEqual(cfg["fattore_valore_deposito"], "0.90")
        self.assertIn("negozio", cfg["categorie_spesa_deposito"])

    def test_p2p_conserva_natura_conto_deposito(self):
        from personaggi.models import (
            PropostaTransazione,
            STATO_TRANSAZIONE_ACCETTATA,
            STATO_TRANSAZIONE_IN_ATTESA,
            TransazioneSospesa,
        )

        altro = Personaggio.objects.create(
            nome="Eco PG 2",
            proprietario=User.objects.create_user(username="eco_user2", password="x"),
            tipologia=self.tipologia,
            campagna=self.campagna,
        )
        modifica_crediti(self.pg, Decimal("50"), "fondi dep", conto=CONTO_DEPOSITO)
        dep_a = saldo_deposito(self.pg)
        dep_b = saldo_deposito(altro)
        tx = TransazioneSospesa.objects.create(
            iniziatore=self.pg,
            destinatario=altro,
            stato=STATO_TRANSAZIONE_IN_ATTESA,
        )
        p_a = PropostaTransazione.objects.create(
            transazione=tx,
            autore=self.pg,
            crediti_da_dare=Decimal("20.00"),
            crediti_da_ricevere=0,
            conto_crediti=CONTO_DEPOSITO,
            is_attiva=True,
        )
        p_b = PropostaTransazione.objects.create(
            transazione=tx,
            autore=altro,
            crediti_da_dare=0,
            crediti_da_ricevere=Decimal("20.00"),
            conto_crediti=CONTO_CORRENTE,
            is_attiva=True,
        )
        tx.ultima_proposta_iniziatore = p_a
        tx.ultima_proposta_destinatario = p_b
        tx.save()
        tx.accetta()
        self.assertEqual(tx.stato, STATO_TRANSAZIONE_ACCETTATA)
        self.assertEqual(saldo_deposito(self.pg), dep_a - Decimal("20.00"))
        self.assertEqual(saldo_deposito(altro), dep_b + Decimal("20.00"))
        # Corrente invariata da questo scambio
        self.assertEqual(saldo_corrente(altro), saldo_corrente(altro))
