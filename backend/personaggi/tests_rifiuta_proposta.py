"""Regressione: rifiuto proposta tecnica dalla dashboard staff «Valutazione proposte».

Il client deve colpire l'URL canonico `staff/proposta/<id>/rifiuta/` (singolare,
allineato ad approvazione). Resta anche l'alias plurale `staff/proposte/<id>/rifiuta/`
usato in produzione prima del fix.

Il rifiuto non è terminale: la proposta torna BOZZA (con le note), esce dalla coda
di valutazione e il personaggio può modificarla e ripresentarla.
"""
from decimal import Decimal
from unittest.mock import PropertyMock, patch

from django.contrib.admin.sites import AdminSite
from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase

from personaggi.admin import PropostaTecnicaAdmin
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
    STATO_PROPOSTA_RIFIUTATA,
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
        self.altra = PropostaTecnica.objects.create(
            personaggio=self.pg,
            tipo=TIPO_PROPOSTA_TESSITURA,
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            nome='Altra ancora in coda',
            descrizione='Resta in valutazione',
            aura=self.aura,
            livello_proposto=1,
        )
        self.client.force_login(self.staff)

    def _righe_valutazione(self):
        resp = self.client.get(
            '/api/personaggi/api/staff/proposte/valutazione/',
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        return data if isinstance(data, list) else data.get('results') or []

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

    def test_rifiuto_esce_dalla_coda_e_il_giocatore_la_riprende(self):
        self._assert_rifiuto_ok(
            f'/api/personaggi/api/staff/proposta/{self.proposta.pk}/rifiuta/'
        )
        ids_in_coda = {row['id'] for row in self._righe_valutazione()}
        self.assertNotIn(self.proposta.pk, ids_in_coda)
        self.assertIn(self.altra.pk, ids_in_coda)

        self.client.force_login(self.giocatore)
        lista = self.client.get(f'/api/personaggi/api/proposte/?char_id={self.pg.pk}')
        self.assertEqual(lista.status_code, 200, lista.content)
        payload = lista.json()
        righe = payload if isinstance(payload, list) else payload.get('results') or []
        propria = next(row for row in righe if row['id'] == self.proposta.pk)
        self.assertEqual(propria['stato'], STATO_PROPOSTA_BOZZA)
        self.assertEqual(propria['nome'], 'Soffio da rivedere')
        self.assertIn('mattoni', propria['note_staff'])

        modifica = self.client.patch(
            f'/api/personaggi/api/proposte/{self.proposta.pk}/',
            {'nome': 'Soffio rivisto', 'descrizione': 'Ragionamento aggiornato sulle note.'},
            content_type='application/json',
        )
        self.assertEqual(modifica.status_code, 200, modifica.content)
        self.assertEqual(modifica.json()['stato'], STATO_PROPOSTA_BOZZA)
        self.assertIn('mattoni', modifica.json()['note_staff'])

        with patch.object(Personaggio, 'get_valore_aura_effettivo', return_value=5), \
             patch.object(Personaggio, 'max_livello_creazione', return_value=5), \
             patch.object(
                 Personaggio,
                 'caratteristiche_base',
                 new_callable=PropertyMock,
                 return_value={self.caratteristica.nome: 5},
             ), \
             patch.object(
                 Personaggio,
                 'crediti',
                 new_callable=PropertyMock,
                 return_value=Decimal('500'),
             ):
            invio = self.client.post(
                f'/api/personaggi/api/proposte/{self.proposta.pk}/invia_proposta/',
                content_type='application/json',
            )
        self.assertEqual(invio.status_code, 200, invio.content)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_IN_VALUTAZIONE)
        self.assertEqual(self.proposta.nome, 'Soffio rivisto')
        self.assertIn('mattoni', self.proposta.note_staff)

        self.client.force_login(self.staff)
        ids_dopo = {row['id'] for row in self._righe_valutazione()}
        self.assertIn(self.proposta.pk, ids_dopo)

    def test_secondo_rifiuto_su_bozza_non_cambia_lo_stato(self):
        self._assert_rifiuto_ok(
            f'/api/personaggi/api/staff/proposta/{self.proposta.pk}/rifiuta/'
        )
        resp = self.client.post(
            f'/api/personaggi/api/staff/proposta/{self.proposta.pk}/rifiuta/',
            {'note_staff': 'Nota che non deve sostituire la prima.'},
            content_type='application/json',
        )
        self.assertEqual(resp.status_code, 400, resp.content)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_BOZZA)
        self.assertIn('mattoni', self.proposta.note_staff)

    def test_patch_rifiutata_legacy_diventa_bozza(self):
        self.proposta.stato = STATO_PROPOSTA_RIFIUTATA
        self.proposta.note_staff = 'Sistema il testo.'
        self.proposta.save()
        self.client.force_login(self.giocatore)
        modifica = self.client.patch(
            f'/api/personaggi/api/proposte/{self.proposta.pk}/',
            {'nome': 'Soffio dopo rifiuto legacy'},
            content_type='application/json',
        )
        self.assertEqual(modifica.status_code, 200, modifica.content)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_BOZZA)
        self.assertEqual(self.proposta.nome, 'Soffio dopo rifiuto legacy')
        self.assertEqual(self.proposta.note_staff, 'Sistema il testo.')

    def test_rifiuto_legacy_admin_torna_bozza_modificabile(self):
        self.proposta.stato = STATO_PROPOSTA_RIFIUTATA
        self.proposta.note_staff = 'Sistema il testo.'
        self.proposta.save()

        class _Form:
            changed_data = ['stato']

        request = RequestFactory().post('/admin/personaggi/propostatecnica/')
        request.user = self.staff
        PropostaTecnicaAdmin(PropostaTecnica, AdminSite()).save_model(
            request, self.proposta, _Form(), change=True
        )
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_BOZZA)
        msg = Messaggio.objects.filter(destinatario_personaggio=self.pg).latest('data_invio')
        self.assertIn('bozza', msg.testo.lower())
        self.assertIn('Sistema il testo', msg.testo)
        self.assertEqual(self.proposta.note_staff, 'Sistema il testo.')
