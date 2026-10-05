"""Regressione: rifiuto proposta tecnica dalla dashboard staff «Valutazione proposte».

Il client deve colpire l'URL canonico `staff/proposta/<id>/rifiuta/` (singolare,
allineato ad approvazione). Resta anche l'alias plurale `staff/proposte/<id>/rifiuta/`
usato in produzione prima del fix.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Campagna,
    Messaggio,
    Personaggio,
    PropostaTecnica,
    PropostaTecnicaCaratteristica,
    Punteggio,
    STATO_PROPOSTA_BOZZA,
    STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_TESSITURA,
    TipologiaPersonaggio,
)

User = get_user_model()


class RifiutaPropostaStaffTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug='camp-rifiuta-tes',
            nome='Camp Rifiuta TES',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome='Standard Rifiuta TES')
        self.staff = User.objects.create_user(
            username='staff_rifiuta_tes', password='x', is_staff=True, is_superuser=True
        )
        self.giocatore = User.objects.create_user(username='player_rifiuta_tes', password='x')
        self.aura = Punteggio.objects.create(nome='Aura Rifiuta', sigla='ARF', tipo=AURA)
        self.caratteristica = Punteggio.objects.create(
            nome='Caratt Rifiuta', sigla='CRF', tipo=CARATTERISTICA
        )
        self.pg = Personaggio.objects.create(
            nome='PG Rifiuta TES',
            proprietario=self.giocatore,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.proposta = PropostaTecnica.objects.create(
            personaggio=self.pg,
            tipo=TIPO_PROPOSTA_TESSITURA,
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            nome='Soffio da rivedere',
            descrizione='Ragionamento del giocatore',
            aura=self.aura,
            livello_proposto=2,
        )
        PropostaTecnicaCaratteristica.objects.create(
            proposta=self.proposta, caratteristica=self.caratteristica, valore=2
        )
        self.client.force_login(self.staff)

    def _assert_rifiuto_ok(self, url):
        resp = self.client.post(
            url,
            {'note_staff': 'Manca il ragionamento sui mattoni.'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_BOZZA)
        self.assertIn('mattoni', self.proposta.note_staff)
        msg = Messaggio.objects.get(destinatario_personaggio=self.pg)
        self.assertIn('Soffio da rivedere', msg.titolo)

    def test_rifiuto_url_canonico_singolare(self):
        self._assert_rifiuto_ok(
            f'/api/personaggi/api/staff/proposta/{self.proposta.pk}/rifiuta/'
        )

    def test_rifiuto_url_alias_plurale_usato_dal_client(self):
        self._assert_rifiuto_ok(
            f'/api/personaggi/api/staff/proposte/{self.proposta.pk}/rifiuta/'
        )
