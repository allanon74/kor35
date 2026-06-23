"""Test scambi transazioni: trasferimento consumabili."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone

from personaggi.models import (
    Campagna,
    ConsumabilePersonaggio,
    Personaggio,
    PropostaTransazione,
    STATO_TRANSAZIONE_ACCETTATA,
    STATO_TRANSAZIONE_IN_ATTESA,
    TipologiaPersonaggio,
    TransazioneSospesa,
)

User = get_user_model()


class TransazioneConsumabiliTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-trans-test",
            nome="Kor35 Trans Test",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Trans Test")
        cls.user_a = User.objects.create_user(username="trans_a", password="x")
        cls.user_b = User.objects.create_user(username="trans_b", password="y")
        cls.pg_a = Personaggio.objects.create(
            nome="PG A",
            proprietario=cls.user_a,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )
        cls.pg_b = Personaggio.objects.create(
            nome="PG B",
            proprietario=cls.user_b,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )
        cls.scadenza = (timezone.now() + timedelta(days=7)).date()

    def _crea_transazione_con_proposte(self):
        transazione = TransazioneSospesa.objects.create(
            iniziatore=self.pg_a,
            destinatario=self.pg_b,
            stato=STATO_TRANSAZIONE_IN_ATTESA,
        )
        cons_a = ConsumabilePersonaggio.objects.create(
            personaggio=self.pg_a,
            nome="Pozione A",
            descrizione="Test",
            utilizzi_rimanenti=2,
            data_scadenza=self.scadenza,
        )
        cons_b = ConsumabilePersonaggio.objects.create(
            personaggio=self.pg_b,
            nome="Pozione B",
            descrizione="Test",
            utilizzi_rimanenti=1,
            data_scadenza=self.scadenza,
        )
        prop_a = PropostaTransazione.objects.create(
            transazione=transazione,
            autore=self.pg_a,
            crediti_da_dare=10,
            crediti_da_ricevere=5,
            is_attiva=True,
        )
        prop_a.consumabili_da_dare.set([cons_a])
        prop_a.consumabili_da_ricevere.set([cons_b])
        transazione.ultima_proposta_iniziatore = prop_a
        transazione.save()

        prop_b = PropostaTransazione.objects.create(
            transazione=transazione,
            autore=self.pg_b,
            crediti_da_dare=5,
            crediti_da_ricevere=10,
            is_attiva=True,
        )
        prop_b.consumabili_da_dare.set([cons_b])
        prop_b.consumabili_da_ricevere.set([cons_a])
        transazione.ultima_proposta_destinatario = prop_b
        transazione.save()
        return transazione, cons_a, cons_b

    def test_accetta_trasferisce_consumabili(self):
        transazione, cons_a, cons_b = self._crea_transazione_con_proposte()
        transazione.accetta()
        transazione.refresh_from_db()
        cons_a.refresh_from_db()
        cons_b.refresh_from_db()

        self.assertEqual(transazione.stato, STATO_TRANSAZIONE_ACCETTATA)
        self.assertEqual(cons_a.personaggio_id, self.pg_b.id)
        self.assertEqual(cons_b.personaggio_id, self.pg_a.id)
