"""Lista staff «Valutazione proposte»: include il nome del giocatore."""

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase

from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Campagna,
    Personaggio,
    PropostaTecnica,
    PropostaTecnicaCaratteristica,
    Punteggio,
    STATO_PROPOSTA_IN_VALUTAZIONE,
    TIPO_PROPOSTA_TESSITURA,
    TipologiaPersonaggio,
)


class ProposteValutazioneGiocatoreTests(APITestCase):
    def setUp(self):
        self.campagna = Campagna.objects.create(
            slug="camp-prop-gioc",
            nome="Camp Prop Gioc",
            attiva=True,
            is_default=True,
            is_base=True,
        )
        self.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Prop Gioc")
        self.staff = User.objects.create_user(
            username="staff-prop-gioc", password="x", is_staff=True, is_superuser=True
        )
        self.giocatore = User.objects.create_user(
            username="player_prop_gioc",
            password="x",
            first_name="Luca",
            last_name="Bianchi",
        )
        self.aura = Punteggio.objects.create(nome="Aura Prop Gioc", sigla="APG", tipo=AURA)
        self.caratteristica = Punteggio.objects.create(
            nome="Caratt Prop Gioc", sigla="CPG", tipo=CARATTERISTICA
        )
        self.pg = Personaggio.objects.create(
            nome="PG Prop Gioc",
            proprietario=self.giocatore,
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        self.proposta = PropostaTecnica.objects.create(
            personaggio=self.pg,
            tipo=TIPO_PROPOSTA_TESSITURA,
            stato=STATO_PROPOSTA_IN_VALUTAZIONE,
            nome="Soffio da valutare",
            descrizione="Ragionamento",
            aura=self.aura,
            livello_proposto=2,
        )
        PropostaTecnicaCaratteristica.objects.create(
            proposta=self.proposta, caratteristica=self.caratteristica, valore=2
        )
        self.client.force_authenticate(user=self.staff)
        self.url = "/api/personaggi/api/staff/proposte/valutazione/"

    def _rows(self, response):
        data = response.data
        return data if isinstance(data, list) else data.get("results") or []

    def test_lista_include_nome_giocatore(self):
        r = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        match = next((row for row in self._rows(r) if row["id"] == self.proposta.id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["personaggio_nome"], "PG Prop Gioc")
        self.assertEqual(match["giocatore_nome"], "Luca Bianchi")

    def test_fallback_username_se_manca_nome_anagrafico(self):
        self.giocatore.first_name = ""
        self.giocatore.last_name = ""
        self.giocatore.save()
        r = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(r.status_code, status.HTTP_200_OK, r.data)
        match = next((row for row in self._rows(r) if row["id"] == self.proposta.id), None)
        self.assertIsNotNone(match)
        self.assertEqual(match["giocatore_nome"], "player_prop_gioc")

    def test_giocatore_non_staff_forbidden(self):
        player = User.objects.create_user(username="player-only-prop", password="x")
        self.client.force_authenticate(user=player)
        r = self.client.get(self.url, HTTP_X_CAMPAGNA=self.campagna.slug)
        self.assertEqual(r.status_code, status.HTTP_403_FORBIDDEN)
