"""Alchimia: creazione consumabili solo a evento aperto e con PG iscritto."""

from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APITestCase

from gestione_plot.models import Evento
from personaggi.consumabili_evento import esito_creazione_consumabile_alchimia
from personaggi.models import (
    AURA,
    CARATTERISTICA,
    Abilita,
    Campagna,
    ConsumabilePersonaggio,
    CreazioneConsumabileInCorso,
    Personaggio,
    PersonaggioAbilita,
    PersonaggioTessitura,
    Punteggio,
    Tessitura,
    TipologiaPersonaggio,
    abilita_punteggio,
)
from personaggi.services import CreazioneConsumabileService


class CreazioneConsumabileEventoTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="alc-evento", password="x")
        self.client.force_authenticate(user=self.user)
        self.campagna = Campagna.objects.create(
            slug="kor35-alc-evento",
            nome="Kor35 Alchimia Evento",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        self.tipo = TipologiaPersonaggio.objects.create(nome="PG alchimia evento", giocante=True)
        self.pg = Personaggio.objects.create(
            nome="Alchimista",
            proprietario=self.user,
            tipologia=self.tipo,
            campagna=self.campagna,
        )
        self.ca = Punteggio.objects.create(nome="Car Alchimia", sigla="CAL", tipo=CARATTERISTICA)
        self.aura = Punteggio.objects.create(
            nome="Aura Alchimia Evento", sigla="ALC", tipo=AURA, is_generica=False
        )
        grant = Abilita.objects.create(
            nome="Grant ALC evento",
            caratteristica=self.ca,
            costo_pc=0,
            costo_crediti=0,
            campagna=self.campagna,
        )
        abilita_punteggio.objects.create(abilita=grant, punteggio=self.aura, valore=3)
        PersonaggioAbilita.objects.create(personaggio=self.pg, abilita=grant)
        self.tess = Tessitura.objects.create(
            nome="Elisir di prova",
            testo="descrizione elisir",
            formula="formula elisir",
            aura_richiesta=self.aura,
            campagna=self.campagna,
        )
        PersonaggioTessitura.objects.create(personaggio=self.pg, tessitura=self.tess)
        self.pg.modifica_crediti(500, "fondi test alchimia")
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Evento alchimia",
            data_inizio=now + timedelta(days=3),
            data_fine=now + timedelta(days=4),
        )

    def _avvia(self):
        return self.client.post(
            reverse("personaggi:avvia_creazione_consumabile"),
            {"personaggio_id": self.pg.id, "tessitura_id": self.tess.id},
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )

    def _apri_evento(self):
        self.evento.started_at = timezone.now()
        self.evento.ended_at = None
        self.evento.save(update_fields=["started_at", "ended_at", "updated_at"])

    def test_senza_evento_aperto_bloccata(self):
        ok, msg = esito_creazione_consumabile_alchimia(self.pg)
        self.assertFalse(ok)
        self.assertIn("evento aperto", msg)
        resp = self._avvia()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("evento aperto", resp.json()["error"])
        self.assertFalse(
            CreazioneConsumabileInCorso.objects.filter(personaggio=self.pg).exists()
        )

    def test_evento_aperto_senza_iscrizione_bloccata(self):
        self._apri_evento()
        ok, msg = esito_creazione_consumabile_alchimia(self.pg)
        self.assertFalse(ok)
        self.assertIn("iscritto", msg)
        resp = self._avvia()
        self.assertEqual(resp.status_code, 400)
        self.assertIn("iscritto", resp.json()["error"])

    def test_evento_aperto_e_iscritto_avvia(self):
        self._apri_evento()
        self.evento.partecipanti.add(self.pg)
        ok, msg = esito_creazione_consumabile_alchimia(self.pg)
        self.assertTrue(ok, msg)
        resp = self._avvia()
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertTrue(resp.json()["success"])
        self.assertTrue(
            CreazioneConsumabileInCorso.objects.filter(
                personaggio=self.pg, tessitura=self.tess, completata=False
            ).exists()
        )

    def test_completamento_non_richiede_evento(self):
        """Chi ha già pagato il timer può ritirare il consumabile anche a evento chiuso."""
        CreazioneConsumabileInCorso.objects.create(
            personaggio=self.pg,
            tessitura=self.tess,
            data_fine_creazione=timezone.now() - timedelta(seconds=5),
            completata=False,
        )
        ok, data = CreazioneConsumabileService.completa_creazione(self.pg)
        self.assertTrue(ok, data)
        self.assertTrue(
            ConsumabilePersonaggio.objects.filter(personaggio=self.pg, nome=self.tess.nome).exists()
        )
