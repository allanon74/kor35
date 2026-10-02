"""Regressione: approvazione proposta di tessitura dalla maschera staff «Valutazione proposte».

Il frontend invia il payload dell'editor tessitura (campi testuali della proposta
inclusi). Qui si verifica che l'approvazione crei la tessitura e non perda la
formula scritta dallo staff.
"""
from django.contrib.auth import get_user_model
from django.test import TestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Campagna,
    DEFAULT_WEAVE_FORMULA_TEMPLATE,
    Personaggio,
    PropostaTecnica,
    PropostaTecnicaCaratteristica,
    Punteggio,
    STATO_PROPOSTA_APPROVATA,
    STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_TESSITURA,
    Tessitura,
    TipologiaPersonaggio,
)

User = get_user_model()


class ApprovaPropostaTessituraTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug='camp-approva-tes',
            nome='Camp Approva TES',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome='Standard Approva TES')
        self.staff = User.objects.create_user(
            username='staff_approva_tes', password='x', is_staff=True, is_superuser=True
        )
        self.giocatore = User.objects.create_user(username='player_approva_tes', password='x')
        self.aura = Punteggio.objects.create(nome='Aura Approva', sigla='AAP', tipo=AURA)
        self.caratteristica = Punteggio.objects.create(
            nome='Caratt Approva', sigla='CAP', tipo=CARATTERISTICA
        )
        self.pg = Personaggio.objects.create(
            nome='PG Approva TES',
            proprietario=self.giocatore,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.proposta = PropostaTecnica.objects.create(
            personaggio=self.pg,
            tipo=TIPO_PROPOSTA_TESSITURA,
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            nome='Soffio di Brace',
            descrizione='Ragionamento del giocatore',
            aura=self.aura,
            livello_proposto=2,
        )
        PropostaTecnicaCaratteristica.objects.create(
            proposta=self.proposta, caratteristica=self.caratteristica, valore=2
        )
        self.client.force_login(self.staff)

    def _url(self):
        return f'/api/personaggi/api/staff/proposta/{self.proposta.pk}/approva/'

    def _payload(self, **overrides):
        """Payload come lo manda `TessituraEditor` in modalità approvazione."""
        payload = {
            'nome': self.proposta.nome,
            'descrizione': self.proposta.descrizione,
            'testo': self.proposta.descrizione,
            'aura_richiesta': self.aura.id,
            'livello': self.proposta.livello,
            'liv': self.proposta.livello_proposto,
            'mattoni_generici': 0,
            'componenti': [{'caratteristica': self.caratteristica.id, 'valore': 2}],
            'prerequisiti': '',
            'svolgimento': '',
            'effetto': '',
            'note_staff': 'ok dallo staff',
            'formula': 'Aura + 1d10',
            'elemento_principale': None,
            'abilita_temporanea': None,
            'statistiche_base': [],
            'costi_attivazione': [],
            'non_acquistabile': False,
            'escluso_negozio_ufficiale': False,
            'non_vendibile': False,
            'usa_effetto_temporaneo': False,
            'durata_effetto_secondi': 0,
            'oggetto_runtime_config': None,
        }
        payload.update(overrides)
        return payload

    def test_approvazione_crea_tessitura_con_formula_dello_staff(self):
        resp = self.client.post(self._url(), self._payload(), content_type='application/json')

        self.assertEqual(resp.status_code, 201, resp.content)
        tessitura = Tessitura.objects.get(proposta_creazione=self.proposta)
        self.assertEqual(tessitura.nome, 'Soffio di Brace')
        self.assertEqual(tessitura.formula, 'Aura + 1d10')
        self.assertEqual(tessitura.componenti.count(), 1)
        self.proposta.refresh_from_db()
        self.assertEqual(self.proposta.stato, STATO_PROPOSTA_APPROVATA)

    def test_formula_vuota_ricade_sul_template_di_default(self):
        """Senza formula dallo staff la tessitura non deve nascere senza formula."""
        resp = self.client.post(
            self._url(), self._payload(formula=''), content_type='application/json'
        )

        self.assertEqual(resp.status_code, 201, resp.content)
        tessitura = Tessitura.objects.get(proposta_creazione=self.proposta)
        self.assertEqual(tessitura.formula, DEFAULT_WEAVE_FORMULA_TEMPLATE)

    def test_formula_assente_dal_payload_ricade_sul_template_di_default(self):
        payload = self._payload()
        payload.pop('formula')

        resp = self.client.post(self._url(), payload, content_type='application/json')

        self.assertEqual(resp.status_code, 201, resp.content)
        tessitura = Tessitura.objects.get(proposta_creazione=self.proposta)
        self.assertEqual(tessitura.formula, DEFAULT_WEAVE_FORMULA_TEMPLATE)


class TessituraStaffEditorTests(TestCase):
    """Maschera staff «Tessiture»: creazione e modifica non devono perdere la formula."""

    def setUp(self):
        Campagna.objects.create(
            slug='camp-editor-tes',
            nome='Camp Editor TES',
            attiva=True,
            is_default=True,
            is_base=True,
        )
        self.staff = User.objects.create_user(
            username='staff_editor_tes', password='x', is_staff=True, is_superuser=True
        )
        self.aura = Punteggio.objects.create(nome='Aura Editor', sigla='AED', tipo=AURA)
        self.caratteristica = Punteggio.objects.create(
            nome='Caratt Editor', sigla='CED', tipo=CARATTERISTICA
        )
        self.client.force_login(self.staff)

    def _payload(self, **overrides):
        payload = {
            'nome': 'Tessitura Editor',
            'testo': 'Descrizione',
            'formula': 'Aura + 2d6',
            'aura_richiesta': self.aura.id,
            'elemento_principale': None,
            'abilita_temporanea': None,
            'componenti': [{'caratteristica': self.caratteristica.id, 'valore': 1}],
            'statistiche_base': [],
            'costi_attivazione': [],
            'non_acquistabile': False,
            'escluso_negozio_ufficiale': False,
            'non_vendibile': False,
            'usa_effetto_temporaneo': False,
            'durata_effetto_secondi': 0,
            'oggetto_runtime_config': None,
        }
        payload.update(overrides)
        return payload

    def test_creazione_conserva_la_formula(self):
        resp = self.client.post(
            '/api/personaggi/api/staff/tessiture/', self._payload(), content_type='application/json'
        )

        self.assertEqual(resp.status_code, 201, resp.content)
        tessitura = Tessitura.objects.get(nome='Tessitura Editor')
        self.assertEqual(tessitura.formula, 'Aura + 2d6')

    def test_modifica_conserva_la_formula_riscritta(self):
        tessitura = Tessitura.objects.create(
            nome='Tessitura Esistente', aura_richiesta=self.aura, formula='Vecchia formula'
        )

        resp = self.client.patch(
            f'/api/personaggi/api/staff/tessiture/{tessitura.pk}/',
            self._payload(nome='Tessitura Esistente', formula='Nuova formula'),
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        tessitura.refresh_from_db()
        self.assertEqual(tessitura.formula, 'Nuova formula')

    def test_modifica_puo_svuotare_la_formula(self):
        """Sulla maschera standard lo staff deve poter azzerare la formula a mano."""
        tessitura = Tessitura.objects.create(
            nome='Tessitura Da Svuotare', aura_richiesta=self.aura, formula='Qualcosa'
        )

        resp = self.client.patch(
            f'/api/personaggi/api/staff/tessiture/{tessitura.pk}/',
            {'formula': ''},
            content_type='application/json',
        )

        self.assertEqual(resp.status_code, 200, resp.content)
        tessitura.refresh_from_db()
        self.assertEqual(tessitura.formula, '')

    def test_opzioni_semantiche_espongono_il_template_di_default(self):
        resp = self.client.get('/api/personaggi/api/staff/formula-semantic-options/')

        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(
            resp.json().get('formula_default_template'), DEFAULT_WEAVE_FORMULA_TEMPLATE
        )
