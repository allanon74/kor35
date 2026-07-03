"""Test gate furti/scambi/transfer missiva solo con evento aperto."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework.test import APIClient

from gestione_plot.models import Evento
from personaggi.models import Campagna, CampagnaUtente, CAMPAGNA_ROLE_STAFFER, Personaggio, TipologiaPersonaggio
from personaggi.transazioni_evento import evento_aperto_in_corso, gioco_live_consentito, gioco_stato_evento

User = get_user_model()


class TransazioniEventoGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.create(
            slug="kor35-evento-gate",
            nome="Kor35 Evento Gate",
            is_default=True,
            is_base=True,
            attiva=True,
        )
        cls.tipologia = TipologiaPersonaggio.objects.create(nome="Standard Gate Test")
        cls.user = User.objects.create_user(username="gate_user", password="x")
        cls.pg = Personaggio.objects.create(
            nome="PG Gate",
            proprietario=cls.user,
            campagna=cls.campagna,
            tipologia=cls.tipologia,
        )
        now = timezone.now()
        cls.evento = Evento.objects.create(
            titolo="Evento Test Gate",
            data_inizio=now + timedelta(days=2),
            data_fine=now + timedelta(days=3),
        )

    def setUp(self):
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_senza_evento_aperto_transazioni_bloccate(self):
        self.assertFalse(evento_aperto_in_corso())
        resp = self.client.post(
            reverse("personaggi:api_ruba"),
            {"oggetto_id": 1, "target_personaggio_id": self.pg.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)
        self.assertIn("evento aperto", resp.json().get("error", "").lower())

    def test_con_evento_avviato_ruba_non_bloccato_per_gate(self):
        self.evento.started_at = timezone.now()
        self.evento.ended_at = None
        self.evento.save(update_fields=["started_at", "ended_at", "updated_at"])
        self.assertTrue(evento_aperto_in_corso())
        resp = self.client.post(
            reverse("personaggi:api_ruba"),
            {"oggetto_id": 1, "target_personaggio_id": self.pg.id},
            format="json",
        )
        self.assertNotEqual(resp.status_code, 403)

    def test_messaggio_transfer_bloccato_fuori_evento(self):
        dest = Personaggio.objects.create(
            nome="PG Dest",
            proprietario=User.objects.create_user(username="dest", password="y"),
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        resp = self.client.post(
            reverse("personaggi:messaggio-send"),
            {
                "destinatario_id": dest.id,
                "mittente_personaggio_id": self.pg.id,
                "titolo": "Test",
                "testo": "Ciao",
                "crediti_da_inviare": 10,
                "oggetti_ids": [],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 400)
        payload = resp.json()
        detail = payload.get("detail") or payload.get("non_field_errors")
        if isinstance(detail, list):
            detail = detail[0] if detail else ""
        self.assertIn("evento aperto", str(detail).lower())

    def test_messaggio_solo_testo_consentito_fuori_evento(self):
        dest = Personaggio.objects.create(
            nome="PG Dest 2",
            proprietario=User.objects.create_user(username="dest2", password="y"),
            campagna=self.campagna,
            tipologia=self.tipologia,
        )
        resp = self.client.post(
            reverse("personaggi:messaggio-send"),
            {
                "destinatario_id": dest.id,
                "mittente_personaggio_id": self.pg.id,
                "titolo": "Test",
                "testo": "Solo testo",
                "crediti_da_inviare": 0,
                "oggetti_ids": [],
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)

    def test_api_gioco_evento_stato(self):
        resp = self.client.get(reverse("personaggi:api_gioco_evento_stato"))
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertFalse(data["evento_aperto"])
        self.assertFalse(data["transazioni_giocatore_abilitate"])
        self.assertFalse(data["azioni_live_abilitate"])

        self.evento.started_at = timezone.now()
        self.evento.save(update_fields=["started_at", "updated_at"])
        stato = gioco_stato_evento()
        self.assertTrue(stato["evento_aperto"])
        self.assertEqual(stato["evento_titolo"], "Evento Test Gate")

    def test_staff_campagna_bypass_inter_evento(self):
        staff_user = User.objects.create_user(username="staff_gate", password="x")
        CampagnaUtente.objects.create(
            user=staff_user,
            campagna=self.campagna,
            ruolo=CAMPAGNA_ROLE_STAFFER,
            attivo=True,
        )
        self.assertFalse(evento_aperto_in_corso())
        self.assertTrue(
            gioco_live_consentito(user=staff_user, campagna=self.campagna)
        )
        self.client.force_authenticate(user=staff_user)
        resp = self.client.post(
            reverse("personaggi:api_ruba"),
            {
                "oggetto_id": 1,
                "target_personaggio_id": self.pg.id,
                "personaggio_id": self.pg.id,
            },
            format="json",
            HTTP_X_CAMPAGNA=self.campagna.slug,
        )
        self.assertNotEqual(resp.status_code, 403)
