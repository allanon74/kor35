"""Test modelli messaggio staff, invio evento, pool sorteggio pesato e ack priorità."""

from datetime import timedelta
from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from gestione_plot.models import Evento
from gestione_plot.staff_dashboard_layout import KNOWN_STAFF_TOOL_IDS, default_staff_dashboard_layout
from personaggi.models import (
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    Messaggio,
    MessaggioModelloStaff,
    Personaggio,
    PersonaggioPool,
    PersonaggioPoolMembro,
    PersonaggioPoolSorteggioEsito,
    TipologiaPersonaggio,
)
from personaggi.pool_sorteggio import campiona_pesato, peso_sorteggio, render_placeholders


class PesoSorteggioUnitTests(TestCase):
    def test_zero_sorteggi_peso_uno(self):
        self.assertEqual(peso_sorteggio(0.8, 0), 1.0)

    def test_due_sorteggi_fattore_08(self):
        self.assertAlmostEqual(peso_sorteggio(0.8, 2), 0.64, places=6)

    def test_fattore_uno_non_cambia(self):
        self.assertEqual(peso_sorteggio(1.0, 9), 1.0)

    def test_fattore_maggiore_di_uno_aumenta(self):
        self.assertAlmostEqual(peso_sorteggio(1.25, 2), 1.5625, places=6)

    def test_campiona_rispetta_k(self):
        items = [(i, 1.0) for i in range(10)]
        scelti = campiona_pesato(items, 3)
        self.assertEqual(len(scelti), 3)
        self.assertEqual(len(set(scelti)), 3)

    def test_placeholder_sostituzione(self):
        out = render_placeholders("Ciao {{ nome_personaggio }}", {"nome_personaggio": "Maria"})
        self.assertEqual(out, "Ciao Maria")


class StaffPoolPgApiTests(TestCase):
    def setUp(self):
        self.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True, is_base=True
        )
        self.staff = User.objects.create_user(username="pool_staff", password="x")
        CampagnaUtente.objects.update_or_create(
            user=self.staff,
            campagna=self.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_STAFFER, "attivo": True},
        )
        self.player = User.objects.create_user(
            username="maria_user", password="x", first_name="Maria", last_name="Rossi"
        )
        self.player2 = User.objects.create_user(username="luca_user", password="x", first_name="Luca")
        self.pg = Personaggio.objects.create(
            nome="Maria PG", proprietario=self.player, campagna=self.campagna
        )
        self.pg2 = Personaggio.objects.create(
            nome="Luca PG", proprietario=self.player2, campagna=self.campagna
        )
        self.png_tipo = TipologiaPersonaggio.objects.create(nome="PNG-test-pool", giocante=False)
        self.png = Personaggio.objects.create(
            nome="Servo PNG", proprietario=self.staff, campagna=self.campagna, tipologia=self.png_tipo
        )
        now = timezone.now()
        self.evento = Evento.objects.create(
            titolo="Live test",
            data_inizio=now,
            data_fine=now + timedelta(days=2),
        )
        self.evento.partecipanti.add(self.pg)
        token, _ = Token.objects.get_or_create(user=self.staff)
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}", HTTP_X_CAMPAGNA="kor35")

    def test_tool_nel_layout_default(self):
        self.assertIn("pool-pg", KNOWN_STAFF_TOOL_IDS)
        layout = default_staff_dashboard_layout()
        comm = layout["groups"][3]["tool_ids"]
        self.assertIn("pool-pg", comm)

    def test_modello_crud_e_invio_evento_individuale(self):
        res = self.client.post(
            "/api/personaggi/api/staff/messaggi-modelli/",
            {"nome": "Welcome", "titolo": "Ciao", "testo": "<p>Benvenuto</p>"},
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        mid = res.json()["id"]
        self.assertTrue(MessaggioModelloStaff.objects.filter(pk=mid).exists())

        res = self.client.post(
            "/api/personaggi/api/messaggi/staff/evento-invio/",
            {
                "evento_id": self.evento.id,
                "titolo": "Avviso",
                "testo": "<p>Messaggio a {{nome_personaggio}}</p>",
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        self.assertEqual(res.json()["inviati"], 1)
        msg = Messaggio.objects.get(destinatario_personaggio=self.pg, titolo="Avviso")
        self.assertEqual(msg.tipo_messaggio, Messaggio.TIPO_INDIVIDUALE)
        self.assertTrue(msg.is_staff_message)

        inbox = APIClient()
        ptoken, _ = Token.objects.get_or_create(user=self.player)
        inbox.credentials(HTTP_AUTHORIZATION=f"Token {ptoken.key}", HTTP_X_CAMPAGNA="kor35")
        listed = inbox.get(f"/api/personaggi/api/messaggi/?personaggio_id={self.pg.id}")
        self.assertEqual(listed.status_code, 200)
        payload = listed.json()
        rows = payload if isinstance(payload, list) else payload.get("results") or []
        ids = [m["id"] for m in rows]
        self.assertIn(msg.id, ids)

    def test_pool_sorteggio_pesato_e_ack(self):
        res = self.client.post(
            "/api/personaggi/api/staff/pool-pg/",
            {
                "nome": "Plot A",
                "sorteggio_min": 1,
                "sorteggio_max": 1,
                "fattore_peso": "0.8",
                "messaggio_titolo": "Estratto {{nome_personaggio}}",
                "messaggio_testo": "<p>Ciao {{nome_giocatore}}</p>",
                "invio_prioritario": True,
                "escludi_png": True,
            },
            format="json",
        )
        self.assertEqual(res.status_code, 201, res.content)
        pool_id = res.json()["id"]
        self.client.post(
            f"/api/personaggi/api/staff/pool-pg/{pool_id}/membri/",
            {"personaggio_id": self.pg.id, "attivo": True},
            format="json",
        )
        self.client.post(
            f"/api/personaggi/api/staff/pool-pg/{pool_id}/membri/",
            {"personaggio_id": self.pg2.id, "attivo": True},
            format="json",
        )
        lista = self.client.get(
            f"/api/personaggi/api/staff/pool-pg/{pool_id}/personaggi/?evento_id={self.evento.id}"
        )
        self.assertEqual(lista.status_code, 200)
        rows = lista.json()["results"]
        self.assertEqual(rows[0]["id"], self.pg.id)
        self.assertTrue(rows[0]["iscritto_evento"])
        png_ids = [r["id"] for r in rows]
        self.assertNotIn(self.png.id, png_ids)

        with patch("personaggi.views_pool_pg.campiona_pesato", return_value=[self.pg]):
            draw = self.client.post(
                f"/api/personaggi/api/staff/pool-pg/{pool_id}/sorteggia/",
                {},
                format="json",
            )
        self.assertEqual(draw.status_code, 201, draw.content)
        body = draw.json()
        self.assertEqual(body["n_estratti"], 1)
        self.assertEqual(body["esiti"][0]["personaggio_id"], self.pg.id)
        esito_id = body["esiti"][0]["id"]
        msg = Messaggio.objects.get(pk=body["esiti"][0]["messaggio_id"])
        self.assertIn("Maria PG", msg.titolo)
        self.assertIn("Maria Rossi", msg.testo)

        counts = self.client.get(f"/api/personaggi/api/staff/pool-pg/{pool_id}/conteggi/")
        self.assertEqual(counts.status_code, 200)
        by_id = {r["id"]: r for r in counts.json()["results"]}
        self.assertEqual(by_id[self.pg.id]["sorteggi_count"], 1)
        self.assertAlmostEqual(by_id[self.pg.id]["peso"], 0.8, places=5)
        self.assertAlmostEqual(by_id[self.pg2.id]["peso"], 1.0, places=5)

        player_client = APIClient()
        ptoken, _ = Token.objects.get_or_create(user=self.player)
        player_client.credentials(HTTP_AUTHORIZATION=f"Token {ptoken.key}", HTTP_X_CAMPAGNA="kor35")
        pending = player_client.get(
            f"/api/personaggi/api/sorteggio-ack/pending/?personaggio_id={self.pg.id}"
        )
        self.assertEqual(pending.status_code, 200)
        self.assertEqual(len(pending.json()), 1)
        ack = player_client.post(
            f"/api/personaggi/api/sorteggio-ack/{esito_id}/conferma/",
            {
                "personaggio_id": self.pg.id,
                "dispositivo": {"platform": "Linux", "screen": "390x844", "native": False},
            },
            format="json",
        )
        self.assertEqual(ack.status_code, 200, ack.content)
        esito = PersonaggioPoolSorteggioEsito.objects.get(pk=esito_id)
        self.assertIsNotNone(esito.confermato_at)
        self.assertEqual(esito.confermato_dispositivo.get("platform"), "Linux")

        pending2 = player_client.get(
            f"/api/personaggi/api/sorteggio-ack/pending/?personaggio_id={self.pg.id}"
        )
        self.assertEqual(pending2.json(), [])

    def test_nuovo_pg_resta_disattivo(self):
        pool = PersonaggioPool.objects.create(nome="Esistente", campagna=self.campagna)
        PersonaggioPoolMembro.objects.create(pool=pool, personaggio=self.pg, attivo=True)
        nuovo = Personaggio.objects.create(
            nome="Nuovo", proprietario=self.player, campagna=self.campagna
        )
        lista = self.client.get(f"/api/personaggi/api/staff/pool-pg/{pool.id}/personaggi/")
        rows = {r["id"]: r for r in lista.json()["results"]}
        self.assertTrue(rows[self.pg.id]["attivo"])
        self.assertFalse(rows[nuovo.id]["attivo"])
        self.assertAlmostEqual(peso_sorteggio(Decimal("0.8"), 0), 1.0)
