"""Test modernizzazione messaggistica (conversazioni, reply, unread campagna)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

from personaggi.models import (
    CAMPAGNA_ROLE_STAFFER,
    Campagna,
    CampagnaUtente,
    LetturaMessaggio,
    Messaggio,
    Personaggio,
)


User = get_user_model()


class MessagingModernizationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.campagna = Campagna.objects.filter(slug="kor35").first() or Campagna.objects.create(
            slug="kor35", nome="KOR35", attiva=True, is_default=True
        )
        cls.other_campagna = Campagna.objects.create(
            slug="altra-msg-test", nome="Altra", attiva=True
        )

        cls.player = User.objects.create_user(username="msg_player", password="x")
        cls.peer = User.objects.create_user(username="msg_peer", password="x")
        cls.staffer = User.objects.create_user(username="msg_staffer", password="x")
        CampagnaUtente.objects.update_or_create(
            user=cls.staffer,
            campagna=cls.campagna,
            defaults={"ruolo": CAMPAGNA_ROLE_STAFFER, "attivo": True},
        )

        cls.pg_player = Personaggio.objects.create(
            nome="PG Player", proprietario=cls.player, campagna=cls.campagna
        )
        cls.pg_peer = Personaggio.objects.create(
            nome="PG Peer", proprietario=cls.peer, campagna=cls.campagna
        )
        cls.pg_other_camp = Personaggio.objects.create(
            nome="PG Altra", proprietario=cls.player, campagna=cls.other_campagna
        )

    def _auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        client = APIClient()
        client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}", HTTP_X_CAMPAGNA="kor35")
        return client

    def test_conversazioni_groups_p2p_sent_and_received(self):
        client = self._auth(self.player)
        Messaggio.objects.create(
            mittente_personaggio=self.pg_peer,
            destinatario_personaggio=self.pg_player,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Ciao",
            testo="Ricevuto",
            campagna=self.campagna,
        )
        Messaggio.objects.create(
            mittente_personaggio=self.pg_player,
            destinatario_personaggio=self.pg_peer,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Re",
            testo="Inviato",
            campagna=self.campagna,
        )
        resp = client.get(
            f"/api/personaggi/api/messaggi/conversazioni/?personaggio_id={self.pg_player.id}"
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["conversazione_id"], f"pg_{self.pg_peer.id}")
        self.assertEqual(len(data[0]["messaggi"]), 2)

    def test_rispondi_creates_indv_not_staff_for_p2p(self):
        client = self._auth(self.player)
        original = Messaggio.objects.create(
            mittente_personaggio=self.pg_peer,
            destinatario_personaggio=self.pg_player,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Ping",
            testo="Hey",
            campagna=self.campagna,
        )
        resp = client.post(
            f"/api/personaggi/api/messaggi/{original.id}/rispondi/",
            {
                "personaggio_id": self.pg_player.id,
                "testo": "Pong",
            },
            format="json",
        )
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["tipo_messaggio"], Messaggio.TIPO_INDIVIDUALE)
        self.assertFalse(body.get("is_staff_message"))

    def test_unread_scoped_to_active_campaign(self):
        client = self._auth(self.player)
        msg = Messaggio.objects.create(
            mittente_personaggio=self.pg_peer,
            destinatario_personaggio=self.pg_other_camp,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Altra camp",
            testo="x",
            campagna=self.other_campagna,
        )
        LetturaMessaggio.objects.filter(messaggio=msg).delete()

        Messaggio.objects.create(
            mittente_personaggio=self.pg_peer,
            destinatario_personaggio=self.pg_player,
            tipo_messaggio=Messaggio.TIPO_INDIVIDUALE,
            titolo="Questa camp",
            testo="y",
            campagna=self.campagna,
        )

        resp = client.get("/api/personaggi/api/messaggi/unread_counts/")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        ids = {r["personaggio_id"] for r in data["by_character"]}
        self.assertIn(self.pg_player.id, ids)
        self.assertNotIn(self.pg_other_camp.id, ids)

    def test_staff_inbox_accessible_to_campaign_staffer(self):
        client = self._auth(self.staffer)
        Messaggio.objects.create(
            mittente_personaggio=self.pg_player,
            tipo_messaggio=Messaggio.TIPO_STAFF,
            titolo="Aiuto",
            testo="Serve staff",
            is_staff_message=True,
            campagna=self.campagna,
        )
        resp = client.get("/api/personaggi/api/staff/messages/")
        self.assertEqual(resp.status_code, 200)
        self.assertGreaterEqual(len(resp.json()), 1)

    def test_push_url_relative_in_signal_helpers(self):
        from personaggi.signals import _strip_html_preview
        from social.mention_notifications import instafame_deep_link_path

        self.assertEqual(instafame_deep_link_path(post_id=12), "/app/social?post=12")
        self.assertIn("ciao", _strip_html_preview("<p>ciao <b>mondo</b></p>"))
